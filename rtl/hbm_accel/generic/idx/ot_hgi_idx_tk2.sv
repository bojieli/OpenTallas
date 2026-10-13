`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.TOPK engine tk2 (el1013 redesign-idx, 2026-10-13): the production shape of IDX.TOPK (DS route.top6:
// n 384, k 6, ascending ids) built from scratch for k <= 8 and a unit inner stride.  No SRAM, no heap.
//
//   reader   A is prefetched sector by sector on the unit's VM packet client: up to 4 requests outstanding (reads and
//            writes share the 4; the responses come back in request order, a 4-entry kind queue tells them apart), into
//            a 4-entry sector FIFO.
//   S1       the FIFO head sector is taken in two phases (words 0-3, then 4-7): per lane one word a cycle, registered
//            as {valid, key, nz, id}.  key = the FP32 value as an unsigned total order with -0 folded onto +0 (the
//            golden compares as numbers: -0 == +0, ties to the lowest index); nz remembers a -0 so the R value keeps
//            its bit pattern.  A NaN among the row's words fails the record closed (no output of that row is written).
//   lanes    4 sorted register lists of 8 entries; each inserts its one word a cycle: 8 parallel compares against the
//            registered entries + a one-position shift insert.  Within a lane the ids arrive ascending, so a strict
//            value compare keeps the lowest index on ties.
//   merge    after the row's last word the lanes shift out their first k entries one a cycle (4 k cycles) into the
//            final 8-entry list (total order: value descending, id ascending).
//   order    one cycle: every final entry's rank among the k (order = 1: by id, 28 id compares; order = 0: its slot);
//            one cycle: the k results placed by rank (one-hot AND-OR); then O (ids, U32) and R (values, FP32, when
//            present) are rotated to their word offset and written as WHOLE-SECTOR VM writes with byte masks (one write
//            a touched sector, at most two a stream).
//   rows     m rows back to back (row r at a_base + r a_str, outputs at o_base + r o_str / r_base + r r_str).
// done / fault pulse once every issued request has been answered (the outputs are in VM when done rises).
// MUT (bench): 1 the ascending order ranks by score instead of id; 2 ties go to the HIGHER index; 3 the merge skips
// lane 3.  Each must FAIL a bench whose vectors exercise it.
module ot_hgi_idx_tk2_list #(
    parameter integer IDW = 20,
    parameter integer FULL = 0,          // 1: ids are not monotonic at the input -> the tie compare includes the id
    parameter integer TIEHI = 0          // bench mutant: ties to the higher index
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   clr,
    input  wire                   sh,       // shift the head out
    input  wire                   ins_v,
    input  wire [31:0]            ins_key,
    input  wire                   ins_nz,
    input  wire [IDW-1:0]         ins_id,
    output wire [8*(IDW+34)-1:0]  e         // entry i = {v, key 32, nz, id}; entry 0 = the best
);
    localparam integer EW = IDW + 34;
    reg [7:0] ev; reg [EW-2:0] ed [0:7];
    wire [7:0] beats;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_e
        wire [31:0] ek = ed[g][IDW+32:IDW+1];
        wire [IDW-1:0] ei = ed[g][IDW-1:0];
        wire tie = (FULL != 0) ? (ins_key == ek && (TIEHI != 0 ? ins_id > ei : ins_id < ei))
                               : (TIEHI != 0 && ins_key == ek);
        assign beats[g] = !ev[g] || ins_key > ek || tie;
        assign e[g*EW +: EW] = {ev[g], ed[g]};
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) ev[g] <= 1'b0;
            else if (clr) ev[g] <= 1'b0;
            else if (sh) ev[g] <= (g == 7) ? 1'b0 : ev[g + (g == 7 ? 0 : 1)];
            else if (ins_v && beats[g]) ev[g] <= (g != 0 && beats[g - (g == 0 ? 0 : 1)]) ? ev[g - (g == 0 ? 0 : 1)] : 1'b1;
        end
        always @(posedge clk) begin
            if (sh) begin if (g != 7) ed[g] <= ed[g + (g == 7 ? 0 : 1)]; end
            else if (ins_v && beats[g])
                ed[g] <= (g != 0 && beats[g - (g == 0 ? 0 : 1)]) ? ed[g - (g == 0 ? 0 : 1)] : {ins_key, ins_nz, ins_id};
        end
    end endgenerate
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
    localparam [3:0] E_IDLE = 4'd0, E_SET1 = 4'd1, E_SET2 = 4'd2, E_FEED = 4'd3, E_FLUSH = 4'd4, E_MERGE = 4'd5,
                     E_MFL = 4'd6, E_RANK = 4'd7, E_PK1 = 4'd8, E_PKO = 4'd9, E_WI = 4'd10, E_PKR = 4'd11,
                     E_NEXT = 4'd12, E_WAIT = 4'd13;
    reg [3:0] st; reg flt;
    // ---------------------------------------------------------------- VM packet client (<= 4 outstanding, in order)
    reg [337:0] vmq_t; assign vmq = vmq_t;
    reg [2:0] fl_n; reg [3:0] fl_k; reg [1:0] fl_h, fl_t;
    wire rsp    = vmr[273] && fl_n != 3'd0;
    wire rsp_rd = rsp && !fl_k[fl_h];
    wire slot   = fl_n < 3'd4;
    // ---------------------------------------------------------------- read issuer + sector FIFO
    reg [1:0] i_st;                                  // 0 stopped, 1 row setup, 2 issuing
    reg [19:0] i_row; reg [17:0] i_rb; reg [14:0] i_sec, i_end;
    wire [17:0] i_le = i_rb + n[17:0] - 18'd1;
    reg [2:0] q_res, q_cnt; reg [1:0] q_h, q_t; reg [255:0] q_dat [0:3];
    wire wr_want = st == E_WI;
    wire rd_iss  = i_st == 2'd2 && slot && !wr_want && q_res < 3'd4;
    wire wr_iss  = wr_want && slot;
    // ---------------------------------------------------------------- feeder (S1)
    reg [19:0] c_row; reg [17:0] c_rb, c_le, o_rb, r_rb;
    reg [2:0] c_off, c_lastw; reg c_ph, c_last; reg [14:0] c_cnt; reg [IDW:0] c_col0;
    wire feed    = st == E_FEED && q_cnt != 3'd0;
    wire end_sec = c_ph || (c_last && !c_lastw[2]);
    wire c_pop   = feed && end_sec;
    wire [255:0] hd = q_dat[q_h];
    reg [3:0] s1_v; reg [31:0] s1_key [0:3]; reg [3:0] s1_nz; reg [IDW-1:0] s1_id [0:3]; reg s1_nan, f_nan;
    reg [3:0] f_v; reg [31:0] f_w [0:3]; reg [3:0] f_isnan; reg [IDW:0] f_idx [0:3];
    integer l;
    always @* begin
        for (l = 0; l < 4; l = l + 1) begin : fw
            reg [2:0] w; w = {c_ph, l[1:0]};
            f_w[l] = hd[32 * w +: 32];
            f_v[l] = feed && w >= c_off && (!c_last || w <= c_lastw);
            f_isnan[l] = f_w[l][30:23] == 8'hff && f_w[l][22:0] != 23'd0;
            f_idx[l] = c_col0 + {{(IDW-2){1'b0}}, w};
        end
    end
    // ---------------------------------------------------------------- lanes, merge, final list
    reg [1:0] m_lane; reg [3:0] m_cnt; reg cand_v; reg [EW-1:0] cand;
    wire [8*EW-1:0] le [0:3]; wire [8*EW-1:0] fe;
    wire lclr = st == E_RANK;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_lane
        ot_hgi_idx_tk2_list #(.IDW(IDW), .FULL(0), .TIEHI(MUT == 2 ? 1 : 0)) u_l (.clk(clk), .rst_n(rst_n), .clr(lclr),
            .sh(st == E_MERGE && m_lane == g[1:0]), .ins_v(s1_v[g]), .ins_key(s1_key[g]), .ins_nz(s1_nz[g]),
            .ins_id(s1_id[g]), .e(le[g]));
    end endgenerate
    ot_hgi_idx_tk2_list #(.IDW(IDW), .FULL(1), .TIEHI(MUT == 2 ? 1 : 0)) u_f (.clk(clk), .rst_n(rst_n), .clr(st == E_PK1 || (st == E_IDLE && go)),
        .sh(1'b0), .ins_v(cand_v && cand[EW-1]), .ins_key(cand[IDW+32:IDW+1]), .ins_nz(cand[IDW]),
        .ins_id(cand[IDW-1:0]), .e(fe));
    wire [1:0] last_lane = (MUT == 3) ? 2'd2 : 2'd3;
    // ---------------------------------------------------------------- order (rank) and placement
    reg [7:0] fv; reg [31:0] fk [0:7]; reg fz [0:7]; reg [IDW-1:0] fi [0:7];
    reg [2:0] rk_c [0:7]; reg [2:0] rk [0:7];
    reg [IDW-1:0] pk_id [0:7]; reg [31:0] pk_val [0:7];
    reg [IDW-1:0] o_w [0:7]; reg [31:0] r_w [0:7];
    integer a, b;
    always @* begin
        for (a = 0; a < 8; a = a + 1) begin
            fv[a] = fe[a*EW + EW - 1]; fk[a] = fe[a*EW + IDW + 1 +: 32]; fz[a] = fe[a*EW + IDW]; fi[a] = fe[a*EW +: IDW];
        end
        for (a = 0; a < 8; a = a + 1) begin
            rk_c[a] = 3'd0;
            if (!order) rk_c[a] = a[2:0];
            else for (b = 0; b < 8; b = b + 1)
                if (b != a && b[3:0] < k &&
                    ((MUT == 1) ? (fk[b] < fk[a] || (fk[b] == fk[a] && b > a)) : (fi[b] < fi[a])))
                    rk_c[a] = rk_c[a] + 3'd1;
        end
        for (a = 0; a < 8; a = a + 1) begin
            pk_id[a] = {IDW{1'b0}}; pk_val[a] = 32'd0;
            for (b = 0; b < 8; b = b + 1)
                if (b[3:0] < k && rk[b] == a[2:0]) begin
                    pk_id[a] = pk_id[a] | fi[b];
                    pk_val[a] = pk_val[a] | (fz[b] ? 32'h8000_0000 : fk[b][31] ? {1'b0, fk[b][30:0]} : ~fk[b]);
                end
        end
    end
    // ---------------------------------------------------------------- sector writer
    reg [255:0] win; reg [15:0] wm; reg [14:0] wsec; reg w_b, w_isr;
    wire [7:0]  kmask = 8'hff >> (4'd8 - k);
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

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_IDLE; flt <= 1'b0; done <= 1'b0; fault <= 1'b0; vmq_t <= 338'd0;
            fl_n <= 3'd0; fl_k <= 4'd0; fl_h <= 2'd0; fl_t <= 2'd0;
            i_st <= 2'd0; q_res <= 3'd0; q_cnt <= 3'd0; q_h <= 2'd0; q_t <= 2'd0;
            s1_v <= 4'd0; s1_nan <= 1'b0; f_nan <= 1'b0; cand_v <= 1'b0; w_b <= 1'b0; w_isr <= 1'b0;
            c_ph <= 1'b0; c_last <= 1'b0; m_lane <= 2'd0; m_cnt <= 4'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq_t[337] <= 1'b0;
            // ---- client bookkeeping
            fl_n <= fl_n + ((rd_iss || wr_iss) ? 3'd1 : 3'd0) - (rsp ? 3'd1 : 3'd0);
            if (rd_iss || wr_iss) begin fl_k[fl_t] <= wr_iss; fl_t <= fl_t + 2'd1; end
            if (rsp) fl_h <= fl_h + 2'd1;
            if (rsp_rd) begin q_dat[q_t] <= vmr[255:0]; q_t <= q_t + 2'd1; end
            q_res <= q_res + (rd_iss ? 3'd1 : 3'd0) - (c_pop ? 3'd1 : 3'd0);
            q_cnt <= q_cnt + (rsp_rd ? 3'd1 : 3'd0) - (c_pop ? 3'd1 : 3'd0);
            if (c_pop) q_h <= q_h + 2'd1;
            // ---- read issuer
            if (i_st == 2'd1) begin i_sec <= i_rb[17:3]; i_end <= i_le[17:3]; i_st <= 2'd2; end
            if (rd_iss) begin
                vmq_t <= {1'b1, 1'b0, {12'd0, i_sec, 5'd0}, 256'd0, 32'd0, 16'h0904};
                if (i_sec == i_end) begin
                    if (i_row + 20'd1 == m) i_st <= 2'd0;
                    else begin i_row <= i_row + 20'd1; i_rb <= i_rb + a_str; i_st <= 2'd1; end
                end else i_sec <= i_sec + 15'd1;
            end
            // ---- S1: one word a lane a cycle
            s1_v <= f_v;
            s1_nan <= |(f_v & f_isnan);
            if (s1_nan) f_nan <= 1'b1;
            for (l = 0; l < 4; l = l + 1) begin
                s1_key[l] <= f_w[l][31] ? ((f_w[l][30:0] == 31'd0) ? 32'h8000_0000 : ~f_w[l]) : {1'b1, f_w[l][30:0]};
                s1_nz[l]  <= f_w[l][31] && f_w[l][30:0] == 31'd0;
                s1_id[l]  <= f_idx[l][IDW-1:0];
            end
            cand_v <= st == E_MERGE;
            case (m_lane)
                2'd0: cand <= le[0][EW-1:0]; 2'd1: cand <= le[1][EW-1:0];
                2'd2: cand <= le[2][EW-1:0]; default: cand <= le[3][EW-1:0];
            endcase
            // ---- row engine
            case (st)
                E_IDLE: if (go) begin
                    flt <= 1'b0; f_nan <= 1'b0; c_row <= 20'd0; c_rb <= a_base; o_rb <= o_base; r_rb <= r_base;
                    q_res <= 3'd0; q_cnt <= 3'd0; q_h <= 2'd0; q_t <= 2'd0;
                    if (k == 4'd0 || k > 4'd8 || n < {16'd0, k} || m == 20'd0) begin flt <= 1'b1; st <= E_WAIT; end
                    else begin i_row <= 20'd0; i_rb <= a_base; i_st <= 2'd1; st <= E_SET1; end
                end
                E_SET1: begin c_le <= c_rb + n[17:0] - 18'd1; st <= E_SET2; end
                E_SET2: begin
                    c_off <= c_rb[2:0]; c_ph <= c_rb[2]; c_col0 <= {(IDW+1){1'b0}} - {{(IDW-2){1'b0}}, c_rb[2:0]};
                    c_cnt <= c_le[17:3] - c_rb[17:3]; c_last <= c_le[17:3] == c_rb[17:3]; c_lastw <= c_le[2:0];
                    st <= E_FEED;
                end
                E_FEED: if (feed) begin
                    if (end_sec) begin
                        c_ph <= 1'b0; c_off <= 3'd0; c_col0 <= c_col0 + {{(IDW-3){1'b0}}, 4'd8};
                        c_cnt <= c_cnt - 15'd1; c_last <= c_cnt == 15'd1;
                        if (c_last) st <= E_FLUSH;
                    end else c_ph <= 1'b1;
                end
                E_FLUSH: begin m_lane <= 2'd0; m_cnt <= 4'd0; st <= E_MERGE; end      // S1 lands in the lanes
                E_MERGE: begin
                    if (m_cnt + 4'd1 == k) begin
                        m_cnt <= 4'd0; m_lane <= m_lane + 2'd1;
                        if (m_lane == last_lane) st <= E_MFL;
                    end else m_cnt <= m_cnt + 4'd1;
                end
                E_MFL: st <= E_RANK;                                                  // the last candidate lands
                E_RANK: begin
                    for (a = 0; a < 8; a = a + 1) rk[a] <= rk_c[a];
                    if (f_nan || !fv[k[2:0] - 3'd1]) begin flt <= 1'b1; i_st <= 2'd0; st <= E_WAIT; end
                    else st <= E_PK1;
                end
                E_PK1: begin
                    for (a = 0; a < 8; a = a + 1) begin o_w[a] <= pk_id[a]; r_w[a] <= pk_val[a]; end
                    st <= E_PKO;
                end
                E_PKO, E_PKR: begin
                    win <= pk_rot[511:256]; wm <= {8'd0, kmask} << pk_off;
                    wsec <= (st == E_PKR) ? r_rb[17:3] : o_rb[17:3]; w_isr <= st == E_PKR; w_b <= 1'b0; st <= E_WI;
                end
                E_WI: if (wr_iss) begin
                    vmq_t <= {1'b1, 1'b1, {12'd0, ws_now, 5'd0}, win, bm_now, 16'h0905};
                    if (!w_b && wm[15:8] != 8'd0) w_b <= 1'b1;
                    else st <= (has_r && !w_isr) ? E_PKR : E_NEXT;
                end
                E_NEXT: begin
                    if (c_row + 20'd1 == m) st <= E_WAIT;
                    else begin
                        c_row <= c_row + 20'd1; c_rb <= c_rb + a_str; o_rb <= o_rb + o_str; r_rb <= r_rb + r_str;
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
