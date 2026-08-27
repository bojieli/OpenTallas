`timescale 1ns/1ps
// Deterministic stage transaction controller.  It provides the architectural
// state-machine skeleton around qualified tile/HBM/link services; service
// datapaths may be replaced by model-specific engines without changing command
// ordering, session generation, credit release, or poison semantics.
module ot_stage_controller #(
    parameter integer SINKS = 8,
    parameter integer STAGE_ID = 0,
    parameter integer OWNED_FIRST_LAYER = 0,
    parameter integer OWNED_LAST_LAYER = 127
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         cmd_valid,
    output wire                         cmd_ready,
    input  wire [7:0]                   cmd_opcode,
    input  wire [7:0]                   cmd_flags,
    input  wire [7:0]                   cmd_epoch,
    input  wire [7:0]                   cmd_schedule,
    input  wire [23:0]                  cmd_session,
    input  wire [19:0]                  cmd_position,
    input  wire [19:0]                  cmd_context_minus_one,
    input  wire [15:0]                  cmd_batch_minus_one,
    input  wire [6:0]                   cmd_first_layer,
    input  wire [6:0]                   cmd_last_layer,
    input  wire [3:0]                   cmd_draft_tokens,
    input  wire [7:0]                   cmd_image_slot,
    input  wire [47:0]                  cmd_activation_address,
    input  wire [31:0]                  cmd_cookie,
    input  wire [15:0]                  cmd_transaction_id,
    input  wire                         quiesce,
    input  wire                         admission_block,
    input  wire                         abort_valid,
    input  wire [15:0]                  abort_transaction_id,
    output wire                         session_req_valid,
    input  wire                         session_req_ready,
    output wire [2:0]                   session_req_op,
    output wire [23:0]                  session_req_session,
    output wire [7:0]                   session_req_image_slot,
    output wire [19:0]                  session_req_context_minus_one,
    output wire [19:0]                  session_req_position,
    output wire [7:0]                   session_req_epoch,
    output wire [15:0]                  session_req_transaction,
    output wire                         session_req_force,
    input  wire                         session_rsp_valid,
    input  wire [7:0]                   session_rsp_status,
    input  wire                         session_rsp_hit,
    input  wire [7:0]                   session_rsp_generation,
    input  wire [19:0]                  session_rsp_expected_position,
    input  wire                         session_rsp_poison,
    output wire                         credit_reserve_valid,
    input  wire                         credit_reserve_ready,
    output wire [SINKS-1:0]             credit_reserve_mask,
    output wire                         credit_release_valid,
    output wire [SINKS-1:0]             credit_release_mask,
    output wire                         service_start_valid,
    input  wire                         service_start_ready,
    output wire [15:0]                  service_transaction_id,
    output wire [23:0]                  service_session_id,
    output wire [7:0]                   service_session_generation,
    output wire [6:0]                   service_first_layer,
    output wire [6:0]                   service_last_layer,
    output wire [15:0]                  service_batch_minus_one,
    output wire [3:0]                   service_draft_tokens,
    output wire [7:0]                   service_schedule_id,
    output wire [7:0]                   service_flags,
    output wire [47:0]                  service_activation_address,
    output wire                         service_poison,
    input  wire                         service_done_valid,
    input  wire [7:0]                   service_done_status,
    input  wire [7:0]                   service_done_error_source,
    input  wire [3:0]                   service_done_syndrome,
    input  wire                         watchdog_timeout,
    output reg                          completion_valid,
    output reg [7:0]                   completion_status,
    output reg [7:0]                   completion_error_source,
    output reg [3:0]                   completion_syndrome,
    output reg [15:0]                  completion_transaction_id,
    output reg [23:0]                  completion_session_id,
    output reg [19:0]                  completion_position,
    output reg [31:0]                  completion_cookie,
    output wire                         stage_idle,
    output reg                          stage_poison
`ifdef FORMAL
    , output wire [3:0]                 formal_state
    , output wire                       formal_credits_held
    , output wire                       formal_service_started
    , output wire                       formal_terminate_now
`endif
);
    localparam [7:0] ST_SUCCESS=8'h00, ST_BAD_FIELD=8'h03,
                     ST_NO_CREDIT=8'h06, ST_EPOCH=8'h07, ST_CAPACITY=8'h09,
                     ST_TIMEOUT=8'h0b, ST_ABORTED=8'h0e, ST_INTERNAL=8'h0f;
    localparam [3:0] S_IDLE=4'd0, S_SESSION=4'd1, S_RESERVE=4'd2,
                     S_START=4'd3, S_EXEC=4'd4, S_COMMIT=4'd5,
                     S_RELEASE=4'd6, S_COMPLETE=4'd7, S_ABORT=4'd8;
    reg [3:0] state;
    reg [7:0] opcode_d, flags_d, schedule_d;
    reg [7:0] epoch_d, image_slot_d;
    reg [23:0] session_d;
    reg [7:0] session_generation_d;
    reg [19:0] position_d, context_d;
    reg [15:0] batch_d, txn_d;
    reg [6:0] first_layer_d, last_layer_d;
    reg [3:0] draft_d;
    reg [47:0] activation_d;
    reg [31:0] cookie_d;
    reg [7:0] terminal_status;
    reg [7:0] terminal_source;
    reg [3:0] terminal_syndrome;
    reg credits_held;
    reg service_started;
    reg abort_pending;
    reg session_issued;
    wire cmd_fire = cmd_valid && cmd_ready;
    wire abort_match = abort_valid && (abort_transaction_id == txn_d);
    wire interruptible = (state != S_IDLE) && (state != S_ABORT) &&
                         (state != S_RELEASE) && (state != S_COMPLETE);
    wire terminate_now = interruptible && (watchdog_timeout || abort_match);
    wire session_fire = session_req_valid && session_req_ready;
    wire credit_fire = credit_reserve_valid && credit_reserve_ready;
    wire service_fire = service_start_valid && service_start_ready;
    wire first_layer_out_of_range;
    wire last_layer_out_of_range;
    generate
        if (OWNED_FIRST_LAYER <= 0) begin : GEN_FIRST_LAYER_ZERO
            assign first_layer_out_of_range = 1'b0;
        end else begin : GEN_FIRST_LAYER_BOUND
            localparam [6:0] OWNED_FIRST_VALUE = OWNED_FIRST_LAYER;
            assign first_layer_out_of_range = (cmd_first_layer < OWNED_FIRST_VALUE);
        end
        if (OWNED_LAST_LAYER >= 127) begin : GEN_LAST_LAYER_MAX
            assign last_layer_out_of_range = 1'b0;
        end else begin : GEN_LAST_LAYER_BOUND
            localparam [6:0] OWNED_LAST_VALUE = OWNED_LAST_LAYER;
            assign last_layer_out_of_range = (cmd_last_layer > OWNED_LAST_VALUE);
        end
    endgenerate

    assign stage_idle = (state == S_IDLE);
    assign cmd_ready = (state == S_IDLE) && !quiesce && !admission_block;
    // A same-cycle abort/watchdog must suppress every new architectural side
    // effect.  S_ABORT itself remains able to issue the poison request.
    assign session_req_valid = ((state == S_SESSION) || (state == S_COMMIT) ||
                                ((state == S_ABORT) && !service_started)) && !session_issued &&
                               (!terminate_now || (state == S_ABORT));
    assign session_req_op = (state == S_COMMIT) ? 3'd3 :
                            ((state == S_ABORT) ? 3'd4 :
                             ((opcode_d == 8'h01) ? 3'd0 :
                              ((opcode_d == 8'h02) ? 3'd1 : 3'd2)));
    assign session_req_session = session_d;
    assign session_req_image_slot = image_slot_d;
    assign session_req_context_minus_one = context_d;
    assign session_req_position = position_d;
    assign session_req_epoch = epoch_d;
    assign session_req_transaction = txn_d;
    assign session_req_force = (flags_d[5] || opcode_d == 8'h7f);
    assign credit_reserve_valid = (state == S_RESERVE) && !credits_held && !terminate_now;
    assign credit_reserve_mask = {SINKS{1'b1}};
    assign credit_release_valid = (state == S_RELEASE) && credits_held;
    assign credit_release_mask = {SINKS{1'b1}};
    assign service_start_valid = (state == S_START) && !service_started && !terminate_now;
    assign service_transaction_id = txn_d;
    assign service_session_id = session_d;
    assign service_session_generation = session_generation_d;
    assign service_first_layer = first_layer_d;
    assign service_last_layer = last_layer_d;
    assign service_batch_minus_one = batch_d;
    assign service_draft_tokens = draft_d;
    assign service_schedule_id = schedule_d;
    assign service_flags = flags_d;
    assign service_activation_address = activation_d;
    assign service_poison = stage_poison || abort_pending;
`ifdef FORMAL
    assign formal_state = state;
    assign formal_credits_held = credits_held;
    assign formal_service_started = service_started;
    assign formal_terminate_now = terminate_now;
`endif

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            opcode_d <= 0; flags_d <= 0; schedule_d <= 0; epoch_d <= 0; image_slot_d <= 0;
            session_d <= 0; session_generation_d <= 0; position_d <= 0; context_d <= 0; batch_d <= 0;
            txn_d <= 0; first_layer_d <= 0; last_layer_d <= 0; draft_d <= 0;
            activation_d <= 0; cookie_d <= 0;
            terminal_status <= ST_SUCCESS; terminal_source <= 0; terminal_syndrome <= 0;
            credits_held <= 1'b0; service_started <= 1'b0; abort_pending <= 1'b0;
            session_issued <= 1'b0;
            completion_valid <= 1'b0; completion_status <= 0; completion_error_source <= 0;
            completion_syndrome <= 0; completion_transaction_id <= 0;
            completion_session_id <= 0; completion_position <= 0; completion_cookie <= 0;
            stage_poison <= 1'b0;
        end else begin
            completion_valid <= 1'b0;
            if (cmd_fire) begin
                opcode_d <= cmd_opcode; flags_d <= cmd_flags; epoch_d <= cmd_epoch;
                schedule_d <= cmd_schedule;
                image_slot_d <= cmd_image_slot; session_d <= cmd_session;
                position_d <= cmd_position; context_d <= cmd_context_minus_one;
                batch_d <= cmd_batch_minus_one; txn_d <= cmd_transaction_id;
                first_layer_d <= cmd_first_layer; last_layer_d <= cmd_last_layer;
                draft_d <= cmd_draft_tokens; activation_d <= cmd_activation_address;
                cookie_d <= cmd_cookie; stage_poison <= 1'b0; abort_pending <= 1'b0;
                service_started <= 1'b0; credits_held <= 1'b0;
                session_issued <= 1'b0;
                terminal_status <= ST_SUCCESS;
                terminal_source <= 8'h00;
                terminal_syndrome <= 4'h0;
                if (cmd_opcode == 8'h00) begin
                    terminal_status <= ST_SUCCESS; state <= S_COMPLETE;
                end else if (cmd_opcode == 8'h01 || cmd_opcode == 8'h02 ||
                             cmd_opcode == 8'h10 || cmd_opcode == 8'h11 ||
                             cmd_opcode == 8'h7f) begin
                    if ((cmd_opcode == 8'h10 || cmd_opcode == 8'h11) &&
                        (first_layer_out_of_range || last_layer_out_of_range)) begin
                        terminal_status <= ST_BAD_FIELD; state <= S_COMPLETE;
                    end else if (cmd_opcode == 8'h7f) begin
                        terminal_status <= ST_ABORTED;
                        state <= S_ABORT;
                        session_issued <= 1'b0;
                    end else begin
                        state <= S_SESSION;
                    end
                end else begin
                    terminal_status <= ST_BAD_FIELD; state <= S_COMPLETE;
                end
            end
            if (interruptible && watchdog_timeout) begin
                stage_poison <= 1'b1;
                abort_pending <= 1'b1;
                terminal_status <= ST_TIMEOUT;
                terminal_source <= 8'hfe;
                session_issued <= 1'b0;
                if (service_started && service_done_valid)
                    service_started <= 1'b0;
                state <= S_ABORT;
            end else if (interruptible && abort_match) begin
                abort_pending <= 1'b1;
                stage_poison <= 1'b1;
                terminal_status <= ST_ABORTED;
                session_issued <= 1'b0;
                if (service_started && service_done_valid)
                    service_started <= 1'b0;
                state <= S_ABORT;
            end else case (state)
                S_IDLE: begin
                    // Command capture above owns the transition out of idle.
                end
                S_SESSION: begin
                    if (session_fire)
                        session_issued <= 1'b1;
                    if (session_rsp_valid) begin
                        session_issued <= 1'b0;
                        if (session_rsp_status != ST_SUCCESS || !session_rsp_hit || session_rsp_poison) begin
                            terminal_status <= session_rsp_status == ST_SUCCESS ? ST_CAPACITY : session_rsp_status;
                            if (session_rsp_poison) begin
                                terminal_status <= ST_INTERNAL;
                                stage_poison <= 1'b1;
                            end
                            state <= S_COMPLETE;
                        end else if (opcode_d == 8'h01 || opcode_d == 8'h02) begin
                            state <= S_COMPLETE;
                        end else if (session_rsp_expected_position != position_d) begin
                            terminal_status <= ST_EPOCH;
                            state <= S_COMPLETE;
                        end else begin
                            session_generation_d <= session_rsp_generation;
                            state <= S_RESERVE;
                        end
                    end
                end
                S_RESERVE: begin
                    if (credit_fire) begin
                        credits_held <= 1'b1;
                        state <= S_START;
                    end else if (credit_reserve_valid && !credit_reserve_ready) begin
                        terminal_status <= ST_NO_CREDIT;
                        // Lookup has already marked the session busy.  Route
                        // every post-lookup failure through the common abort
                        // owner so capacity cannot leak on admission failure.
                        abort_pending <= 1'b1;
                        stage_poison <= 1'b1;
                        session_issued <= 1'b0;
                        state <= S_ABORT;
                    end
                end
                S_START: if (service_fire) begin service_started <= 1'b1; state <= S_EXEC; end
                S_EXEC: begin
                    if (service_done_valid) begin
                        service_started <= 1'b0;
                        if (service_done_status != ST_SUCCESS || service_done_error_source != 0) begin
                            terminal_status <= service_done_status == ST_SUCCESS ? ST_INTERNAL : service_done_status;
                            terminal_source <= service_done_error_source;
                            terminal_syndrome <= service_done_syndrome;
                            stage_poison <= 1'b1;
                            abort_pending <= 1'b1;
                            session_issued <= 1'b0;
                            state <= S_ABORT;
                        end else begin
                            state <= S_COMMIT;
                        end
                    end
                end
                S_COMMIT: begin
                    if (session_fire)
                        session_issued <= 1'b1;
                    if (session_rsp_valid) begin
                        session_issued <= 1'b0;
                    if (session_rsp_status != ST_SUCCESS || session_rsp_poison) begin
                        terminal_status <= session_rsp_status;
                        if (session_rsp_poison)
                            terminal_status <= ST_INTERNAL;
                        stage_poison <= 1'b1;
                        abort_pending <= 1'b1;
                        session_issued <= 1'b0;
                        state <= S_ABORT;
                    end else begin
                        state <= S_RELEASE;
                    end
                    end
                end
                S_RELEASE: begin
                    if (credits_held) credits_held <= 1'b0;
                    state <= S_COMPLETE;
                end
                S_ABORT: begin
                    // An abort is allowed to poison/release a configured
                    // session, but never reaches COMMIT.  If service already
                    // launched, service_poison first requests deterministic
                    // drain and credits remain held until its terminal result.
                    if (service_started) begin
                        if (service_done_valid)
                            service_started <= 1'b0;
                    end else begin
                        if (session_fire)
                            session_issued <= 1'b1;
                        if (session_rsp_valid) begin
                            session_issued <= 1'b0;
                            state <= credits_held ? S_RELEASE : S_COMPLETE;
                        end
                    end
                end
                S_COMPLETE: begin
                    completion_valid <= 1'b1;
                    completion_status <= terminal_status;
                    completion_error_source <= terminal_source;
                    completion_syndrome <= terminal_syndrome;
                    completion_transaction_id <= txn_d;
                    completion_session_id <= session_d;
                    completion_position <= position_d;
                    completion_cookie <= cookie_d;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (STAGE_ID < 0 || STAGE_ID > 255)
            $error("ot_stage_controller STAGE_ID outside architectural limit");
    end
`endif
endmodule
