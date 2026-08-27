`timescale 1ns/1ps
module f_stage_controller;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;

    (* anyseq *) reg cmd_valid;
    (* anyseq *) reg [7:0] cmd_opcode, cmd_flags, cmd_epoch, cmd_schedule;
    (* anyseq *) reg [23:0] cmd_session;
    (* anyseq *) reg [19:0] cmd_position, cmd_context_minus_one;
    (* anyseq *) reg [15:0] cmd_batch_minus_one, cmd_transaction_id;
    (* anyseq *) reg [6:0] cmd_first_layer, cmd_last_layer;
    (* anyseq *) reg [3:0] cmd_draft_tokens;
    (* anyseq *) reg [7:0] cmd_image_slot;
    (* anyseq *) reg [47:0] cmd_activation_address;
    (* anyseq *) reg [31:0] cmd_cookie;
    (* anyseq *) reg quiesce, admission_block, abort_valid;
    (* anyseq *) reg [15:0] abort_transaction_id;
    (* anyseq *) reg session_req_ready, session_rsp_valid, session_rsp_hit;
    (* anyseq *) reg [7:0] session_rsp_status;
    (* anyseq *) reg [7:0] session_rsp_generation;
    (* anyseq *) reg [19:0] session_rsp_expected_position;
    (* anyseq *) reg session_rsp_poison;
    (* anyseq *) reg credit_reserve_ready, service_start_ready;
    (* anyseq *) reg service_done_valid;
    (* anyseq *) reg [7:0] service_done_status, service_done_error_source;
    (* anyseq *) reg [3:0] service_done_syndrome;
    (* anyseq *) reg watchdog_timeout;

    wire cmd_ready, session_req_valid, session_req_force;
    wire [2:0] session_req_op;
    wire [23:0] session_req_session;
    wire [7:0] session_req_image_slot, session_req_epoch;
    wire [19:0] session_req_context_minus_one, session_req_position;
    wire [15:0] session_req_transaction;
    wire credit_reserve_valid, credit_release_valid;
    wire [1:0] credit_reserve_mask, credit_release_mask;
    wire service_start_valid, service_poison;
    wire [15:0] service_transaction_id, service_batch_minus_one;
    wire [23:0] service_session_id;
    wire [7:0] service_session_generation;
    wire [6:0] service_first_layer, service_last_layer;
    wire [3:0] service_draft_tokens;
    wire [7:0] service_schedule_id, service_flags;
    wire [47:0] service_activation_address;
    wire completion_valid, stage_idle, stage_poison;
    wire [7:0] completion_status, completion_error_source;
    wire [3:0] completion_syndrome;
    wire [15:0] completion_transaction_id;
    wire [23:0] completion_session_id;
    wire [19:0] completion_position;
    wire [31:0] completion_cookie;
    wire [3:0] formal_state;
    wire formal_credits_held, formal_service_started, formal_terminate_now;
    wire cmd_fire = cmd_valid && cmd_ready;
    wire session_fire = session_req_valid && session_req_ready;
    wire credit_fire = credit_reserve_valid && credit_reserve_ready;
    wire service_fire = service_start_valid && service_start_ready;

    reg [1:0] transaction_count;
    reg model_credit_held;
    reg model_service_active;
    reg transaction_aborted;
    reg [7:0] model_opcode;
    reg [15:0] model_transaction_id;
    reg [23:0] model_session_id;
    reg [19:0] model_position;
    reg [31:0] model_cookie;

    ot_stage_controller #(
        .SINKS(2), .STAGE_ID(0), .OWNED_FIRST_LAYER(0), .OWNED_LAST_LAYER(3)
    ) dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .cmd_opcode(cmd_opcode), .cmd_flags(cmd_flags), .cmd_epoch(cmd_epoch),
        .cmd_schedule(cmd_schedule), .cmd_session(cmd_session), .cmd_position(cmd_position),
        .cmd_context_minus_one(cmd_context_minus_one), .cmd_batch_minus_one(cmd_batch_minus_one),
        .cmd_first_layer(cmd_first_layer), .cmd_last_layer(cmd_last_layer),
        .cmd_draft_tokens(cmd_draft_tokens), .cmd_image_slot(cmd_image_slot),
        .cmd_activation_address(cmd_activation_address), .cmd_cookie(cmd_cookie),
        .cmd_transaction_id(cmd_transaction_id), .quiesce(quiesce),
        .admission_block(admission_block), .abort_valid(abort_valid),
        .abort_transaction_id(abort_transaction_id), .session_req_valid(session_req_valid),
        .session_req_ready(session_req_ready), .session_req_op(session_req_op),
        .session_req_session(session_req_session), .session_req_image_slot(session_req_image_slot),
        .session_req_context_minus_one(session_req_context_minus_one),
        .session_req_position(session_req_position), .session_req_epoch(session_req_epoch),
        .session_req_transaction(session_req_transaction), .session_req_force(session_req_force),
        .session_rsp_valid(session_rsp_valid), .session_rsp_status(session_rsp_status),
        .session_rsp_hit(session_rsp_hit),
        .session_rsp_generation(session_rsp_generation),
        .session_rsp_expected_position(session_rsp_expected_position),
        .session_rsp_poison(session_rsp_poison),
        .credit_reserve_valid(credit_reserve_valid), .credit_reserve_ready(credit_reserve_ready),
        .credit_reserve_mask(credit_reserve_mask), .credit_release_valid(credit_release_valid),
        .credit_release_mask(credit_release_mask), .service_start_valid(service_start_valid),
        .service_start_ready(service_start_ready), .service_transaction_id(service_transaction_id),
        .service_session_id(service_session_id),
        .service_session_generation(service_session_generation),
        .service_first_layer(service_first_layer),
        .service_last_layer(service_last_layer), .service_batch_minus_one(service_batch_minus_one),
        .service_draft_tokens(service_draft_tokens), .service_schedule_id(service_schedule_id),
        .service_flags(service_flags), .service_activation_address(service_activation_address),
        .service_poison(service_poison),
        .service_done_valid(service_done_valid), .service_done_status(service_done_status),
        .service_done_error_source(service_done_error_source),
        .service_done_syndrome(service_done_syndrome), .watchdog_timeout(watchdog_timeout),
        .completion_valid(completion_valid), .completion_status(completion_status),
        .completion_error_source(completion_error_source), .completion_syndrome(completion_syndrome),
        .completion_transaction_id(completion_transaction_id),
        .completion_session_id(completion_session_id), .completion_position(completion_position),
        .completion_cookie(completion_cookie), .stage_idle(stage_idle), .stage_poison(stage_poison)
        ,.formal_state(formal_state), .formal_credits_held(formal_credits_held),
        .formal_service_started(formal_service_started),
        .formal_terminate_now(formal_terminate_now)
    );

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (!rst_n) begin
            transaction_count <= 0;
            model_credit_held <= 0;
            model_service_active <= 0;
            transaction_aborted <= 0;
            model_opcode <= 0;
            model_transaction_id <= 0;
            model_session_id <= 0;
            model_position <= 0;
            model_cookie <= 0;
        end else begin
            // The concrete session table emits exactly one response one cycle
            // after each accepted request.  Response contents remain arbitrary.
            if (f_past_valid)
                assume(session_rsp_valid == $past(rst_n && session_fire));
            assume(!service_done_valid || model_service_active);

            assert(formal_state <= 4'd8);
            assert(stage_idle == (formal_state == 4'd0));
            assert(formal_credits_held == model_credit_held);
            assert(formal_service_started == model_service_active);
            assert(transaction_count <= 1);
            assert(!(credit_reserve_valid && credit_release_valid));
            assert(!(service_start_valid && credit_release_valid));
            assert(!credit_release_valid || model_credit_held);
            assert(!credit_reserve_valid || !model_credit_held);
            assert(!service_start_valid || !model_service_active);
            if (completion_valid) begin
                assert(transaction_count != 0);
                assert(stage_idle);
                assert(f_past_valid && $past(formal_state == 4'd7));
                assert(completion_transaction_id == model_transaction_id);
                assert(completion_session_id == model_session_id);
                assert(completion_position == model_position);
                assert(completion_cookie == model_cookie);
                if (model_opcode == 8'h00) begin
                    assert(completion_status == 8'h00);
                    assert(completion_error_source == 8'h00);
                    assert(completion_syndrome == 4'h0);
                end
            end
            if (cmd_fire)
                assert((transaction_count == 0) || completion_valid);
            if (session_req_valid && (session_req_op == 3'd3)) begin
                assert(!transaction_aborted);
                assert(!formal_terminate_now);
            end
            if (formal_terminate_now) begin
                assert(!credit_reserve_valid);
                assert(!service_start_valid);
                assert(!(session_req_valid && (session_req_op == 3'd3)));
            end
            if (f_past_valid && $past(rst_n && formal_terminate_now)) begin
                assert(formal_state == 4'd8);
                assert(stage_poison);
            end
            if (f_past_valid && $past(stage_poison && rst_n && !cmd_fire))
                assert(stage_poison);

            case ({cmd_fire,completion_valid})
                2'b10: transaction_count <= transaction_count + 1'b1;
                2'b01: transaction_count <= transaction_count - 1'b1;
                default: transaction_count <= transaction_count;
            endcase
            if (credit_fire) begin
                assert(!model_credit_held);
                model_credit_held <= 1'b1;
            end
            if (credit_release_valid) begin
                assert(model_credit_held);
                model_credit_held <= 1'b0;
            end
            if (service_fire) begin
                assert(!model_service_active);
                model_service_active <= 1'b1;
            end
            if (service_done_valid)
                model_service_active <= 1'b0;
            if (cmd_fire) begin
                transaction_aborted <= (cmd_opcode == 8'h7f);
                model_opcode <= cmd_opcode;
                model_transaction_id <= cmd_transaction_id;
                model_session_id <= cmd_session;
                model_position <= cmd_position;
                model_cookie <= cmd_cookie;
            end
            if (formal_terminate_now)
                transaction_aborted <= 1'b1;
            if (completion_valid && !cmd_fire)
                transaction_aborted <= 1'b0;

            cover(completion_valid && completion_status == 8'h00);
            cover(completion_valid && completion_status == 8'h0e);
            cover(completion_valid && completion_status == 8'h0b);
            cover(credit_release_valid && stage_poison);
        end
    end
endmodule
