`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Special-function pipelines of the hardwired decode core: exp, reciprocal and
// reciprocal square root.  Each is an unrolled chain of the qualified binary32
// multiply/add pipes (LATENCY 5, II 1) plus single-cycle integer steps, so each
// accepts one operand per cycle and returns it a fixed DEPTH later.  No divider,
// no iteration, no combinational IEEE operation.
//
// The algorithms and their operation order are the specification in
// tools/hdc_golden.py (exp, reciprocal, rsqrt); the RTL matches it bit for bit.
// ---------------------------------------------------------------------------

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_vline #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule

// exp(x): clamp to [-87, 88]; n = rint(x*log2e) by the 1.5*2^23 trick; two-
// constant Cody-Waite reduction; degree-6 Horner; 2^n added to the exponent.
module ot_hdc_exp (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 92;
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [31:0] K_MAGIC = 32'h4B400000;   //  1.5 * 2^23
    localparam [31:0] K_NMAGIC = 32'hCB400000;
    localparam [31:0] K_HI    = 32'h3F317200;   //  ln2 high part
    localparam [31:0] K_LO    = 32'h35BFBE8E;   //  ln2 low part
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t, u, n, a_hi, a_lo, r1, r, xc_d20, lo_d5;
    wire [6:0] f;
    ot_hdc_fmul m_t  (clk, rst_n, vd[1],  xc, K_LOG2E, t,   f[0]);   // 6
    ot_hdc_fadd a_u  (clk, rst_n, vd[6],  t,  K_MAGIC, u,   f[1]);   // 11
    ot_hdc_fadd a_n  (clk, rst_n, vd[11], u,  K_NMAGIC, n,  f[2]);   // 16
    ot_hdc_fmul m_hi (clk, rst_n, vd[16], n,  K_HI,    a_hi, f[3]);  // 21
    ot_hdc_fmul m_lo (clk, rst_n, vd[16], n,  K_LO,    a_lo, f[4]);  // 21
    ot_hdc_delay #(.W(32), .D(20)) d_x (clk, rst_n, xc, xc_d20);
    ot_hdc_fadd a_r1 (clk, rst_n, vd[21], xc_d20, {~a_hi[31], a_hi[30:0]}, r1, f[5]);  // 26
    ot_hdc_delay #(.W(32), .D(5)) d_lo (clk, rst_n, a_lo, lo_d5);
    ot_hdc_fadd a_r  (clk, rst_n, vd[26], r1, {~lo_d5[31], lo_d5[30:0]}, r, f[6]);     // 31

    // Horner: p = C0; six times p = p*r + C[k]; r travels in 10-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay #(.W(32), .D(10)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_fmul u_m (clk, rst_n, vd[31 + 10*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_fadd u_a (clk, rst_n, vd[36 + 10*(k-1)], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    // n as an integer: u = 1.5*2^23 + n exactly, so n sits in u's fraction.
    reg  [8:0] nint;
    wire [8:0] nint_d;
    always @(posedge clk) nint <= u[8:0];   // low 9 bits of 0x400000 + n are n
    ot_hdc_delay #(.W(9), .D(79)) d_n (clk, rst_n, nint, nint_d);   // 12 -> 91
    always @(posedge clk) y <= pa[6] + {{14{nint_d[8]}}, nint_d, 23'd0};   // 92

    assign fault = |{f, hf};
endmodule

// 1/d: seed 0x7ef311c7 - bits(d), three Newton-Raphson steps y*(2 - d*y).
module ot_hdc_recip (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 46;
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0, d1;
    always @(posedge clk) begin
        y0 <= 32'h7EF311C7 - x;
        d1 <= x;
    end
    wire [31:0] yi [0:3];
    wire [31:0] dd [0:2];
    wire [31:0] m [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [8:0] f;
    assign yi[0] = y0;
    assign dd[0] = d1;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_d
                ot_hdc_delay #(.W(32), .D(15)) d_d (clk, rst_n, dd[k], dd[k+1]);
            end
            ot_hdc_fmul m_m (clk, rst_n, vd[1 + 15*k], dd[k], yi[k], m[k], f[3*k]);
            ot_hdc_fadd a_s (clk, rst_n, vd[6 + 15*k], 32'h40000000, {~m[k][31], m[k][30:0]}, s[k], f[3*k+1]);
            ot_hdc_delay #(.W(32), .D(10)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y (clk, rst_n, vd[11 + 15*k], yd[k], s[k], yi[k+1], f[3*k+2]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_rsqrt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 61;
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    always @(posedge clk) y0 <= 32'h5F3759DF - {1'b0, x[31:1]};
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_fmul m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // 5
    ot_hdc_delay #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 6
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay #(.W(32), .D(20)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_fmul m_yy (clk, rst_n, vd[1 + 20*k],  yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_fmul m_hm (clk, rst_n, vd[6 + 20*k],  hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_fadd a_s  (clk, rst_n, vd[11 + 20*k], 32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay #(.W(32), .D(15)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y  (clk, rst_n, vd[16 + 20*k], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule
