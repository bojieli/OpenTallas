`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Timing probe: a tensor-core-style pipelined MAC.
//
// BF16 x BF16 -> FP32 accumulate, the precision pair every current accelerator
// uses for this class of work. The point of the probe is the PIPELINE, not the
// numerics: five balanced stages, one result per cycle, no combinational path
// spanning more than one of them.
//
// Contrast with ot_fp32_rne_pkg::fp32_add_rne, which resolves align -> add ->
// normalize -> round in ONE cycle through a 524-bit exact intermediate and
// therefore measures 174 MHz. A BF16 product needs only 8x8 mantissa bits, so
// the product is exact in 16 bits with no wide intermediate at all.
// ---------------------------------------------------------------------------
module ot_probe_mac_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [15:0] a,          // BF16
    input  wire [15:0] b,          // BF16
    input  wire [31:0] c,          // FP32 accumulator in
    output reg  [31:0] y,          // FP32 accumulator out
    output reg         valid_out
);
    // ---- stage 1: unpack, exponent add, exact 8x8 mantissa multiply --------
    reg        s1_v, s1_sign;
    reg [9:0]  s1_exp;             // biased sum, room for carry
    reg [15:0] s1_prod;            // 8x8 exact
    reg [31:0] s1_c;

    wire       a_zero = (a[14:0] == 15'b0);
    wire       b_zero = (b[14:0] == 15'b0);
    wire [7:0] a_man  = {1'b1, a[6:0]};
    wire [7:0] b_man  = {1'b1, b[6:0]};

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s1_sign <= 1'b0; s1_exp <= 10'b0;
                          s1_prod <= 16'b0; s1_c <= 32'b0; end
        else begin
            s1_v    <= valid_in;
            s1_sign <= a[15] ^ b[15];
            s1_exp  <= {2'b0, a[14:7]} + {2'b0, b[14:7]};
            s1_prod <= (a_zero || b_zero) ? 16'b0 : (a_man * b_man);
            s1_c    <= c;
        end

    // ---- stage 2: normalise the product into a 24-bit significand ---------
    reg        s2_v, s2_sign;
    reg [9:0]  s2_exp;
    reg [23:0] s2_man;
    reg [31:0] s2_c;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s2_v <= 1'b0; s2_sign <= 1'b0; s2_exp <= 10'b0;
                          s2_man <= 24'b0; s2_c <= 32'b0; end
        else begin
            s2_v    <= s1_v;
            s2_sign <= s1_sign;
            // the 8x8 product is 15 or 16 bits; one shift normalises it
            s2_exp  <= s1_prod[15] ? (s1_exp + 10'd1) : s1_exp;
            s2_man  <= s1_prod[15] ? {s1_prod, 8'b0} : {s1_prod[14:0], 9'b0};
            s2_c    <= s1_c;
        end

    // ---- stage 3: align the smaller operand -------------------------------
    reg        s3_v, s3_sign_p, s3_sign_c;
    reg [9:0]  s3_exp;
    reg [26:0] s3_p, s3_q;

    wire [9:0]  c_exp  = {2'b0, s2_c[30:23]} + 10'd127;   // same bias domain
    wire [23:0] c_man  = (s2_c[30:23] == 8'b0) ? 24'b0 : {1'b1, s2_c[22:0]};
    wire        p_bigger = s2_exp >= c_exp;
    wire [9:0]  shift    = p_bigger ? (s2_exp - c_exp) : (c_exp - s2_exp);
    wire [4:0]  shift_s  = (shift > 10'd26) ? 5'd26 : shift[4:0];

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s3_v <= 1'b0; s3_exp <= 10'b0; s3_p <= 27'b0;
                          s3_q <= 27'b0; s3_sign_p <= 1'b0; s3_sign_c <= 1'b0; end
        else begin
            s3_v      <= s2_v;
            s3_sign_p <= s2_sign;
            s3_sign_c <= s2_c[31];
            s3_exp    <= p_bigger ? s2_exp : c_exp;
            s3_p      <= p_bigger ? {1'b0, s2_man, 2'b0}
                                  : ({1'b0, s2_man, 2'b0} >> shift_s);
            s3_q      <= p_bigger ? ({1'b0, c_man, 2'b0} >> shift_s)
                                  : {1'b0, c_man, 2'b0};
        end

    // ---- stage 4: signed add ----------------------------------------------
    reg        s4_v, s4_sign;
    reg [9:0]  s4_exp;
    reg [27:0] s4_sum;

    wire        same     = (s3_sign_p == s3_sign_c);
    wire [27:0] added    = {1'b0, s3_p} + {1'b0, s3_q};
    wire        p_ge     = s3_p >= s3_q;
    wire [27:0] subbed   = p_ge ? ({1'b0, s3_p} - {1'b0, s3_q})
                                : ({1'b0, s3_q} - {1'b0, s3_p});

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s4_v <= 1'b0; s4_sign <= 1'b0; s4_exp <= 10'b0;
                          s4_sum <= 28'b0; end
        else begin
            s4_v    <= s3_v;
            s4_exp  <= s3_exp;
            s4_sign <= same ? s3_sign_p : (p_ge ? s3_sign_p : s3_sign_c);
            s4_sum  <= same ? added : subbed;
        end

    // ---- stage 5: normalise, round to nearest even, pack ------------------
    reg [4:0]  lz;
    wire [27:0] nrm = s4_sum << lz;
    reg [9:0]  e;
    always @* begin
        casez (s4_sum)
            28'b1???????????????????????????: lz = 5'd0;
            28'b01??????????????????????????: lz = 5'd1;
            28'b001?????????????????????????: lz = 5'd2;
            28'b0001????????????????????????: lz = 5'd3;
            28'b00001???????????????????????: lz = 5'd4;
            28'b000001??????????????????????: lz = 5'd5;
            28'b0000001?????????????????????: lz = 5'd6;
            28'b00000001????????????????????: lz = 5'd7;
            28'b000000001???????????????????: lz = 5'd8;
            28'b0000000001??????????????????: lz = 5'd9;
            28'b00000000001?????????????????: lz = 5'd10;
            28'b000000000001????????????????: lz = 5'd11;
            28'b0000000000001???????????????: lz = 5'd12;
            28'b00000000000001??????????????: lz = 5'd13;
            28'b000000000000001?????????????: lz = 5'd14;
            28'b0000000000000001????????????: lz = 5'd15;
            28'b00000000000000001???????????: lz = 5'd16;
            28'b000000000000000001??????????: lz = 5'd17;
            28'b0000000000000000001?????????: lz = 5'd18;
            28'b00000000000000000001????????: lz = 5'd19;
            28'b000000000000000000001???????: lz = 5'd20;
            28'b0000000000000000000001??????: lz = 5'd21;
            28'b00000000000000000000001?????: lz = 5'd22;
            28'b000000000000000000000001????: lz = 5'd23;
            28'b0000000000000000000000001???: lz = 5'd24;
            28'b00000000000000000000000001??: lz = 5'd25;
            28'b000000000000000000000000001?: lz = 5'd26;
            default:                          lz = 5'd27;
        endcase
    end

    wire [24:0] rounded = {1'b0, nrm[27:4]} +
                          ((nrm[3] && (nrm[2:0] != 3'b0 || nrm[4])) ? 25'd1 : 25'd0);

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin y <= 32'b0; valid_out <= 1'b0; end
        else begin
            valid_out <= s4_v;
            e = s4_exp + 10'd4 - {5'b0, lz} + (rounded[24] ? 10'd1 : 10'd0);
            if (s4_sum == 28'b0 || e < 10'd254)
                y <= 32'b0;                        // zero / underflow to zero
            else
                y <= {s4_sign, e[7:0] - 8'd127,
                      rounded[24] ? rounded[23:1] : rounded[22:0]};
        end
endmodule
