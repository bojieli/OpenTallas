`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SELECTION.TOKEN_APPEND -- the instruction that ends a generation, or does
// not.
//
// ADR-003 section 8.7 makes token selection a device operation, and this is
// the second half of it: ARGMAX decides which token, TOKEN_APPEND decides
// whether the session continues.  The golden authority is
// ``runtime.sim.engines.selection.token_append``, and every one of its checks
// is reproduced here in the same order, because each is a different refusal:
//
//   * the bound GENERATION_POLICY must declare GREEDY_ARGMAX_LOWEST_ID.  A
//     policy naming a sampling mode is a capability refusal, not a shape one:
//     this device implements no sampling contract.
//   * the request's MAX_NEW_TOKENS must lie in 1..the policy's ceiling.  The
//     immutable policy is the deployment bound; the authenticated request
//     carries the active one, and a request outside the policy is refused.
//   * the policy's declared EOS count must lie in 0..8, the frozen ABI bound.
//   * the token must lie inside the policy's vocabulary.  A token outside it
//     is a numeric fault -- it is not clamped, and it is not appended.
//
// Only after all four does the token become architecturally visible: the
// optional token-ring output view is written, the append is counted, and the
// EOS reason is published.  Membership of the policy's EOS set raises
// OFFICIAL_EOS; otherwise reaching the request's token ceiling raises
// MAX_NEW_TOKENS.  EOS membership wins, exactly as the golden model returns
// early on it, so a final token that is also the length stop reports the
// official reason and not the length one.
//
// No write happens on any refusal: ``out_we`` is asserted only from the store
// state, which is unreachable once a refusal has been taken.
//
// One ordering is deliberately stricter than the golden model's, and it is
// recorded here rather than left for someone to find.  The golden model tests
// the policy's EOS *count* after it has already appended the token and written
// the ring; this engine tests the whole policy record before it reads the
// token object at all.  The difference is unobservable in the integrated path
// -- ot_a3_engine_issue_bridge refuses a GENERATION_POLICY declaring more than
// the frozen eight EOS tokens with a DESCRIPTOR trap, so such a policy never
// reaches this engine -- and where it is observable, in this block's own
// campaign, the strict order is the safe one: a policy record this device
// cannot honour causes no architectural read and no architectural write.
// ---------------------------------------------------------------------------
module ot_a3_selection_token_append (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    // the single U32 token element produced by the preceding selection
    input  wire [31:0] cfg_token_base,
    // the optional token-ring output element
    input  wire        cfg_ring_bound,
    input  wire [31:0] cfg_out_base,
    // bound GENERATION_POLICY fields
    input  wire [7:0]  cfg_selection_mode,
    input  wire [15:0] cfg_eos_count,
    input  wire [31:0] cfg_policy_max_new_tokens,
    input  wire [31:0] cfg_vocabulary,
    input  wire [31:0] cfg_eos_token_0,
    input  wire [31:0] cfg_eos_token_1,
    input  wire [31:0] cfg_eos_token_2,
    input  wire [31:0] cfg_eos_token_3,
    input  wire [31:0] cfg_eos_token_4,
    input  wire [31:0] cfg_eos_token_5,
    input  wire [31:0] cfg_eos_token_6,
    input  wire [31:0] cfg_eos_token_7,
    // the authenticated request bound and the tokens already produced
    input  wire [31:0] cfg_request_max_new_tokens,
    input  wire [31:0] cfg_generated_before,

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [31:0] a_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg         refusal_capability,
    output reg  [31:0] token,
    output reg  [7:0]  eos_reason,
    output reg  [31:0] appended_count,
    output reg  [31:0] out_count
);
    // Package constants are re-declared as local parameters and package
    // functions are called through their scope, never pulled in with a
    // wildcard import: Icarus 11 turns a wildcard-imported identifier that
    // appears only in a port connection into an implicit net, and the pinned
    // Yosys 0.68 Verilog frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    // runtime.abi3.descriptors.SelectionMode
    localparam [7:0] MODE_GREEDY_ARGMAX_LOWEST_ID = 8'd0;
    // runtime.abi3.descriptors.MAX_EOS_TOKENS
    localparam [15:0] MAX_EOS_TOKENS = 16'd8;
    // runtime.abi3.records.EosReason
    localparam [7:0] EOS_NONE = 8'd0;
    localparam [7:0] EOS_OFFICIAL = 8'd1;
    localparam [7:0] EOS_MAX_NEW_TOKENS = 8'd2;

    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_ISSUE   = 3'd1;
    // The token memory answers one cycle after the address is driven.
    localparam [2:0] S_WAIT    = 3'd2;
    localparam [2:0] S_ADMIT   = 3'd3;
    localparam [2:0] S_STORE   = 3'd4;
    localparam [2:0] S_DONE    = 3'd5;

    reg [2:0] state;

    wire [31:0] observed_token = a_rd_data;
    wire eos_member =
        ((cfg_eos_count > 16'd0) && (observed_token == cfg_eos_token_0)) ||
        ((cfg_eos_count > 16'd1) && (observed_token == cfg_eos_token_1)) ||
        ((cfg_eos_count > 16'd2) && (observed_token == cfg_eos_token_2)) ||
        ((cfg_eos_count > 16'd3) && (observed_token == cfg_eos_token_3)) ||
        ((cfg_eos_count > 16'd4) && (observed_token == cfg_eos_token_4)) ||
        ((cfg_eos_count > 16'd5) && (observed_token == cfg_eos_token_5)) ||
        ((cfg_eos_count > 16'd6) && (observed_token == cfg_eos_token_6)) ||
        ((cfg_eos_count > 16'd7) && (observed_token == cfg_eos_token_7));
    wire [32:0] produced_after = {1'b0, cfg_generated_before} + 33'd1;
    wire length_stop =
        produced_after >= {1'b0, cfg_request_max_new_tokens};

    wire policy_mode_ok = (cfg_selection_mode == MODE_GREEDY_ARGMAX_LOWEST_ID);
    wire request_bound_ok =
        (cfg_request_max_new_tokens >= 32'd1) &&
        (cfg_request_max_new_tokens <= cfg_policy_max_new_tokens);
    wire eos_count_ok = (cfg_eos_count <= MAX_EOS_TOKENS);
    wire vocabulary_ok = (cfg_vocabulary != 32'd0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            refusal_capability <= 1'b0;
            token <= 32'b0;
            eos_reason <= EOS_NONE;
            appended_count <= 32'b0;
            out_count <= 32'b0;
            a_rd_en <= 1'b0;
            a_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            a_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        refusal_capability <= 1'b0;
                        token <= 32'b0;
                        eos_reason <= EOS_NONE;
                        appended_count <= 32'b0;
                        out_count <= 32'b0;
                        // The policy is checked before the token is even
                        // read, exactly as the golden model does: a policy
                        // this device cannot honour must not cause a memory
                        // access on the token object.
                        if (!policy_mode_ok || !request_bound_ok) begin
                            error_code <= ERR_SHAPE;
                            refusal_capability <= 1'b1;
                            state <= S_DONE;
                        end else if (!eos_count_ok || !vocabulary_ok) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            state <= S_ISSUE;
                        end
                    end
                end

                S_ISSUE: begin
                    a_rd_en <= 1'b1;
                    a_rd_addr <= cfg_token_base;
                    state <= S_WAIT;
                end

                S_WAIT: state <= S_ADMIT;

                S_ADMIT: begin
                    if (observed_token >= cfg_vocabulary) begin
                        error_code <= ERR_INDEX_RANGE;
                        state <= S_DONE;
                    end else begin
                        token <= observed_token;
                        appended_count <= 32'd1;
                        eos_reason <= eos_member
                            ? EOS_OFFICIAL
                            : (length_stop ? EOS_MAX_NEW_TOKENS : EOS_NONE);
                        state <= S_STORE;
                    end
                end

                S_STORE: begin
                    if (cfg_ring_bound) begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base;
                        out_data <= token;
                        out_count <= 32'd1;
                    end
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
