`timescale 1ns/1ps
// Thin wrappers over the binary32 pipes: one result per cycle, LATENCY = 5,
// IEEE RNE with gradual underflow and canonical +0 zeros.  The adder is the
// qualified rtl/proto pipe; the multiplier is its stage-rebalanced copy
// ot_hdc_fp32_mul_pipe (1,275 vs 1,052 MHz routed alone on ASAP7), proven
// cycle-equivalent by rtl/test/tb_hdc_mul_equiv.sv.
// A nonfinite operand or an overflow raises `fault` on a valid result; the
// decode core ORs every fault into one sticky status bit.
module ot_hdc_fadd (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_fp32_add_rne_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b),
                            .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_fmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_hdc_fp32_mul_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b),
                            .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

// BF16 x BF16 -> FP32 multiply, exact.  Two 8-bit significands give at most 16
// significant bits, so the binary32 product needs no rounding whenever it is
// normal, or subnormal by at most 7 bits of shift; there it is bit-identical
// to ot_fp32_mul_rne_pipe on the same operands (RN of an exact value is that
// value).  Operands arrive as binary32 words whose low 16 bits are ignored.
// A zero operand gives +0.  A product too small to be exact, an overflow or a
// nonfinite operand FAILS CLOSED through `fault` (and y = +0) -- the qualified
// pipe would round or refuse there.  LATENCY 5, like the FP32 pipe, so a
// lane's schedule does not depend on which multiplier it has.
module ot_hdc_bmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    // stage 1: decode; a subnormal significand is normalised by its top bit
    function automatic [17:0] dec;   // {sig[7:0], E[9:0] signed}
        input [7:0] e;
        input [6:0] m;
        integer i;
        reg [2:0] p;
        begin
            if (e != 0) dec = {1'b1, m, e - 10'sd127};
            else begin
                p = 0;
                for (i = 0; i < 7; i = i + 1) if (m[i]) p = i[2:0];
                dec = {({1'b0, m} << (7 - p)), $signed(-10'sd133) + $signed({7'd0, p})};
            end
        end
    endfunction
    wire [17:0] da = dec(a[30:23], a[22:16]);
    wire [17:0] db = dec(b[30:23], b[22:16]);
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= v;
    end
    always @(posedge clk) begin
        s1_s <= a[31] ^ b[31];
        s1_z <= (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2: the 8x8 product, a carry-save tree and a kept prefix adder (a flattened `*` is re-mapped by
    // ABC as a ripple carry chain: -496 ps at 0.833 ns SS); the product is unchanged
    wire [15:0] p8x8;
    ot_hdc_mul8x8_cs u_m (.a(s1_a), .b(s1_b), .p(p8x8));
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [15:0] s2_p;
    reg signed [10:0] s2_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf; s2_e <= s1_e;
        s2_p <= p8x8;
    end
    // stage 3: normalise (leading bit 15 or 14) and bias
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (s2_p[15]) begin s3_f <= {s2_p[14:0], 8'd0}; s3_be <= s2_e + 11'sd128; end
        else          begin s3_f <= {s2_p[13:0], 9'd0}; s3_be <= s2_e + 11'sd127; end
    end
    // stage 4: encode; a subnormal result shifts right by 1 - biased (<= 7)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire [3:0]  sub_sh = 4'd1 - s3_be[3:0];
    wire [23:0] sub_v = sig24 >> sub_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= s3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (s3_z && !s3_nf) s4_y <= 32'd0;
        else if (s3_nf || s3_be > 11'sd254 || s3_be < -11'sd6) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (s3_be >= 11'sd1) s4_y <= {s3_s, s3_be[7:0], s3_f};
        else s4_y <= {s3_s, 8'd0, sub_v[22:0]};
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule

// 8 x 8 unsigned product: AND array, 3:2 carry-save levels (8 -> 6 -> 4 -> 3 -> 2 rows), kept Kogge-Stone final add
module ot_hdc_mul8x8_cs (
    input  wire [7:0]  a,
    input  wire [7:0]  b,
    output wire [15:0] p
);
    function automatic [31:0] csa;        // {carry, sum} of three 16-bit rows
        input [15:0] r0, r1, r2;
        begin
            csa[15:0] = r0 ^ r1 ^ r2;
            csa[31:16] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [16*8-1:0] l0;
    genvar i;
    generate for (i = 0; i < 8; i = i + 1) begin : g_pp
        assign l0[16*i +: 16] = {8'd0, a & {8{b[i]}}} << i;
    end endgenerate
    (* keep *) wire [16*6-1:0] l1;
    (* keep *) wire [16*4-1:0] l2;
    (* keep *) wire [16*3-1:0] l3;
    (* keep *) wire [16*2-1:0] l4;
    assign l1[0 +: 32]  = csa(l0[0 +: 16], l0[16 +: 16], l0[32 +: 16]);
    assign l1[32 +: 32] = csa(l0[48 +: 16], l0[64 +: 16], l0[80 +: 16]);
    assign l1[64 +: 32] = l0[96 +: 32];
    assign l2[0 +: 32]  = csa(l1[0 +: 16], l1[16 +: 16], l1[32 +: 16]);
    assign l2[32 +: 32] = csa(l1[48 +: 16], l1[64 +: 16], l1[80 +: 16]);
    assign l3[0 +: 32]  = csa(l2[0 +: 16], l2[16 +: 16], l2[32 +: 16]);
    assign l3[32 +: 16] = l2[48 +: 16];
    assign l4 = csa(l3[0 +: 16], l3[16 +: 16], l3[32 +: 16]);
    // kept prefix levels (as ot_hdc_ksa, local so this file stands alone)
    localparam integer L = 4;
    generate
        for (i = 0; i <= L; i = i + 1) begin : g_lv
            (* keep *) wire [15:0] g, q;
            if (i == 0) begin : g0
                assign g = l4[0 +: 16] & l4[16 +: 16];
                assign q = l4[0 +: 16] ^ l4[16 +: 16];
            end else begin : gi
                genvar j;
                for (j = 0; j < 16; j = j + 1) begin : g_b
                    if (j >= (1 << (i - 1))) begin : g_op
                        assign g[j] = g_lv[i-1].g[j] | (g_lv[i-1].q[j] & g_lv[i-1].g[j - (1 << (i - 1))]);
                        assign q[j] = g_lv[i-1].q[j] & g_lv[i-1].q[j - (1 << (i - 1))];
                    end else begin : g_pass
                        assign g[j] = g_lv[i-1].g[j];
                        assign q[j] = g_lv[i-1].q[j];
                    end
                end
            end
        end
    endgenerate
    assign p = (l4[0 +: 16] ^ l4[16 +: 16]) ^ {g_lv[L].g[14:0], 1'b0};
endmodule
