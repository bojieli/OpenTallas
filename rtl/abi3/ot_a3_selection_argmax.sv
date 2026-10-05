`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SELECTION.ARGMAX -- the only place on this device where a token comes into
// existence, and therefore the datapath whose disagreement is a different
// answer rather than a different number.
//
// ADR-003 section 8.7 makes selection a device operation.  The frozen rule is
// ``greedy_lowest_token_id_argmax``: widen the logits to binary32, take the
// maximum, and select the *lowest* token ID among the maxima.  This block
// keeps the lowest by construction -- the running best is replaced only on a
// strictly greater key, never on an equal one -- so the tie rule is a property
// of the comparison and not of a later fix-up.
//
// Signed zero is canonicalised before the comparison key is formed, because
// +0.0 and -0.0 compare equal in binary32 and a logits vector that reaches the
// maximum at both must still select the lower index.
//
// A NaN or infinite logit is a numeric fault, not a value to skip: the block
// stops with ERR_SELECT_NONFINITE and writes no token.  The tie multiplicity
// is published beside the token because the functional simulator counts it and
// a silent tie is how a greedy decode stops being reproducible.
// ---------------------------------------------------------------------------
module ot_a3_selection_argmax (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_count,        // vocabulary elements
    input  wire [7:0]  cfg_dtype,        // BF16 or FP32
    input  wire [31:0] cfg_in_base,
    input  wire [31:0] cfg_out_base,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] token,
    output reg  [31:0] tie_multiplicity,
    output reg  [31:0] elements_read
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

    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_ISSUE   = 3'd1;
    // The logits memory answers one cycle after the address is driven.
    localparam [2:0] S_WAIT    = 3'd5;
    localparam [2:0] S_COMPARE = 3'd2;
    localparam [2:0] S_STORE   = 3'd3;
    localparam [2:0] S_DONE    = 3'd4;

    reg [2:0]  state;
    reg [31:0] index;
    reg [31:0] best_key;
    reg        have_best;

    wire [33:0] decoded = ot_a3_format_pkg::decode_element(cfg_dtype, a_rd_data);
    wire [31:0] key = ot_a3_engine_pkg::order_key(decoded[31:0]);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            token <= 32'b0;
            tie_multiplicity <= 32'b0;
            elements_read <= 32'b0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            index <= 32'b0;
            best_key <= 32'b0;
            have_best <= 1'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            a_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        token <= 32'b0;
                        tie_multiplicity <= 32'b0;
                        elements_read <= 32'b0;
                        index <= 32'b0;
                        best_key <= 32'b0;
                        have_best <= 1'b0;
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
                    a_rd_addr <= cfg_in_base + index;
                    state <= S_WAIT;
                end

                S_WAIT: begin
                    state <= S_COMPARE;
                end

                S_COMPARE: begin
                    if (decoded[33:32] != 2'd0) begin
                        error_code <= ERR_SELECT_NONFINITE;
                        state <= S_DONE;
                    end else begin
                        elements_read <= elements_read + 32'd1;
                        if (!have_best || (key > best_key)) begin
                            have_best <= 1'b1;
                            best_key <= key;
                            token <= index;
                            tie_multiplicity <= 32'd1;
                        end else if (key == best_key) begin
                            tie_multiplicity <= tie_multiplicity + 32'd1;
                        end
                        if (index + 32'd1 == cfg_count) begin
                            state <= S_STORE;
                        end else begin
                            index <= index + 32'd1;
                            state <= S_ISSUE;
                        end
                    end
                end

                S_STORE: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base;
                    out_data <= token;
                    state <= S_DONE;
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
