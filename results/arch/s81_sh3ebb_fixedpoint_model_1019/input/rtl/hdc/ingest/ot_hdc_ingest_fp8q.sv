`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// FP32 -> FP8 E4M3 quantiser of the KV ingest engine (combinational).
//
// E4M3FN conversion for the KV ingest path: bias 7, largest finite
// 448, subnormal quantum 2^-9, round to nearest even, SATURATING (anything that
// rounds above 448, and +-inf, gives +-448); a zero result is +0 (the core's
// canonical zero rule).  FP32 zeros and subnormals give +0.  A NaN
// input (never produced by a serving engine's KV) saturates like infinity.
// BF16 inputs arrive as {bf16, 16'b0}: BF16 -> E4M3 is the same function.
// FP8 E4M3 code: {sign, exponent[3:0], mantissa[2:0]}; 0x7E = 448.
// ---------------------------------------------------------------------------
module ot_hdc_ingest_fp8q (
    input  wire [31:0] f,
    output reg  [7:0]  q
);
    wire        s  = f[31];
    wire [7:0]  e  = f[30:23];
    wire [23:0] m  = {1'b1, f[22:0]};
    // unbiased exponent u = e - 127; normal E4M3 when u >= -6 (e >= 121)
    reg  [4:0]  qn;                 // 1.xxx before rounding, then after (may carry to 16)
    reg         up;
    reg  [4:0]  eb;                 // biased E4M3 exponent (may reach 16)
    reg  [7:0]  sh;                 // subnormal shift 14 - u = 141 - e
    reg  [24:0] mm;
    reg  [3:0]  n;
    reg  [24:0] rem, half;
    always @* begin
        q = 8'h00;
        qn = 5'd0; up = 1'b0; eb = 5'd0; sh = 8'd0; mm = 25'd0; n = 4'd0; rem = 25'd0; half = 25'd0;
        if (e == 8'd0) begin
            q = 8'h00;                                   // zero / FP32 subnormal: |x| < 2^-126
        end else if (e == 8'hFF || e > 8'd135) begin
            q = {s, 7'h7E};                              // u > 8, inf, NaN: saturate to 448
        end else if (e >= 8'd121) begin
            // normal: keep 3 fraction bits, round the other 20 to nearest even
            qn = {1'b0, m[23:20]};
            up = (m[19:0] > 20'h80000) || (m[19:0] == 20'h80000 && m[20]);
            qn = qn + {4'd0, up};
            eb = 5'(e - 8'd120);                         // u + 7, 1 .. 15
            if (qn[4]) begin eb = eb + 5'd1; qn = 5'd8; end
            if (eb > 5'd15 || (eb == 5'd15 && qn[2:0] == 3'd7)) q = {s, 7'h7E};
            else q = {s, eb[3:0], qn[2:0]};
        end else begin
            // subnormal E4M3: |x| / 2^-9 = m * 2^(u + 9 - 23), round to an integer 0 .. 8
            if (e < 8'd116) begin
                n = 4'd0;                                // sh > 25: below half the quantum
            end else begin
                sh = 8'd141 - e;                         // 14 - u: 21 .. 25 (e 116 .. 120)
                mm = {1'b0, m};
                n = 4'(mm >> sh);
                rem = mm & ((25'd1 << sh) - 25'd1);
                half = 25'd1 << (sh - 8'd1);
                up = (rem > half) || (rem == half && n[0]);
                n = n + {3'd0, up};
            end
            if (n == 4'd0) q = 8'h00;                    // +0 (never -0)
            else if (n[3]) q = {s, 7'h08};               // 8 x 2^-9 = 2^-6: the smallest normal
            else q = {s, 4'd0, n[2:0]};
        end
    end
endmodule
