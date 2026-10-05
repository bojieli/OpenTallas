`timescale 1ns/1ps
// Correctly rounded finite-positive binary32 reciprocal square root.  A binary
// search over positive finite encodings uses exact integer comparison of
// candidate^2 * argument against one, followed by the exact midpoint/ties-even
// decision.  This is a bounded correctness implementation, not a throughput-
// optimized arithmetic macro.
//
// THE COMPARISON IS TWO CYCLES AND THERE IS ONE OF IT, WHICH IS WHY THIS MODULE
// SYNTHESISES.  It did not.  ot_a3_vector_rms_norm's route failed with
// "timed out after 14400 seconds" in 1_2_yosys -- four hours and no netlist --
// and this module synthesised alone produces nothing in ten minutes either
// (results/physical_abi3/asap7/rsqrt_is_the_rms_norm_synthesis_wall.json).
// ot_a3_hc_projection_rms_rne instantiates it too and timed out the same way.
//
// The old shape computed the comparison TWICE in one combinational block, once
// for the search's candidate and once for the midpoint, and each copy chained a
// 25-by-25 multiply into a 50-by-24 multiply, a 74-bit priority scan for the
// product's top set bit and a 74-bit OR below it.  Four wide multiplies and two
// 74-iteration loops in every cycle of a 31-step binary search.
//
// Now there is ONE comparison datapath, its operands multiplexed between the
// candidate and the midpoint, and it takes two cycles: the square in one, the
// product and the scan in the next.  So a cycle carries either a 25-by-25
// multiply or a 50-by-24 multiply and one scan -- a quarter of the multipliers
// and half the chain.
//
// NOTHING ABOUT THE ARITHMETIC CHANGES.  The same exact integer comparison on
// the same values in the same order; the search makes the same decisions and
// the midpoint/ties-even rule is the one that shipped.  The cost is CYCLES: a
// search step is two where it was one, and the midpoint comparison is two more
// at the end, so a reciprocal square root is about 64 cycles rather than 31.
// rtl/test/tb_fp32_rsqrt_split_equiv.sv drives this against the single-cycle
// form on the same arguments and compares every result bit.
module ot_fp32_rsqrt_rne (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [31:0] argument_code,
    output reg         out_valid,
    input  wire        out_ready,
    output reg  [31:0] result_code,
    output reg  [1:0]  result_error
);
    localparam [1:0] ERR_NONE = 2'd0;
    localparam [1:0] ERR_ARGUMENT = 2'd1;

    reg busy;
    reg [31:0] low_code;
    reg [31:0] high_code;
    reg [31:0] lower_code;
    reg [23:0] argument_significand;
    integer argument_power;

    wire [31:0] candidate_code =
        low_code + ((high_code - low_code) >> 1);
    reg [24:0] candidate_significand;
    integer candidate_power;
    integer comparison;
    reg [24:0] square_operand;
    integer    square_power;

    reg [31:0] upper_code;
    reg [24:0] lower_significand;
    reg [24:0] upper_significand;
    integer lower_power;
    integer upper_power;
    integer common_power;
    reg [24:0] lower_aligned;
    reg [24:0] upper_aligned;
    reg [24:0] midpoint_significand;
    integer midpoint_power;

    //: The second half of the comparison. The square is an operand now, computed
    //: a cycle earlier and registered, so this cone carries one multiply and one
    //: scan rather than two multiplies and two scans.
    function automatic integer compare_square_product_to_one;
        input [49:0] square;
        input integer value_power;
        input [23:0] arg_significand;
        input integer arg_power;
        reg [73:0] product;
        integer product_msb;
        integer combined_power;
        integer bit_index;
        reg lower_bits;
        begin
            // Explicitly widen one operand at the multiply.  This preserves
            // every exact product bit under both IEEE expression-sizing
            // interpretations used by the supported simulators/synthesizers.
            product = {{24{1'b0}}, square} * arg_significand;
            product_msb = -1;
            lower_bits = 1'b0;
            for (bit_index = 0; bit_index < 74; bit_index = bit_index + 1)
                if (product[bit_index])
                    product_msb = bit_index;
            if (product_msb < 0) begin
                compare_square_product_to_one = -1;
            end else begin
                combined_power = product_msb +
                                 2 * value_power + arg_power;
                if (combined_power < 0) begin
                    compare_square_product_to_one = -1;
                end else if (combined_power > 0) begin
                    compare_square_product_to_one = 1;
                end else begin
                    for (bit_index = 0; bit_index < 74;
                         bit_index = bit_index + 1)
                        if (bit_index < product_msb)
                            lower_bits = lower_bits | product[bit_index];
                    compare_square_product_to_one = lower_bits ? 1 : 0;
                end
            end
        end
    endfunction

    task automatic decode_positive;
        input [30:0] code;
        output [24:0] significand;
        output integer value_power;
        begin
            if (code[30:23] == 0) begin
                significand = {2'b0, code[22:0]};
                value_power = -149;
            end else begin
                significand = {1'b0, 1'b1, code[22:0]};
                value_power = {24'b0, code[30:23]};
                value_power = value_power - 150;
            end
        end
    endtask

    //: ONE comparison datapath, its operands multiplexed. During the search it
    //: sees the candidate; at the end it sees the midpoint. The square is
    //: registered between the two cycles, which is what takes the second
    //: multiply out of the first one's cone.
    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_SQUARE  = 3'd1;
    localparam [2:0] S_COMPARE = 3'd2;
    localparam [2:0] S_FIN_SQ  = 3'd3;
    localparam [2:0] S_FIN_CMP = 3'd4;
    reg [2:0]  state;
    reg [49:0] square_q;
    integer    power_q;

    always @* begin
        decode_positive(candidate_code[30:0], candidate_significand,
                        candidate_power);

        upper_code = lower_code + 1'b1;
        decode_positive(lower_code[30:0], lower_significand, lower_power);
        decode_positive(upper_code[30:0], upper_significand, upper_power);
        common_power = lower_power < upper_power ? lower_power : upper_power;
        lower_aligned = lower_significand << (lower_power - common_power);
        upper_aligned = upper_significand << (upper_power - common_power);
        midpoint_significand = lower_aligned + upper_aligned;
        midpoint_power = common_power - 1;

        //: Whose square this cycle computes: the candidate during the search,
        //: the midpoint once it has finished.
        if (state == S_FIN_SQ) begin
            square_operand = midpoint_significand;
            square_power   = midpoint_power;
        end else begin
            square_operand = candidate_significand;
            square_power   = candidate_power;
        end

        //: The second half, on the square this datapath registered a cycle ago.
        comparison = compare_square_product_to_one(
            square_q, power_q, argument_significand, argument_power
        );
    end

    assign in_ready = !busy && (!out_valid || out_ready);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            low_code <= 0;
            high_code <= 0;
            lower_code <= 0;
            argument_significand <= 0;
            argument_power <= 0;
            out_valid <= 1'b0;
            result_code <= 0;
            result_error <= ERR_NONE;
            state <= S_IDLE;
            square_q <= 50'd0;
            power_q <= 0;
        end else begin
            if (out_valid && out_ready)
                out_valid <= 1'b0;

            if (in_valid && in_ready) begin
                if (argument_code[31] || argument_code[30:23] == 8'hff ||
                    argument_code[30:0] == 0) begin
                    out_valid <= 1'b1;
                    result_code <= 0;
                    result_error <= ERR_ARGUMENT;
                end else begin
                    busy <= 1'b1;
                    low_code <= 0;
                    high_code <= 32'h7f7f_ffff;
                    lower_code <= 0;
                    if (argument_code[30:23] == 0) begin
                        argument_significand <= {1'b0, argument_code[22:0]};
                        argument_power <= -149;
                    end else begin
                        argument_significand <= {
                            1'b1, argument_code[22:0]
                        };
                        argument_power <=
                            {24'b0, argument_code[30:23]} - 32'd150;
                    end
                    result_error <= ERR_NONE;
                    state <= S_SQUARE;
                end
            end else if (busy) begin
                case (state)
                    //: One cycle of the comparison: the square, registered with
                    //: its power so the next cycle needs neither operand again.
                    S_SQUARE: begin
                        if (low_code <= high_code) begin
                            square_q <= {{25{1'b0}}, square_operand} *
                                        square_operand;
                            power_q <= square_power;
                            state <= S_COMPARE;
                        end else begin
                            //: The search is over. The midpoint decision uses the
                            //: same datapath, two cycles more.
                            state <= S_FIN_SQ;
                        end
                    end

                    //: The other cycle: the product, the scan, and the search
                    //: step's own decision -- the same decision the one-cycle
                    //: form made on the same values.
                    S_COMPARE: begin
                        if (comparison <= 0) begin
                            lower_code <= candidate_code;
                            low_code <= candidate_code + 1'b1;
                        end else begin
                            high_code <= candidate_code - 1'b1;
                        end
                        state <= S_SQUARE;
                    end

                    S_FIN_SQ: begin
                        square_q <= {{25{1'b0}}, square_operand} * square_operand;
                        power_q <= square_power;
                        state <= S_FIN_CMP;
                    end

                    S_FIN_CMP: begin
                        busy <= 1'b0;
                        out_valid <= 1'b1;
                        result_error <= ERR_NONE;
                        if (lower_code == 32'h7f7f_ffff)
                            result_code <= lower_code;
                        else if (comparison < 0)
                            result_code <= upper_code;
                        else if (comparison > 0)
                            result_code <= lower_code;
                        else
                            result_code <= lower_code[0]
                                           ? upper_code : lower_code;
                        state <= S_IDLE;
                    end

                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
