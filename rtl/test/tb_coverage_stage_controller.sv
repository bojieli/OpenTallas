`timescale 1ns/1ps

// Deterministic state/transition coverage for the architectural stage owner.
// External session, credit, and service agents are modeled independently so
// every terminal path can be checked without relying on integration timing.
module tb_coverage_stage_controller;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer failures = 0;
    integer checks = 0;
    integer wait_cycles;
    reg [31:0] rng_state = 32'h5354_434f;

    function automatic [31:0] random32;
        reg [31:0] x;
        begin
            x = rng_state;
            x = x ^ (x << 13);
            x = x ^ (x >> 17);
            x = x ^ (x << 5);
            rng_state = x;
            random32 = x;
        end
    endfunction

    task automatic require_true;
        input condition;
        input [8*96-1:0] message;
        begin
            checks = checks + 1;
            if (!condition) begin
                failures = failures + 1;
                $display("FAIL check=%0d %0s",checks,message);
            end
        end
    endtask

    task automatic pass_bin;
        input [8*96-1:0] bin_id;
        input condition;
        begin
            require_true(condition,bin_id);
            if (condition)
                $display("COVER_BIN %0s PASS",bin_id);
        end
    endtask

    reg cmd_valid = 1'b0;
    wire cmd_ready;
    reg [7:0] cmd_opcode = 8'b0;
    reg [7:0] cmd_flags = 8'b0;
    reg [7:0] cmd_epoch = 8'b0;
    reg [7:0] cmd_schedule = 8'b0;
    reg [23:0] cmd_session = 24'b0;
    reg [19:0] cmd_position = 20'b0;
    reg [19:0] cmd_context_minus_one = 20'b0;
    reg [15:0] cmd_batch_minus_one = 16'b0;
    reg [6:0] cmd_first_layer = 7'b0;
    reg [6:0] cmd_last_layer = 7'b0;
    reg [3:0] cmd_draft_tokens = 4'b0;
    reg [7:0] cmd_image_slot = 8'b0;
    reg [47:0] cmd_activation_address = 48'b0;
    reg [31:0] cmd_cookie = 32'b0;
    reg [15:0] cmd_transaction_id = 16'b0;
    reg quiesce = 1'b0;
    reg admission_block = 1'b0;
    reg abort_valid = 1'b0;
    reg [15:0] abort_transaction_id = 16'b0;

    wire session_req_valid;
    reg session_req_ready = 1'b1;
    wire [2:0] session_req_op;
    wire [23:0] session_req_session;
    wire [7:0] session_req_image_slot;
    wire [19:0] session_req_context_minus_one;
    wire [19:0] session_req_position;
    wire [7:0] session_req_epoch;
    wire [15:0] session_req_transaction;
    wire session_req_force;
    reg session_rsp_valid = 1'b0;
    reg [7:0] session_rsp_status = 8'b0;
    reg session_rsp_hit = 1'b0;
    reg [7:0] session_rsp_generation = 8'b0;
    reg [19:0] session_rsp_expected_position = 20'b0;
    reg session_rsp_poison = 1'b0;

    wire credit_reserve_valid;
    reg credit_reserve_ready = 1'b0;
    wire [3:0] credit_reserve_mask;
    wire credit_release_valid;
    wire [3:0] credit_release_mask;

    wire service_start_valid;
    reg service_start_ready = 1'b0;
    wire [15:0] service_transaction_id;
    wire [23:0] service_session_id;
    wire [7:0] service_session_generation;
    wire [6:0] service_first_layer;
    wire [6:0] service_last_layer;
    wire [15:0] service_batch_minus_one;
    wire [3:0] service_draft_tokens;
    wire [7:0] service_schedule_id;
    wire [7:0] service_flags;
    wire [47:0] service_activation_address;
    wire service_poison;
    reg service_done_valid = 1'b0;
    reg [7:0] service_done_status = 8'b0;
    reg [7:0] service_done_error_source = 8'b0;
    reg [3:0] service_done_syndrome = 4'b0;
    reg watchdog_timeout = 1'b0;

    wire completion_valid;
    wire [7:0] completion_status;
    wire [7:0] completion_error_source;
    wire [3:0] completion_syndrome;
    wire [15:0] completion_transaction_id;
    wire [23:0] completion_session_id;
    wire [19:0] completion_position;
    wire [31:0] completion_cookie;
    wire stage_idle;
    wire stage_poison;
    reg [8:0] seen_stage_state = 9'b0;

    ot_stage_controller #(
        .SINKS(4),.STAGE_ID(7),.OWNED_FIRST_LAYER(4),.OWNED_LAST_LAYER(11)
    ) dut (
        .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_opcode(cmd_opcode),.cmd_flags(cmd_flags),.cmd_epoch(cmd_epoch),
        .cmd_schedule(cmd_schedule),.cmd_session(cmd_session),
        .cmd_position(cmd_position),.cmd_context_minus_one(cmd_context_minus_one),
        .cmd_batch_minus_one(cmd_batch_minus_one),.cmd_first_layer(cmd_first_layer),
        .cmd_last_layer(cmd_last_layer),.cmd_draft_tokens(cmd_draft_tokens),
        .cmd_image_slot(cmd_image_slot),.cmd_activation_address(cmd_activation_address),
        .cmd_cookie(cmd_cookie),.cmd_transaction_id(cmd_transaction_id),
        .quiesce(quiesce),.admission_block(admission_block),
        .abort_valid(abort_valid),.abort_transaction_id(abort_transaction_id),
        .session_req_valid(session_req_valid),.session_req_ready(session_req_ready),
        .session_req_op(session_req_op),.session_req_session(session_req_session),
        .session_req_image_slot(session_req_image_slot),
        .session_req_context_minus_one(session_req_context_minus_one),
        .session_req_position(session_req_position),.session_req_epoch(session_req_epoch),
        .session_req_transaction(session_req_transaction),.session_req_force(session_req_force),
        .session_rsp_valid(session_rsp_valid),.session_rsp_status(session_rsp_status),
        .session_rsp_hit(session_rsp_hit),.session_rsp_generation(session_rsp_generation),
        .session_rsp_expected_position(session_rsp_expected_position),
        .session_rsp_poison(session_rsp_poison),
        .credit_reserve_valid(credit_reserve_valid),
        .credit_reserve_ready(credit_reserve_ready),
        .credit_reserve_mask(credit_reserve_mask),
        .credit_release_valid(credit_release_valid),
        .credit_release_mask(credit_release_mask),
        .service_start_valid(service_start_valid),.service_start_ready(service_start_ready),
        .service_transaction_id(service_transaction_id),
        .service_session_id(service_session_id),
        .service_session_generation(service_session_generation),
        .service_first_layer(service_first_layer),.service_last_layer(service_last_layer),
        .service_batch_minus_one(service_batch_minus_one),
        .service_draft_tokens(service_draft_tokens),
        .service_schedule_id(service_schedule_id),.service_flags(service_flags),
        .service_activation_address(service_activation_address),
        .service_poison(service_poison),.service_done_valid(service_done_valid),
        .service_done_status(service_done_status),
        .service_done_error_source(service_done_error_source),
        .service_done_syndrome(service_done_syndrome),
        .watchdog_timeout(watchdog_timeout),.completion_valid(completion_valid),
        .completion_status(completion_status),
        .completion_error_source(completion_error_source),
        .completion_syndrome(completion_syndrome),
        .completion_transaction_id(completion_transaction_id),
        .completion_session_id(completion_session_id),
        .completion_position(completion_position),.completion_cookie(completion_cookie),
        .stage_idle(stage_idle),.stage_poison(stage_poison));

    always @(posedge clk) begin
        case (dut.state)
            4'd0: seen_stage_state[0] <= 1'b1;
            4'd1: seen_stage_state[1] <= 1'b1;
            4'd2: seen_stage_state[2] <= 1'b1;
            4'd3: seen_stage_state[3] <= 1'b1;
            4'd4: seen_stage_state[4] <= 1'b1;
            4'd5: seen_stage_state[5] <= 1'b1;
            4'd6: seen_stage_state[6] <= 1'b1;
            4'd7: seen_stage_state[7] <= 1'b1;
            4'd8: seen_stage_state[8] <= 1'b1;
            default: seen_stage_state <= seen_stage_state;
        endcase
    end

    task automatic load_and_send_command;
        input [7:0] opcode;
        input [7:0] flags;
        input [6:0] first_layer;
        input [6:0] last_layer;
        reg [31:0] a;
        reg [31:0] b;
        reg [31:0] c;
        reg [31:0] d;
        reg [31:0] e;
        reg [31:0] f;
        begin
            a = random32();
            b = random32();
            c = random32();
            d = random32();
            e = random32();
            f = random32();
            while (!cmd_ready)
                @(negedge clk);
            cmd_opcode = opcode;
            cmd_flags = flags;
            cmd_epoch = a[7:0];
            cmd_schedule = a[15:8];
            cmd_session = {a[31:16],b[7:0]};
            cmd_position = b[27:8];
            cmd_context_minus_one = {b[31:28],c[15:0]};
            cmd_batch_minus_one = c[31:16];
            cmd_first_layer = first_layer;
            cmd_last_layer = last_layer;
            cmd_draft_tokens = a[19:16];
            cmd_image_slot = b[15:8];
            cmd_activation_address = {d[15:0],e};
            cmd_cookie = f;
            cmd_transaction_id = d[31:16] ^ f[15:0];
            cmd_valid = 1'b1;
            @(negedge clk);
            cmd_valid = 1'b0;
        end
    endtask

    task automatic respond_session;
        input [2:0] expected_operation;
        input [7:0] status;
        input hit;
        input [7:0] generation;
        input [19:0] expected_position;
        input poison;
        input expect_force;
        begin
            wait_cycles = 0;
            while (!session_req_valid && wait_cycles < 40) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(session_req_valid,"stage controller session request timeout");
            require_true(session_req_op == expected_operation,"stage controller session operation");
            require_true(session_req_session == cmd_session &&
                         session_req_image_slot == cmd_image_slot &&
                         session_req_context_minus_one == cmd_context_minus_one &&
                         session_req_position == cmd_position &&
                         session_req_epoch == cmd_epoch &&
                         session_req_transaction == cmd_transaction_id,
                         "stage controller session payload");
            require_true(session_req_force == expect_force,"stage controller force semantics");
            session_rsp_status = status;
            session_rsp_hit = hit;
            session_rsp_generation = generation;
            session_rsp_expected_position = expected_position;
            session_rsp_poison = poison;
            session_rsp_valid = 1'b1;
            @(negedge clk);
            session_rsp_valid = 1'b0;
            session_rsp_poison = 1'b0;
        end
    endtask

    task automatic grant_credit;
        begin
            wait_cycles = 0;
            while (!credit_reserve_valid && wait_cycles < 20) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(credit_reserve_valid && credit_reserve_mask == 4'hf,
                         "stage controller credit reservation");
            credit_reserve_ready = 1'b1;
            @(negedge clk);
            credit_reserve_ready = 1'b0;
        end
    endtask

    task automatic accept_service;
        input integer stall_cycles;
        integer stall_index;
        begin
            wait_cycles = 0;
            while (!service_start_valid && wait_cycles < 30) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(service_start_valid,"stage controller service start timeout");
            for (stall_index = 0; stall_index < stall_cycles; stall_index = stall_index + 1) begin
                require_true(service_start_valid,"stage service valid dropped while stalled");
                @(negedge clk);
            end
            require_true(service_transaction_id == cmd_transaction_id &&
                         service_session_id == cmd_session &&
                         service_first_layer == cmd_first_layer &&
                         service_last_layer == cmd_last_layer &&
                         service_batch_minus_one == cmd_batch_minus_one &&
                         service_draft_tokens == cmd_draft_tokens &&
                         service_schedule_id == cmd_schedule &&
                         service_flags == cmd_flags &&
                         service_activation_address == cmd_activation_address,
                         "stage controller service payload");
            service_start_ready = 1'b1;
            @(negedge clk);
            service_start_ready = 1'b0;
        end
    endtask

    task automatic finish_service;
        input [7:0] status;
        input [7:0] source;
        input [3:0] syndrome;
        begin
            service_done_status = status;
            service_done_error_source = source;
            service_done_syndrome = syndrome;
            service_done_valid = 1'b1;
            @(negedge clk);
            service_done_valid = 1'b0;
        end
    endtask

    task automatic expect_completion;
        input [7:0] status;
        input [7:0] source;
        input [3:0] syndrome;
        begin
            wait_cycles = 0;
            while (!completion_valid && wait_cycles < 60) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(completion_valid,"stage controller completion timeout");
            require_true(completion_status == status &&
                         completion_error_source == source &&
                         completion_syndrome == syndrome,
                         "stage controller terminal status");
            require_true(completion_transaction_id == cmd_transaction_id &&
                         completion_session_id == cmd_session &&
                         completion_position == cmd_position &&
                         completion_cookie == cmd_cookie,
                         "stage controller completion payload");
            @(negedge clk);
            require_true(stage_idle,"stage controller returned idle");
        end
    endtask

    task automatic expect_abort_request_and_complete;
        input [7:0] status;
        input [7:0] source;
        input [3:0] syndrome;
        begin
            respond_session(3'd4,8'h00,1'b1,8'h00,cmd_position,1'b1,1'b0);
            if (credit_release_valid) begin
                require_true(credit_release_mask == 4'hf,"stage controller credit release mask");
                @(negedge clk);
            end
            expect_completion(status,source,syndrome);
        end
    endtask

    initial begin
        quiesce = 1'b1;
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
    end

    initial begin : main_sequence
        wait (rst_n === 1'b1);
        @(negedge clk);
        require_true(!cmd_ready,"stage controller quiesce gate");
        quiesce = 1'b0;
        admission_block = 1'b1;
        @(negedge clk);
        require_true(!cmd_ready,"stage controller admission gate");
        admission_block = 1'b0;

        load_and_send_command(8'h00,8'h01,7'd4,7'd11);
        expect_completion(8'h00,8'h00,4'h0);
        load_and_send_command(8'h55,8'h02,7'd4,7'd11);
        expect_completion(8'h03,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-NOOP-ILLEGAL",stage_idle && !stage_poison);

        load_and_send_command(8'h10,8'h04,7'd3,7'd11);
        expect_completion(8'h03,8'h00,4'h0);
        load_and_send_command(8'h11,8'h08,7'd4,7'd12);
        expect_completion(8'h03,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-LAYER-BOUNDS",stage_idle);

        load_and_send_command(8'h01,8'h10,7'd4,7'd11);
        respond_session(3'd0,8'h00,1'b1,8'h11,cmd_position,1'b0,1'b0);
        expect_completion(8'h00,8'h00,4'h0);
        load_and_send_command(8'h02,8'h20,7'd4,7'd11);
        respond_session(3'd1,8'h00,1'b1,8'h22,cmd_position,1'b0,1'b1);
        expect_completion(8'h00,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-CONFIG-RELEASE",stage_idle);

        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b0,8'h00,cmd_position,1'b0,1'b0);
        expect_completion(8'h09,8'h00,4'h0);
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h33,cmd_position,1'b1,1'b0);
        expect_completion(8'h0f,8'h00,4'h0);
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h05,1'b1,8'h44,cmd_position,1'b0,1'b0);
        expect_completion(8'h05,8'h00,4'h0);
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h55,cmd_position ^ 20'h1,1'b0,1'b0);
        expect_completion(8'h07,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-SESSION-REJECTS",stage_idle);

        // A single unavailable reservation is a deterministic admission
        // failure; the post-lookup busy session is poisoned before completion.
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h66,cmd_position,1'b0,1'b0);
        while (!credit_reserve_valid) @(negedge clk);
        @(negedge clk);
        expect_abort_request_and_complete(8'h06,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-NO-CREDIT",stage_idle && stage_poison);

        // Successful service retains every command field, commits position,
        // and releases all credits exactly once.
        load_and_send_command(8'h11,8'ha5,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h77,cmd_position,1'b0,1'b1);
        grant_credit();
        accept_service(3);
        require_true(service_session_generation == 8'h77,"stage service session generation");
        finish_service(8'h00,8'h00,4'h0);
        respond_session(3'd3,8'h00,1'b1,8'h77,cmd_position + 1'b1,1'b0,1'b1);
        while (!credit_release_valid) @(negedge clk);
        require_true(credit_release_mask == 4'hf,"stage successful credit release");
        @(negedge clk);
        expect_completion(8'h00,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-SERVICE-COMMIT",stage_idle && !stage_poison);

        // Commit failure is contained by poison and credit release.
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h88,cmd_position,1'b0,1'b0);
        grant_credit();
        accept_service(0);
        finish_service(8'h00,8'h00,4'h0);
        respond_session(3'd3,8'h07,1'b1,8'h88,cmd_position,1'b0,1'b0);
        expect_abort_request_and_complete(8'h07,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-COMMIT-FAIL",stage_idle && stage_poison);

        // A source error with success status is normalized to INTERNAL.
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'h99,cmd_position,1'b0,1'b0);
        grant_credit();
        accept_service(1);
        finish_service(8'h00,8'hc3,4'ha);
        expect_abort_request_and_complete(8'h0f,8'hc3,4'ha);
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'haa,cmd_position,1'b0,1'b0);
        grant_credit();
        accept_service(0);
        finish_service(8'h0c,8'h5a,4'h5);
        expect_abort_request_and_complete(8'h0c,8'h5a,4'h5);
        pass_bin("COV-STAGECTRL-SERVICE-ERROR",stage_idle && stage_poison);

        // Watchdog after launch first drains the service, then poisons the
        // session and releases credits.
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'hbb,cmd_position,1'b0,1'b0);
        grant_credit();
        accept_service(0);
        watchdog_timeout = 1'b1;
        @(negedge clk);
        watchdog_timeout = 1'b0;
        require_true(service_poison,"stage watchdog service poison");
        finish_service(8'h0e,8'hee,4'he);
        expect_abort_request_and_complete(8'h0b,8'hfe,4'h0);
        pass_bin("COV-STAGECTRL-WATCHDOG-DRAIN",stage_idle && stage_poison);

        // An external abort matching the active transaction has the same
        // deterministic drain contract but reports ABORTED.
        load_and_send_command(8'h10,8'h00,7'd4,7'd11);
        respond_session(3'd2,8'h00,1'b1,8'hcc,cmd_position,1'b0,1'b0);
        grant_credit();
        accept_service(0);
        abort_transaction_id = cmd_transaction_id;
        abort_valid = 1'b1;
        @(negedge clk);
        abort_valid = 1'b0;
        require_true(service_poison,"stage external abort service poison");
        finish_service(8'h00,8'h00,4'h0);
        expect_abort_request_and_complete(8'h0e,8'h00,4'h0);

        load_and_send_command(8'h7f,8'hff,7'd4,7'd11);
        respond_session(3'd4,8'h00,1'b1,8'h00,cmd_position,1'b1,1'b1);
        expect_completion(8'h0e,8'h00,4'h0);
        pass_bin("COV-STAGECTRL-ABORT-FORCE",stage_idle && !stage_poison);

        pass_bin("COV-FSM-STAGE-IDLE",seen_stage_state[0]);
        pass_bin("COV-FSM-STAGE-SESSION",seen_stage_state[1]);
        pass_bin("COV-FSM-STAGE-RESERVE",seen_stage_state[2]);
        pass_bin("COV-FSM-STAGE-START",seen_stage_state[3]);
        pass_bin("COV-FSM-STAGE-EXEC",seen_stage_state[4]);
        pass_bin("COV-FSM-STAGE-COMMIT",seen_stage_state[5]);
        pass_bin("COV-FSM-STAGE-RELEASE",seen_stage_state[6]);
        pass_bin("COV-FSM-STAGE-COMPLETE",seen_stage_state[7]);
        pass_bin("COV-FSM-STAGE-ABORT",seen_stage_state[8]);

        if (failures == 0) begin
            $display("PASS: coverage stage controller seed=0x5354434f checks=%0d",checks);
            $finish;
        end else begin
            $fatal(1,"coverage stage controller failed: %0d failures in %0d checks",
                   failures,checks);
        end
    end
endmodule
