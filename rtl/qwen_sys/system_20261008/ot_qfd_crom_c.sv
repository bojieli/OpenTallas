`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// q13-kvleaves 2026-10-13: the constant-ROM group tile as a THIN CLUSTER (ot_qfd_crom_gc).  The flat slot-shaped tile
// ot_qfd_crom_gr (qfd_crom_g_m5-q13a: TT -9.84 / FF -66.62, one clock root over a 550-um column of six ROM macros,
// TritonCTS insertion 430..621 ps, register-to-register skew on both checks) is cut into hard children with their own
// clock roots; the cluster holds no register and no logic:
//   ot_qfd_crom_col x3  one macro column, 2 deep: per-macro {ce, addr} pin flops (e3b), the two ROM macros, their
//                       capture flops (e4) and the depth-selected answer register (e5a) -- every macro path is local
//   ot_qfd_crom_gh  x1  N-face head: input station (e1), region decode (e2), column select (e3a), side band, output
//                       station (e5b) and faults
// Same registers, same edges as ot_qfd_crom LBS=1 RLY=1 RSTR=1 SW=8 (strobe -> q 8 edges, fault timing unchanged); the
// one re-association is the e5a lane register s_w: its WIDE / NARROW terms are registered in the column tiles (zero when
// the lane's kind is not theirs) and its QSCALE term as a flag in the head, OR-ed in front of the output station q_r.
// One column master serves wide (4 lanes x 64 b) and narrow (8 lanes x 32 b) columns: eight 32-bit answer slots, each
// with its own enable and depth bit (a wide lane drives two adjacent slots).
// Mutants (bench only): head MUT=1 (answer bit 0 flipped, as ot_qfd_crom MUT), +define+QFD_CROM_COL_MUT (slot 0 reads
// the other depth).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_crom_col
`ifndef SYNTHESIS
  #(parameter string IMG0 = "", parameter string IMG1 = "")
`endif
(
    input  wire         clk,
    input  wire [1:0]   ce_i,            // from the head: column register ce0 per depth
    input  wire [11:0]  a_i,             //                column register a0
    input  wire [7:0]   en_i,            //                slot enable (lane kind = this column's, m stage)
    input  wire [7:0]   dp_i,            //                slot depth bit (m stage)
    output reg  [255:0] sw               // e5a answer slots (0 when not enabled)
);
    reg [1:0]   ce1;
    reg [11:0]  a1_0, a1_1;              // one address register per macro, beside its pins
    reg [7:0]   c_en, c_dp;
    always @(posedge clk) begin ce1 <= ce_i; a1_0 <= a_i; a1_1 <= a_i; c_en <= en_i; c_dp <= dp_i; end
    wire [265:0] rd0, rd1;
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 u_m0 (.clk(clk), .ce_in(ce1[0]), .addr_in(a1_0), .rd_out(rd0));
    ot_rom_4096x266_m8 u_m1 (.clk(clk), .ce_in(ce1[1]), .addr_in(a1_1), .rd_out(rd1));
`else
    ot_rom_4096x266_m8 #(.INSTANCE(IMG0)) u_m0 (.clk(clk), .ce_in(ce1[0]), .addr_in(a1_0), .rd_out(rd0));
    ot_rom_4096x266_m8 #(.INSTANCE(IMG1)) u_m1 (.clk(clk), .ce_in(ce1[1]), .addr_in(a1_1), .rd_out(rd1));
`endif
    reg [255:0] cap0, cap1;
    always @(posedge clk) begin cap0 <= rd0[255:0]; cap1 <= rd1[255:0]; end
    integer s;
    always @(posedge clk)
        for (s = 0; s < 8; s = s + 1)
`ifdef QFD_CROM_COL_MUT
            sw[32*s +: 32] <= !c_en[s] ? 32'd0 : ((c_dp[s] ^ (s == 0)) ? cap1[32*s +: 32] : cap0[32*s +: 32]);
`else
            sw[32*s +: 32] <= !c_en[s] ? 32'd0 : (c_dp[s] ? cap1[32*s +: 32] : cap0[32*s +: 32]);
`endif
endmodule

module ot_qfd_crom_gh
`ifndef SYNTHESIS
  #(parameter integer MUT = 0)
`endif
(
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    crom_re,        // N face (die pins)
    input  wire [191:0]  crom_addr,
    input  wire [5:0]    crom_stage,
    input  wire [5:0]    crom_lb,
    output wire [511:0]  crom_q,
    output reg           fault,
    output reg  [1:0]    fault_code,
    // to / from the column tiles (S face): wide column 0 (lanes 0-3), wide column 1 (lanes 4-7), narrow column (lanes 0-7)
    output reg  [1:0]    w0_ce,
    output reg  [11:0]   w0_a,
    output wire [7:0]    w0_en,
    output wire [7:0]    w0_dp,
    input  wire [255:0]  w0_sw,
    output reg  [1:0]    w1_ce,
    output reg  [11:0]   w1_a,
    output wire [7:0]    w1_en,
    output wire [7:0]    w1_dp,
    input  wire [255:0]  w1_sw,
    output reg  [1:0]    n_ce,
    output reg  [11:0]   n_a,
    output wire [7:0]    n_en,
    output wire [7:0]    n_dp,
    input  wire [255:0]  n_sw
);
    localparam integer SW = 8, AW = 24, LW = 6, RW = 13, WL = 4, NL = 8, WC = 2, NC = 1;
    localparam integer QK0 = 4096, POST0 = 5376, QSCALE = 9472, ROPE0 = 9473, OSC0 = 533761, DSC0 = 537857, END = 541953,
                       HEAD = 36, HEAD_N = 4096, QKR = 20, FN_ROW0 = 5328;
    localparam [63:0] QSCALE_WORD = 64'h3db504f3_00000000;
    localparam [AW-1:0] A_QK0 = QK0, A_POST0 = POST0, A_QSC = QSCALE, A_ROPE0 = ROPE0, A_OSC0 = OSC0, A_DSC0 = DSC0,
                        A_END = END, A_HN = HEAD_N;
    localparam [RW-1:0] R_QKR = QKR, R_QKR64 = QKR + 64, R_FN0 = FN_ROW0;
    localparam [LW-1:0] S_HEAD = HEAD;
    localparam [2:0] K_ZERO = 3'd0, K_QSC = 3'd1, K_WIDE = 3'd2, K_NARROW = 3'd3, K_BAD = 3'd4;

    // ---- reset relay (ot_qfd_crom RSTR = 1) ----
    (* async_reg = "true" *) reg [1:0] rr_s;
    (* keep = "true", dont_touch = "true" *) reg [1:0] rr_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rr_s <= 2'b00; rr_q <= 2'd0; end
        else begin rr_s <= {rr_s[0], 1'b1}; rr_q <= {2{rr_s[1]}}; end
    end
    wire rst_a, rst_c;
    assign {rst_c, rst_a} = rr_q;
    // ---- e1: input station ----
    reg [SW-1:0]    re1;
    reg [SW*AW-1:0] a1;
    reg [LW-1:0]    st1;
    reg [5:0]       lb1;
    always @(posedge clk or negedge rst_a) if (!rst_a) re1 <= 0; else re1 <= crom_re;
    always @(posedge clk) begin a1 <= crom_addr; st1 <= crom_stage; lb1 <= crom_lb; end
    // ---- e2: per-lane region decode (as ot_qfd_crom) ----
    wire [RW-1:0] lbase = ({{(RW-LW){1'b0}}, st1} << 7) + ({{(RW-LW){1'b0}}, st1} << 4) + ({{(RW-LW){1'b0}}, st1} << 2);
    reg  [SW-1:0]    t_v;
    reg  [SW*3-1:0]  t_kind;
    reg  [SW*RW-1:0] t_row;
    reg  [SW-1:0]    t_rng, t_al;
    integer l;
    reg  [SW-1:0]    t_v_n, t_rng_n, t_al_n;
    reg  [SW*3-1:0]  t_kind_n;
    reg  [SW*RW-1:0] t_row_n;
    always @(*) begin
        t_v_n = 0; t_rng_n = 0; t_al_n = 0; t_kind_n = 0; t_row_n = 0;
            for (l = 0; l < SW; l = l + 1) begin : g_dec
                reg [AW-1:0] a, off;
                reg [2:0] k;
                reg [RW-1:0] r;
                reg al;
                a = a1[l*AW +: AW];
                off = 0; r = 0; al = 1'b1;
                if (st1 == S_HEAD) begin
                    if (a < A_HN) begin k = K_NARROW; off = a; r = R_FN0 + off[6 +: RW]; end
                    else k = K_BAD;
                end else if (st1 > S_HEAD) k = K_BAD;
                else if (a < A_QK0 || (a >= A_POST0 && a < A_QSC)) k = K_ZERO;
                else if (a < A_POST0) begin k = K_NARROW; off = a - A_QK0; r = lbase + off[6 +: RW]; end
                else if (a == A_QSC) k = K_QSC;
                else if (a < A_OSC0) begin k = K_WIDE; off = a - A_ROPE0; r = off[6 +: RW]; end
                else if (a < A_DSC0) begin k = K_NARROW; off = a - A_OSC0; r = lbase + R_QKR + off[6 +: RW]; end
                else if (a < A_END) begin k = K_NARROW; off = a - A_DSC0; r = lbase + R_QKR64 + off[6 +: RW]; end
                else k = K_BAD;
                if ((k == K_WIDE || k == K_NARROW) && off[5:0] != (l[5:0] + lb1)) al = 1'b0;
                t_v_n[l] = re1[l];
                t_kind_n[l*3 +: 3] = k;
                t_row_n[l*RW +: RW] = r;
                t_rng_n[l] = re1[l] && k == K_BAD;
                t_al_n[l] = re1[l] && !al;
            end
    end
    always @(posedge clk or negedge rst_a) begin
        if (!rst_a) begin t_v <= 0; t_rng <= 0; t_al <= 0; end
        else begin t_v <= t_v_n; t_rng <= t_rng_n; t_al <= t_al_n; end
    end
    always @(posedge clk) begin t_kind <= t_kind_n; t_row <= t_row_n; end
    // ---- e3: macro columns (address = first active lane's row) ----
    wire [WC-1:0]    w_ce;
    wire [WC*RW-1:0] w_row;
    wire [NC-1:0]    n_cew;
    wire [NC*RW-1:0] n_row;
    wire [WC-1:0]    w_dis;
    wire [NC-1:0]    n_dis;
    genvar g;
    generate
        for (g = 0; g < WC; g = g + 1) begin : g_wsel
            reg ce; reg [RW-1:0] row; reg dis;
            integer j;
            always @(*) begin
                ce = 1'b0; row = 0; dis = 1'b0;
                for (j = WL - 1; j >= 0; j = j - 1)
                    if (t_v[g*WL + j] && t_kind[(g*WL + j)*3 +: 3] == K_WIDE) begin ce = 1'b1; row = t_row[(g*WL + j)*RW +: RW]; end
                for (j = 0; j < WL; j = j + 1)
                    if (t_v[g*WL + j] && t_kind[(g*WL + j)*3 +: 3] == K_WIDE && t_row[(g*WL + j)*RW +: RW] != row) dis = 1'b1;
            end
            assign w_ce[g] = ce; assign w_row[g*RW +: RW] = row; assign w_dis[g] = dis;
        end
        for (g = 0; g < NC; g = g + 1) begin : g_nsel
            reg ce; reg [RW-1:0] row; reg dis;
            integer j;
            always @(*) begin
                ce = 1'b0; row = 0; dis = 1'b0;
                for (j = NL - 1; j >= 0; j = j - 1)
                    if (t_v[g*NL + j] && t_kind[(g*NL + j)*3 +: 3] == K_NARROW) begin ce = 1'b1; row = t_row[(g*NL + j)*RW +: RW]; end
                for (j = 0; j < NL; j = j + 1)
                    if (t_v[g*NL + j] && t_kind[(g*NL + j)*3 +: 3] == K_NARROW && t_row[(g*NL + j)*RW +: RW] != row) dis = 1'b1;
            end
            assign n_cew[g] = ce; assign n_row[g*RW +: RW] = row; assign n_dis[g] = dis;
        end
    endgenerate
    // e3a column registers (ot_qfd_crom RLY ce0 / a0): the column tiles' pin flops are the per-macro e3b registers
    always @(posedge clk) begin
        w0_ce <= {w_ce[0] && w_row[0*RW + 12], w_ce[0] && !w_row[0*RW + 12]}; w0_a <= w_row[0*RW +: 12];
        w1_ce <= {w_ce[1] && w_row[1*RW + 12], w_ce[1] && !w_row[1*RW + 12]}; w1_a <= w_row[1*RW +: 12];
        n_ce  <= {n_cew[0] && n_row[12], n_cew[0] && !n_row[12]};             n_a  <= n_row[0 +: 12];
    end
    // ---- per-lane side band: two relay edges (v0 / v1), then the m stage that leaves for the column tiles ----
    reg [SW-1:0]   v0, v1, dp0, dp1, m_v, c_v, s_v;
    reg [SW*3-1:0] k0, k1;
    reg [SW-1:0]   m_w, m_n, m_q, m_dpw, m_dpn, c_q, s_q;      // m stage: kind flags and depth (two copies: wide / narrow tile)
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin v0 <= 0; v1 <= 0; m_v <= 0; c_v <= 0; s_v <= 0; end
        else begin v0 <= t_v; v1 <= v0; m_v <= v1; c_v <= m_v; s_v <= c_v; end
    end
    always @(posedge clk) begin
        k0 <= t_kind; k1 <= k0;
        for (l = 0; l < SW; l = l + 1) begin
            dp0[l] <= t_row[l*RW + 12];
            m_w[l] <= (k1[l*3 +: 3] == K_WIDE); m_n[l] <= (k1[l*3 +: 3] == K_NARROW); m_q[l] <= (k1[l*3 +: 3] == K_QSC);
        end
        dp1 <= dp0; m_dpw <= dp1; m_dpn <= dp1;
        c_q <= m_q; s_q <= c_q;
    end
    // wide column g serves lanes 4g .. 4g+3, each on two adjacent 32-bit slots; the narrow column lanes 0 .. 7
    generate for (g = 0; g < 4; g = g + 1) begin : g_wmap
        assign w0_en[2*g +: 2] = {2{m_w[g]}};     assign w0_dp[2*g +: 2] = {2{m_dpw[g]}};
        assign w1_en[2*g +: 2] = {2{m_w[4 + g]}}; assign w1_dp[2*g +: 2] = {2{m_dpw[4 + g]}};
    end endgenerate
    assign n_en = m_n; assign n_dp = m_dpn;
    // ---- e5b: output station (held when not read) ----
    reg [SW*64-1:0] q_r;
    wire [SW*64-1:0] w_all = {w1_sw, w0_sw};
    always @(posedge clk)
        for (l = 0; l < SW; l = l + 1)
            if (s_v[l]) q_r[l*64 +: 64] <= w_all[l*64 +: 64] | {32'd0, n_sw[l*32 +: 32]} | (s_q[l] ? QSCALE_WORD : 64'd0);
`ifndef SYNTHESIS
    assign crom_q = (MUT != 0) ? (q_r ^ {{(SW*64-1){1'b0}}, 1'b1}) : q_r;
`else
    assign crom_q = q_r;
`endif
    // ---- faults (sticky, first cause) ----
    reg f_rng, f_al, f_dis;
    always @(posedge clk or negedge rst_a) begin
        if (!rst_a) begin
            f_rng <= 1'b0; f_al <= 1'b0; f_dis <= 1'b0; fault <= 1'b0; fault_code <= 2'd0;
        end else begin
            f_rng <= |t_rng; f_al <= |t_al; f_dis <= (|w_dis) || (|n_dis);
            if (!fault && (f_rng || f_al || f_dis)) begin
                fault <= 1'b1;
                fault_code <= f_rng ? 2'd1 : f_al ? 2'd2 : 2'd3;
            end
        end
    end
endmodule

// Die master qfd_crom_g as a thin cluster: wiring only.  IMG_LB names the simulation mask images, MUT the bench mutant.
module ot_qfd_crom_gc #(
    parameter integer IMG_LB = 0,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        crom_re,
    input  wire [8*24-1:0]   crom_addr,
    input  wire [5:0]        crom_stage,
    input  wire [5:0]        crom_lb,
    output wire [8*64-1:0]   crom_q,
    output wire              fault,
    output wire [1:0]        fault_code
);
    wire [1:0] w0_ce, w1_ce, n_ce; wire [11:0] w0_a, w1_a, n_a; wire [7:0] w0_en, w0_dp, w1_en, w1_dp, n_en, n_dp;
    wire [255:0] w0_sw, w1_sw, n_sw;
`ifndef SYNTHESIS
    ot_qfd_crom_gh #(.MUT(MUT)) u_h (
`else
    ot_qfd_crom_gh u_h (
`endif
        .clk(clk), .rst_n(rst_n), .crom_re(crom_re), .crom_addr(crom_addr), .crom_stage(crom_stage), .crom_lb(crom_lb),
        .crom_q(crom_q), .fault(fault), .fault_code(fault_code),
        .w0_ce(w0_ce), .w0_a(w0_a), .w0_en(w0_en), .w0_dp(w0_dp), .w0_sw(w0_sw),
        .w1_ce(w1_ce), .w1_a(w1_a), .w1_en(w1_en), .w1_dp(w1_dp), .w1_sw(w1_sw),
        .n_ce(n_ce), .n_a(n_a), .n_en(n_en), .n_dp(n_dp), .n_sw(n_sw));
`ifndef SYNTHESIS
    ot_qfd_crom_col #(.IMG0($sformatf("crom_w_c%0d_d0", 0 + IMG_LB / 4)), .IMG1($sformatf("crom_w_c%0d_d1", 0 + IMG_LB / 4))) u_w0 (
`else
    ot_qfd_crom_col u_w0 (
`endif
        .clk(clk), .ce_i(w0_ce), .a_i(w0_a), .en_i(w0_en), .dp_i(w0_dp), .sw(w0_sw));
`ifndef SYNTHESIS
    ot_qfd_crom_col #(.IMG0($sformatf("crom_w_c%0d_d0", 1 + IMG_LB / 4)), .IMG1($sformatf("crom_w_c%0d_d1", 1 + IMG_LB / 4))) u_w1 (
`else
    ot_qfd_crom_col u_w1 (
`endif
        .clk(clk), .ce_i(w1_ce), .a_i(w1_a), .en_i(w1_en), .dp_i(w1_dp), .sw(w1_sw));
`ifndef SYNTHESIS
    ot_qfd_crom_col #(.IMG0($sformatf("crom_n_c%0d_d0", IMG_LB / 8)), .IMG1($sformatf("crom_n_c%0d_d1", IMG_LB / 8))) u_n (
`else
    ot_qfd_crom_col u_n (
`endif
        .clk(clk), .ce_i(n_ce), .a_i(n_a), .en_i(n_en), .dp_i(n_dp), .sw(n_sw));
endmodule
