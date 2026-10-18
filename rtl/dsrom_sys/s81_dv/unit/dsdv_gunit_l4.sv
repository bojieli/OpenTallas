`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l4 -- G-unit leaf L4 (2nd of 6): the HC coefficient finish.
//
// Function (tools/hdc_golden_v41.Model.hc_mixes, R-ARITH chunk8, every rounding the golden's): the golden tree above the
// slice roots, exactly -- every add one ot_dsrom_qadd, the same operands in the same association:
//   A  group (k, m) (L0's stream, one a cycle) -> the 5 level-5 nodes 20 k + 5 m + 0..4:
//        N0 = A32   N1 = (A8 + B8) + B16a   N2 = B16b + C16a   N3 = C16b + (C8 + D8)   N4 = D32
//   Q  quads of level-5 nodes -> level-7 nodes 0..19, one a cycle (3 adders)
//   T  streaming levels 8..12 (one adder each; an odd node adds its stored left sibling, the last node when even adds
//      +0: the golden's own add(x, 0) padding) -> the root
//   ss -> ot_dsrom_divc (/ 20,480) -> + eps -> ot_dsrom_rsqrt -> r;   mix_o = mul(proj_o, r), 24 multiplies
// then the launch of L5's tail with the 24 mixes and the job's {set, which, row, masks}.  mix_go (the mix phase starts)
// and launch go back to L0 (job bookkeeping).
// cw (relayed by L0): table row 62 of set cw_a[8] carries the norm eps [255:224]; relayed on to L5 (2 edges).
// Feedthroughs: the rung (L0 <-> L5), cw, sid, the HC CTL rows (L5 -> L0).
// fault (sticky): an adder / multiplier / divider / rsqrt fault, a root twice, a quad pass overrun, L5's fault.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 5 = group association
// N1 = A8 + (B8 + B16a); 7 = the r chain skips + eps.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l4 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L0)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          g_v, input wire [3:0] g_i, input wire [4:0] g_acc, input wire [319:0] g_d,
    input  wire          j_v, input wire j_set, input wire j_w, input wire [9:0] j_row, input wire [4:0] j_lm,
    input  wire [15:0]   j_sm,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output wire          hct_v, output wire [275:0] hct_b,
    output reg           mix_go_s, output reg launch_s, output reg fault,
    // N face (L5)
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           launch, output reg [767:0] mixes, output reg t_set, output reg t_w, output reg [9:0] t_row,
    output reg  [4:0]    t_lm, output reg [15:0] t_sm,
    output wire          cwo_v, output wire [9:0] cwo_a, output wire [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct5_v, input wire [275:0] hct5_b, input wire f5
);
    localparam integer V = 276, LA = 4, LM = 5, NACC = 25, NSET = 2;
    // ---------------------------------------------------------------- feedthroughs
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rst_n), .d(rs_i), .q(rn_o));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rst_n), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(277)) u_ct (.clk(clk), .rst_n(rst_n), .d({hct5_b, hct5_v}), .q({hct_b, hct_v}));
    dsdv_gunit_pass #(.W(271)) u_cw (.clk(clk), .rst_n(rst_n), .d({cw_d, cw_a, cw_v}), .q({cwo_d, cwo_a, cwo_v}));
    dsdv_gunit_pass #(.W(4)) u_sid (.clk(clk), .rst_n(rst_n), .d(sid_i), .q(sid_o));
    // ---------------------------------------------------------------- input flops
    reg o_v, wv, f5_q; reg [3:0] o_i; reg [4:0] o_acc; reg [31:0] A32, A8, B8, B16a, B16b, C16a, C16b, C8, D8, D32;
    reg aj_v, aj_set, aj_w; reg [9:0] aj_row; reg [4:0] aj_lm; reg [15:0] aj_sm; reg [9:0] wa; reg [255:0] wd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; wv <= 1'b0; f5_q <= 1'b0; aj_v <= 1'b0; end
        else begin o_v <= g_v; wv <= cw_v; f5_q <= f5; aj_v <= j_v; end
    always @(posedge clk) begin
        o_i <= g_i; o_acc <= g_acc;
        {D32, D8, C8, C16b, C16a, B16b, B16a, B8, A8, A32} <= g_d;
        aj_set <= j_set; aj_w <= j_w; aj_row <= j_row; aj_lm <= j_lm; aj_sm <= j_sm; wa <= cw_a; wd <= cw_d;
    end
    reg [31:0] eps_t [0:NSET-1];
    always @(posedge clk) if (wv && !wa[9] && wa[5:0] == 6'd62) eps_t[wa[8]] <= wd[255:224];
    // ---------------------------------------------------------------- A: level 1 / level 2 adders
    wire [31:0] p1, n2, p2, n1, n3; wire f1, f2, f3, f4, f5a;
    ot_dsrom_qadd #(.LAT(LA)) u_a1 (clk, rst_n, o_v, (MUT == 5) ? B8 : A8, (MUT == 5) ? B16a : B8, p1, f1);
    ot_dsrom_qadd #(.LAT(LA)) u_a2 (clk, rst_n, o_v, B16b, C16a, n2, f2);
    ot_dsrom_qadd #(.LAT(LA)) u_a3 (clk, rst_n, o_v, C8, D8, p2, f3);
    wire [31:0] d_a32, d_b16a, d_c16b, d_d32, d_a8; wire [8:0] d_t1; wire [LA:0] v1;
    ot_hdc_delay #(.W(160), .D(LA)) u_d1 (.clk(clk), .rst_n(rst_n), .d({A32, B16a, C16b, D32, A8}),
                                          .q({d_a32, d_b16a, d_c16b, d_d32, d_a8}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t1 (.clk(clk), .rst_n(rst_n), .d({o_i, o_acc}), .q(d_t1));
    ot_hdc_vline #(.D(LA)) u_v1 (.clk(clk), .rst_n(rst_n), .v(o_v), .vd(v1));
    ot_dsrom_qadd #(.LAT(LA)) u_a4 (clk, rst_n, v1[LA], (MUT == 5) ? d_a8 : p1, (MUT == 5) ? p1 : d_b16a, n1, f4);
    ot_dsrom_qadd #(.LAT(LA)) u_a5 (clk, rst_n, v1[LA], d_c16b, p2, n3, f5a);
    wire [31:0] e_a32, e_n2, e_d32; wire [8:0] e_t; wire [LA:0] v2;
    ot_hdc_delay #(.W(96), .D(LA)) u_d2 (.clk(clk), .rst_n(rst_n), .d({d_a32, n2, d_d32}), .q({e_a32, e_n2, e_d32}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t2 (.clk(clk), .rst_n(rst_n), .d(d_t1), .q(e_t));
    ot_hdc_vline #(.D(LA)) u_v2 (.clk(clk), .rst_n(rst_n), .v(v1[LA]), .vd(v2));
    reg [31:0] l5 [0:79];
    wire [3:0] e_i = e_t[8:5];
    always @(posedge clk) if (v2[LA]) begin
        l5[5 * e_i + 0] <= e_a32; l5[5 * e_i + 1] <= n1; l5[5 * e_i + 2] <= e_n2; l5[5 * e_i + 3] <= n3;
        l5[5 * e_i + 4] <= e_d32;
    end
    // ---------------------------------------------------------------- Q: quads -> level-7 nodes, one a cycle
    // start: DQ - 2 edges after group 0 lands in this leaf's input flop (= the one-leaf form's DQ after go_a)
    localparam integer DQ = 2 + 2 * LA;
    wire s0 = o_v && o_i == 4'd0;
    wire [DQ-2:0] qs;
    ot_hdc_vline #(.D(DQ - 2)) u_qs (.clk(clk), .rst_n(rst_n), .v(s0), .vd(qs));
    wire [4:0] q_acc0;
    ot_hdc_delay #(.W(5), .D(DQ - 2)) u_qacc (.clk(clk), .rst_n(rst_n), .d(o_acc), .q(q_acc0));
    reg q_on; reg [4:0] q_i; reg [4:0] q_acc;
    reg qr_v; reg [4:0] qr_i; reg [4:0] qr_acc; reg [31:0] q0, q1, q2, q3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_on <= 1'b0; q_i <= 5'd0; qr_v <= 1'b0; end
        else begin
            if (qs[DQ - 2]) begin q_on <= 1'b1; q_i <= 5'd0; q_acc <= q_acc0; end
            else if (q_on) begin q_i <= q_i + 5'd1; if (q_i == 5'd19) q_on <= 1'b0; end
            qr_v <= q_on; qr_i <= q_i; qr_acc <= q_acc;
        end
    always @(posedge clk) begin q0 <= l5[4 * q_i]; q1 <= l5[4 * q_i + 1]; q2 <= l5[4 * q_i + 2]; q3 <= l5[4 * q_i + 3]; end
    wire [31:0] l6a, l6b, l7; wire f6, f7, f8; wire [LA:0] vq1, vq2; wire [9:0] tq1, tq2;
    ot_dsrom_qadd #(.LAT(LA)) u_a6 (clk, rst_n, qr_v, q0, q1, l6a, f6);
    ot_dsrom_qadd #(.LAT(LA)) u_a7 (clk, rst_n, qr_v, q2, q3, l6b, f7);
    ot_hdc_vline #(.D(LA)) u_vq1 (.clk(clk), .rst_n(rst_n), .v(qr_v), .vd(vq1));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq1 (.clk(clk), .rst_n(rst_n), .d({qr_i, qr_acc}), .q(tq1));
    ot_dsrom_qadd #(.LAT(LA)) u_a8 (clk, rst_n, vq1[LA], l6a, l6b, l7, f8);
    ot_hdc_vline #(.D(LA)) u_vq2 (.clk(clk), .rst_n(rst_n), .v(vq1[LA]), .vd(vq2));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq2 (.clk(clk), .rst_n(rst_n), .d(tq1), .q(tq2));
    // ---------------------------------------------------------------- T: streaming levels 8 .. 12
    wire [5:0] t_vv; wire [32*6-1:0] t_d; wire [5*6-1:0] t_i; wire [5:0] t_l; wire [5*6-1:0] t_a; wire [4:0] t_f;
    assign t_vv[0] = vq2[LA]; assign t_d[31:0] = l7; assign t_i[4:0] = tq2[9:5]; assign t_l[0] = tq2[9:5] == 5'd19;
    assign t_a[4:0] = tq2[4:0];
    genvar lv;
    generate for (lv = 0; lv < 5; lv = lv + 1) begin : g_lv
        wire        iv = t_vv[lv];
        wire [31:0] id = t_d[32 * lv +: 32];
        wire [4:0]  ii = t_i[5 * lv +: 5], ia = t_a[5 * lv +: 5];
        wire        il = t_l[lv];
        reg  [31:0] pend;
        always @(posedge clk) if (iv && !ii[0]) pend <= id;
        wire go = iv && (ii[0] || il);
        wire [31:0] y; wire f; wire [LA:0] vv; wire [10:0] tt;
        ot_dsrom_qadd #(.LAT(LA)) u_t (clk, rst_n, go, ii[0] ? pend : id, ii[0] ? id : 32'd0, y, f);
        ot_hdc_vline #(.D(LA)) u_tv (.clk(clk), .rst_n(rst_n), .v(go), .vd(vv));
        ot_hdc_delay #(.W(11), .D(LA)) u_tt (.clk(clk), .rst_n(rst_n), .d({il, ii >> 1, ia}), .q(tt));
        assign t_vv[lv + 1] = vv[LA];
        assign t_d[32 * (lv + 1) +: 32] = y; assign t_i[5 * (lv + 1) +: 5] = tt[9:5]; assign t_a[5 * (lv + 1) +: 5] = tt[4:0];
        assign t_l[lv + 1] = tt[10];
        assign t_f[lv] = f;
    end endgenerate
    wire root_v = t_vv[5]; wire [31:0] root = t_d[32 * 5 +: 32]; wire [4:0] root_acc = t_a[5 * 5 +: 5];
    // ---------------------------------------------------------------- roots -> proj / ss -> r
    reg [31:0] proj [0:23];
    reg [24:0] rdone; reg ss_v; reg [31:0] ss; reg [31:0] eps_c;
    always @(posedge clk) if (root_v && root_acc < 5'd24) proj[root_acc] <= root;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ss_v <= 1'b0;
        else ss_v <= root_v && root_acc == 5'd24;
    always @(posedge clk) begin if (root_v) ss <= root; eps_c <= (MUT == 7) ? 32'd0 : eps_t[aj_set]; end
    wire [31:0] mq, me, rr; wire mq_v, me_v, rr_v, f_div, f_eps, f_rsq; wire [LA:0] ve;
    ot_dsrom_divc #(.F(5), .K(12)) u_div (.clk(clk), .rst_n(rst_n), .v(ss_v), .x(ss), .y(mq), .vo(mq_v), .fault(f_div));
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps_c, me, f_eps);
    assign me_v = ve[LA];
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_ok; reg [31:0] r;
    // ---------------------------------------------------------------- mix phase: 24 multiplies, then the tail launch
    reg m_on; reg [4:0] m_i; reg mm_v; reg [4:0] mm_i; reg [31:0] mm_a; reg mix_go;
    wire [31:0] my; wire f_mul; wire [LM:0] vm; wire [4:0] mi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rdone <= 25'd0; r_ok <= 1'b0; m_on <= 1'b0; mm_v <= 1'b0; mix_go <= 1'b0; mix_go_s <= 1'b0;
            launch <= 1'b0; launch_s <= 1'b0; fault <= 1'b0;
        end else begin
            mix_go <= 1'b0; launch <= 1'b0;
            if (root_v) rdone <= rdone | (25'd1 << root_acc);
            if (rr_v) begin r_ok <= 1'b1; r <= rr; end
            if (!m_on && rdone == {NACC{1'b1}} && r_ok) begin
                m_on <= 1'b1; m_i <= 5'd0; mix_go <= 1'b1; rdone <= 25'd0; r_ok <= 1'b0;
                t_set <= aj_set; t_w <= aj_w; t_row <= aj_row; t_lm <= aj_lm; t_sm <= aj_sm;
            end
            if (m_on) begin m_i <= m_i + 5'd1; if (m_i == 5'd23) m_on <= 1'b0; end
            mm_v <= m_on; mm_i <= m_i;
            if (vm[LM] && mi == 5'd23) launch <= 1'b1;
            mix_go_s <= mix_go; launch_s <= launch;
            if (f1 | f2 | f3 | f4 | f5a | f6 | f7 | f8 | (|t_f) | f_div | f_eps | f_rsq | f_mul | f5_q
                | (root_v && rdone[root_acc]) | (mix_go && !aj_v) | (qs[DQ - 2] && q_on && q_i != 5'd19)) fault <= 1'b1;
        end
    always @(posedge clk) mm_a <= proj[m_i];
    ot_hdc_qmul_lat #(.LAT(LM)) u_mul (clk, rst_n, mm_v, mm_a, r, my, f_mul);
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mm_v), .vd(vm));
    ot_hdc_delay #(.W(5), .D(LM)) u_mi (.clk(clk), .rst_n(rst_n), .d(mm_i), .q(mi));
    always @(posedge clk) if (vm[LM]) mixes[32 * mi +: 32] <= my;
endmodule
