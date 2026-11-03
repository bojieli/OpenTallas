`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-S81 (owner 0dv 2026-10-18): ot_s81sl_eg -- the Engram SCALAR FINISH of a DV vector slice (slice centre,
// replicated x16: every slice receives the same 12 finished sums from xfin ENG mode and computes the same 4 gates from
// the same operands in the same order, so all slices hold bit-identical gates without a broadcast).  It replaces the
// scalar row of the deleted hub-era mix (dsfd_engram_mix4_half / ot_s81_engram_mix_control_core).
//
// Golden (tools/hdc_golden_v41.py Model.engram_layer), copy j, D = 5120, totals hh / kk / dd = csum(h*h), csum(k*k),
// csum((h*w)*k) finished by xfin:
//   rstd = rsqrt(hh/D + eps) * rsqrt(kk/D + eps)
//   dot  = (dd * rstd) * scale
//   gate = sigmoid(sign(dot) * sqrt(max(|dot|, 1e-6)))
// Arithmetic leaves are the gated hub-era Engram leaves UNCHANGED (rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv):
//   ot_s81_engram_norm x2 (/D by ot_dsrom_divc, +eps, rsqrt), ot_hdc_qmul_lat x3 (rstd_h*rstd_k, dd*rstd, *scale) in the
//   mix control's order, ot_s81_engram_gate (signed sqrt with the 1e-6 clamp, then sigmoid).  Every leaf is II 1, so
//   copies stream back to back (one i_v a cycle).
// Static schedule, no ready / credit: i_v carries copy i_c's three totals; g_v / g_c / g leave FIXED latency later
// (LAT_EG = 1 + LN + 1 + 3 LM + 1 + LG + 1 = 221 cycles at LM 5 / LA 4 in the flat form; 222 in the S81-RF1 3-block form below, measured by tb_s81sl_eg).  dd and the copy tag ride
// fixed delay lines beside the norm and gate pipes; each depth is checked every cycle against the leaf's own valid, so a
// drifted constant, a norm-pair valid mismatch or any leaf fault is a sticky fault.  eps / scale are static per Engram layer (CTL body, xr), held from before the first
// i_v until the last g_v.  Every input lands in a flop; every output leaves a flop.
// MUT (bench negative controls only, 0 in every build): 1 sign dropped (|dot| into the gate); 2 one rstd only
// (rstd = rsqrt_h * rsqrt_h); 3 scale applied before rstd ((dd*scale)*rstd: same operands, golden association broken).
// ---------------------------------------------------------------------------------------------------------------------
// ---------------------------------------------------------------------------------------------------------------------
// S81-RF1 RE-FORM (DIE-S81-51/RF-B 2026-11-03, OWNER TWO-STRIKES): the 267k-cell flat eg (S81-045: synth LEC NOT EQ 4 on
// the merged rsqrt sign pipes, FF hold -174 structural, ioref TT -3.1) is cut into THREE hard blocks on its natural
// leaf boundaries, every block I/O registered at the face (face-to-face wire only between blocks):
//   u_nh, u_nk : ot_s81sl_egn  (ONE template, 2 instances): pin flops -> ot_s81_engram_norm -> output face flops.
//   u_gg       : ot_s81sl_egg  : pin flops (i_v/i_c/i_dd/scale + the two norm faces) -> 3 products -> gate -> pin flops.
// The wrapper ot_s81sl_eg has no logic (wires only) and keeps its port list, so every parent slice is unchanged.
// Every block output face = face flop -> negative-level lockup latch -> port (0 cycles; DIE-S81-51/CLK row 1).
// Cost: +1 cycle i_v -> g_v (the egn output face; the egg input face is the old rh_q / rk_q / nv_q stage):
// LAT_EG 221 -> 222, measured by tb_s81sl_eg.  Function bit-identical (same leaves, same order, same faults).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_eg #(parameter integer D = 5120, LM = 5, LA = 4, MUT = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] eps,
    input  wire [31:0] scale,
    input  wire        i_v,
    input  wire [1:0]  i_c,
    input  wire [31:0] i_hh,
    input  wire [31:0] i_kk,
    input  wire [31:0] i_dd,
    output wire        g_v,
    output wire [1:0]  g_c,
    output wire [31:0] g,
    output wire        fault
);
    initial if (D != 5120) $fatal(1, "ot_s81sl_eg: ot_s81_engram_norm divides by 5120 (ot_dsrom_divc F 5 K 10)");
    wire nh_v, nk_v, nh_f, nk_f; wire [31:0] nh_r, nk_r;
    ot_s81sl_egn #(.LM(LM), .LA(LA)) u_nh (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_x(i_hh), .eps(eps),
        .o_v(nh_v), .o_r(nh_r), .o_f(nh_f));
    ot_s81sl_egn #(.LM(LM), .LA(LA)) u_nk (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_x(i_kk), .eps(eps),
        .o_v(nk_v), .o_r(nk_r), .o_f(nk_f));
    ot_s81sl_egg #(.LM(LM), .LA(LA), .MUT(MUT)) u_gg (.clk(clk), .rst_n(rst_n), .scale(scale), .i_v(i_v), .i_c(i_c),
        .i_dd(i_dd), .n_v({nk_v, nh_v}), .n_rh(nh_r), .n_rk(nk_r), .n_f({nk_f, nh_f}),
        .g_v(g_v), .g_c(g_c), .g(g), .fault(fault));
endmodule

// ot_s81sl_egn: one Engram norm, rsqrt(x / 5120 + eps), as a hard block.  Input face: iv_q / x_q / eps_q (the old eg pin
// flops); output face: o_v / o_r / o_f flops (+1 cycle).  LN_EGN = 1 + LN + 1 (face in, norm, face out).
module ot_s81sl_egn #(parameter integer LM = 5, LA = 4) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_x,
    input  wire [31:0] eps,
    output wire        o_v,
    output wire [31:0] o_r,
    output wire        o_f
);
    wire rn;
    ot_s81_engram_reset u_rst (clk, rst_n, rn);
    reg iv_q; reg [31:0] x_q, eps_q;
    always @(posedge clk or negedge rn) if (!rn) iv_q <= 1'b0; else iv_q <= i_v;
    always @(posedge clk) begin x_q <= i_x; eps_q <= eps; end
    wire nv, nf; wire [31:0] rs;
    ot_s81_engram_norm #(.LM(LM), .LA(LA)) u_n (clk, rst_n, iv_q, x_q, eps_q, nv, rs, nf);
    reg ov_f, of_f; reg [31:0] or_f;          // output face flops
    always @(posedge clk or negedge rn) if (!rn) begin ov_f <= 1'b0; of_f <= 1'b0; end else begin ov_f <= nv; of_f <= nf; end
    always @(posedge clk) or_f <= rs;
    // out-face lockup (DIE-S81-51/CLK crossing table row 1): face flop -> negative-level latch -> port, no logic between.
    // The port takes the flop's new value at the falling edge; the receiver captures it at the next rising edge = the
    // same edge as without the latch (0 cycles), hold margin ~T/2 by construction.
    reg ov_l, of_l; reg [31:0] or_l;
    // DIE-S81-51/NFF 11-03 (uniform out-face form ruling): default = negative-EDGE flop (DFFLQN) per bit, same T/2
    // hold window, 0 cycles; +define+OT_S81SL_EG_OLATCH keeps the transparent-low latch.
`ifdef OT_S81SL_EG_OLATCH
    always_latch if (!clk) begin ov_l = ov_f; of_l = of_f; or_l = or_f; end
`else
    always @(negedge clk) begin ov_l <= ov_f; of_l <= of_f; or_l <= or_f; end
`endif
    assign o_v = ov_l; assign o_f = of_l; assign o_r = or_l;
endmodule

// ot_s81sl_egg: products (rstd_h * rstd_k, dd * rstd, * scale) + gate (signed sqrt, sigmoid) + fault, as a hard block.
// Input face: iv_q / ic_q / dd_q / sc_q (pins from the parent, same edge as egn's iv_q) and nv_q / rh_q / rk_q / nf_q
// (the egn output faces).  dd / copy tag ride LN + 1 delay lines (the norm + the egn output face).  Every input lands in
// a flop; every output leaves a flop; the old order / ring checks are unchanged (nchk depth LN + 2 = nv_q).
module ot_s81sl_egg #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] scale,
    input  wire        i_v,
    input  wire [1:0]  i_c,
    input  wire [31:0] i_dd,
    input  wire [1:0]  n_v,
    input  wire [31:0] n_rh,
    input  wire [31:0] n_rk,
    input  wire [1:0]  n_f,
    output wire        g_v,
    output wire [1:0]  g_c,
    output wire [31:0] g,
    output wire        fault
);
    wire rn;
    ot_s81_engram_reset u_rst (clk, rst_n, rn);
    reg gv_f, flt_f; reg [1:0] gc_f; reg [31:0] g_f;    // output face flops
    reg iv_q; reg [1:0] ic_q; reg [31:0] dd_q, sc_q;
    always @(posedge clk or negedge rn) if (!rn) iv_q <= 1'b0; else iv_q <= i_v;
    always @(posedge clk) begin ic_q <= i_c; dd_q <= i_dd; sc_q <= scale; end
    localparam integer LN = 1 + 9 + LA + 1 + 3 * (3 * LM + LA);
    localparam integer LG = 2 + 31 + 1 + 1 + (7 * LM + 8 * LA + 4) + LA + 19 + 1;
    localparam integer LNF = LN + 1;           // + the egn output face
    wire g_o;
    wire [31:0] dd_n; wire [1:0] c_n, c_o; wire [LNF+1:0] nchk; wire [LG:0] gchk;
    ot_hdc_delay #(.W(32), .D(LNF)) u_ddl (clk, rn, dd_q, dd_n);
    ot_hdc_delay #(.W(2), .D(LNF)) u_cl0 (clk, rn, ic_q, c_n);
    ot_hdc_vline #(.D(LNF + 1)) u_nchk (clk, rn, iv_q, nchk);
    // egn output faces land here (the old rh_q / rk_q / nv_q stage)
    reg [1:0] nv_q, nf_q; reg [31:0] rh_q, rk_q, dd_a; reg [1:0] c_a;
    always @(posedge clk or negedge rn) if (!rn) begin nv_q <= 2'b0; nf_q <= 2'b0; end else begin nv_q <= n_v; nf_q <= n_f; end
    always @(posedge clk) begin rh_q <= n_rh; rk_q <= n_rk; dd_a <= dd_n; c_a <= c_n; end
    reg ring_f;
    always @(posedge clk or negedge rn)
        if (!rn) ring_f <= 1'b0;
        else if (nchk[LNF+1] != nv_q[0] || nv_q[0] != nv_q[1] || gchk[LG] != g_o) ring_f <= 1'b1;
    wire [3*LM:0] pv;
    ot_hdc_vline #(.D(3 * LM)) u_pv (clk, rn, nv_q[0], pv);
    wire [31:0] rstd, dd_d, sc_d, m1, m2; wire [2:0] mf;
    ot_hdc_qmul_lat #(LM) u_m0 (clk, rn, pv[0], rh_q, (MUT == 2) ? rh_q : rk_q, rstd, mf[0]);
    ot_hdc_delay #(.W(32), .D(LM)) u_dd (clk, rn, dd_a, dd_d);
    ot_hdc_delay #(.W(32), .D(LM)) u_sc (clk, rn, sc_q, sc_d);
    wire [31:0] rstd_d;
    ot_hdc_delay #(.W(32), .D(LM)) u_rd (clk, rn, rstd, rstd_d);
    ot_hdc_qmul_lat #(LM) u_m1 (clk, rn, pv[LM], dd_d, (MUT == 3) ? sc_d : rstd, m1, mf[1]);
    ot_hdc_qmul_lat #(LM) u_m2 (clk, rn, pv[2 * LM], m1, (MUT == 3) ? rstd_d : sc_q, m2, mf[2]);
    wire [1:0] c_p; ot_hdc_delay #(.W(2), .D(3 * LM)) u_cl1 (clk, rn, c_a, c_p);
    reg dv_q; reg [31:0] dot_q; reg [1:0] c_d;
    always @(posedge clk or negedge rn) if (!rn) dv_q <= 1'b0; else dv_q <= pv[3 * LM];
    always @(posedge clk) begin dot_q <= (MUT == 1) ? {1'b0, m2[30:0]} : m2; c_d <= c_p; end
    ot_hdc_delay #(.W(2), .D(LG)) u_cl2 (clk, rn, c_d, c_o);
    ot_hdc_vline #(.D(LG)) u_gchk (clk, rn, dv_q, gchk);
    wire [31:0] gy; wire [1:0] gf;
    ot_s81_engram_gate #(.LM(LM), .LA(LA)) u_g (clk, rst_n, dv_q, dot_q, g_o, gy, gf, clk);
    (* keep *) reg flt_s; (* keep *) reg [31:0] g_s; (* keep *) reg [1:0] gc_s;
    wire flt_n = flt_s | ring_f | (|nf_q) | (|mf) | (|gf);
    always @(posedge clk or negedge rn)
        if (!rn) begin gv_f <= 1'b0; flt_f <= 1'b0; flt_s <= 1'b0; end
        else begin
            gv_f <= g_o; flt_s <= flt_n; flt_f <= flt_n;
        end
    always @(posedge clk) begin
        if (g_o) begin g_s <= gy; gc_s <= c_o; end
`ifdef OT_RTLB_PINFLOP_MUT
        g_f <= gy; gc_f <= c_o;
`else
        g_f <= g_o ? gy : g_s; gc_f <= g_o ? c_o : gc_s;
`endif
    end
    // out-face lockup (DIE-S81-51/CLK row 1): face flop -> negative-level latch -> port, no logic between (0 cycles).
    reg gv_l, flt_l; reg [1:0] gc_l; reg [31:0] g_l;
    // DIE-S81-51/NFF 11-03 (uniform out-face form ruling): default = negative-EDGE flop (DFFLQN) per bit, same T/2
    // hold window, 0 cycles; +define+OT_S81SL_EG_OLATCH keeps the transparent-low latch.
`ifdef OT_S81SL_EG_OLATCH
    always_latch if (!clk) begin gv_l = gv_f; flt_l = flt_f; gc_l = gc_f; g_l = g_f; end
`else
    always @(negedge clk) begin gv_l <= gv_f; flt_l <= flt_f; gc_l <= gc_f; g_l <= g_f; end
`endif
    assign g_v = gv_l; assign fault = flt_l; assign g_c = gc_l; assign g = g_l;
endmodule
