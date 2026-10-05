`timescale 1ns/1ps
// Equivalence of the successor FP8 KV rounding (tools/qwen_hbmacc_vstream_f12_emit.py: constant-shift subnormal
// branch) with the pinned lane's fp8r: EVERY input whose exponent field is 100..135 (both signs, all 2^23
// significands: the whole subnormal branch, its boundaries and the low normal binades), plus 2^26 random words.
// Functions copied verbatim from rtl/hdc/ot_hdc_vstream_lane.sv and rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_f12.sv.
module tb_fp8r_equiv;
    function automatic [31:0] fp8r_ref(input [31:0] v);
        reg [7:0] ex; reg [22:0] mt; reg [24:0] sig; reg [4:0] sh; reg [24:0] n, rem, half;
        reg [3:0] m4; reg up; integer e; reg [31:0] y;
        begin
            ex = v[30:23]; mt = v[22:0]; e = ex - 127;
            if (ex == 0) y = 32'd0;                                   // zero (and FP32 subnormals: below 2^-9)
            else if (e >= -6) begin
                up = v[19] && ((|v[18:0]) || v[20]);
                m4 = {1'b1, v[22:20]} + up;                          // 8..16
                if (m4 == 0) begin e = e + 1; m4 = 4'd8; end          // 16 wraps: the next binade
                if (e > 8 || (e == 8 && m4 > 4'd14)) y = {v[31], 8'd135, 3'b110, 20'd0};   // saturate at 448
                else y = {v[31], e[7:0] + 8'd127, m4[2:0], 20'd0};
            end else begin
                // subnormal: n = round(|v| / 2^-9), |v| = sig * 2^(e-23), sh = 14 - e
                sig = {2'b01, mt};
                if (14 - e >= 26) y = 32'd0;
                else begin
                    sh = 14 - e;
                    n = sig >> sh; rem = sig & ((25'd1 << sh) - 1); half = 25'd1 << (sh - 1);
                    if (rem > half || (rem == half && n[0])) n = n + 1;
                    if (n == 0) y = 32'd0;
                    else if (n[3]) y = {v[31], 8'd121, 23'd0};          // 8 x 2^-9 = 2^-6
                    else if (n[2]) y = {v[31], 8'd120, n[1:0], 21'd0};
                    else if (n[1]) y = {v[31], 8'd119, n[0], 22'd0};
                    else y = {v[31], 8'd118, 23'd0};
                end
            end
            fp8r_ref = y;
        end
    endfunction
    function automatic [24:0] fp8r_sub(input [24:0] sig, input integer sh);   // round(sig / 2^sh), half to even
        reg [24:0] n, rem, half;
        begin
            n = sig >> sh; rem = sig & ((25'd1 << sh) - 1); half = 25'd1 << (sh - 1);
            if (rem > half || (rem == half && n[0])) n = n + 1;
            fp8r_sub = n;
        end
    endfunction
    function automatic [31:0] fp8r(input [31:0] v);
        reg [7:0] ex; reg [22:0] mt; reg [24:0] sig; reg [4:0] sh; reg [24:0] n, rem, half;
        reg [3:0] m4; reg up; integer e; reg [31:0] y;
        begin
            ex = v[30:23]; mt = v[22:0]; e = ex - 127;
            if (ex == 0) y = 32'd0;                                   // zero (and FP32 subnormals: below 2^-9)
            else if (e >= -6) begin
                up = v[19] && ((|v[18:0]) || v[20]);
                m4 = {1'b1, v[22:20]} + up;                          // 8..16
                if (m4 == 0) begin e = e + 1; m4 = 4'd8; end          // 16 wraps: the next binade
                if (e > 8 || (e == 8 && m4 > 4'd14)) y = {v[31], 8'd135, 3'b110, 20'd0};   // saturate at 448
                else y = {v[31], e[7:0] + 8'd127, m4[2:0], 20'd0};
            end else begin
                // subnormal: n = round(|v| / 2^-9), |v| = sig * 2^(e-23), sh = 14 - e
                sig = {2'b01, mt};
                if (ex < 8'd116) y = 32'd0;
                else begin
                    case (ex)
                        8'd116:  n = fp8r_sub(sig, 25);
                        8'd117:  n = fp8r_sub(sig, 24);
                        8'd118:  n = fp8r_sub(sig, 23);
                        8'd119:  n = fp8r_sub(sig, 22);
                        default: n = fp8r_sub(sig, 21);
                    endcase
                    if (n == 0) y = 32'd0;
                    else if (n[3]) y = {v[31], 8'd121, 23'd0};          // 8 x 2^-9 = 2^-6
                    else if (n[2]) y = {v[31], 8'd120, n[1:0], 21'd0};
                    else if (n[1]) y = {v[31], 8'd119, n[0], 22'd0};
                    else y = {v[31], 8'd118, 23'd0};
                end
            end
            fp8r = y;
        end
    endfunction

    integer ex, s, bad; longint m, nchk;
    reg [31:0] v;
    initial begin
        bad = 0; nchk = 0;
        for (ex = 100; ex <= 135; ex = ex + 1)
            for (s = 0; s < 2; s = s + 1)
                for (m = 0; m < (1 << 23); m = m + 1) begin
                    v = {s[0], ex[7:0], m[22:0]};
                    if (fp8r(v) !== fp8r_ref(v)) bad = bad + 1;
                    nchk = nchk + 1;
                end
        for (m = 0; m < (1 << 26); m = m + 1) begin
            v = $urandom;
            if (fp8r(v) !== fp8r_ref(v)) bad = bad + 1;
            nchk = nchk + 1;
        end
        $display("RESULT fp8r_equiv checked=%0d mismatches=%0d", nchk, bad);
        $finish;
    end
endmodule
