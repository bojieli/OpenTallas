
// ---------------------------------------------------------------------------
// Binary32 add, LATENCY 3, II 1.  Stage for stage:
//   1  decode; |b| > |a| as one 31-bit prefix compare of the encodings; both
//      exponent differences; the smaller significand aligned with a jam
//   2  the add and the subtract (both prefix adders); the add's one-bit
//      renormalize; the cancellation normalize, its shift the leading-zero
//      count of the difference OR a sentinel at the exponent floor
//   3  round to nearest even (prefix increment), encode, the refusals
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_fast (
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
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    //: Magnitude order is the integer order of the encodings (a subnormal's
    //: exponent 1 and a normal's hidden bit agree with it), so the swap is one
    //: compare: b[30:0] > a[30:0] exactly when a - b borrows.
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksa #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksa #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksa #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    //: Three guard bits, everything shifted past them OR-ed into the lowest.
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    //: Both alignments, then the pick: when b is the larger b's exponent is
    //: not below a's, so dba is the distance; otherwise dab.
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= bypass;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= bypass_code;
        s1_sub <= a[31] ^ b[31];
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum, dif;
    wire sum_c, dif_c;
    ot_hdc_ksa #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    ot_hdc_ksa #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif), .cout(dif_c));
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    //: The authority normalizes one bit at a time while bit 26 is clear and the
    //: exponent is above 1: the shift is min(lzc, exp - 1).  A one at bit
    //: 26 - (exp - 1) makes the count stop there.
    wire [7:0]  room = s1_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz;
    ot_hdc_lzc32 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz));
    wire [26:0] sub_val = dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksa #(.W(8)) u_esub (.a(s1_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksa #(.W(8)) u_eadd (.a(s1_exp), .b(8'd0), .cin(carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_code <= s1_code; s2_sign <= s1_sign;
        s2_zero <= s1_sub && (dif == 28'd0);
        s2_exp <= s1_sub ? exp_sub : exp_add;
        s2_val <= s1_sub ? sub_val : add_val;
    end

    // -- stage 3 ------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd), .cout(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s2_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s2_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (s2_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= s2_code; err <= s2_err; end
            else if (s2_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule
