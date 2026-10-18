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
// (LAT_EG cycles, measured by tb_s81sl_eg).  dd and the copy tag ride in-order rings (depth 8) beside the norm and the
// gate pipes, so no hand-counted delay constant can drift; a ring over- or under-flow, a norm-pair valid mismatch or any
// leaf fault is a sticky fault.  eps / scale are static per Engram layer (CTL body, xr), held from before the first
// i_v until the last g_v.  Every input lands in a flop; every output leaves a flop.
// MUT (bench negative controls only, 0 in every build): 1 sign dropped (|dot| into the gate); 2 one rstd only
// (rstd = rsqrt_h * rsqrt_h); 3 scale applied before rstd ((dd*scale)*rstd: same operands, golden association broken).
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
    output reg         g_v,
    output reg  [1:0]  g_c,
    output reg  [31:0] g,
    output reg         fault
);
    initial if (D != 5120) $fatal(1, "ot_s81sl_eg: ot_s81_engram_norm divides by 5120 (ot_dsrom_divc F 5 K 10)");
    wire rn;
    ot_s81_engram_reset u_rst (clk, rst_n, rn);
    // ---------------------------------------------------------------- input pin flops
    reg iv_q; reg [1:0] ic_q; reg [31:0] hh_q, kk_q, dd_q, eps_q, sc_q;
    always @(posedge clk or negedge rn) if (!rn) iv_q <= 1'b0; else iv_q <= i_v;
    always @(posedge clk) begin ic_q <= i_c; hh_q <= i_hh; kk_q <= i_kk; dd_q <= i_dd; eps_q <= eps; sc_q <= scale; end
    // ---------------------------------------------------------------- norms (hh, kk in lockstep)
    wire [1:0] nv, nf; wire [31:0] rs_h, rs_k;
    ot_s81_engram_norm #(.LM(LM), .LA(LA)) u_nh (clk, rst_n, iv_q, hh_q, eps_q, nv[0], rs_h, nf[0]);
    ot_s81_engram_norm #(.LM(LM), .LA(LA)) u_nk (clk, rst_n, iv_q, kk_q, eps_q, nv[1], rs_k, nf[1]);
    // ---------------------------------------------------------------- in-order rings: dd (to the norm output), copy (to the gate output)
    reg [31:0] dd_r [0:7]; reg [1:0] c_r [0:7];
    reg [2:0] dw, drd, cw, crd; reg [3:0] dn, cn;
    wire g_o;                                   // gate output valid (pops the copy ring)
    reg [31:0] dd_n; reg [1:0] c_o;
    always @(posedge clk) begin
        if (iv_q) begin dd_r[dw] <= dd_q; c_r[cw] <= ic_q; end
    end
    always @(*) begin dd_n = dd_r[drd]; c_o = c_r[crd]; end
    reg ring_f;
    always @(posedge clk or negedge rn)
        if (!rn) begin dw <= 3'd0; drd <= 3'd0; cw <= 3'd0; crd <= 3'd0; dn <= 4'd0; cn <= 4'd0; ring_f <= 1'b0; end
        else begin
            if (iv_q) begin dw <= dw + 3'd1; cw <= cw + 3'd1; end
            if (nv[0]) drd <= drd + 3'd1;
            if (g_o) crd <= crd + 3'd1;
            dn <= dn + {3'd0, iv_q} - {3'd0, nv[0]};
            cn <= cn + {3'd0, iv_q} - {3'd0, g_o};
            if ((dn == 4'd8 && iv_q && !nv[0]) || (dn == 4'd0 && nv[0]) || (cn == 4'd8 && iv_q && !g_o) ||
                (cn == 4'd0 && g_o) || nv[0] != nv[1]) ring_f <= 1'b1;
        end
    // ---------------------------------------------------------------- products in the mix control's order
    reg nv_q; reg [31:0] rh_q, rk_q, dd_a;
    always @(posedge clk or negedge rn) if (!rn) nv_q <= 1'b0; else nv_q <= nv[0];
    always @(posedge clk) begin rh_q <= rs_h; rk_q <= rs_k; dd_a <= dd_n; end
    wire [3*LM:0] pv;
    ot_hdc_vline #(.D(3 * LM)) u_pv (clk, rn, nv_q, pv);
    wire [31:0] rstd, dd_d, sc_d, m1, m2, dot; wire [2:0] mf;
    ot_hdc_qmul_lat #(LM) u_m0 (clk, rn, pv[0], rh_q, (MUT == 2) ? rh_q : rk_q, rstd, mf[0]);
    ot_hdc_delay #(.W(32), .D(LM)) u_dd (clk, rn, dd_a, dd_d);
    ot_hdc_delay #(.W(32), .D(LM)) u_sc (clk, rn, sc_q, sc_d);
    // golden: m1 = dd * rstd, dot = m1 * scale.  MUT 3: m1 = dd * scale, dot = m1 * rstd.
    wire [31:0] rstd_d;
    ot_hdc_delay #(.W(32), .D(LM)) u_rd (clk, rn, rstd, rstd_d);
    ot_hdc_qmul_lat #(LM) u_m1 (clk, rn, pv[LM], dd_d, (MUT == 3) ? sc_d : rstd, m1, mf[1]);
    ot_hdc_qmul_lat #(LM) u_m2 (clk, rn, pv[2 * LM], m1, (MUT == 3) ? rstd_d : sc_q, m2, mf[2]);
    reg dv_q; reg [31:0] dot_q;
    always @(posedge clk or negedge rn) if (!rn) dv_q <= 1'b0; else dv_q <= pv[3 * LM];
    always @(posedge clk) dot_q <= (MUT == 1) ? {1'b0, m2[30:0]} : m2;
    // ---------------------------------------------------------------- gate (signed sqrt + clamp, sigmoid)
    wire [31:0] gy; wire [1:0] gf;
    ot_s81_engram_gate #(.LM(LM), .LA(LA)) u_g (clk, rst_n, dv_q, dot_q, g_o, gy, gf, clk);
    // ---------------------------------------------------------------- output pin flops + sticky fault
    always @(posedge clk or negedge rn)
        if (!rn) begin g_v <= 1'b0; fault <= 1'b0; end
        else begin
            g_v <= g_o;
            if (ring_f || (|nf) || (|mf) || (|gf)) fault <= 1'b1;
        end
    always @(posedge clk) if (g_o) begin g <= gy; g_c <= c_o; end
endmodule
