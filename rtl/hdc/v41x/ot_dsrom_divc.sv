`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 division by a CONSTANT D = F * 2^K, F in {1, 5} (DS-ROM recovery lever su_norm):
// y = RN_even(x / D), gradual underflow, every zero result +0 -- the golden's div(x, float32(D)) for the RMSNorm
// mean (D = 5,120 = 5 * 2^10, 1,280 = 5 * 2^8, 512 = 2^9).  A correctly rounded quotient is unique, so this equals
// any IEEE divider bit for bit; it replaces the general ot_hdc_v41x_fdiv (19 stages, which misses 0.833 ns at SS
// by 357 ps) in the fused 1.2 GHz pipelines.  Proof: rtl/test/tb_dsrom_divc.cpp checks EVERY positive finite
// binary32 input against the C++ float division for each D used.
//
// Method.  Normalise x = m * 2^(E-23), m in [2^23, 2^24).  For F = 5: m * 2^26 / 5 = Qm * 2^26 + tail(r0) exactly
// in its integer part, with Qm = floor(m / 5), r0 = m mod 5 and tail(r0) = floor(r0 * 2^26 / 5) (5 constants);
// the dropped remainder (r0 * 2^26) mod 5 is non-zero iff r0 != 0 (2^26 = 4 mod 5), which is the sticky bit.
// floor(m / 5) is six radix-16 digit steps of a 7-bit table each (remainder < 5), two a stage.  For F = 1: Qm = m, r0 = 0.
// Q = {Qm, tail} (50 bits) scaled by 2^(E-49-K) is the exact quotient truncated, plus the sticky; one rounding
// at the result's own exponent (normal or subnormal) finishes it.
// Stages (LATENCY 9): decode + LZC | normalise | 2 digits | 2 digits | 2 digits | exponent, shift amount |
// shift, guard, sticky | round (keep-prefix increment) | encode.  Needs rtl/hdc/ot_hdc_fastfp_lat_f12.sv (or
// ot_hdc_fastfp_lat.sv: ot_hdc_kinc) and rtl/hdc/ot_hdc_prefix.sv.
// Nonfinite input raises fault (y = +0); the RMSNorm operand (sum of squares + nothing) is finite and >= +0.
// ---------------------------------------------------------------------------
module ot_dsrom_divc #(
    parameter integer F = 5,
    parameter integer K = 10
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer LATENCY = 9;
    initial if (F != 1 && F != 5) $error("ot_dsrom_divc: F must be 1 or 5");
    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    assign vo = vl[LATENCY];

    // -- S1: decode, leading-zero count of the significand ---------------------------------
    reg        s1_s, s1_z, s1_nf, s1_sub;
    reg [23:0] s1_m;
    reg [7:0]  s1_e;
    reg [4:0]  s1_lz;
    reg [4:0]  lz;
    wire [23:0] m0 = {(x[30:23] != 8'd0), x[22:0]};
    integer i;
    always @(*) begin
        lz = 5'd0;
        for (i = 0; i < 24; i = i + 1) if (m0[i]) lz = 5'd23 - i[4:0];
    end
    always @(posedge clk) begin
        s1_s <= x[31];
        s1_z <= (x[30:0] == 31'd0);
        s1_nf <= (x[30:23] == 8'hFF);
        s1_sub <= (x[30:23] == 8'd0);
        s1_m <= m0;
        s1_e <= x[30:23];
        s1_lz <= lz;
    end
    // -- S2: normalise ------------------------------------------------------------------------
    reg               s2_s, s2_z, s2_nf;
    reg [23:0]        s2_m;
    reg signed [10:0] s2_eu;                 // unbiased exponent of the normalised significand
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf;
        s2_m <= s1_m << s1_lz;
        s2_eu <= (s1_sub ? -11'sd126 : ($signed({3'b000, s1_e}) - 11'sd127)) - $signed({6'd0, s1_lz});
    end
    // -- S3, S4: floor(m / 5), m mod 5: radix-16 digits, three a stage --------------------------
    function automatic [6:0] dstep(input [2:0] r, input [3:0] d);   // {q digit[3:0], remainder[2:0]}
        reg [6:0] t, q, m;
        begin
            t = {r, d};                       // r * 16 + d, <= 79
            q = t / 7'd5;
            m = t % 7'd5;
            dstep = {q[3:0], m[2:0]};
        end
    endfunction
    // three stages of two digits: S3 digits 0-1, S3b digits 2-3, S4 digits 4-5
    reg               s3_s, s3_z, s3_nf, s3b_s, s3b_z, s3b_nf;
    reg [23:0]        s3_m, s3b_m;
    reg [7:0]         s3_qh;
    reg [15:0]        s3b_qh;
    reg [2:0]         s3_r, s3b_r;
    reg signed [10:0] s3_eu, s3b_eu;
    reg [6:0] d0, d1, d2, d3, d4, d5;
    always @(*) begin
        d0 = dstep(3'd0, s2_m[23:20]);
        d1 = dstep(d0[2:0], s2_m[19:16]);
        d2 = dstep(s3_r, s3_m[15:12]);
        d3 = dstep(d2[2:0], s3_m[11:8]);
        d4 = dstep(s3b_r, s3b_m[7:4]);
        d5 = dstep(d4[2:0], s3b_m[3:0]);
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf; s3_m <= s2_m; s3_eu <= s2_eu;
        s3_qh <= {d0[6:3], d1[6:3]};
        s3_r <= d1[2:0];
        s3b_s <= s3_s; s3b_z <= s3_z; s3b_nf <= s3_nf; s3b_m <= s3_m; s3b_eu <= s3_eu;
        s3b_qh <= {s3_qh, d2[6:3], d3[6:3]};
        s3b_r <= d3[2:0];
    end
    reg               s4_s, s4_z, s4_nf;
    reg [23:0]        s4_qm;
    reg [2:0]         s4_r0;
    reg signed [10:0] s4_eu;
    always @(posedge clk) begin
        s4_s <= s3b_s; s4_z <= s3b_z; s4_nf <= s3b_nf; s4_eu <= s3b_eu;
        s4_qm <= (F == 5) ? {s3b_qh, d4[6:3], d5[6:3]} : s3b_m;
        s4_r0 <= (F == 5) ? d5[2:0] : 3'd0;
    end
    // -- S5: the exact truncated quotient Q (50 bits), its exponent and the shift --------------------
    function automatic [25:0] tail(input [2:0] r);                    // floor(r * 2^26 / 5)
        case (r)
            3'd1: tail = 26'd13421772;
            3'd2: tail = 26'd26843545;
            3'd3: tail = 26'd40265318;
            3'd4: tail = 26'd53687091;
            default: tail = 26'd0;
        endcase
    endfunction
    reg               s5_s, s5_z, s5_nf, s5_st0, s5_sub;
    reg [49:0]        s5_q;
    reg [5:0]         s5_sh;
    reg signed [10:0] s5_er;
    reg [5:0]         lead;
    reg signed [10:0] er;
    reg signed [11:0] sh;
    always @(*) begin
        lead = (F == 5) ? (s4_qm[21] ? 6'd47 : 6'd46) : 6'd49;
        er = s4_eu - 11'sd49 - K + $signed({5'd0, lead});
        sh = $signed({6'd0, lead}) - 12'sd23 + ((er < -11'sd126) ? (-12'sd126 - er) : 12'sd0);
    end
    always @(posedge clk) begin
        s5_s <= s4_s; s5_z <= s4_z; s5_nf <= s4_nf;
        s5_q <= {s4_qm, tail(s4_r0)};
        s5_st0 <= (s4_r0 != 3'd0);
        s5_er <= er;
        s5_sub <= (er < -11'sd126);
        s5_sh <= (sh > 12'sd51) ? 6'd51 : sh[5:0];         // 51: every bit of Q below the guard (sticky only)
    end
    // -- S6: shift, guard, sticky ---------------------------------------------------------------------
    reg               s6_s, s6_z, s6_nf, s6_g, s6_st, s6_sub;
    reg [24:0]        s6_m;
    reg signed [10:0] s6_er;
    reg [50:0]        w;
    always @(*) w = {s5_q, 1'b0} >> s5_sh;    // w[0]: guard; the bits shifted out below it: sticky
    reg [49:0] lowmask;
    always @(posedge clk) begin
        s6_s <= s5_s; s6_z <= s5_z; s6_nf <= s5_nf; s6_er <= s5_er; s6_sub <= s5_sub;
        s6_m <= w[25:1];
        s6_g <= w[0];
        lowmask = (s5_sh == 6'd0) ? 50'd0 : ((50'd1 << (s5_sh - 6'd1)) - 50'd1);
        s6_st <= s5_st0 | ((s5_q & lowmask) != 50'd0);
    end
    // -- S7: round ------------------------------------------------------------------------------------
    reg               s7_s, s7_z, s7_nf, s7_sub;
    reg [24:0]        s7_m;
    reg signed [10:0] s7_er;
    wire [24:0] s6_mi;
    ot_hdc_kinc #(.W(25), .K(1)) u_inc (.a(s6_m), .inc(s6_g & (s6_st | s6_m[0])), .y(s6_mi));   // keep-prefix
    always @(posedge clk) begin
        s7_s <= s6_s; s7_z <= s6_z; s7_nf <= s6_nf; s7_er <= s6_er; s7_sub <= s6_sub;
        s7_m <= s6_mi;
    end
    // -- S8: encode ---------------------------------------------------------------------------------------
    always @(posedge clk) begin
        fault <= vl[8] && s7_nf;
        if (s7_nf || s7_z || s7_m == 25'd0)
            y <= 32'd0;
        else if (s7_sub)                                    // subnormal; rounding up to 2^23 is the least normal
            y <= {s7_s, (s7_m[23] ? 8'd1 : 8'd0), s7_m[22:0]};
        else if (s7_m[24])                                  // rounded up to 2^24: next binade
            y <= {s7_s, s7_er[7:0] + 8'd128, 23'd0};
        else
            y <= {s7_s, s7_er[7:0] + 8'd127, s7_m[22:0]};
    end
endmodule
