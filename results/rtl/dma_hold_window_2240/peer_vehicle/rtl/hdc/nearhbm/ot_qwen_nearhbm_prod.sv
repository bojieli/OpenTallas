`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_nearhbm_prod: the EXACT product bf16(x) x fp8_e4m3(k) as a binary32, LAT 4, one per cycle.  NEW (near-HBM
// attention lanes); proven bit-identical to the golden's mul (tools/hdc_golden.py: numpy binary32 RNE with
// canonical +0) on ALL 2^16 x 2^8 operand pairs by rtl/test/nearhbm/tb_qwen_nearhbm_prod.cpp.
//
// An 8-bit x 4-bit significand product has at most 12 significant bits, and its LSB weight is at least
// 2^-133 x 2^-9 = 2^-142 > 2^-149, so the product is representable: no rounding ever happens, only normalisation
// (normal result) or alignment to the subnormal grid.  A zero product is +0 (the golden's z()).  A BF16 Inf/NaN, an
// E4M3 NaN (S.1111.111) or a product above the binary32 range FAILS CLOSED (fault, y = +0) -- the golden would
// carry an Inf there, which the qualified pipes refuse as well.
// Why not ot_mac_bf16_fp32_pipe: its align and round stages close at 593-793 MHz at SS (pre-layout); this unit has
// neither (nothing to align, nothing to round).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_prod (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [15:0] a,            // BF16
    input  wire [7:0]  k,            // FP8 E4M3 (bias 7)
    output reg  [31:0] y,
    output reg         fault,        // registered with y
    output reg         valid_out
);
    // ---- stage 1: decode, 8 x 4 significand product, LSB exponent -----------------------------------------------
    wire        a_sub = (a[14:7] == 8'd0);
    wire [7:0]  sa = {!a_sub, a[6:0]};
    wire [9:0]  ea = a_sub ? 10'd1 : {2'd0, a[14:7]};               // LSB weight 2^(ea - 134)
    wire        k_sub = (k[6:3] == 4'd0);
    wire [3:0]  sk = {!k_sub, k[2:0]};
    wire [9:0]  ek = k_sub ? 10'd1 : {6'd0, k[6:3]};                // LSB weight 2^(ek - 10)
    wire        bad1 = (a[14:7] == 8'hFF) || (k[6:0] == 7'h7F);
    reg         v1, s1_sign, s1_bad;
    reg [11:0]  s1_p;
    reg [9:0]   s1_e;                                              // E + 149 = ea + ek + 5  (>= 7)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v1 <= 1'b0; else v1 <= valid_in;
    end
    always @(posedge clk) begin
        s1_sign <= a[15] ^ k[7];
        s1_bad <= bad1;
        s1_p <= sa * sk;
        s1_e <= ea + ek + 10'd5;
    end
    // ---- stage 2: leading one, exponent, placement shift amounts -------------------------------------------------
    reg [3:0] lz;                                                  // position of the leading one (0..11)
    integer i;
    always @* begin
        lz = 4'd0;
        for (i = 0; i < 12; i = i + 1) if (s1_p[i]) lz = i[3:0];
    end
    // value = p x 2^(s1_e - 149); leading one at 2^(s1_e - 149 + lz); biased exponent be = s1_e - 22 + lz
    wire [10:0] be = {1'b0, s1_e} + {7'd0, lz} - 11'd22;
    reg         v2, s2_bad, s2_zero, s2_sign, s2_ovf, s2_normal;
    reg [11:0]  s2_p;
    reg [7:0]   s2_be;
    reg [4:0]   s2_sh;                                             // left shift of p into the 23-bit field
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v2 <= 1'b0; else v2 <= v1;
    end
    always @(posedge clk) begin
        s2_bad <= s1_bad;
        s2_sign <= s1_sign;
        s2_zero <= (s1_p == 12'd0);
        s2_p <= s1_p;
        s2_normal <= !be[10] && (be != 11'd0);
        s2_ovf <= !be[10] && (be >= 11'd255);
        s2_be <= be[7:0];
        // normal: the leading one to bit 23 (dropped); subnormal: LSB 2^-149 at bit 0 (s1_e >= 7, < 23 here)
        s2_sh <= (!be[10] && (be != 11'd0)) ? (5'd23 - {1'b0, lz}) : s1_e[4:0];
    end
    // ---- stage 3: placement -------------------------------------------------------------------------------------
    wire [34:0] sh = {23'd0, s2_p} << s2_sh;
    reg         v3, s3_bad, s3_zero, s3_ovf;
    reg [31:0]  s3_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v3 <= 1'b0; else v3 <= v2;
    end
    always @(posedge clk) begin
        s3_bad <= s2_bad;
        s3_zero <= s2_zero;
        s3_ovf <= s2_ovf;
        s3_y <= {s2_sign, s2_normal ? s2_be : 8'd0, sh[22:0]};
    end
    // ---- stage 4: canonical zero, refusals ---------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin valid_out <= 1'b0; y <= 32'd0; fault <= 1'b0; end
        else begin
            valid_out <= v3;
            if (s3_bad || s3_ovf) begin y <= 32'd0; fault <= v3; end
            else begin y <= s3_zero ? 32'd0 : s3_y; fault <= 1'b0; end
        end
    end
endmodule
