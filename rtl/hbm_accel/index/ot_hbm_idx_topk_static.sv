`timescale 1ns/1ps
`default_nettype none
// Static IDX.TOPK (H-IDX 2026-10-15). Successor of ot_hgi_idx_tk2 (historical: VM packet client with up to four
// requests outstanding, an in-order kind queue and a sector FIFO). Every VM read, every lane word, every select
// round and every VM write sits on an edge fixed by the descriptor; nothing waits for data, credits or ready.
// Arithmetic is unchanged from the closed tk2: eight ot_hgi_idx_tk2_lane sorted lists (two-stage insert), a
// registered 8>4>2>1 tournament, the 8x8 id-rank compare and the one-hot placement.
//
// Ports. Reads use the INDEX VM read group of the SW slice (8 banks, direct, bank samples n+1 and answers n+7;
// this engine captures at n+8, the ot_hbm_idx_vm_static face timing). Writes use the slice packet client
// ('idx' record, cq338/cr274) through ot_vms_hub_static: one whole-sector write with byte masks per edge.
//
// Compiler timeline. G = the edge that samples go (the descriptor is sampled with it; no hold needed).
//   illegal descriptor (k 0 or > 8, n < k, m 0, a non-mirror read outside sid, O/R outside sid, o_mirror = 1:
//       mirror output visibility needs the ring acknowledgement calendar, not part of this version):
//       fault pulse after G+1, no VM traffic.
//   S_0 = G+3. Row r: rb = a_base + r a_str, sec0 = rb>>3, ns = ((rb+n-1)>>3) - sec0 + 1.
//   read j < ns: rq registered at S_r+2j (sector sec0+j, bank (sec0+j)%8), bank samples S_r+2j+1,
//       capture S_r+2j+8, lane word S_r+2j+9.  F = S_r + 2(ns-1) + 9.
//   select k rounds: last sample F+3+4k; RK1 F+4+4k, RK2, PK1, PKO = P = F+7+4k.
//   writes W_i = P+1+i, i < nw: O sector(s) then R sector(s) (two when the k words cross a sector boundary).
//       cq registered at W_i, client_seq = i; the hub samples W_i+1 (calendar: bank_enable/bank_client then).
//       cr is sampled into the pin register at W_i+ACK and compared at W_i+ACK+1.
//   S_{r+1} = W_{nw-1} + 3.  done (or fault) pulse after W_last + ACK + 1.
// A NaN score in row r faults the record (hgi_sim u_idx_topk: rows before r stand, row r and later write nothing):
// their writes still occupy their slots with zero byte masks (the
// calendar is unchanged), and the record ends with fault on the same edge done would rise.
// MUT (bench): 1 ascending order ranks by score; 2 ties to the higher index; 3 select skips lanes 3/7;
//              4 capture one edge early; 5 the second sector of a split output is not written.
module ot_hbm_idx_topk_static #(
    parameter integer MUT = 0,
    parameter integer IDW = 20,
    parameter integer ACK = 12      // measured: cq at W, hub W+1, bank W+3, echo W+9, response W+10, cr pin W+12
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sid,
    input  wire          go,
    input  wire [3:0]    k,
    input  wire          order,
    input  wire [19:0]   n,
    input  wire [19:0]   m,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,     // word address {sid2,row10,bank3,word3}
    input  wire [17:0]   a_str,
    input  wire          o_mirror,
    input  wire [17:0]   o_base,
    input  wire [17:0]   o_str,
    input  wire          has_r,
    input  wire [17:0]   r_base,
    input  wire [17:0]   r_str,
    output reg  [135:0]  vm_rq,      // eight {valid, mirror/global_sector15}
    input  wire [2055:0] vm_rr,
    output reg  [337:0]  cq,         // {v, we, byte_addr32, data256, byte_mask32, tag16}
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,         // {v, tag16, we, data256}
    output reg           busy,
    output reg           done,
    output reg           fault
);
    localparam integer EW = IDW + 34;
    localparam [4:0] E_IDLE=0, E_CHK=1, E_ROW=2, E_RD=3, E_DR=4, E_FL1=5, E_FL2=6, E_FL3=7, E_SEL=8, E_RK1=9,
                     E_RK2=10, E_PK1=11, E_PKO=12, E_WR=13, E_NEXT=14, E_END=15;
    integer l, a, b;
    genvar g;
    // ------------------------------------------------------------ descriptor (sampled with go)
    reg [3:0] k_q; reg order_q, has_r_q, am_q, om_q; reg [19:0] n_q, m_q;
    reg [17:0] a_base_q, a_str_q, o_base_q, o_str_q, r_base_q, r_str_q;
    always @(posedge clk) if (go && !busy) begin
        k_q <= k; order_q <= order; has_r_q <= has_r; am_q <= a_mirror; om_q <= o_mirror; n_q <= n; m_q <= m;
        a_base_q <= a_base; a_str_q <= a_str; o_base_q <= o_base; o_str_q <= o_str; r_base_q <= r_base; r_str_q <= r_str;
    end
    reg [4:0] st; reg [3:0] cnt; reg flt, f_nan, s_inv;
    reg [19:0] c_row; reg [17:0] c_rb, c_le, o_rb, r_rb;
    reg [14:0] i_sec; reg [14:0] i_left; reg i_tgl, i_first;
    // ------------------------------------------------------------ fixed read pipeline (face timing n+1 / n+7 / n+8)
    // info {v, bank3, first, last, off3, lastw3}
    reg [11:0] dp [0:8];
    wire [11:0] di = dp[(MUT == 4) ? 6 : 7];
    reg cap_v, cap_first, cap_last; reg [2:0] cap_off, cap_lastw; reg [255:0] cap_d;
    wire rd_now = st == E_RD && !i_tgl;
    wire rd_last = rd_now && i_left == 15'd0;
    wire [2:0] i_off = i_first ? c_rb[2:0] : 3'd0;
    wire [2:0] i_lw  = c_le[2:0];
    wire rsid_bad = !am_q && i_sec[14:13] != sid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vm_rq <= 136'd0; cap_v <= 1'b0;
            for (integer d = 0; d < 9; d = d + 1) dp[d] <= 12'd0;
        end else begin
            vm_rq <= 136'd0;
            for (integer d = 1; d < 9; d = d + 1) dp[d] <= dp[d-1];
            dp[0] <= 12'd0;
            if (rd_now && !rsid_bad) begin
                vm_rq[17*i_sec[2:0] +: 17] <= {1'b1, am_q, i_sec};
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_off, i_lw};
            end
            cap_v <= di[11];
        end
    end
    always @(posedge clk) begin
        cap_d <= vm_rr[257*di[10:8] +: 256];
        {cap_first, cap_last, cap_off, cap_lastw} <= di[7:0];
    end
    // any response on a bank this engine did not reserve, or a reserved one missing, is a schedule fault
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (l = 0; l < 8; l = l + 1)
            if (vm_rr[257*l+256] != (di[11] && di[10:8] == 3'(l))) rd_bad = 1'b1;
    end
    // ------------------------------------------------------------ S1 feed: one sector of eight words per two edges
    reg [IDW:0] col0;
    wire [IDW:0] col_now = cap_first ? ({(IDW+1){1'b0}} - {{(IDW-2){1'b0}}, cap_off}) : col0;
    reg [7:0] s1_v; reg [31:0] s1_key [0:7]; reg [7:0] s1_nz; reg [IDW-1:0] s1_id [0:7]; reg s1_nan;
    reg [7:0] f_v; reg [31:0] f_w [0:7]; reg [7:0] f_isnan; reg [IDW:0] f_idx [0:7];
    always @* for (l = 0; l < 8; l = l + 1) begin
        f_w[l] = cap_d[32*l +: 32];
        f_v[l] = cap_v && (!cap_first || l[2:0] >= cap_off) && (!cap_last || l[2:0] <= cap_lastw);
        f_isnan[l] = f_w[l][30:23] == 8'hff && f_w[l][22:0] != 23'd0;
        f_idx[l] = col_now + {{(IDW-2){1'b0}}, l[2:0]};
    end
    always @(posedge clk) begin
        if (cap_v) col0 <= col_now + {{(IDW-3){1'b0}}, 4'd8};
        for (l = 0; l < 8; l = l + 1) begin
            s1_key[l] <= f_w[l][31] ? ((f_w[l][30:0] == 31'd0) ? 32'h8000_0000 : ~f_w[l]) : {1'b1, f_w[l][30:0]};
            s1_nz[l]  <= f_w[l][31] && f_w[l][30:0] == 31'd0;
            s1_id[l]  <= f_idx[l][IDW-1:0];
        end
    end
    // ------------------------------------------------------------ lanes (closed tk2 lane, unchanged)
    wire [7:0] l_sh; wire [EW-1:0] lh [0:7];
    wire lclr = st == E_RK1 || st == E_CHK;
    generate for (g = 0; g < 8; g = g + 1) begin : g_lane
        ot_hgi_idx_tk2_lane #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u_l (.clk(clk), .rn(rst_n), .clr(lclr),
            .sh(l_sh[g]), .ins_v(s1_v[g]), .ins_key(s1_key[g]), .ins_nz(s1_nz[g]), .ins_id(s1_id[g]), .head(lh[g]));
    end endgenerate
    // ------------------------------------------------------------ tournament (as tk2)
    function automatic better(input [EW-1:0] x, input [EW-1:0] y);
        better = x[EW-1] && (!y[EW-1] || x[IDW+32:IDW+1] > y[IDW+32:IDW+1] ||
                 (x[IDW+32:IDW+1] == y[IDW+32:IDW+1] && ((MUT == 2) ? x[IDW-1:0] > y[IDW-1:0] : x[IDW-1:0] < y[IDW-1:0])));
    endfunction
    reg [EW-1:0] t1 [0:3]; reg [3:0] t1_s; reg [EW-1:0] t2 [0:1]; reg [3:0] t2_l; reg [EW-1:0] t3; reg [2:0] t3_l;
    reg [1:0] s_ph; reg [3:0] s_cnt;
    generate for (g = 0; g < 8; g = g + 1) begin : g_sh
        assign l_sh[g] = st == E_SEL && s_ph == 2'd3 && t3[EW-1] && t3_l == g[2:0];
    end endgenerate
    reg [EW-1:0] hx [0:7];
    always @* for (l = 0; l < 8; l = l + 1) hx[l] = (MUT == 3 && (l % 4) == 3) ? {EW{1'b0}} : lh[l];
    // ------------------------------------------------------------ rank and placement (as tk2)
    reg [31:0] fk [0:7]; reg fz [0:7]; reg [IDW-1:0] fi [0:7];
    reg [7:0] cm [0:7]; reg [2:0] rk [0:7]; reg [2:0] rk_c [0:7];
    reg [IDW-1:0] pk_id [0:7]; reg [31:0] pk_val [0:7];
    reg [IDW-1:0] o_w [0:7]; reg [31:0] r_w [0:7];
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
    // ------------------------------------------------------------ static writer: O and R packed in the same edge
    wire [7:0] kmask = 8'hff >> (4'd8 - k_q);
    wire [255:0] o_flat, r_flat;
    generate for (g = 0; g < 8; g = g + 1) begin : g_flat
        assign o_flat[g*32 +: 32] = {{(32-IDW){1'b0}}, o_w[g]};
        assign r_flat[g*32 +: 32] = r_w[g];
    end endgenerate
    wire [511:0] o_rot = {o_flat, o_flat} << {o_rb[2:0], 5'd0};
    wire [511:0] r_rot = {r_flat, r_flat} << {r_rb[2:0], 5'd0};
    wire [15:0] o_wm = {8'd0, kmask} << o_rb[2:0];
    wire [15:0] r_wm = {8'd0, kmask} << r_rb[2:0];
    // write list: up to four {sector15, wordmask8}; data selects O or R
    reg [2:0] nw, wi; reg [14:0] wl_sec [0:3]; reg [7:0] wl_wm [0:3]; reg [3:0] wl_isr;
    reg [255:0] w_o, w_r; reg wsid_bad;
    function automatic [31:0] bmask(input [7:0] wm);
        for (integer w = 0; w < 8; w = w + 1) bmask[4*w +: 4] = {4{wm[w]}};
    endfunction
    // ------------------------------------------------------------ write acknowledgement check (fixed edge)
    reg [2:0] ap [0:ACK];            // {expected, seq2}
    reg cr_v; reg [15:0] cr_tag; reg cr_we;
    wire [2:0] ax = ap[ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h0244, ax[1:0]} || !cr_we));
    reg wr_now;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cr_v <= 1'b0;
            for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0;
        end else begin
            cr_v <= cr[273];
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
            ap[0] <= {wr_now, cq_seq};
        end
    always @(posedge clk) begin cr_tag <= cr[272:257]; cr_we <= cr[256]; end
    // ------------------------------------------------------------ datapath registers (no reset)
    always @(posedge clk) begin
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
        if (st == E_RK2) for (a = 0; a < 8; a = a + 1) rk[a] <= order_q ? rk_c[a] : a[2:0];
        if (st == E_PK1) for (a = 0; a < 8; a = a + 1) begin o_w[a] <= pk_id[a]; r_w[a] <= pk_val[a]; end
        if (st == E_PKO) begin
            w_o <= o_rot[511:256]; w_r <= r_rot[511:256];
            wl_sec[0] <= o_rb[17:3]; wl_wm[0] <= o_wm[7:0]; wl_isr[0] <= 1'b0;
            if (o_wm[15:8] != 8'd0) begin
                wl_sec[1] <= o_rb[17:3] + 15'd1; wl_wm[1] <= o_wm[15:8]; wl_isr[1] <= 1'b0;
                wl_sec[2] <= r_rb[17:3]; wl_wm[2] <= r_wm[7:0]; wl_isr[2] <= 1'b1;
                wl_sec[3] <= r_rb[17:3] + 15'd1; wl_wm[3] <= r_wm[15:8]; wl_isr[3] <= 1'b1;
            end else begin
                wl_sec[1] <= r_rb[17:3]; wl_wm[1] <= r_wm[7:0]; wl_isr[1] <= 1'b1;
                wl_sec[2] <= r_rb[17:3] + 15'd1; wl_wm[2] <= r_wm[15:8]; wl_isr[2] <= 1'b1;
            end
            nw <= 3'd1 + ((o_wm[15:8] != 8'd0) ? 3'd1 : 3'd0)
                  + (has_r_q ? 3'd1 + ((r_wm[15:8] != 8'd0) ? 3'd1 : 3'd0) : 3'd0);
        end
    end
    // ------------------------------------------------------------ control: a fixed-length sequencer
    wire [14:0] w_sec = wl_sec[wi[1:0]];
    wire wkill = flt || f_nan || s_inv || (MUT == 5 && wi == 3'd1 && nw == 3'd2);
    wire w_bad_sid = !om_q && w_sec[14:13] != sid;
    wire legal = k >= 4'd1 && k <= 4'd8 && n >= {16'd0, k} && m != 20'd0 &&
                 (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid) &&
                 !o_mirror && o_base[17:16] == sid && (!has_r || r_base[17:16] == sid);
    reg legal_q;
    always @(posedge clk) if (go && !busy) legal_q <= legal;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; flt <= 1'b0; f_nan <= 1'b0; s_inv <= 1'b0;
            cq <= 338'd0; cq_seq <= 2'd0; s1_v <= 8'd0; s1_nan <= 1'b0; wr_now <= 1'b0; wi <= 3'd0; cnt <= 4'd0;
            i_tgl <= 1'b0; s_ph <= 2'd0; s_cnt <= 4'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0;
            s1_v <= f_v; s1_nan <= |(f_v & f_isnan);
            if (s1_nan) f_nan <= 1'b1;
            if (busy && (rd_bad || ack_bad) && st != E_CHK) flt <= 1'b1;
            if (rd_now && rsid_bad) flt <= 1'b1;
            case (st)
                E_IDLE: if (go) begin busy <= 1'b1; st <= E_CHK; end
                E_CHK: begin                                              // G+1: row-0 setup (= E_NEXT for row 0)
                    flt <= 1'b0; f_nan <= 1'b0; s_inv <= 1'b0; c_row <= 20'd0;
                    c_rb <= a_base_q; c_le <= a_base_q + n_q[17:0] - 18'd1; o_rb <= o_base_q; r_rb <= r_base_q;
                    if (!legal_q) begin fault <= 1'b1; busy <= 1'b0; st <= E_IDLE; end
                    else st <= E_ROW;
                end
                E_ROW: begin
                    i_sec <= c_rb[17:3]; i_left <= c_le[17:3] - c_rb[17:3]; i_tgl <= 1'b0; i_first <= 1'b1;
                    st <= E_RD;
                end
                E_RD: begin
                    i_tgl <= !i_tgl;
                    if (rd_now) begin
                        i_sec <= i_sec + 15'd1; i_left <= i_left - 15'd1; i_first <= 1'b0;
                        if (rd_last) begin cnt <= 4'd8; st <= E_DR; end
                    end
                end
                E_DR: if (cnt == 4'd0) st <= E_FL1; else cnt <= cnt - 4'd1;
                E_FL1: st <= E_FL2;
                E_FL2: st <= E_FL3;
                E_FL3: begin s_ph <= 2'd0; s_cnt <= 4'd0; st <= E_SEL; end
                E_SEL: begin
                    s_ph <= s_ph + 2'd1;
                    if (s_ph == 2'd3) begin
                        if (!t3[EW-1]) s_inv <= 1'b1;
                        s_cnt <= s_cnt + 4'd1;
                        if (s_cnt + 4'd1 == k_q) st <= E_RK1;
                    end
                end
                E_RK1: st <= E_RK2;
                E_RK2: st <= E_PK1;
                E_PK1: st <= E_PKO;
                E_PKO: begin wi <= 3'd0; st <= E_WR; end
                E_WR: begin                                               // W_i = P+1+i
                    wr_now <= 1'b1;
                    cq <= {1'b1, 1'b1, 11'd0, om_q, w_sec, 5'd0, wl_isr[wi[1:0]] ? w_r : w_o,
                           (wkill || w_bad_sid) ? 32'd0 : bmask(wl_wm[wi[1:0]]), {14'h0244, wi[1:0]}};
                    if (w_bad_sid) flt <= 1'b1;
                    cq_seq <= wi[1:0];
                    wi <= wi + 3'd1;
                    if (wi + 3'd1 == nw) st <= E_NEXT;
                end
                E_NEXT: begin                                             // W_last+1
                    if (c_row + 20'd1 == m_q) begin cnt <= 4'(ACK - 1); st <= E_END; end
                    else begin
                        c_row <= c_row + 20'd1; c_rb <= c_rb + a_str_q; c_le <= c_le + a_str_q;
                        o_rb <= o_rb + o_str_q; r_rb <= r_rb + r_str_q; st <= E_ROW;
                    end
                end
                E_END: if (cnt == 4'd0) begin                             // W_last + ACK + 1
                    done <= !(flt || f_nan || s_inv || ack_bad); fault <= flt || f_nan || s_inv || ack_bad;
                    busy <= 1'b0; st <= E_IDLE;
                end else cnt <= cnt - 4'd1;
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
