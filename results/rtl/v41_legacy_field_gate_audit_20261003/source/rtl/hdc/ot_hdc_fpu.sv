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
    // stage 2: the 8x8 product
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [15:0] s2_p;
    reg signed [10:0] s2_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf; s2_e <= s1_e;
        s2_p <= s1_a * s1_b;
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
