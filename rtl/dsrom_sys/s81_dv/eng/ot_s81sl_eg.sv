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
// (LAT_EG = 1 + LN + 1 + 3 LM + 1 + LG + 1 = 221 cycles at LM 5 / LA 4, measured by tb_s81sl_eg).  dd and the copy tag ride
// fixed delay lines beside the norm and gate pipes; each depth is checked every cycle against the leaf's own valid, so a
// drifted constant, a norm-pair valid mismatch or any leaf fault is a sticky fault.  eps / scale are static per Engram layer (CTL body, xr), held from before the first
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
    // ---------------------------------------------------------------- dd and the copy tag ride fixed delay lines beside the pipes
    // LN = ot_s81_engram_norm v -> vo (pin flop 1 + ot_dsrom_divc 9 + eps add LA + ot_dsrom_rsqrt 1 + 3 (3 LM + LA));
    // LG = ot_s81_engram_gate v -> vo (signed sqrt 2 + ot_hdc_fsqrt 31 + 1, sigmoid 1 + (7 LM + 8 LA + 4) + LA + 19 + 1).
    // Each constant is CHECKED every cycle: a valid line of the same depth must equal the leaf's own valid (else fault).
    localparam integer LN = 1 + 9 + LA + 1 + 3 * (3 * LM + LA);
    localparam integer LG = 2 + 31 + 1 + 1 + (7 * LM + 8 * LA + 4) + LA + 19 + 1;
    wire g_o;                                   // gate output valid
    wire [31:0] dd_n; wire [1:0] c_n, c_o; wire [LN:0] nchk; wire [LG:0] gchk;
    ot_hdc_delay #(.W(32), .D(LN)) u_ddl (clk, rn, dd_q, dd_n);
    ot_hdc_delay #(.W(2), .D(LN)) u_cl0 (clk, rn, ic_q, c_n);
    ot_hdc_vline #(.D(LN)) u_nchk (clk, rn, iv_q, nchk);
    reg ring_f;
    always @(posedge clk or negedge rn)
        if (!rn) ring_f <= 1'b0;
        else if (nchk[LN] != nv[0] || nv[0] != nv[1] || gchk[LG] != g_o) ring_f <= 1'b1;
    // ---------------------------------------------------------------- products in the mix control's order
    reg nv_q; reg [31:0] rh_q, rk_q, dd_a;
    always @(posedge clk or negedge rn) if (!rn) nv_q <= 1'b0; else nv_q <= nv[0];
    reg [1:0] c_a; always @(posedge clk) begin rh_q <= rs_h; rk_q <= rs_k; dd_a <= dd_n; c_a <= c_n; end
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
    wire [1:0] c_p; ot_hdc_delay #(.W(2), .D(3 * LM)) u_cl1 (clk, rn, c_a, c_p);
    reg dv_q; reg [31:0] dot_q; reg [1:0] c_d;
    always @(posedge clk or negedge rn) if (!rn) dv_q <= 1'b0; else dv_q <= pv[3 * LM];
    always @(posedge clk) begin dot_q <= (MUT == 1) ? {1'b0, m2[30:0]} : m2; c_d <= c_p; end
    ot_hdc_delay #(.W(2), .D(LG)) u_cl2 (clk, rn, c_d, c_o);
    ot_hdc_vline #(.D(LG)) u_gchk (clk, rn, dv_q, gchk);
    // ---------------------------------------------------------------- gate (signed sqrt + clamp, sigmoid)
    wire [31:0] gy; wire [1:0] gf;
    ot_s81_engram_gate #(.LM(LM), .LA(LA)) u_g (clk, rst_n, dv_q, dot_q, g_o, gy, gf, clk);
    // ---------------------------------------------------------------- output pin flops + sticky fault
    // S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): fault / g / g_c leave pin-only flops loaded
    // with the next value of kept state registers (sticky fault flt_s; gate hold g_s / gc_s), so no pin flop feeds its
    // own D any more (face_guard 'shared').  Pin flop == state register every cycle: 0 cycles.
    (* keep *) reg flt_s; (* keep *) reg [31:0] g_s; (* keep *) reg [1:0] gc_s;
    wire flt_n = flt_s | ring_f | (|nf) | (|mf) | (|gf);
    always @(posedge clk or negedge rn)
        if (!rn) begin g_v <= 1'b0; fault <= 1'b0; flt_s <= 1'b0; end
        else begin
            g_v <= g_o; flt_s <= flt_n; fault <= flt_n;
        end
    always @(posedge clk) begin
        if (g_o) begin g_s <= gy; gc_s <= c_o; end
`ifdef OT_RTLB_PINFLOP_MUT
        g <= gy; g_c <= c_o;                               // mutant: pin flops do not hold between gates
`else
        g <= g_o ? gy : g_s; g_c <= g_o ? c_o : gc_s;
`endif
    end
endmodule
