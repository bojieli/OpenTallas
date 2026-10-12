`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Activation quantiser of the DeepSeek-V4.1 hardwired decode core.
//
// One 32-element block per cycle (II = 1, fixed latency LATENCY, no stall).
// Two formats, chosen per block by `fp4`, both specified in
// tools/hdc_golden_v41.py:
//
//   fp4 = 0  quant_fp8 / qdq_fp8: amax = max(max|x|, 1e-4); e = ceil_log2(
//            amax * (1/448)) from the bits of the binary32 product; codes are
//            E4M3 of x * 2^-e, round-to-nearest-even;
//   fp4 = 1  qdq_fp4_e8m0: amax = max(max|x|, 6 * 2^-126); e = ceil_log2(
//            amax * (1/6)); codes are E2M1 (low nibble of each byte) of
//            x * 2^-e, RNE.
//
// NO SATURATION STAGE.  The golden clips x * 2^-e to +-448 (+-6) before
// rounding, but the clip can never act: float32(1/448) and float32(1/6) both
// round UP, by less than half an ulp of 1, so RN(amax * c) >= 2^k forces
// amax * 2^-k <= 448 (6) whenever the ceiling lands on k.  The campaign
// (tools/rtl_hdc_v41_blockdot_campaign.py) checks this over every finite
// positive binary32 amax for both formats and records the count (zero).
//
// Outputs per block: the codes `q` (what the block-linear lane consumes), the
// scale exponent `e` (scale = 2^e) and the dequantised values q * 2^e as BF16
// words `y` (what qdq_fp8 / qdq_fp4_e8m0 return).  A negative element that
// rounds to zero keeps its sign; -0 itself quantises to +0, as the golden's
// np.sign(-0.0) = +0 does.
//
// The scale product amax * c is one binary32 multiply (ot_hdc_fmul, RNE with
// gradual underflow: the FP4 floor times 1/6 can be subnormal, and
// ceil_log2 then reads exponent field 0 as -127, plus one for a nonzero
// fraction, exactly as the golden's _ceil_log2 does).  Everything else is
// exponent arithmetic and one short rounding shift per element:
//
//   Ev = exponent(x) - e;  g = max(Ev, min_exp);  count = RNE(sig(x) >>
//   (23 - mant_bits + g - Ev)),  value = count * 2^(g - mant_bits)
//
// A nonfinite element raises `fault` (the golden's inputs are finite).
//
// Stages: S0 input register; S1 |x| and 32->8 of the max tree; S2 8->2; S2b
// 2->1 and the floor; S3-S7 the scale multiply; S8 e; S9 per-element shift
// amounts; S10 round; S11 encode (output registers).  LATENCY = 13 cycles.
// ---------------------------------------------------------------------------
module ot_hdc_actquant (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          fp4,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [30:0] FLOOR_FP4 = 31'h01c00000;   // float32(6 * 2^-126)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    localparam [31:0] INV_6     = 32'h3e2aaaab;   // float32(1/6)

    function automatic [30:0] mx(input [30:0] a, input [30:0] b);
        mx = (a >= b) ? a : b;
    endfunction

    integer i;

    // -- S0: input register ------------------------------------------------------
    reg          s0_v, s0_fp4;
    reg [1023:0] s0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s0_v <= 1'b0;
        else s0_v <= v;
    end
    always @(posedge clk) begin
        s0_x <= x; s0_fp4 <= fp4;
    end

    // -- S1: magnitudes, 32 -> 8 (two compare levels per stage: one 31-bit ------------
    //    compare-and-select is ~350 ps routed on ASAP7) ---------------------------------
    reg        s1_v, s1_fp4, s1_nf;
    reg [30:0] s1_m [0:7];
    reg [30:0] t16 [0:15];
    reg        nf0;
    always @(*) begin
        nf0 = 1'b0;
        for (i = 0; i < 32; i = i + 1) nf0 = nf0 | (s0_x[32*i + 23 +: 8] == 8'hFF);
        for (i = 0; i < 16; i = i + 1) t16[i] = mx(s0_x[64*i +: 31], s0_x[64*i + 32 +: 31]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= s0_v;
    end
    always @(posedge clk) begin
        s1_fp4 <= s0_fp4; s1_nf <= nf0;
        for (i = 0; i < 8; i = i + 1) s1_m[i] <= mx(t16[2*i], t16[2*i+1]);
    end

    // -- S2: 8 -> 2 ------------------------------------------------------------------------
    reg        s2a_v, s2a_fp4, s2a_nf;
    reg [30:0] s2a_m [0:1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2a_v <= 1'b0;
        else s2a_v <= s1_v;
    end
    always @(posedge clk) begin
        s2a_fp4 <= s1_fp4; s2a_nf <= s1_nf;
        for (i = 0; i < 2; i = i + 1)
            s2a_m[i] <= mx(mx(s1_m[4*i], s1_m[4*i+1]), mx(s1_m[4*i+2], s1_m[4*i+3]));
    end

    // -- S2b: 2 -> 1 and the floor ----------------------------------------------------------
    reg        s2_v, s2_fp4, s2_nf;
    reg [30:0] s2_amax;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s2a_v;
    end
    always @(posedge clk) begin
        s2_fp4 <= s2a_fp4; s2_nf <= s2a_nf;
        s2_amax <= mx(mx(s2a_m[0], s2a_m[1]), s2a_fp4 ? FLOOR_FP4 : FLOOR_FP8);
    end

    // -- S3-S7: amax * (1/448 or 1/6), one binary32 multiply ------------------------------
    wire [31:0] prod;
    wire        pfault;
    ot_hdc_fmul u_scale (.clk(clk), .rst_n(rst_n), .v(s2_v), .a({1'b0, s2_amax}),
                         .b(s2_fp4 ? INV_6 : INV_448), .y(prod), .fault(pfault));
    reg [4:0] vl;                                   // valid of S3..S7
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vl <= 5'd0;
        else vl <= {vl[3:0], s2_v};
    end
    wire s7_v = vl[4];
    wire s7_fp4, s7_nf;
    ot_hdc_delay #(.W(2), .D(5)) u_d27 (.clk(clk), .rst_n(rst_n), .d({s2_fp4, s2_nf}), .q({s7_fp4, s7_nf}));

    // elements, from S0 to S8 (nine registers: S1, S2, S2b, S3-S7, S8)
    wire [1023:0] x8;
    ot_hdc_delay #(.W(1024), .D(9)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(x8));

    // -- S8: e = ceil_log2(prod) ------------------------------------------------------------
    reg              s8_v, s8_fp4, s8_nf;
    reg signed [9:0] s8_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s8_v <= 1'b0;
        else s8_v <= s7_v;
    end
    always @(posedge clk) begin
        s8_fp4 <= s7_fp4; s8_nf <= s7_nf | pfault;
        s8_e <= $signed({2'b00, prod[30:23]}) - 10'sd127 + {9'd0, (prod[22:0] != 23'd0)};
    end

    // -- S9: per-element grid exponent and shift ----------------------------------------------
    reg              s9_v, s9_fp4, s9_nf;
    reg signed [9:0] s9_e;
    reg [23:0]       s9_sig [0:31];
    reg [4:0]        s9_rs [0:31];
    reg signed [4:0] s9_g [0:31];
    reg [31:0]       s9_sgn;
    reg [7:0]        fld;
    reg [22:0]       man;
    reg signed [10:0] ev, dd, mine;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s9_v <= 1'b0;
        else s9_v <= s8_v;
    end
    always @(posedge clk) begin
        s9_fp4 <= s8_fp4; s9_nf <= s8_nf; s9_e <= s8_e;
        for (i = 0; i < 32; i = i + 1) begin
            fld = x8[32*i + 23 +: 8];
            man = x8[32*i +: 23];
            //: a subnormal element has exponent -126 and no leading one
            ev = ((fld == 8'd0) ? -11'sd126 : ($signed({3'b000, fld}) - 11'sd127)) - s8_e;
            mine = s8_fp4 ? 11'sd0 : -11'sd6;
            dd = mine - ev;
            s9_sig[i] <= {(fld != 8'd0), man};
            s9_sgn[i] <= x8[32*i + 31] && (x8[32*i +: 31] != 31'd0);
            if (dd > 11'sd0) begin
                s9_g[i] <= mine[4:0];
                //: past 26 every bit of the 24-bit significand is below the guard
                s9_rs[i] <= (dd > (s8_fp4 ? 11'sd4 : 11'sd6)) ? 5'd26 : ((s8_fp4 ? 5'd22 : 5'd20) + dd[4:0]);
            end else begin
                s9_g[i] <= ev[4:0];
                s9_rs[i] <= s8_fp4 ? 5'd22 : 5'd20;
            end
        end
    end

    // -- S10: round to the grid ----------------------------------------------------------------
    reg              s10_v, s10_fp4, s10_nf;
    reg signed [9:0] s10_e;
    reg [4:0]        s10_c [0:31];
    reg signed [4:0] s10_g [0:31];
    reg [31:0]       s10_sgn;
    reg [50:0]       wide;
    reg [23:0]       tq;
    reg              gd, st;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s10_v <= 1'b0;
        else s10_v <= s9_v;
    end
    always @(posedge clk) begin
        s10_fp4 <= s9_fp4; s10_nf <= s9_nf; s10_e <= s9_e; s10_sgn <= s9_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            wide = {s9_sig[i], 27'd0} >> s9_rs[i];
            tq = wide[50:27];
            gd = wide[26];
            st = (wide[25:0] != 26'd0);
            s10_c[i] <= tq[4:0] + {4'd0, gd & (st | tq[0])};
            s10_g[i] <= s9_g[i];
        end
    end

    // -- S11: codes and dequantised BF16 --------------------------------------------------------
    reg [2:0]         p;
    reg signed [11:0] be;
    reg [4:0]         c;
    reg [7:0]         cn;
    reg [6:0]         sub;
    reg signed [11:0] shs;
    reg [3:0]         g4;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= s10_v; fault <= s10_v && s10_nf; end
    end
    always @(posedge clk) begin
        e <= s10_e;
        for (i = 0; i < 32; i = i + 1) begin
            c = s10_c[i];
            g4 = s10_g[i][3:0];
            // codes
            if (!s10_fp4) begin
                if (c[4])      q[8*i +: 8] <= {s10_sgn[i], g4 + 4'd8, 3'd0};
                else if (c[3]) q[8*i +: 8] <= {s10_sgn[i], g4 + 4'd7, c[2:0]};
                else           q[8*i +: 8] <= {s10_sgn[i], 4'd0, c[2:0]};
            end else begin
                if (c[2])      q[8*i +: 8] <= {4'd0, s10_sgn[i], g4[1:0] + 2'd2, 1'b0};
                else if (c[1]) q[8*i +: 8] <= {4'd0, s10_sgn[i], g4[1:0] + 2'd1, c[0]};
                else           q[8*i +: 8] <= {4'd0, s10_sgn[i], 2'd0, c[0]};
            end
            // value c * 2^(g - mant_bits + e) as BF16
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            be = $signed({9'd0, p}) + s10_g[i] - (s10_fp4 ? 12'sd1 : 12'sd3) + s10_e + 12'sd127;
            cn = {3'd0, c} << (3'd7 - p);
            shs = s10_g[i] - (s10_fp4 ? 12'sd1 : 12'sd3) + s10_e + 12'sd133;
            sub = (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
            if (c == 5'd0)           y[16*i +: 16] <= {s10_sgn[i], 15'd0};
            else if (be >= 12'sd255) y[16*i +: 16] <= {s10_sgn[i], 8'hFF, 7'd0};
            else if (be >= 12'sd1)   y[16*i +: 16] <= {s10_sgn[i], be[7:0], cn[6:0]};
            else                     y[16*i +: 16] <= {s10_sgn[i], 8'd0, sub};
        end
    end
endmodule
