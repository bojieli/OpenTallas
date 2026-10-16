`timescale 1ns/1ps
`default_nettype none
// Static IDX.TOPK, P-ROW PIPELINED successor (H-MTP2/idx 2026-10-16). NEW additive master, same ports and the same
// descriptor / VM faces as ot_hbm_idx_topk_static (drop-in); the existing engine is unchanged.
//
// Why: the multi-position verify issues the route top-6 as ONE record of R = P rows (m = P). The existing engine runs
// rows strictly one after another and reads one sector per two edges (each tk2 lane inserts at most every other edge),
// so a row of n 384 costs 139.8 edges (measured, rtl/test/hbm_idx_rows). Here:
//   * reads issue one sector EVERY edge; sector j of a row goes to lane half (j & 1) (8 + 8 lanes), so each closed
//     tk2 lane still inserts at most every other edge;
//   * two lane banks (16 lanes each), ping-pong by row parity: row r+1 streams into bank (r+1)&1 while row r is
//     selected, ranked and written from bank r&1 (heap reset per row: a bank is cleared at its row's RK1);
//   * one 16 > 8 > 4 > 2 > 1 registered tournament (5 edges a select round), the 16 x 16 id-rank compare of the
//     selected k <= 8 (only k entries are ever compared, as tk2), one-hot placement and the static writer as before.
// Arithmetic (key transform, ordering, ties to the lower index, ascending-id placement, R values) is the tk2 / static
// engine's, unchanged.
//
// Compiler timeline (G = the edge that samples go; tools/hbm_idx_topk_rows_vectors.py replays it edge by edge):
//   reader: G+1 CHK; G+2 first ROW edge. ROW (one edge): row r's bank b = r & 1 must be free (cleared by the RK1 of
//     row r-2), else ROW repeats. RD: sector j registered on vm_rq at R_r + j (j < ns_r), bank samples +1, capture +8,
//     lane word +9. After the last sector: next row's ROW edge.
//   selector: a row's bank is FULL 12 edges after its last read edge (lane insert done + 1, as the static engine's
//     FL3). WAIT -> SEL when the current row's bank is full; SEL 5 edges a round (shift at phase 4), k rounds; RK1
//     (bank cleared), RK2, PK1, PKO; writes W_i (O then R sectors, as the static engine); NEXT; then WAIT for the
//     next row. done / fault pulse at W_last(final row) + ACK + 1.
// Faults: illegal descriptor -> fault after G+1, no traffic; NaN in row r: rows before r stand, row r and later write
// zero masks on their slots (same calendar), fault at the done edge; read / ack schedule mismatch -> fault.
// MUT (bench): 1 heap NOT reset between rows (bank cleared only at the record start); 2 row stride dropped on the read
//              side (every row re-reads row 0); 3 every sector into the even lane half (lane insert rate violated).
module ot_hbm_idx_topk_rows_static #(
    parameter integer MUT = 0,
    parameter integer IDW = 20,
    parameter integer ACK = 12
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
    input  wire [17:0]   a_base,
    input  wire [17:0]   a_str,
    input  wire          o_mirror,
    input  wire [17:0]   o_base,
    input  wire [17:0]   o_str,
    input  wire          has_r,
    input  wire [17:0]   r_base,
    input  wire [17:0]   r_str,
    output reg  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output reg  [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output reg           busy,
    output reg           done,
    output reg           fault
);
    localparam integer EW = IDW + 34;
    localparam integer NL = 16;                      // lanes per bank
    localparam [2:0] R_IDLE = 0, R_ROW = 1, R_RD = 2, R_DONE = 3;
    localparam [3:0] S_IDLE = 0, S_CHK = 1, S_WAIT = 2, S_SEL = 3, S_RK1 = 4, S_RK2 = 5, S_PK1 = 6, S_PKO = 7,
                     S_WR = 8, S_NEXT = 9, S_END = 10;
    integer l, a, b;
    genvar g;
    // ------------------------------------------------------------ descriptor (sampled with go)
    reg [3:0] k_q; reg order_q, has_r_q, am_q, om_q; reg [19:0] n_q, m_q;
    reg [17:0] a_base_q, a_str_q, o_base_q, o_str_q, r_base_q, r_str_q;
    always @(posedge clk) if (go && !busy) begin
        k_q <= k; order_q <= order; has_r_q <= has_r; am_q <= a_mirror; om_q <= o_mirror; n_q <= n; m_q <= m;
        a_base_q <= a_base; a_str_q <= a_str; o_base_q <= o_base; o_str_q <= o_str; r_base_q <= r_base; r_str_q <= r_str;
    end
    wire legal = k >= 4'd1 && k <= 4'd8 && n >= {16'd0, k} && m != 20'd0 &&
                 (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid) &&
                 !o_mirror && o_base[17:16] == sid && (!has_r || r_base[17:16] == sid);
    reg legal_q;
    always @(posedge clk) if (go && !busy) legal_q <= legal;
    // ------------------------------------------------------------ reader
    reg [2:0] rs; reg [19:0] rd_row; reg [17:0] c_rb, c_le; reg [14:0] i_sec, i_left; reg i_first, i_par;
    reg [1:0] bank_busy;
    wire rd_bank = rd_row[0];
    wire rd_now = rs == R_RD;
    wire rd_last = rd_now && i_left == 15'd0;
    wire [2:0] i_off = i_first ? c_rb[2:0] : 3'd0;
    wire [2:0] i_lw = c_le[2:0];
    wire rsid_bad = !am_q && i_sec[14:13] != sid;
    // read pipeline info {v, vmbank3, first, last, off3, lastw3, lbank, par}
    reg [13:0] dp [0:8];
    wire [13:0] di = dp[7];
    reg cap_v, cap_first, cap_last, cap_lb, cap_par; reg [2:0] cap_off, cap_lastw; reg [255:0] cap_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vm_rq <= 136'd0; cap_v <= 1'b0;
            for (integer d = 0; d < 9; d = d + 1) dp[d] <= 14'd0;
        end else begin
            vm_rq <= 136'd0;
            for (integer d = 1; d < 9; d = d + 1) dp[d] <= dp[d-1];
            dp[0] <= 14'd0;
            if (rd_now && !rsid_bad) begin
                vm_rq[17*i_sec[2:0] +: 17] <= {1'b1, am_q, i_sec};
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_off, i_lw, rd_bank, i_par};
            end
            cap_v <= di[13];
        end
    end
    always @(posedge clk) begin
        cap_d <= vm_rr[257*di[12:10] +: 256];
        {cap_first, cap_last, cap_off, cap_lastw, cap_lb, cap_par} <= di[9:0];
    end
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (l = 0; l < 8; l = l + 1)
            if (vm_rr[257*l+256] != (di[13] && di[12:10] == 3'(l))) rd_bad = 1'b1;
    end
    // ------------------------------------------------------------ S1 feed: one sector of eight words per edge
    reg [IDW:0] col0;
    wire [IDW:0] col_now = cap_first ? ({(IDW+1){1'b0}} - {{(IDW-2){1'b0}}, cap_off}) : col0;
    reg [7:0] f_v; reg [31:0] f_w [0:7]; reg [7:0] f_isnan; reg [IDW:0] f_idx [0:7];
    always @* for (l = 0; l < 8; l = l + 1) begin
        f_w[l] = cap_d[32*l +: 32];
        f_v[l] = cap_v && (!cap_first || l[2:0] >= cap_off) && (!cap_last || l[2:0] <= cap_lastw);
        f_isnan[l] = f_w[l][30:23] == 8'hff && f_w[l][22:0] != 23'd0;
        f_idx[l] = col_now + {{(IDW-2){1'b0}}, l[2:0]};
    end
    reg [31:0] s1_key [0:7]; reg [7:0] s1_nz; reg [IDW-1:0] s1_id [0:7]; reg [7:0] s1_v8; reg s1_lb, s1_par, s1_nan;
    always @(posedge clk) begin
        if (cap_v) col0 <= col_now + {{(IDW-3){1'b0}}, 4'd8};
        s1_lb <= cap_lb; s1_par <= (MUT == 3) ? 1'b0 : cap_par;
        for (l = 0; l < 8; l = l + 1) begin
            s1_key[l] <= f_w[l][31] ? ((f_w[l][30:0] == 31'd0) ? 32'h8000_0000 : ~f_w[l]) : {1'b1, f_w[l][30:0]};
            s1_nz[l]  <= f_w[l][31] && f_w[l][30:0] == 31'd0;
            s1_id[l]  <= f_idx[l][IDW-1:0];
        end
    end
    // ------------------------------------------------------------ two lane banks x 16 closed tk2 lanes
    reg [3:0] st; reg sel_bank; reg [1:0] lclr;
    wire [2*NL-1:0] l_sh; wire [EW-1:0] lh [0:2*NL-1];      // lane g = bank g / 16, lane g % 16
    generate for (g = 0; g < 2*NL; g = g + 1) begin : g_lane
        localparam integer BK = g / NL, LN = g % NL;
        wire ins = s1_v8[LN % 8] && s1_lb == BK[0] && s1_par == (LN >= 8);
        ot_hgi_idx_tk2_lane #(.IDW(IDW)) u_l (.clk(clk), .rn(rst_n), .clr(lclr[BK]),
            .sh(l_sh[g]), .ins_v(ins), .ins_key(s1_key[LN % 8]), .ins_nz(s1_nz[LN % 8]), .ins_id(s1_id[LN % 8]),
            .head(lh[g]));
    end endgenerate
    // ------------------------------------------------------------ tournament 16 > 8 > 4 > 2 > 1 (as tk2)
    function automatic better(input [EW-1:0] x, input [EW-1:0] y);
        better = x[EW-1] && (!y[EW-1] || x[IDW+32:IDW+1] > y[IDW+32:IDW+1] ||
                 (x[IDW+32:IDW+1] == y[IDW+32:IDW+1] && x[IDW-1:0] < y[IDW-1:0]));
    endfunction
    reg [EW-1:0] hx [0:NL-1];
    always @* for (l = 0; l < NL; l = l + 1) hx[l] = sel_bank ? lh[NL + l] : lh[l];
    reg [EW-1:0] t1 [0:7]; reg [7:0] t1_l;
    reg [EW-1:0] t2 [0:3]; reg [7:0] t2_l;
    reg [EW-1:0] t3 [0:1]; reg [5:0] t3_l;
    reg [EW-1:0] t4; reg [3:0] t4_l;
    reg [2:0] s_ph; reg [3:0] s_cnt;
    wire sh_now = st == S_SEL && s_ph == 3'd4 && t4[EW-1];
    generate for (g = 0; g < NL; g = g + 1) begin : g_sh
        assign l_sh[g] = sh_now && !sel_bank && t4_l == g[3:0];
        assign l_sh[NL + g] = sh_now && sel_bank && t4_l == g[3:0];
    end endgenerate
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
    // ------------------------------------------------------------ static writer (as the static engine)
    reg [17:0] o_rb, r_rb;
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
    reg [2:0] nw, wi; reg [14:0] wl_sec [0:3]; reg [7:0] wl_wm [0:3]; reg [3:0] wl_isr;
    reg [255:0] w_o, w_r;
    function automatic [31:0] bmask(input [7:0] wm);
        for (integer w = 0; w < 8; w = w + 1) bmask[4*w +: 4] = {4{wm[w]}};
    endfunction
    reg [2:0] ap [0:ACK];
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
        for (l = 0; l < 8; l = l + 1) begin
            t1_l[l] <= !better(hx[2*l], hx[2*l+1]);
            t1[l]   <= better(hx[2*l], hx[2*l+1]) ? hx[2*l] : hx[2*l+1];
        end
        for (l = 0; l < 4; l = l + 1) begin
            t2_l[2*l +: 2] <= better(t1[2*l], t1[2*l+1]) ? {1'b0, t1_l[2*l]} : {1'b1, t1_l[2*l+1]};
            t2[l]          <= better(t1[2*l], t1[2*l+1]) ? t1[2*l] : t1[2*l+1];
        end
        for (l = 0; l < 2; l = l + 1) begin
            t3_l[3*l +: 3] <= better(t2[2*l], t2[2*l+1]) ? {1'b0, t2_l[4*l +: 2]} : {1'b1, t2_l[4*l+2 +: 2]};
            t3[l]          <= better(t2[2*l], t2[2*l+1]) ? t2[2*l] : t2[2*l+1];
        end
        t4_l <= better(t3[0], t3[1]) ? {1'b0, t3_l[2:0]} : {1'b1, t3_l[5:3]};
        t4   <= better(t3[0], t3[1]) ? t3[0] : t3[1];
        if (sh_now) begin
            fk[s_cnt[2:0]] <= t4[IDW+32:IDW+1]; fz[s_cnt[2:0]] <= t4[IDW]; fi[s_cnt[2:0]] <= t4[IDW-1:0];
        end
        if (st == S_RK1)
            for (a = 0; a < 8; a = a + 1)
                for (b = 0; b < 8; b = b + 1)
                    cm[a][b] <= b != a && b[3:0] < k_q && fi[b] < fi[a];
        if (st == S_RK2) for (a = 0; a < 8; a = a + 1) rk[a] <= order_q ? rk_c[a] : a[2:0];
        if (st == S_PK1) for (a = 0; a < 8; a = a + 1) begin o_w[a] <= pk_id[a]; r_w[a] <= pk_val[a]; end
        if (st == S_PKO) begin
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
    // ------------------------------------------------------------ bank FULL token: last read edge + 12
    reg [11:0] ft_v; reg [11:0] ft_b;
    reg [1:0] full, nan_b;
    // ------------------------------------------------------------ control
    reg flt, f_nan, s_inv; reg [19:0] sel_row; reg [3:0] cnt;
    wire [14:0] w_sec = wl_sec[wi[1:0]];
    wire wkill = flt || f_nan || s_inv;
    wire w_bad_sid = !om_q && w_sec[14:13] != sid;
    always @* begin
        lclr = 2'b00;
        if (st == S_CHK) lclr = 2'b11;
        if (st == S_RK1 && MUT != 1) lclr[sel_bank] = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; rs <= R_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; flt <= 1'b0; f_nan <= 1'b0;
            s_inv <= 1'b0; cq <= 338'd0; cq_seq <= 2'd0; s1_v8 <= 8'd0; s1_nan <= 1'b0; wr_now <= 1'b0; wi <= 3'd0;
            cnt <= 4'd0; s_ph <= 3'd0; s_cnt <= 4'd0; bank_busy <= 2'b00; full <= 2'b00; nan_b <= 2'b00;
            ft_v <= 12'd0; ft_b <= 12'd0; sel_bank <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0;
            s1_v8 <= f_v; s1_nan <= |(f_v & f_isnan);
            if (s1_nan) nan_b[s1_lb] <= 1'b1;
            if (busy && (rd_bad || ack_bad) && st != S_CHK) flt <= 1'b1;
            if (rd_now && rsid_bad) flt <= 1'b1;
            // FULL token: issued on the last read edge, lands 12 edges later
            ft_v <= {ft_v[10:0], rd_last}; ft_b <= {ft_b[10:0], rd_bank};
            if (ft_v[11]) full[ft_b[11]] <= 1'b1;
            // ---------------- reader
            case (rs)
                R_ROW: if (!bank_busy[rd_bank]) begin
                    bank_busy[rd_bank] <= 1'b1;
                    i_sec <= c_rb[17:3]; i_left <= c_le[17:3] - c_rb[17:3]; i_first <= 1'b1; i_par <= 1'b0;
                    rs <= R_RD;
                end
                R_RD: begin
                    i_sec <= i_sec + 15'd1; i_left <= i_left - 15'd1; i_first <= 1'b0; i_par <= !i_par;
                    if (rd_last) begin
                        if (rd_row + 20'd1 == m_q) rs <= R_DONE;
                        else begin
                            rd_row <= rd_row + 20'd1;
                            if (MUT != 2) begin c_rb <= c_rb + a_str_q; c_le <= c_le + a_str_q; end
                            rs <= R_ROW;
                        end
                    end
                end
                default: ;
            endcase
            // ---------------- selector / writer
            case (st)
                S_IDLE: if (go) begin busy <= 1'b1; st <= S_CHK; end
                S_CHK: begin                                              // G+1
                    flt <= 1'b0; f_nan <= 1'b0; s_inv <= 1'b0; sel_row <= 20'd0; sel_bank <= 1'b0;
                    bank_busy <= 2'b00; full <= 2'b00; nan_b <= 2'b00; ft_v <= 12'd0;
                    rd_row <= 20'd0; c_rb <= a_base_q; c_le <= a_base_q + n_q[17:0] - 18'd1;
                    o_rb <= o_base_q; r_rb <= r_base_q;
                    if (!legal_q) begin fault <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                    else begin st <= S_WAIT; rs <= R_ROW; end
                end
                S_WAIT: if (full[sel_bank]) begin
                    full[sel_bank] <= 1'b0;
                    if (nan_b[sel_bank]) f_nan <= 1'b1;
                    s_ph <= 3'd0; s_cnt <= 4'd0; st <= S_SEL;
                end
                S_SEL: begin
                    s_ph <= (s_ph == 3'd4) ? 3'd0 : s_ph + 3'd1;
                    if (s_ph == 3'd4) begin
                        if (!t4[EW-1]) s_inv <= 1'b1;
                        s_cnt <= s_cnt + 4'd1;
                        if (s_cnt + 4'd1 == k_q) st <= S_RK1;
                    end
                end
                S_RK1: begin                                              // this row's bank cleared (lclr)
                    bank_busy[sel_bank] <= 1'b0; nan_b[sel_bank] <= 1'b0; st <= S_RK2;
                end
                S_RK2: st <= S_PK1;
                S_PK1: st <= S_PKO;
                S_PKO: begin wi <= 3'd0; st <= S_WR; end
                S_WR: begin
                    wr_now <= 1'b1;
                    cq <= {1'b1, 1'b1, 11'd0, om_q, w_sec, 5'd0, wl_isr[wi[1:0]] ? w_r : w_o,
                           (wkill || w_bad_sid) ? 32'd0 : bmask(wl_wm[wi[1:0]]), {14'h0244, wi[1:0]}};
                    if (w_bad_sid) flt <= 1'b1;
                    cq_seq <= wi[1:0];
                    wi <= wi + 3'd1;
                    if (wi + 3'd1 == nw) st <= S_NEXT;
                end
                S_NEXT: begin
                    if (sel_row + 20'd1 == m_q) begin cnt <= 4'(ACK - 1); st <= S_END; end
                    else begin
                        sel_row <= sel_row + 20'd1; sel_bank <= !sel_bank;
                        o_rb <= o_rb + o_str_q; r_rb <= r_rb + r_str_q; st <= S_WAIT;
                    end
                end
                S_END: if (cnt == 4'd0) begin
                    done <= !(flt || f_nan || s_inv || ack_bad); fault <= flt || f_nan || s_inv || ack_bad;
                    busy <= 1'b0; st <= S_IDLE; rs <= R_IDLE;
                end else cnt <= cnt - 4'd1;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
