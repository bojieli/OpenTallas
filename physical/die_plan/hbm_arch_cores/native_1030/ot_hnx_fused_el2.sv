
// ---------------------------------------------------------------------------------------------------------------------
// one FUSED element, n4 (LH-P3UNITS/FUSED 2026-10-19, SAFE-DESIGN structural redesign of the n3 lane: 113,400 flops on
// one root, textbook REFUSE).  HC_PRE_NORM's mix x = bf16(((h0 p0 + h1 p1) + h2 p2) + h3 p3) is the first three sums
// of HC_POST's chain o = bf16((((r0 c0 + r1 c1) + r2 c2) + r3 c3) + y p) (ot_dsrom_su_hcpost_lane), and the two ops
// never run together (one record at a time, op static per record).  So ONE product/sum chain serves both: products
// j = a_j * b_j (j 0..3) and y * p, sums in the hcpost order; PRE taps x = bf16(a3) (the mix's RNE), HC_POST takes
// bf16(a4).  The multipliers / adders are the same f12 cores the two ops used (only register cuts differ: bit for bit
// the same function; the adder operands of sums 2 and 3 are swapped vs the mix -- IEEE add commutes).  This removes
// the mix's 4 multipliers + 3 adders + its 18-deep operand delays from every column (~1/3 of the column).  Operand
// delays are ring buffers (ot_hdc_delay_ring RING 1: no flop-to-flop hold chain).  Latencies: ML 7 (l7; y * p l6r +1
// align), AL 6 (l6x), squares LM 5, scale LMS 6.  x leaves at ML + 3 AL + 1 (was LM + 3 LA + 1: +2 edges).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hnx_fused_el2 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire         x_v,
    input  wire         xo_v,
    input  wire         wv,
    input  wire [31:0]  y,
    input  wire [31:0]  a0,
    input  wire [31:0]  a1,
    input  wire [31:0]  a2,
    input  wire [31:0]  a3,
    input  wire [31:0]  b0,
    input  wire [31:0]  b1,
    input  wire [31:0]  b2,
    input  wire [31:0]  b3,
    input  wire [31:0]  p,
    input  wire [31:0]  xo,
    input  wire [31:0]  rh,
    input  wire [31:0]  wo,
    output reg          hv,
    output reg  [31:0]  ho,
    output reg          hf,
    output wire [31:0]  xl,
    output wire [31:0]  sq,
    output wire         sf,
    output wire [31:0]  qq,
    output wire         f1,
    output wire         f2
);
    localparam integer LM = 5, LMS = 6, ML = 7, AL = 6, LM4 = 6;
    wire [31:0] m0, m1, m2, m3, m4, s1, s2, s3, s4, m2d, m3d, m4d;
    wire [1:0] e0, e1, e2, e3, e4, e4a, es1, es2, es3, es4;
    wire vm, vs1, vs2, vs3, vs4;
    ot_hdc_fp32_mul_f12_l7  u_m0 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a0), .b(b0), .y(m0), .err(e0), .valid_out(vm));
    ot_hdc_fp32_mul_f12_l7  u_m1 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a1), .b(b1), .y(m1), .err(e1), .valid_out());
    ot_hdc_fp32_mul_f12_l7  u_m2 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a2), .b(b2), .y(m2), .err(e2), .valid_out());
    ot_hdc_fp32_mul_f12_l7  u_m3 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a3), .b(b3), .y(m3), .err(e3), .valid_out());
    ot_hdc_fp32_mul_f12_l6r u_m4 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(y),  .b(p),  .y(m4), .err(e4), .valid_out());
    ot_hdc_delay #(.W(2), .D(ML - LM4)) u_e4 (.clk(clk), .rst_n(rst_n), .d(e4), .q(e4a));
    ot_hdc_fp32_add_f12_l6x u_s1 (.clk(clk), .rst_n(rst_n), .valid_in(vm), .a(m0), .b(m1), .y(s1), .err(es1), .valid_out(vs1));
    ot_hdc_delay_ring #(.W(32), .D(AL), .RING(1)) u_d2 (.clk(clk), .rst_n(rst_n), .d(m2), .q(m2d));
    ot_hdc_fp32_add_f12_l6x u_s2 (.clk(clk), .rst_n(rst_n), .valid_in(vs1), .a(m2d), .b(s1), .y(s2), .err(es2), .valid_out(vs2));
    ot_hdc_delay_ring #(.W(32), .D(2 * AL), .RING(1)) u_d3 (.clk(clk), .rst_n(rst_n), .d(m3), .q(m3d));
    ot_hdc_fp32_add_f12_l6x u_s3 (.clk(clk), .rst_n(rst_n), .valid_in(vs2), .a(m3d), .b(s2), .y(s3), .err(es3), .valid_out(vs3));
    ot_hdc_delay_ring #(.W(32), .D(3 * AL + ML - LM4), .RING(1)) u_d4 (.clk(clk), .rst_n(rst_n), .d(m4), .q(m4d));
    ot_hdc_fp32_add_f12_l6x u_s4 (.clk(clk), .rst_n(rst_n), .valid_in(vs3), .a(m4d), .b(s3), .y(s4), .err(es4), .valid_out(vs4));
    // PRE: x = RNE bf16 of the third sum (ot_dsrom_su_norm_mix's rounding), registered (the mix's xr)
    reg [31:0] xr;
    wire [32:0] rs = {1'b0, s3} + 33'h7FFF + {32'd0, s3[16]};
    always @(posedge clk) xr <= {rs[31:16], 16'd0};
    assign xl = xr;
    // HC_POST: o = bf16(fourth sum) (ot_dsrom_su_hcpost_lane's rounding); flags sticky (the hcpost lane's fault)
    wire [15:0] hi;
    ot_hdc_inc_k #(.W(16)) u_rnd (.a(s4[31:16]), .inc(s4[15] & (s4[16] | (|s4[14:0]))), .y(hi), .co());
    reg [3*AL:0] fm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hv <= 1'b0; hf <= 1'b0; fm <= '0; end
        else begin
            hv <= vs4;
            fm <= {fm[3*AL-1:0], vm && ((e0 | e1 | e2 | e3 | e4a) != 2'd0)};
            hf <= hf | fm[0] | (vs1 && es1 != 2'd0) | (vs2 && es2 != 2'd0) | (vs3 && es3 != 2'd0) | (vs4 && es4 != 2'd0);
        end
    end
    always @(posedge clk) ho <= {hi, 16'd0};
    // squares and the scale (unchanged)
    wire [31:0] pp;
    ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq, sf);
    ot_hdc_qmul_lat #(LMS) u_xr (clk, rst_n, xo_v, xo, rh, pp, f1);
    ot_hdc_qmul_lat #(LMS) u_w  (clk, rst_n, wv, wo, pp, qq, f2);
endmodule
