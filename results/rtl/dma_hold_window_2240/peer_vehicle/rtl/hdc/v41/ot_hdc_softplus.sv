`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// softplus and the V4.1 router score sqrt(softplus(x)): II 1, fixed DEPTH 259.
//
// FUNCTION (tools/hdc_golden_v41.softplus and .sqrt, bit for bit):
//
//     t  = exp(-|x|)                      ot_hdc_exp (hdc_golden.exp)
//     u  = t / (t + 2)                    ot_hdc_fadd, ot_hdc_fdiv (IEEE division)
//     u2 = u * u
//     p  = 1/17;  p = p*u2 + 1/(2i+1) for i = 7 .. 0     (eight fmul/fadd pairs)
//     l  = (u * p) * 2                    log1p(t) = 2 atanh(u)
//     sp = max(x, 0) + l                  softplus
//     r  = sqrt(sp)                       ot_hdc_fsqrt (IEEE square root)
//
// every step one binary32 RNE operation with canonical +0 zeros, in the
// golden's order.  Built only from fixed-depth pipes -- the qualified add pipe,
// the decode core's multiplier, its exp, and the correctly rounded divide and
// square-root pipes of rtl/hdc/v41 -- so one argument enters per cycle and
// both results leave DEPTH cycles later, together.
//
// FAULT.  For a finite x every intermediate is finite (t in (0, 1], u in
// (0, 1/3], sp > 0), so no unit refuses.  x = -inf is the golden's too: the
// exp clamps it and max(x, 0) is +0, so the result is finite and exact.  +inf
// and NaN, where the golden's result is not finite, fail closed: the final add
// refuses them, and `fault` is raised on that result (sp = r = +0).
// `fault` is aligned with `vo`; any other unit's refusal is ORed in as well.
// ---------------------------------------------------------------------------
module ot_hdc_softplus (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,      // softplus(x)
    output wire [31:0] r,       // sqrt(softplus(x))
    output wire        vo,
    output wire        fault
);
    localparam integer T_EXP  = 92;              // ot_hdc_exp DEPTH
    localparam integer T_DEN  = T_EXP + 5;       // t + 2
    localparam integer T_U    = T_DEN + 31;      // ot_hdc_fdiv DEPTH
    localparam integer T_U2   = T_U + 5;
    localparam integer T_P    = T_U2 + 8 * 10;   // Horner
    localparam integer T_UP   = T_P + 5;
    localparam integer T_L    = T_UP + 5;
    localparam integer T_SP   = T_L + 5;
    localparam integer DEPTH  = T_SP + 31;       // ot_hdc_fsqrt DEPTH
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i);   // LOG1P_ODD[i]
        coef = C[32*(8-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // t = exp(-|x|)
    wire [31:0] t, den, t_d5, u, u2, lp, l;
    wire f_exp, f_den, f_div, f_u2, f_up, f_l, f_sp, f_sq;
    ot_hdc_exp  u_exp (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b1, x[30:0]}), .y(t), .vo(), .fault(f_exp));
    ot_hdc_fadd a_den (clk, rst_n, vd[T_EXP], t, 32'h40000000, den, f_den);
    ot_hdc_delay #(.W(32), .D(5)) d_t (clk, rst_n, t, t_d5);
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d5), .b(den), .y(u), .vo(), .fault(f_div));
    ot_hdc_fmul m_u2 (clk, rst_n, vd[T_U], u, u, u2, f_u2);

    // Horner in u2; u2 travels in 10-cycle hops
    wire [31:0] u2d [0:7];
    wire [31:0] pm  [1:8];
    wire [31:0] pa  [0:8];
    wire [16:1] hf;
    assign u2d[0] = u2;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay #(.W(32), .D(10)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_fmul u_m (clk, rst_n, vd[T_U2 + 10*(k-1)], pa[k-1], u2d[k-1], pm[k], hf[2*k-1]);
            ot_hdc_fadd u_a (clk, rst_n, vd[T_U2 + 10*(k-1) + 5], pm[k], coef(k), pa[k], hf[2*k]);
        end
    endgenerate

    // l = (u * p) * 2
    wire [31:0] u_d;
    ot_hdc_delay #(.W(32), .D(T_P - T_U)) d_u (clk, rst_n, u, u_d);
    ot_hdc_fmul m_up (clk, rst_n, vd[T_P], u_d, pa[8], lp, f_up);
    ot_hdc_fmul m_l  (clk, rst_n, vd[T_UP], lp, 32'h40000000, l, f_l);

    // sp = max(x, 0) + l
    reg  [31:0] mx;
    wire [31:0] mx_d, spv;
    //: a NaN is not below zero (numpy's maximum propagates it), so it reaches
    //: the add and is refused there; -inf gives +0, like any negative x
    wire x_nan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    always @(posedge clk) mx <= (x[31] && !x_nan) ? 32'd0 : x;
    ot_hdc_delay #(.W(32), .D(T_L - 1)) d_mx (clk, rst_n, mx, mx_d);
    ot_hdc_fadd a_sp (clk, rst_n, vd[T_L], mx_d, l, spv, f_sp);

    // r = sqrt(sp); sp waits for it
    ot_hdc_fsqrt u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    ot_hdc_delay #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);

    // faults: the final add's refusal travels with its result
    wire f_sp_d;
    ot_hdc_delay #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    assign fault = f_sp_d | f_sq | f_exp | f_den | f_div | f_u2 | (|hf) | f_up | f_l;
endmodule
