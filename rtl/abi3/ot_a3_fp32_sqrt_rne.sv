// Correctly-rounded binary32 square root, by exact integer arithmetic.
//
// The authority is ``_binary32_sqrt_rne`` in
// runtime/reference/sqrt_softplus.py, which the DeepSeek V4 router's
// ``F.softplus(scores).sqrt()`` boundary ends in. That reference binary-searches
// the whole binary32 code space with exact rational candidates -- up to 31
// evaluations and a final exact midpoint comparison -- because it is written to
// be obviously right rather than fast. This computes the same answer directly.
//
// WHY THERE IS NO TIE TO BREAK. Write the radicand as N / 2**46 with N an
// integer in [2**46, 2**48), so the root is R / 2**23 with R = floor(sqrt(N)) in
// [2**23, 2**24). The rounding boundary is ((2R+1) / 2**24)**2, so deciding it
// compares 4*N against (2R+1)**2 -- and (2R+1)**2 is ODD while 4*N is EVEN, so
// they are never equal. A binary32 square root is never exactly halfway between
// two binary32 values. The reference's ties-to-even branch is therefore dead on
// this operator, and this module needs no tie logic at all.
//
// The comparison then collapses:
//   4*N > 4*R**2 + 4*R + 1  <=>  4*(N - R**2) > 4*R + 1  <=>  rem > R
// with rem = N - R**2, which the restoring square-root recurrence already
// carries. ROUND UP IFF THE RUNNING REMAINDER EXCEEDS THE ROOT.
//
// THE RESULT IS ALWAYS NORMAL OR ZERO, which is why no subnormal assembly path
// exists here. The smallest positive binary32 is 2**-149 and its square root is
// 2**-74.5, far inside the normal range -- squaring compresses the exponent, so
// no finite nonzero input can produce a subnormal root.
module ot_a3_fp32_sqrt_rne (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    output reg  [31:0] y,
    //: 1 when the operand is negative or nonfinite. The softplus that feeds this
    //: cannot produce either, and the reference raises rather than returning a
    //: value, so this fails closed instead of inventing a NaN.
    output reg         invalid,
    output reg         valid_out,
    output reg         busy
);
    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_NORM = 2'd1;
    localparam [1:0] S_ROOT = 2'd2;
    localparam [1:0] S_DONE = 2'd3;

    reg [1:0]  state;
    reg [47:0] radicand;
    reg [23:0] root;
    reg [49:0] rem;
    reg [4:0]  step;
    reg [9:0]  exp_half;
    reg        zero_q;

    wire        a_sign = a[31];
    wire [7:0]  a_exp  = a[30:23];
    wire [22:0] a_frac = a[22:0];
    wire        a_zero = (a_exp == 8'd0) && (a_frac == 23'd0);
    wire        a_sub  = (a_exp == 8'd0) && (a_frac != 23'd0);
    wire        a_nonfinite = (a_exp == 8'hff);

    //: A subnormal operand is normalized before the recurrence, so the
    //: recurrence itself only ever sees a 24-bit significand with its leading
    //: one in place.
    reg [4:0]  sub_lz;
    integer    k;
    always @* begin
        sub_lz = 5'd22;
        for (k = 0; k <= 22; k = k + 1)
            if (a_frac[k]) sub_lz = 5'd22 - k[4:0];
    end

    //: The unbiased exponent, and the 24-bit significand that goes with it.
    //: -127, NOT -126. A subnormal is frac * 2**-149, and shifting its leading
    //: one up to bit 23 takes sub_lz + 1 places, so the value is
    //: man * 2**(-150 - sub_lz) and the unbiased exponent is -127 - sub_lz. The
    //: check: frac = 2**22 has sub_lz 0 and value 2**22 * 2**-149 = 2**-127,
    //: which is 1.0 * 2**-127. Using -126 put every subnormal one binade high,
    //: and because the exponent is then HALVED the root came out a factor of
    //: sqrt(2) too large -- 74 of 20,210 cases, every one of them subnormal and
    //: no normal case touched.
    wire signed [10:0] norm_exp = a_sub
        ? (-11'sd127 - $signed({6'b0, sub_lz}))
        : ($signed({3'b0, a_exp}) - 11'sd127);
    wire [23:0] norm_man = a_sub
        ? ({1'b0, a_frac} << (sub_lz + 5'd1))
        : {1'b1, a_frac};

    //: THE EXPONENT IS HALVED, SO IT MUST FIRST BE MADE EVEN. An odd exponent
    //: moves one factor of two into the radicand, which is what keeps the root
    //: in [1, 2) and the result's significand exactly 24 bits wide either way.
    //: Verilog's >>> on a negative value floors, which is the wanted direction:
    //: sqrt(2**-3) has exponent -2 with the radicand doubled, not -1.
    wire               exp_is_odd = norm_exp[0];
    wire signed [10:0] even_exp = exp_is_odd ? (norm_exp - 11'sd1) : norm_exp;
    wire [47:0]        start_radicand = exp_is_odd
        ? ({24'd0, norm_man} << 24)
        : ({24'd0, norm_man} << 23);

    wire [49:0] trial = {24'd0, root, 2'b01};
    wire [23:0] rounded_man = root + 24'd1;
    //: NAMED, not indexed in place. Indexing the result of a system function --
    //: `$unsigned(...)[9:0]` -- is accepted by Verilator and REJECTED by the
    //: pinned Icarus and Yosys, so it passes every Verilator gate and fails at
    //: the second simulator and at synthesis. Tenth instance of this in the
    //: tree.
    wire signed [10:0] half_exp_signed = (even_exp >>> 1) + 11'sd127;
    wire [9:0]         half_exp_field = half_exp_signed[9:0];
    wire [49:0] shifted_rem = {rem[47:0], radicand[47:46]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; y <= 32'd0; invalid <= 1'b0;
            valid_out <= 1'b0; busy <= 1'b0;
            radicand <= 48'd0; root <= 24'd0; rem <= 50'd0;
            step <= 5'd0; exp_half <= 10'd0; zero_q <= 1'b0;
        end else begin
            valid_out <= 1'b0;
            case (state)
                S_IDLE: if (valid_in) begin
                    if (a_nonfinite || (a_sign && !a_zero)) begin
                        //: Fails closed rather than returning a NaN: the
                        //: reference raises here, and the softplus upstream
                        //: cannot produce either operand.
                        invalid <= 1'b1;
                        y <= 32'd0;
                        valid_out <= 1'b1;
                    end else if (a_zero) begin
                        //: sqrt(+-0) is +0. The reference returns code 0 for a
                        //: zero of either sign, so the negative zero a flushed
                        //: softplus can produce does not carry through.
                        invalid <= 1'b0;
                        y <= 32'd0;
                        valid_out <= 1'b1;
                    end else begin
                        invalid <= 1'b0;
                        busy <= 1'b1;
                        radicand <= start_radicand;
                        root <= 24'd0;
                        rem <= 50'd0;
                        //: The stored exponent of a root in [1, 2) is
                        //: even_exp / 2 + 127.
                        exp_half <= half_exp_field;
                        step <= 5'd0;
                        state <= S_ROOT;
                    end
                end

                //: The restoring square-root recurrence: two radicand bits and
                //: one root bit per step, twenty-four steps for a 24-bit root.
                S_ROOT: begin
                    if (shifted_rem >= trial) begin
                        rem <= shifted_rem - trial;
                        root <= {root[22:0], 1'b1};
                    end else begin
                        rem <= shifted_rem;
                        root <= {root[22:0], 1'b0};
                    end
                    radicand <= {radicand[45:0], 2'b00};
                    if (step == 5'd23) state <= S_DONE;
                    else step <= step + 5'd1;
                end

                S_DONE: begin
                    busy <= 1'b0;
                    valid_out <= 1'b1;
                    //: rem > root is the whole rounding decision, and a carry
                    //: out of the significand lands on the exponent.
                    if (rem > {26'd0, root}) begin
                        //: THIS CARRY BRANCH IS UNREACHABLE, and kept for the
                        //: same reason the reference keeps its round-to-odd
                        //: step. A mutation deleting it survives every case,
                        //: which is what prompted the proof rather than more
                        //: sampling:
                        //:
                        //: root is R in [2**23, 2**24) for a root value in
                        //: [1, 2), so carrying out needs R = 2**24 - 1 to round
                        //: up, hence an exact root of at least 2 - 2**-24 and a
                        //: radicand of at least 4 - 2**-22 + 2**-48. But the
                        //: radicand is an exact binary32 significand, or twice
                        //: one, so in [2, 4) its values are multiples of 2**-22
                        //: and the largest below four is exactly 4 - 2**-22 --
                        //: short of the threshold by 2**-48. In [1, 2) a root
                        //: below sqrt(2) cannot carry at all.
                        if (root == 24'hff_ffff)
                            y <= {1'b0, exp_half[7:0] + 8'd1, 23'd0};
                        else
                            y <= {1'b0, exp_half[7:0], rounded_man[22:0]};
                    end else begin
                        y <= {1'b0, exp_half[7:0], root[22:0]};
                    end
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
