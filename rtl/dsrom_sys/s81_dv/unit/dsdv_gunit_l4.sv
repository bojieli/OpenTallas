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
// S81U-GUNIT3 (10-17): the r chain (ss -> divc -> + eps -> rsqrt, 9.9k flops) moved to the E-side leaf dsdv_gunit_l4r
// (the one-leaf L4 was 21,174 sinks, TT insertion 436 ps: clock-rule FAIL).  Seam: ss / eps leave from this leaf's own
// registers, r / its valid / L4r's fault come back into input flops (+3 edges on the r chain; the mix phase waits for
// r_ok as before, so only the HC latency moves).  The 24 mixes leave one a cycle as they are made (mx_v / mx_i / mx_y,
// 38 pins, not a 768-bit register + bus): L5 assembles them; launch leaves with the last one as before.
// S81U-GUNIT6 (10-17, native pin rules, NATIVE-2 lessons): cw is captured ONCE (wv / wa / wd are both the eps-table
// input flops and the first stage of the cw feedthrough; cwo_* = their output flops, still 2 edges), so no cw pin feeds
// two captures; the N launch output flop has a kept internal twin (launch_k) that feeds launch_s, so each output flop
// drives only its own pin.  0 edges.
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
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): hct5_b / hct_b = packed CTL rows; cwo_a packed {a[9:8], a[5:0]} (L5 reads no a[7:6])
    output wire          hct_v, output wire [169:0] hct_b,
    output reg           mix_go_s, output reg launch_s, output reg fault,
    // N face (L5)
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           launch, output reg mx_v, output reg [4:0] mx_i, output reg [31:0] mx_y, output reg t_set, output reg t_w, output reg [9:0] t_row,
    output reg  [4:0]    t_lm, output reg [15:0] t_sm,
    output reg           cwo_v, output reg [7:0] cwo_a, output reg [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct5_v, input wire [169:0] hct5_b, input wire f5,
    // E face (L4r: the r chain)
    output reg           ss_v, output reg [31:0] ss, output reg [31:0] eps_c,
    input  wire          r_v, input wire [31:0] r_y, input wire r_f
);
    localparam integer V = 276, LA = 4, LM = 5, NACC = 25, NSET = 2;
    // reset relay (S81U-GUNIT4): the rst_n port drives only ot_rst_relay; 4 kept region copies (each <= ~256
    // reset loads, no port net spans the leaf).  Release is 3 edges after the port (transaction-level exact).
    wire [3:0] rq;
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- feedthroughs
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rq[0]), .d(rs_i), .q(rn_o));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rq[0]), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(171)) u_ct (.clk(clk), .rst_n(rq[0]), .d({hct5_b, hct5_v}), .q({hct_b, hct_v}));
    dsdv_gunit_pass #(.W(4)) u_sid (.clk(clk), .rst_n(rq[0]), .d(sid_i), .q(sid_o));
    // ---------------------------------------------------------------- input flops
    reg o_v, wv, f5_q; reg [3:0] o_i; reg [4:0] o_acc; reg [31:0] A32, A8, B8, B16a, B16b, C16a, C16b, C8, D8, D32;
    reg aj_v, aj_set, aj_w; reg [9:0] aj_row; reg [4:0] aj_lm; reg [15:0] aj_sm; reg [9:0] wa; reg [255:0] wd;
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin o_v <= 1'b0; wv <= 1'b0; f5_q <= 1'b0; aj_v <= 1'b0; end
        else begin o_v <= g_v; wv <= cw_v; f5_q <= f5; aj_v <= j_v; end
    always @(posedge clk) begin
        o_i <= g_i; o_acc <= g_acc;
        {D32, D8, C8, C16b, C16a, B16b, B16a, B8, A8, A32} <= g_d;
        aj_set <= j_set; aj_w <= j_w; aj_row <= j_row; aj_lm <= j_lm; aj_sm <= j_sm; wa <= {cw_a[7:6], 2'd0, cw_a[5:0]}; wd <= cw_d;
    end
    always @(posedge clk or negedge rq[0]) if (!rq[0]) cwo_v <= 1'b0; else cwo_v <= wv;   // cw feedthrough stage 2
`ifdef OT_RTLC_MUT_L4   // RTLC bench mutant: cwo_a packs a[6] in place of a[0]
    always @(posedge clk) begin cwo_a <= {wa[9:8], wa[5:1], wa[6]}; cwo_d <= wd; end
`else
    always @(posedge clk) begin cwo_a <= {wa[9:8], wa[5:0]}; cwo_d <= wd; end
`endif
    reg [31:0] eps_t [0:NSET-1];
    always @(posedge clk) if (wv && !wa[9] && wa[5:0] == 6'd62) eps_t[wa[8]] <= wd[255:224];
    // ---------------------------------------------------------------- A: level 1 / level 2 adders
    wire [31:0] p1, n2, p2, n1, n3; wire f1, f2, f3, f4, f5a;
    ot_dsrom_qadd #(.LAT(LA)) u_a1 (clk, rq[1], o_v, (MUT == 5) ? B8 : A8, (MUT == 5) ? B16a : B8, p1, f1);
    ot_dsrom_qadd #(.LAT(LA)) u_a2 (clk, rq[1], o_v, B16b, C16a, n2, f2);
    ot_dsrom_qadd #(.LAT(LA)) u_a3 (clk, rq[1], o_v, C8, D8, p2, f3);
    wire [31:0] d_a32, d_b16a, d_c16b, d_d32, d_a8; wire [8:0] d_t1; wire [LA:0] v1;
    ot_hdc_delay #(.W(160), .D(LA)) u_d1 (.clk(clk), .rst_n(rq[1]), .d({A32, B16a, C16b, D32, A8}),
                                          .q({d_a32, d_b16a, d_c16b, d_d32, d_a8}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t1 (.clk(clk), .rst_n(rq[1]), .d({o_i, o_acc}), .q(d_t1));
    ot_hdc_vline #(.D(LA)) u_v1 (.clk(clk), .rst_n(rq[1]), .v(o_v), .vd(v1));
    ot_dsrom_qadd #(.LAT(LA)) u_a4 (clk, rq[1], v1[LA], (MUT == 5) ? d_a8 : p1, (MUT == 5) ? p1 : d_b16a, n1, f4);
    ot_dsrom_qadd #(.LAT(LA)) u_a5 (clk, rq[1], v1[LA], d_c16b, p2, n3, f5a);
    wire [31:0] e_a32, e_n2, e_d32; wire [8:0] e_t; wire [LA:0] v2;
    ot_hdc_delay #(.W(96), .D(LA)) u_d2 (.clk(clk), .rst_n(rq[1]), .d({d_a32, n2, d_d32}), .q({e_a32, e_n2, e_d32}));
    ot_hdc_delay #(.W(9), .D(LA)) u_t2 (.clk(clk), .rst_n(rq[1]), .d(d_t1), .q(e_t));
    ot_hdc_vline #(.D(LA)) u_v2 (.clk(clk), .rst_n(rq[1]), .v(v1[LA]), .vd(v2));
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
    ot_hdc_vline #(.D(DQ - 2)) u_qs (.clk(clk), .rst_n(rq[2]), .v(s0), .vd(qs));
    wire [4:0] q_acc0;
    ot_hdc_delay #(.W(5), .D(DQ - 2)) u_qacc (.clk(clk), .rst_n(rq[2]), .d(o_acc), .q(q_acc0));
    reg q_on; reg [4:0] q_i; reg [4:0] q_acc;
    reg qr_v; reg [4:0] qr_i; reg [4:0] qr_acc; reg [31:0] q0, q1, q2, q3;
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) begin q_on <= 1'b0; q_i <= 5'd0; qr_v <= 1'b0; end
        else begin
            if (qs[DQ - 2]) begin q_on <= 1'b1; q_i <= 5'd0; q_acc <= q_acc0; end
            else if (q_on) begin q_i <= q_i + 5'd1; if (q_i == 5'd19) q_on <= 1'b0; end
            qr_v <= q_on; qr_i <= q_i; qr_acc <= q_acc;
        end
    always @(posedge clk) begin q0 <= l5[4 * q_i]; q1 <= l5[4 * q_i + 1]; q2 <= l5[4 * q_i + 2]; q3 <= l5[4 * q_i + 3]; end
    wire [31:0] l6a, l6b, l7; wire f6, f7, f8; wire [LA:0] vq1, vq2; wire [9:0] tq1, tq2;
    ot_dsrom_qadd #(.LAT(LA)) u_a6 (clk, rq[2], qr_v, q0, q1, l6a, f6);
    ot_dsrom_qadd #(.LAT(LA)) u_a7 (clk, rq[2], qr_v, q2, q3, l6b, f7);
    ot_hdc_vline #(.D(LA)) u_vq1 (.clk(clk), .rst_n(rq[2]), .v(qr_v), .vd(vq1));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq1 (.clk(clk), .rst_n(rq[2]), .d({qr_i, qr_acc}), .q(tq1));
    ot_dsrom_qadd #(.LAT(LA)) u_a8 (clk, rq[2], vq1[LA], l6a, l6b, l7, f8);
    ot_hdc_vline #(.D(LA)) u_vq2 (.clk(clk), .rst_n(rq[2]), .v(vq1[LA]), .vd(vq2));
    ot_hdc_delay #(.W(10), .D(LA)) u_tq2 (.clk(clk), .rst_n(rq[2]), .d(tq1), .q(tq2));
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
        ot_dsrom_qadd #(.LAT(LA)) u_t (clk, rq[2], go, ii[0] ? pend : id, ii[0] ? id : 32'd0, y, f);
        ot_hdc_vline #(.D(LA)) u_tv (.clk(clk), .rst_n(rq[2]), .v(go), .vd(vv));
        ot_hdc_delay #(.W(11), .D(LA)) u_tt (.clk(clk), .rst_n(rq[2]), .d({il, ii >> 1, ia}), .q(tt));
        assign t_vv[lv + 1] = vv[LA];
        assign t_d[32 * (lv + 1) +: 32] = y; assign t_i[5 * (lv + 1) +: 5] = tt[9:5]; assign t_a[5 * (lv + 1) +: 5] = tt[4:0];
        assign t_l[lv + 1] = tt[10];
        assign t_f[lv] = f;
    end endgenerate
    wire root_v = t_vv[5]; wire [31:0] root = t_d[32 * 5 +: 32]; wire [4:0] root_acc = t_a[5 * 5 +: 5];
    // ---------------------------------------------------------------- roots -> proj / ss -> r
    reg [31:0] proj [0:23];
    reg [24:0] rdone;
    always @(posedge clk) if (root_v && root_acc < 5'd24) proj[root_acc] <= root;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) ss_v <= 1'b0;
        else ss_v <= root_v && root_acc == 5'd24;
    // S81-KITS-RTLC 10-24 (raw face_guard, 0 edges): held pin registers (ss, t_*, sticky fault) have kept internal twins
    // that hold; each pin flop loads twin-next, never its own Q.  cw_a packed {a[9:8], a[5:0]} (a[7:6] read by no leaf).
    (* keep = "true" *) reg [31:0] ss_k;
    always @(posedge clk) begin if (root_v) ss_k <= root; ss <= root_v ? root : ss_k; eps_c <= (MUT == 7) ? 32'd0 : eps_t[aj_set]; end
    reg rr_v, f_r; reg [31:0] rr;                       // L4r's r: input flops
    always @(posedge clk or negedge rq[3]) if (!rq[3]) begin rr_v <= 1'b0; f_r <= 1'b0; end else begin rr_v <= r_v; f_r <= r_f; end
    always @(posedge clk) rr <= r_y;
    reg r_ok; reg [31:0] r;
    // ---------------------------------------------------------------- mix phase: 24 multiplies, then the tail launch
    reg m_on; reg [4:0] m_i; reg mm_v; reg [4:0] mm_i; reg [31:0] mm_a; reg mix_go;
    (* keep = "true" *) reg launch_k;                   // internal twin of the launch output flop (-> launch_s)
    (* keep = "true" *) reg tk_set, tk_w; (* keep = "true" *) reg [9:0] tk_row; (* keep = "true" *) reg [4:0] tk_lm;
    (* keep = "true" *) reg [15:0] tk_sm; (* keep = "true" *) reg fault_k;
    wire ld_t = !m_on && rdone == {NACC{1'b1}} && r_ok;     // the mix start (rdone / r_ok are 0 in reset)
    always @(posedge clk)
        {t_set, t_w, t_row, t_lm, t_sm} <= ld_t ? {aj_set, aj_w, aj_row, aj_lm, aj_sm} : {tk_set, tk_w, tk_row, tk_lm, tk_sm};
    wire [31:0] my; wire f_mul; wire [LM:0] vm; wire [4:0] mi;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin
            rdone <= 25'd0; r_ok <= 1'b0; m_on <= 1'b0; mm_v <= 1'b0; mix_go <= 1'b0; mix_go_s <= 1'b0;
            launch <= 1'b0; launch_k <= 1'b0; launch_s <= 1'b0; fault <= 1'b0; fault_k <= 1'b0;
        end else begin
            mix_go <= 1'b0; launch <= 1'b0; launch_k <= 1'b0;
            if (root_v) rdone <= rdone | (25'd1 << root_acc);
            if (rr_v) begin r_ok <= 1'b1; r <= rr; end
            if (!m_on && rdone == {NACC{1'b1}} && r_ok) begin
                m_on <= 1'b1; m_i <= 5'd0; mix_go <= 1'b1; rdone <= 25'd0; r_ok <= 1'b0;
                tk_set <= aj_set; tk_w <= aj_w; tk_row <= aj_row; tk_lm <= aj_lm; tk_sm <= aj_sm;
            end
            if (m_on) begin m_i <= m_i + 5'd1; if (m_i == 5'd23) m_on <= 1'b0; end
            mm_v <= m_on; mm_i <= m_i;
            if (vm[LM] && mi == 5'd23) begin launch <= 1'b1; launch_k <= 1'b1; end
            mix_go_s <= mix_go; launch_s <= launch_k;
            if (f1 | f2 | f3 | f4 | f5a | f6 | f7 | f8 | (|t_f) | f_r | f_mul | f5_q
                | (root_v && rdone[root_acc]) | (mix_go && !aj_v) | (qs[DQ - 2] && q_on && q_i != 5'd19)) begin fault_k <= 1'b1; fault <= 1'b1; end
            else fault <= fault_k;
        end
    always @(posedge clk) mm_a <= proj[m_i];
    ot_hdc_qmul_lat #(.LAT(LM)) u_mul (clk, rq[3], mm_v, mm_a, r, my, f_mul);
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rq[3]), .v(mm_v), .vd(vm));
    ot_hdc_delay #(.W(5), .D(LM)) u_mi (.clk(clk), .rst_n(rq[3]), .d(mm_i), .q(mi));
    always @(posedge clk or negedge rq[3]) if (!rq[3]) mx_v <= 1'b0; else mx_v <= vm[LM];
    always @(posedge clk) begin mx_i <= mi; mx_y <= my; end   // one mix a cycle to L5 (L5 assembles the 24)
endmodule
