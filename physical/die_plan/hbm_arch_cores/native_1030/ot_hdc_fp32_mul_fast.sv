
// ---------------------------------------------------------------------------
// Binary32 multiply, LATENCY 3, II 1.
//   1  decode; subnormal operands normalized (tree LZC); the exponent sum;
//      the partial products and three carry-save levels (24 -> 8 rows)
//   2  the rest of the tree and the prefix final add; both exponent
//      decisions (leading bit 47 or 46) and the subnormal-result alignment
//      masks, all from the exponent sum alone
//   3  the product's top bit picks the decision; align, round, encode, refuse
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_fast (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32 u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32 u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    //: The authority's powers: field - 150 for a normal, -149 - shift for a
    //: subnormal (a normal has no leading zero, so the shift is 0 there).
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksa #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));

    //: The first three compressor levels ride in stage 1, after the normalize.
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_rows <= rows;
        s1_power <= power;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [47:0] prod;
    ot_hdc_mul24_sum u_sum (.rows(s1_rows), .p(prod));
    //: floor = power + msb; a subnormal result when floor < -126, and then the
    //: alignment is -(power + 149) whatever the msb, so only the normal path's
    //: fixed alignment (23 or 24) depends on the product.
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    //: sh_sub >= 24 whenever it is used; clamp at 63 (everything below).
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_sign <= s1_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end

    // -- stage 3 ------------------------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa #(.W(24)) u_rnd (.a(main), .b(24'd0), .cin(rb && (st || main[0])), .s(rnd), .cout(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = is_sub ? (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]})
                              : {s2_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= 32'd0; err <= s2_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule
