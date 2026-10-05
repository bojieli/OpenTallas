`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact FP4 (E2M1 x E4M3-per-16) re-encoder of a compressed-KV row from its
// dequantised BF16 values (DeepSeek-V4.1, tools/hdc_golden_v41.py qdq_fp4_e4m3).
//
// The core's QE QDQ4E writes y = BF16(sign(x) * E2M1[code] * s) for the 512
// elements of the position's new compressed row; the 288-B stored row needs
// the codes and the 32 E4M3 scales.  The golden's scale is
//   s = min(E4M3(max(amax_x, 6 * 2^-9) / 6), 448).
// Its largest code is always E2M1 6 (|x| / s rounds to 6 when s comes from
// amax_x: the E4M3 rounding keeps amax_x / s within (5.65, 6.4); saturation
// clamps to 6), unless the floor is active (s = 2^-9).  Hence, from y alone,
//   s = 2^-9                    if amax_y <= 6 * 2^-9
//   s = amax_y / 6              otherwise (exact, an E4M3 value),
// which is the golden's s; code_i = the E2M1 index m with |y_i| = m * s and
// sign(y_i) (a +0 element encodes as code 0, a -0 as code 8 -- the qdq value).
// Every m * s has at most eight significant bits, so all tests are equalities
// on BF16 bit patterns.  A value that is not m * s for the found s faults.
//
// Interface: ld_v with all 512 values (vals[16*i +: 16] = element i, BF16);
// one 16-element block per cycle; o_v (pulse) with o_row = the DMA row format
// (512 nibbles low first at bits 4i, 32 E4M3 scales at 2048 + 8b), o_fault.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_row_encoder (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire [8191:0] vals,
    output wire          busy,
    output reg           o_v,
    output reg  [2303:0] o_row,
    output reg           o_fault
);
    // BF16 of (P * 2^e), P a positive integer < 256 (exact), or 0
    function automatic [15:0] bf16_of(input [7:0] p, input integer e);
        integer hi, k, be;
        reg [7:0] m;
        begin
            hi = 0;
            for (k = 0; k < 8; k = k + 1) if (p[k]) hi = k;
            be = e + hi + 127;
            m = 8'(p << (7 - hi));                    // 1.xxxxxxx
            bf16_of = (p == 0) ? 16'd0 : {1'b0, 8'(be), m[6:0]};
        end
    endfunction
    // E4M3 scale code c (positive, 1..126) as S * 2^E, S in 1..15
    function automatic [7:0] e4m3_sig(input [6:0] c);
        e4m3_sig = (c[6:3] == 0) ? {5'd0, c[2:0]} : {4'd0, 1'b1, c[2:0]};
    endfunction
    function automatic integer e4m3_exp(input [6:0] c);
        e4m3_exp = (c[6:3] == 0) ? -9 : (integer'(c[6:3]) - 10);
    endfunction
    // E2M1 magnitudes as M * 2^-1: M in {0,1,2,3,4,6,8,12}
    function automatic [3:0] e2m1_m(input [2:0] i);
        case (i) 3'd0: e2m1_m = 0; 3'd1: e2m1_m = 1; 3'd2: e2m1_m = 2; 3'd3: e2m1_m = 3;
                 3'd4: e2m1_m = 4; 3'd5: e2m1_m = 6; 3'd6: e2m1_m = 8; default: e2m1_m = 12; endcase
    endfunction

    reg [8191:0] v;
    reg [5:0] blk;
    reg act;
    assign busy = act;
    wire [255:0] bv = v[blk*256 +: 256];
    // block amax (magnitude bits compare as integers)
    integer i, c, k;
    reg [14:0] amax;
    reg [6:0] sc;
    reg found, bad;
    reg [63:0] codes;
    reg [15:0] t;
    always @(*) begin
        amax = 0;
        for (i = 0; i < 16; i = i + 1)
            if (bv[16*i +: 15] > amax) amax = bv[16*i +: 15];
        // s = 2^-9 if amax <= 6 * 2^-9 (= 12 * 2^-10), else the c with bf16(6 s(c)) == amax
        found = 1'b0; sc = 7'd1;
        if ({1'b0, amax} <= bf16_of(8'd12, -10)) begin found = 1'b1; sc = 7'd1; end
        else for (c = 1; c < 127; c = c + 1)
            if (!found && {1'b0, amax} == bf16_of(8'(12 * e4m3_sig(7'(c))), e4m3_exp(7'(c)) - 1)) begin
                found = 1'b1; sc = 7'(c);
            end
        bad = !found;
        codes = 0;
        for (i = 0; i < 16; i = i + 1) begin
            reg hit;
            hit = 1'b0;
            for (k = 0; k < 8; k = k + 1) begin
                t = bf16_of(8'(e2m1_m(3'(k)) * e4m3_sig(sc)), e4m3_exp(sc) - 1);
                if (!hit && bv[16*i +: 15] == t[14:0]) begin hit = 1'b1; codes[4*i +: 4] = {bv[16*i + 15], 3'(k)}; end
            end
            if (!hit || bv[16*i +: 15] >= 15'h7F80) bad = 1'b1;     // not m * s, or non-finite
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin act <= 0; blk <= 0; o_v <= 0; o_fault <= 0; end
        else begin
            o_v <= 1'b0;
            if (ld_v && !act) begin v <= vals; blk <= 0; act <= 1; o_fault <= 0; end
            else if (act) begin
                o_row[64*blk +: 64] <= codes;
                o_row[2048 + 8*blk +: 8] <= {1'b0, sc};
                if (bad) o_fault <= 1'b1;
                blk <= blk + 1'b1;
                if (blk == 6'd31) begin act <= 0; o_v <= 1'b1; end
            end
        end
    end
endmodule
