`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.TOPK engine tk2 (el1013 redesign-idx, 2026-10-13; v2 = the hardened-tile form): the production shape of
// IDX.TOPK (DS route.top6: n 384, k 6, ascending ids) built from scratch for k <= 8 and a unit inner stride.
// No SRAM, no heap, no compare tree deeper than ONE comparator a stage.
//
//   pins     every input lands in a flop (go, the operands, the VM response), every output leaves a flop.
//   reader   A is prefetched sector by sector on the unit's VM packet client: up to 4 requests outstanding (reads and
//            writes share the 4; the responses come back in request order, a 4-entry kind queue tells them apart), into
//            a 4-entry sector FIFO.
//   S1       the FIFO head sector is taken whole, one word a lane (8 lanes), every OTHER cycle (= the client's read
//            rate), registered as {valid, key, nz, id}.  key = the FP32 value as an unsigned total order with -0 folded
//            onto +0 (the golden compares as numbers: -0 == +0, ties to the lowest index); nz remembers a -0 so the R
//            value keeps its bit pattern.  A NaN among the row's words fails the record closed (no output written).
//   lanes    8 sorted register lists of 8 entries, a two-stage insert: C registers the 8 compares of the word against
//            the lane's entries, I shifts the word in.  A lane sees a word every other cycle at most, so C always
//            compares against settled entries (no forwarding).  Within a lane the ids arrive ascending, so a strict
//            value compare keeps the lowest index on ties.
//   select   k rounds of a registered 8 -> 4 -> 2 -> 1 tournament over the lane heads (total order: value descending,
//            id ascending; one comparator a stage), the winner's lane shifts (4 cycles a round).
//   order    R1 registers the 56 id compares of the k winners, R2 their ranks (order = 1: by id; order = 0: the slot),
//            PK1 the k results placed by rank (one-hot AND-OR); then O (ids, U32) and R (values, FP32, when present)
//            are rotated to their word offset and written as WHOLE-SECTOR VM writes with byte masks (one write a
//            touched sector, at most two a stream).
//   rows     m rows back to back (row r at a_base + r a_str, outputs at o_base + r o_str / r_base + r r_str).
// done / fault pulse once every issued request has been answered (the outputs are in VM when done rises).
// The operands are held from go until done / fault (the unit's record register).
// MUT (bench): 1 the ascending order ranks by score instead of id; 2 ties go to the HIGHER index; 3 the select skips
// lanes 3 and 7 (words 3 mod 4).  Each must FAIL a bench whose vectors exercise it.
module ot_hgi_idx_tk2_lane #(
    parameter integer IDW = 20,
    parameter integer TIEHI = 0          // bench mutant: ties to the higher index
) (
    input  wire            clk,
    input  wire            rn,
    input  wire            clr,
    input  wire            sh,           // shift the head out
    input  wire            ins_v,        // at most every other cycle
    input  wire [31:0]     ins_key,
    input  wire            ins_nz,
    input  wire [IDW-1:0]  ins_id,
    output wire [IDW+33:0] head          // {v, key 32, nz, id} of the best entry
);
    localparam integer EW = IDW + 34;
    reg [7:0] ev; reg [EW-2:0] ed [0:7];
    reg c_v; reg [7:0] c_b; reg [EW-2:0] c_d;                  // stage C: the registered compares and the word
    integer i;
    reg [7:0] beats;
    always @* for (i = 0; i < 8; i = i + 1)
        beats[i] = !ev[i] || ins_key > ed[i][IDW+32:IDW+1] || (TIEHI != 0 && ins_key == ed[i][IDW+32:IDW+1]);
    assign head = {ev[0], ed[0]};
    always @(posedge clk or negedge rn)
        if (!rn) begin ev <= 8'd0; c_v <= 1'b0; end
        else begin
            c_v <= ins_v && !clr;
            if (clr) ev <= 8'd0;
            else if (sh) ev <= {1'b0, ev[7:1]};
            else if (c_v) for (i = 0; i < 8; i = i + 1) if (c_b[i]) ev[i] <= (i != 0 && c_b[i == 0 ? 0 : i - 1]) ? ev[i == 0 ? 0 : i - 1] : 1'b1;
        end
    always @(posedge clk) begin
        if (ins_v) begin c_b <= beats; c_d <= {ins_key, ins_nz, ins_id}; end
        if (sh) begin for (i = 0; i < 7; i = i + 1) ed[i] <= ed[i + 1]; end
        else if (c_v) for (i = 0; i < 8; i = i + 1) if (c_b[i]) ed[i] <= (i != 0 && c_b[i == 0 ? 0 : i - 1]) ? ed[i == 0 ? 0 : i - 1] : c_d;
    end
endmodule

module ot_hgi_idx_tk2 #(
    parameter integer MUT = 0,
    parameter integer IDW = 20
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,             // pulse; the operands below are held until done / fault
    input  wire [3:0]    k,              // 1..8
    input  wire          order,          // 1: ascending ids
    input  wire [19:0]   n,
    input  wire [19:0]   m,              // >= 1
    input  wire [17:0]   a_base,
    input  wire [17:0]   a_str,
    input  wire [17:0]   o_base,
    input  wire [17:0]   o_str,
    input  wire [17:0]   r_base,
    input  wire [17:0]   r_str,
    input  wire          has_r,
    output reg           done,
    output reg           fault,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr
);
    localparam integer EW = IDW + 34;
    localparam [4:0] E_IDLE = 5'd0, E_SET1 = 5'd1, E_SET2 = 5'd2, E_FEED = 5'd3, E_FL1 = 5'd4, E_FL2 = 5'd5,
                     E_FL3 = 5'd6, E_SEL = 5'd7, E_RK1 = 5'd8, E_RK2 = 5'd9, E_PK1 = 5'd10, E_PKO = 5'd11,
                     E_WI = 5'd12, E_PKR = 5'd13, E_NEXT = 5'd14, E_WAIT = 5'd15;
    integer l, a, b;
    // ---------------------------------------------------------------- reset relay, pin registers
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg go_q, vr_v; reg [255:0] vr_d;
    reg [3:0] k_q; reg order_q, has_r_q; reg [19:0] n_q, m_q; reg [17:0] a_base_q, a_str_q, o_base_q, o_str_q, r_base_q, r_str_q;
    always @(posedge clk or negedge rn) if (!rn) begin go_q <= 1'b0; vr_v <= 1'b0; end else begin go_q <= go; vr_v <= vmr[273]; end
    always @(posedge clk) begin
        vr_d <= vmr[255:0];
        k_q <= k; order_q <= order; has_r_q <= has_r; n_q <= n; m_q <= m; a_base_q <= a_base; a_str_q <= a_str;
        o_base_q <= o_base; o_str_q <= o_str; r_base_q <= r_base; r_str_q <= r_str;
    end
    reg [4:0] st; reg flt;
    // ---------------------------------------------------------------- VM packet client (<= 4 outstanding, in order)
    reg vmq_v; reg [336:0] vmq_d; assign vmq = {vmq_v, vmq_d};
    reg [2:0] fl_n; reg [3:0] fl_k; reg [1:0] fl_h, fl_t;
    wire rsp    = vr_v && fl_n != 3'd0;
    wire rsp_rd = rsp && !fl_k[fl_h];
    wire slot   = fl_n < 3'd4;
    // ---------------------------------------------------------------- read issuer + sector FIFO
    reg [1:0] i_st;                                  // 0 stopped, 1 row setup, 2 issuing
    reg [19:0] i_row; reg [17:0] i_rb; reg [14:0] i_sec, i_end;
    wire [17:0] i_le = i_rb + n_q[17:0] - 18'd1;
    reg [2:0] q_res, q_cnt; reg [1:0] q_h, q_t; reg [255:0] q_dat [0:3];
    wire wr_want = st == E_WI;
    wire rd_iss  = i_st == 2'd2 && slot && !wr_want && q_res < 3'd4;
    wire wr_iss  = wr_want && slot;
    // ---------------------------------------------------------------- feeder (S1): a sector every other cycle
    reg [19:0] c_row; reg [17:0] c_rb, c_le, o_rb, r_rb;
    reg [2:0] c_off, c_lastw; reg c_last, f_tgl; reg [14:0] c_cnt; reg [IDW:0] c_col0;
    wire feed = st == E_FEED && q_cnt != 3'd0 && !f_tgl;
    wire [255:0] hd = q_dat[q_h];
    reg [7:0] s1_v; reg [31:0] s1_key [0:7]; reg [7:0] s1_nz; reg [IDW-1:0] s1_id [0:7]; reg s1_nan, f_nan;
    reg [7:0] f_v; reg [31:0] f_w [0:7]; reg [7:0] f_isnan; reg [IDW:0] f_idx [0:7];
    always @* begin
        for (l = 0; l < 8; l = l + 1) begin
            f_w[l] = hd[32 * l +: 32];
            f_v[l] = feed && l[2:0] >= c_off && (!c_last || l[2:0] <= c_lastw);
            f_isnan[l] = f_w[l][30:23] == 8'hff && f_w[l][22:0] != 23'd0;
            f_idx[l] = c_col0 + {{(IDW-2){1'b0}}, l[2:0]};
        end
    end
    // ---------------------------------------------------------------- lanes
    wire [7:0] l_sh; wire [EW-1:0] lh [0:7];
    wire lclr = st == E_RK1 || go_q;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_lane
        ot_hgi_idx_tk2_lane #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u_l (.clk(clk), .rn(rn), .clr(lclr),
            .sh(l_sh[g]), .ins_v(s1_v[g]), .ins_key(s1_key[g]), .ins_nz(s1_nz[g]), .ins_id(s1_id[g]), .head(lh[g]));
    end endgenerate
    // ---------------------------------------------------------------- select: registered 8 -> 4 -> 2 -> 1 tournament
    // entry {v, key 32, nz, id}; a beats b: a valid and (b invalid or a.key > b.key or equal keys and the lower id)
    function automatic better(input [EW-1:0] x, input [EW-1:0] y);
        better = x[EW-1] && (!y[EW-1] || x[IDW+32:IDW+1] > y[IDW+32:IDW+1] ||
                 (x[IDW+32:IDW+1] == y[IDW+32:IDW+1] && ((MUT == 2) ? x[IDW-1:0] > y[IDW-1:0] : x[IDW-1:0] < y[IDW-1:0])));
    endfunction
    reg [EW-1:0] t1 [0:3]; reg [3:0] t1_s;          // winner of lanes {2i, 2i+1}; t1_s[i] = 1: the odd lane
    reg [EW-1:0] t2 [0:1]; reg [3:0] t2_l;          // t2_l[2i +: 2] = lane within the quad
    reg [EW-1:0] t3; reg [2:0] t3_l;
    reg [1:0] s_ph; reg [3:0] s_cnt; reg s_inv;
    // the winner's lane shifts at the end of phase 3 (decode of the registered winner lane)
    generate for (g = 0; g < 8; g = g + 1) begin : g_sh
        assign l_sh[g] = st == E_SEL && s_ph == 2'd3 && t3[EW-1] && t3_l == g[2:0];
    end endgenerate
    reg [EW-1:0] hx [0:7];
    always @* for (l = 0; l < 8; l = l + 1)
        hx[l] = (MUT == 3 && (l % 4) == 3) ? {EW{1'b0}} : lh[l];
    // ---------------------------------------------------------------- order (rank) and placement
    reg [31:0] fk [0:7]; reg fz [0:7]; reg [IDW-1:0] fi [0:7];
    reg [7:0] cm [0:7]; reg [2:0] rk [0:7];
    reg [IDW-1:0] pk_id [0:7]; reg [31:0] pk_val [0:7];
    reg [IDW-1:0] o_w [0:7]; reg [31:0] r_w [0:7];
    reg [2:0] rk_c [0:7];
    always @* begin
        for (a = 0; a < 8; a = a + 1) begin
            rk_c[a] = 3'd0;
            for (b = 0; b < 8; b = b + 1) rk_c[a] = rk_c[a] + {2'd0, cm[a][b]};
        end
        for (a = 0; a < 8; a = a + 1) begin
            pk_id[a] = {IDW{1'b0}}; pk_val[a] = 32'd0;
            for (b = 0; b < 8; b = b + 1)
                if (b[3:0] < k_q && rk[b] == a[2:0]) begin
                    pk_id[a] = pk_id[a] | fi[b];
                    pk_val[a] = pk_val[a] | (fz[b] ? 32'h8000_0000 : fk[b][31] ? {1'b0, fk[b][30:0]} : ~fk[b]);
                end
        end
    end
    // ---------------------------------------------------------------- sector writer
    reg [255:0] win; reg [15:0] wm; reg [14:0] wsec; reg w_b, w_isr;
    wire [7:0]  kmask = 8'hff >> (4'd8 - k_q);
    wire [255:0] o_flat, r_flat;
    generate for (g = 0; g < 8; g = g + 1) begin : g_flat
        assign o_flat[g*32 +: 32] = {{(32-IDW){1'b0}}, o_w[g]};
        assign r_flat[g*32 +: 32] = r_w[g];
    end endgenerate
    wire [2:0]   pk_off = (st == E_PKR) ? r_rb[2:0] : o_rb[2:0];
    wire [255:0] pk_src = (st == E_PKR) ? r_flat : o_flat;
    wire [511:0] pk_rot = {pk_src, pk_src} << {pk_off, 5'd0};
    wire [7:0]   wm_now = w_b ? wm[15:8] : wm[7:0];
    wire [31:0]  bm_now = {{4{wm_now[7]}}, {4{wm_now[6]}}, {4{wm_now[5]}}, {4{wm_now[4]}},
                           {4{wm_now[3]}}, {4{wm_now[2]}}, {4{wm_now[1]}}, {4{wm_now[0]}}};
    wire [14:0]  ws_now = wsec + {14'd0, w_b};

    // ---------------------------------------------------------------- payload registers (no reset)
    always @(posedge clk) begin
        if (rsp_rd) q_dat[q_t] <= vr_d;
        if (rd_iss) vmq_d <= {1'b0, {12'd0, i_sec, 5'd0}, 256'd0, 32'd0, 16'h0904};
        if (wr_iss) vmq_d <= {1'b1, {12'd0, ws_now, 5'd0}, win, bm_now, 16'h0905};
        for (l = 0; l < 8; l = l + 1) begin
            s1_key[l] <= f_w[l][31] ? ((f_w[l][30:0] == 31'd0) ? 32'h8000_0000 : ~f_w[l]) : {1'b1, f_w[l][30:0]};
            s1_nz[l]  <= f_w[l][31] && f_w[l][30:0] == 31'd0;
            s1_id[l]  <= f_idx[l][IDW-1:0];
        end
        // tournament (free running; the row engine samples it by phase)
        for (l = 0; l < 4; l = l + 1) begin
            t1_s[l] <= !better(hx[2*l], hx[2*l+1]);
            t1[l]   <= better(hx[2*l], hx[2*l+1]) ? hx[2*l] : hx[2*l+1];
        end
        for (l = 0; l < 2; l = l + 1) begin
            t2_l[2*l +: 2] <= better(t1[2*l], t1[2*l+1]) ? {1'b0, t1_s[2*l]} : {1'b1, t1_s[2*l+1]};
            t2[l]          <= better(t1[2*l], t1[2*l+1]) ? t1[2*l] : t1[2*l+1];
        end
        t3_l <= better(t2[0], t2[1]) ? {1'b0, t2_l[1:0]} : {1'b1, t2_l[3:2]};
        t3   <= better(t2[0], t2[1]) ? t2[0] : t2[1];
        if (st == E_SEL && s_ph == 2'd3) begin
            fk[s_cnt[2:0]] <= t3[IDW+32:IDW+1]; fz[s_cnt[2:0]] <= t3[IDW]; fi[s_cnt[2:0]] <= t3[IDW-1:0];
        end
        if (st == E_RK1)
            for (a = 0; a < 8; a = a + 1)
                for (b = 0; b < 8; b = b + 1)
                    cm[a][b] <= b != a && b[3:0] < k_q &&
                                ((MUT == 1) ? (fk[b] < fk[a] || (fk[b] == fk[a] && b > a)) : (fi[b] < fi[a]));
        if (st == E_RK2)
            for (a = 0; a < 8; a = a + 1) rk[a] <= order_q ? rk_c[a] : a[2:0];
        if (st == E_PK1) for (a = 0; a < 8; a = a + 1) begin o_w[a] <= pk_id[a]; r_w[a] <= pk_val[a]; end
        if (st == E_PKO || st == E_PKR) begin
            win <= pk_rot[511:256]; wm <= {8'd0, kmask} << pk_off;
            wsec <= (st == E_PKR) ? r_rb[17:3] : o_rb[17:3];
        end
    end
    // ---------------------------------------------------------------- control
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            st <= E_IDLE; flt <= 1'b0; done <= 1'b0; fault <= 1'b0; vmq_v <= 1'b0;
            fl_n <= 3'd0; fl_k <= 4'd0; fl_h <= 2'd0; fl_t <= 2'd0;
            i_st <= 2'd0; q_res <= 3'd0; q_cnt <= 3'd0; q_h <= 2'd0; q_t <= 2'd0;
            s1_v <= 8'd0; s1_nan <= 1'b0; f_nan <= 1'b0; w_b <= 1'b0; w_isr <= 1'b0;
            c_last <= 1'b0; f_tgl <= 1'b0; s_ph <= 2'd0; s_cnt <= 4'd0; s_inv <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq_v <= rd_iss || wr_iss;
            // ---- client bookkeeping
            fl_n <= fl_n + ((rd_iss || wr_iss) ? 3'd1 : 3'd0) - (rsp ? 3'd1 : 3'd0);
            if (rd_iss || wr_iss) begin fl_k[fl_t] <= wr_iss; fl_t <= fl_t + 2'd1; end
            if (rsp) fl_h <= fl_h + 2'd1;
            if (rsp_rd) q_t <= q_t + 2'd1;
            q_res <= q_res + (rd_iss ? 3'd1 : 3'd0) - (feed ? 3'd1 : 3'd0);
            q_cnt <= q_cnt + (rsp_rd ? 3'd1 : 3'd0) - (feed ? 3'd1 : 3'd0);
            if (feed) q_h <= q_h + 2'd1;
            // ---- read issuer
            if (i_st == 2'd1) begin i_sec <= i_rb[17:3]; i_end <= i_le[17:3]; i_st <= 2'd2; end
            if (rd_iss) begin
                if (i_sec == i_end) begin
                    if (i_row + 20'd1 == m_q) i_st <= 2'd0;
                    else begin i_row <= i_row + 20'd1; i_rb <= i_rb + a_str_q; i_st <= 2'd1; end
                end else i_sec <= i_sec + 15'd1;
            end
            // ---- S1: one word a lane, a sector every other cycle
            s1_v <= f_v;
            s1_nan <= |(f_v & f_isnan);
            if (s1_nan) f_nan <= 1'b1;
            f_tgl <= feed;
            // ---- row engine
            case (st)
                E_IDLE: if (go_q) begin
                    flt <= 1'b0; f_nan <= 1'b0; c_row <= 20'd0; c_rb <= a_base_q; o_rb <= o_base_q; r_rb <= r_base_q;
                    q_res <= 3'd0; q_cnt <= 3'd0; q_h <= 2'd0; q_t <= 2'd0;
                    if (k_q == 4'd0 || k_q > 4'd8 || n_q < {16'd0, k_q} || m_q == 20'd0) begin flt <= 1'b1; st <= E_WAIT; end
                    else begin i_row <= 20'd0; i_rb <= a_base_q; i_st <= 2'd1; st <= E_SET1; end
                end
                E_SET1: begin c_le <= c_rb + n_q[17:0] - 18'd1; st <= E_SET2; end
                E_SET2: begin
                    c_off <= c_rb[2:0]; c_col0 <= {(IDW+1){1'b0}} - {{(IDW-2){1'b0}}, c_rb[2:0]};
                    c_cnt <= c_le[17:3] - c_rb[17:3]; c_last <= c_le[17:3] == c_rb[17:3]; c_lastw <= c_le[2:0];
                    st <= E_FEED;
                end
                E_FEED: if (feed) begin
                    c_off <= 3'd0; c_col0 <= c_col0 + {{(IDW-3){1'b0}}, 4'd8};
                    c_cnt <= c_cnt - 15'd1; c_last <= c_cnt == 15'd1;
                    if (c_last) st <= E_FL1;
                end
                E_FL1: st <= E_FL2;                                                   // S1
                E_FL2: st <= E_FL3;                                                   // lane stage C
                E_FL3: begin s_ph <= 2'd0; s_cnt <= 4'd0; s_inv <= 1'b0; st <= E_SEL; end   // lane stage I: heads settled
                E_SEL: begin                                                          // ph 0 / 1 / 2: T1 / T2 / T3 load
                    s_ph <= s_ph + 2'd1;
                    if (s_ph == 2'd3) begin
                        if (!t3[EW-1]) s_inv <= 1'b1;
                        s_cnt <= s_cnt + 4'd1;
                        if (s_cnt + 4'd1 == k_q) st <= E_RK1;
                    end
                end
                E_RK1: begin
                    if (f_nan || s_inv) begin flt <= 1'b1; i_st <= 2'd0; st <= E_WAIT; end
                    else st <= E_RK2;
                end
                E_RK2: st <= E_PK1;
                E_PK1: st <= E_PKO;
                E_PKO, E_PKR: begin w_isr <= st == E_PKR; w_b <= 1'b0; st <= E_WI; end
                E_WI: if (wr_iss) begin
                    if (!w_b && wm[15:8] != 8'd0) w_b <= 1'b1;
                    else st <= (has_r_q && !w_isr) ? E_PKR : E_NEXT;
                end
                E_NEXT: begin
                    if (c_row + 20'd1 == m_q) st <= E_WAIT;
                    else begin
                        c_row <= c_row + 20'd1; c_rb <= c_rb + a_str_q; o_rb <= o_rb + o_str_q; r_rb <= r_rb + r_str_q;
                        st <= E_SET1;
                    end
                end
                E_WAIT: if (fl_n == 3'd0 && !rd_iss) begin
                    done <= !flt; fault <= flt; st <= E_IDLE;
                end
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
