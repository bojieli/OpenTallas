`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.SILU_MUL -- the Qwen SwiGLU gate, under qwen3_silu_mul_bf16_v1.
//
// The contract is not "SiLU times up".  It is a specific, explicitly rounded
// subgraph, and the golden authority for it is
// ``runtime.reference.tensor_accelerator_elementwise.qwen3_silu_mul_bf16``
// together with ``_sigmoid_binary32_from_bf16``.  Per element, in this order:
//
//   1. sigmoid, in the stable sign-selected form.  For a gate code whose sign
//      bit is set the argument is already nonpositive, so the engine takes
//      e = exp(gate), d = 1 + e (one binary32 RNE add), sigma = e / d.  For a
//      gate code whose sign bit is clear the argument is negated first -- and
//      +0.0 negates to +0.0, not to -0.0, which is why the zero case is
//      written out rather than left to a sign flip -- then sigma = 1 / d.
//      *One* correctly rounded binary32 exponential, *one* binary32 add and
//      *one* correctly rounded binary32 division.  This is deliberately not
//      the correctly rounded sigmoid: OP_SIGMOID on the shared transcendental
//      would round once where the contract rounds three times, and would
//      differ from the golden model in the last bit.  The engine therefore
//      uses OP_EXP_NONPOS and composes the rest itself.
//   2. the SiLU activation materialises: gate * sigma in binary32, then one
//      RNE conversion to BF16.  The contract makes this a *stored* BF16
//      value, not an internal binary32 one, so the second product reads the
//      rounded activation back and not the wider product.
//   3. the gated output: activation * up in binary32, then one RNE
//      conversion to BF16.
//
// Both conversions saturate to the largest finite BF16 code and are counted
// separately, because the golden model reports the activation saturation and
// the output saturation as two different numbers.  A nonfinite BF16 operand,
// an exponential the shared engine will not certify, a division the shared
// divider refuses, and a product or sum that leaves binary32 range each stop
// the block with no further write.
//
// The exponential and the divider are the already-qualified shared blocks
// (rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv and
// rtl/abi3/ot_a3_fp32_div_rne.sv), not a new approximation.
// ---------------------------------------------------------------------------
module ot_a3_vector_silu_mul (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_gate_base,
    input  wire [31:0] cfg_up_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [31:0] b_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] activation_saturation_count,
    output reg  [31:0] work_count
);
    // Package constants are re-declared as local parameters and package
    // functions are called through their scope, never pulled in with a
    // wildcard import: Icarus 11 turns a wildcard-imported identifier that
    // appears only in a port connection into an implicit net, and the pinned
    // Yosys 0.68 Verilog frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [31:0] FP32_ONE = 32'h3f80_0000;

    localparam [3:0] S_IDLE     = 4'd0;
    localparam [3:0] S_ISSUE    = 4'd1;
    // Both operand memories answer one cycle after the address is driven.
    localparam [3:0] S_WAIT     = 4'd2;
    localparam [3:0] S_LATCH    = 4'd3;
    localparam [3:0] S_EXP_REQ  = 4'd4;
    localparam [3:0] S_EXP_RSP  = 4'd5;
    localparam [3:0] S_DENOM    = 4'd6;
    localparam [3:0] S_DIV_REQ  = 4'd7;
    localparam [3:0] S_DIV_RSP  = 4'd8;
    localparam [3:0] S_SILU     = 4'd9;
    localparam [3:0] S_GATE     = 4'd10;
    localparam [3:0] S_STORE    = 4'd11;
    localparam [3:0] S_DONE     = 4'd12;

    reg [3:0]  state;
    reg [31:0] index;
    reg [15:0] gate_code_q;
    reg [15:0] up_code_q;
    reg [31:0] exponential_q;
    reg [31:0] denominator_q;
    reg [31:0] sigmoid_q;
    reg [15:0] activation_q;
    reg [31:0] gated_q;

    wire [33:0] gate_decoded = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] up_decoded = ot_a3_format_pkg::decode_bf16(b_rd_data[15:0]);

    // The stable sign-selected exponential argument.  A gate code with the
    // sign bit set is already nonpositive; a clear sign bit negates, and the
    // zero code negates to positive zero rather than to negative zero.
    wire gate_negative = gate_code_q[15];
    wire gate_zero_magnitude = (gate_code_q[14:0] == 15'b0);
    wire [31:0] exponential_argument = gate_negative
        ? {gate_code_q, 16'b0}
        : (gate_zero_magnitude ? 32'b0 : {1'b1, gate_code_q[14:0], 16'b0});

    wire        exp_in_ready;
    wire        exp_out_valid;
    wire [31:0] exp_result;
    wire [1:0]  exp_error;

    ot_a3_fp32_transcendental_cr_rne exponential (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_EXP_REQ), .in_ready(exp_in_ready),
        .operation(1'b0), .argument_code(exponential_argument),
        .out_valid(exp_out_valid), .out_ready(state == S_EXP_RSP),
        .result_code(exp_result), .result_error(exp_error)
    );

    wire [33:0] denominator_add =
        ot_fp32_rne_pkg::fp32_add_rne(FP32_ONE, exponential_q);

    wire        divider_in_ready;
    wire        divider_out_valid;
    wire [31:0] divider_result;
    wire [1:0]  divider_error;

    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_DIV_REQ), .in_ready(divider_in_ready),
        .numerator_code(gate_negative ? exponential_q : FP32_ONE),
        .denominator_code(denominator_q),
        .out_valid(divider_out_valid), .out_ready(state == S_DIV_RSP),
        .result_code(divider_result), .result_error(divider_error)
    );

    wire [33:0] silu_product =
        ot_fp32_rne_pkg::fp32_mul_rne({gate_code_q, 16'b0}, sigmoid_q);
    wire [18:0] silu_bf16 =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(silu_product[31:0]);
    wire [33:0] gated_product = ot_fp32_rne_pkg::fp32_mul_rne(
        {activation_q, 16'b0}, {up_code_q, 16'b0}
    );
    wire [18:0] gated_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(gated_q);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'b0;
            saturation_count <= 32'b0;
            activation_saturation_count <= 32'b0;
            work_count <= 32'b0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 32'b0;
            b_rd_en <= 1'b0;
            b_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            index <= 32'b0;
            gate_code_q <= 16'b0;
            up_code_q <= 16'b0;
            exponential_q <= 32'b0;
            denominator_q <= 32'b0;
            sigmoid_q <= 32'b0;
            activation_q <= 16'b0;
            gated_q <= 32'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 32'b0;
                        saturation_count <= 32'b0;
                        activation_saturation_count <= 32'b0;
                        work_count <= 32'b0;
                        index <= 32'b0;
                        if (cfg_count == 32'b0) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                S_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_gate_base + index;
                    b_rd_en <= 1'b1;
                    b_rd_addr <= cfg_up_base + index;
                    state <= S_WAIT;
                end

                S_WAIT: state <= S_LATCH;

                S_LATCH: begin
                    if ((gate_decoded[33:32] != 2'd0) ||
                        (up_decoded[33:32] != 2'd0)) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        gate_code_q <= a_rd_data[15:0];
                        up_code_q <= b_rd_data[15:0];
                        state <= S_EXP_REQ;
                    end
                end

                S_EXP_REQ: begin
                    if (exp_in_ready)
                        state <= S_EXP_RSP;
                end

                S_EXP_RSP: begin
                    if (exp_out_valid) begin
                        if (exp_error != 2'd0) begin
                            error_code <= ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end else begin
                            exponential_q <= exp_result;
                            state <= S_DENOM;
                        end
                    end
                end

                S_DENOM: begin
                    if (denominator_add[33:32] != 2'd0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        denominator_q <= denominator_add[31:0];
                        state <= S_DIV_REQ;
                    end
                end

                S_DIV_REQ: begin
                    if (divider_in_ready)
                        state <= S_DIV_RSP;
                end

                S_DIV_RSP: begin
                    if (divider_out_valid) begin
                        if (divider_error != 2'd0) begin
                            error_code <= ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end else begin
                            sigmoid_q <= divider_result;
                            state <= S_SILU;
                        end
                    end
                end

                S_SILU: begin
                    if (silu_product[33:32] != 2'd0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else if (silu_bf16[18:17] != 2'd0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        activation_q <= silu_bf16[15:0];
                        work_count <= work_count + 32'd1;
                        if (silu_bf16[16])
                            activation_saturation_count <=
                                activation_saturation_count + 32'd1;
                        state <= S_GATE;
                    end
                end

                S_GATE: begin
                    if (gated_product[33:32] != 2'd0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        gated_q <= gated_product[31:0];
                        work_count <= work_count + 32'd1;
                        state <= S_STORE;
                    end
                end

                S_STORE: begin
                    if (gated_bf16[18:17] != 2'd0) begin
                        error_code <= ERR_PRODUCT_RANGE;
                        state <= S_DONE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + index;
                        out_data <= {16'b0, gated_bf16[15:0]};
                        out_count <= out_count + 32'd1;
                        if (gated_bf16[16])
                            saturation_count <= saturation_count + 32'd1;
                        if (index + 32'd1 == cfg_count) begin
                            state <= S_DONE;
                        end else begin
                            index <= index + 32'd1;
                            state <= S_ISSUE;
                        end
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
