`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.ADD -- the residual add, under bf16_add_rne_v1.
//
// One rounding, at the output.  Both BF16 operands widen exactly to binary32
// (the architectural pattern is the high half), the sum is one binary32
// round-to-nearest-even add, and the result converts once to BF16 with the
// same RNE rule, saturating to the largest finite code and counting it.  That
// is the whole of ``runtime.tensor_accelerator.elementwise.bf16_add_rne``,
// whose scalar authority computes the same two steps without any host
// floating-point mode.
//
// A nonfinite BF16 operand and a sum that leaves the binary32 range each stop
// the block; neither is representable as a residual and neither is silently
// substituted.
// ---------------------------------------------------------------------------
module ot_a3_vector_add (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_left_base,
    input  wire [31:0] cfg_right_base,
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
    output reg  [31:0] saturation_count
);
    // Package constants are re-declared as local parameters, and package
    // functions are called through their scope, rather than being pulled in
    // with a wildcard import.  Two reasons, both found the hard way.  Icarus 11
    // does not resolve a wildcard-imported identifier that appears only inside
    // a module-instance port connection -- it silently creates an implicit net
    // of that name, which then shadows the constant for the whole module.  And
    // the pinned Yosys 0.68 Verilog frontend rejects ``import`` outright, in
    // the header and in the body, so a wildcard import is a block that cannot
    // be synthesised or routed at all.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_ISSUE = 3'd1;
    // Both operand memories answer one cycle after the address is driven.
    localparam [2:0] S_WAIT  = 3'd5;
    localparam [2:0] S_ADD   = 3'd2;
    localparam [2:0] S_STORE = 3'd3;
    localparam [2:0] S_DONE  = 3'd4;

    reg [2:0]  state;
    reg [31:0] index;
    reg [31:0] sum;

    wire [33:0] left = ot_a3_format_pkg::decode_bf16(a_rd_data[15:0]);
    wire [33:0] right = ot_a3_format_pkg::decode_bf16(b_rd_data[15:0]);
    wire [33:0] added = ot_fp32_rne_pkg::fp32_add_rne(left[31:0], right[31:0]);
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(sum);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'b0;
            saturation_count <= 32'b0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 32'b0;
            b_rd_en <= 1'b0;
            b_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            index <= 32'b0;
            sum <= 32'b0;
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
                    a_rd_addr <= cfg_left_base + index;
                    b_rd_en <= 1'b1;
                    b_rd_addr <= cfg_right_base + index;
                    state <= S_WAIT;
                end

                S_WAIT: begin
                    state <= S_ADD;
                end

                S_ADD: begin
                    if (left[33:32] != 2'd0 || right[33:32] != 2'd0) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (added[33:32] != 2'd0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        sum <= added[31:0];
                        state <= S_STORE;
                    end
                end

                S_STORE: begin
                    if (narrowed[18:17] != 2'd0) begin
                        error_code <= ERR_ACCUMULATE_RANGE;
                        state <= S_DONE;
                    end else begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + index;
                        out_data <= {16'b0, narrowed[15:0]};
                        out_count <= out_count + 32'd1;
                        if (narrowed[16])
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
