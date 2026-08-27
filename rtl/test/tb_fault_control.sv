`timescale 1ns/1ps
// Directed schedule/session/power/stage containment campaign.  Fault paths are
// required to complete deterministically, release held credits, and avoid a
// session retire/commit unless the service transaction completed successfully.
module tb_fault_control;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;
    integer failures = 0;

    task automatic check_site;
        input [8*64-1:0] site_id;
        input condition;
        begin
            if (condition)
                $display("FAULT_SITE %0s PASS",site_id);
            else begin
                $display("FAULT_SITE %0s FAIL",site_id);
                failures = failures + 1;
            end
        end
    endtask

    task automatic reset_duts;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            repeat (3) @(negedge clk);
            rst_n = 1'b1;
            @(negedge clk);
        end
    endtask

    // ------------------------------------------------------------------
    // AON power/reset/service policy.
    reg power_good = 1'b1;
    reg clock_stable = 1'b1;
    reg core_ready = 1'b1;
    reg hbm_ready = 1'b1;
    reg platform_link_ready = 1'b1;
    reg power_bist_done = 1'b1;
    reg power_bist_pass = 1'b1;
    reg power_service_request = 1'b0;
    reg power_quiesce_request = 1'b0;
    reg power_core_quiescent = 1'b0;
    reg thermal_warning = 1'b0;
    reg thermal_fatal = 1'b0;
    reg platform_fatal = 1'b0;
    reg requalify = 1'b0;
    reg power_test_enable = 1'b0;
    wire [3:0] power_state;
    wire power_core_reset_n;
    wire power_service_enable;
    wire power_isolation;
    wire power_throttle;
    wire power_safe;
    wire power_quiesce_ack;
    wire power_stop_ack;
    wire [7:0] power_reset_cause;

    ot_power_reset_controller power_dut (
        .aon_clk(clk), .aon_rst_n(rst_n), .power_good(power_good),
        .clock_stable(clock_stable), .core_ready(core_ready),
        .hbm_ready(hbm_ready), .link_ready(platform_link_ready),
        .bist_done(power_bist_done), .bist_pass(power_bist_pass),
        .service_request(power_service_request),
        .quiesce_request(power_quiesce_request),
        .core_quiescent(power_core_quiescent),
        .thermal_warning(thermal_warning), .thermal_fatal(thermal_fatal),
        .fatal_error(platform_fatal), .requalify(requalify),
        .test_enable(power_test_enable), .state(power_state),
        .core_reset_n(power_core_reset_n), .service_enable(power_service_enable),
        .isolation_enable(power_isolation), .throttle_enable(power_throttle),
        .safe(power_safe), .quiesce_ack(power_quiesce_ack),
        .stop_ack(power_stop_ack), .reset_cause(power_reset_cause)
    );

    // ------------------------------------------------------------------
    // Checked active/shadow schedule store.
    reg schedule_wr_valid = 1'b0;
    wire schedule_wr_ready;
    reg [1:0] schedule_wr_slot = 2'b0;
    reg [3:0] schedule_wr_data = 4'b0;
    reg schedule_commit_req = 1'b0;
    reg schedule_quiescent = 1'b0;
    reg schedule_epoch_boundary = 1'b0;
    reg schedule_manifest_ok = 1'b1;
    reg [7:0] schedule_commit_id = 8'b0;
    wire schedule_commit_ack;
    wire schedule_commit_error;
    wire schedule_valid;
    wire [7:0] schedule_epoch;
    wire [7:0] schedule_active_id;
    reg [1:0] schedule_active_slot = 2'b0;
    wire schedule_active_slot_valid;
    wire [1:0] schedule_active_source;
    wire schedule_active_expect;
    wire schedule_active_idle;
    wire [31:0] schedule_active_crc;
    wire schedule_commit_pending;
    reg captured_schedule_error;

    ot_schedule_controller #(
        .PORTS(3), .SLOTS(3), .PORT_ID_W(2), .SLOT_W(2), .ENTRY_W(4)
    ) schedule_dut (
        .clk(clk), .rst_n(rst_n), .shadow_wr_valid(schedule_wr_valid),
        .shadow_wr_ready(schedule_wr_ready), .shadow_wr_slot(schedule_wr_slot),
        .shadow_wr_data(schedule_wr_data), .commit_req(schedule_commit_req),
        .quiescent(schedule_quiescent), .epoch_boundary(schedule_epoch_boundary),
        .manifest_crc_ok(schedule_manifest_ok),
        .commit_schedule_id(schedule_commit_id), .commit_ack(schedule_commit_ack),
        .commit_error(schedule_commit_error), .schedule_valid(schedule_valid),
        .epoch_id(schedule_epoch), .active_schedule_id(schedule_active_id),
        .active_slot(schedule_active_slot),
        .active_slot_valid(schedule_active_slot_valid),
        .active_source_port(schedule_active_source),
        .active_expect_valid(schedule_active_expect),
        .active_idle(schedule_active_idle),
        .active_schedule_crc(schedule_active_crc),
        .commit_pending(schedule_commit_pending)
    );

    task automatic schedule_write;
        input [1:0] slot;
        input [3:0] data;
        begin
            @(negedge clk);
            schedule_wr_slot = slot;
            schedule_wr_data = data;
            schedule_wr_valid = 1'b1;
            while (!schedule_wr_ready)
                @(negedge clk);
            @(posedge clk);
            #1 captured_schedule_error = schedule_commit_error;
            @(negedge clk);
            schedule_wr_valid = 1'b0;
        end
    endtask

    task automatic schedule_commit;
        input manifest_ok;
        begin
            @(negedge clk);
            schedule_manifest_ok = manifest_ok;
            schedule_commit_req = 1'b1;
            @(posedge clk);
            #1 captured_schedule_error = schedule_commit_error;
            @(negedge clk);
            schedule_commit_req = 1'b0;
        end
    endtask

    // ------------------------------------------------------------------
    // Capacity-bounded session table.
    reg session_req_valid = 1'b0;
    wire session_req_ready;
    reg [2:0] session_req_op = 3'b0;
    reg [23:0] session_req_id = 24'b0;
    reg [7:0] session_req_image = 8'b0;
    reg [19:0] session_req_context = 20'b0;
    reg [19:0] session_req_position = 20'b0;
    reg [7:0] session_req_epoch = 8'b0;
    reg [15:0] session_req_transaction = 16'b0;
    reg session_req_force = 1'b0;
    wire session_rsp_valid;
    wire [7:0] session_rsp_status;
    wire session_rsp_hit;
    wire [7:0] session_rsp_generation;
    wire [19:0] session_rsp_position;
    wire session_rsp_poison;
    wire [1:0] session_busy_bitmap;
    wire session_integrity_error;
    reg [7:0] captured_session_status;
    reg captured_session_hit;
    reg [7:0] captured_session_generation;
    reg [19:0] captured_session_position;
    reg captured_session_poison;

    ot_session_table #(.ENTRIES(2)) session_dut (
        .clk(clk), .rst_n(rst_n), .req_valid(session_req_valid),
        .req_ready(session_req_ready), .req_op(session_req_op),
        .req_session_id(session_req_id), .req_image_slot(session_req_image),
        .req_context_minus_one(session_req_context),
        .req_position(session_req_position), .req_epoch_id(session_req_epoch),
        .req_transaction_id(session_req_transaction),
        .req_force(session_req_force), .rsp_valid(session_rsp_valid),
        .rsp_status(session_rsp_status), .rsp_hit(session_rsp_hit),
        .rsp_generation(session_rsp_generation),
        .rsp_expected_position(session_rsp_position),
        .rsp_poison(session_rsp_poison), .busy_bitmap(session_busy_bitmap),
        .integrity_error(session_integrity_error)
    );

    task automatic session_request;
        input [2:0] op;
        input [23:0] session_id;
        input [19:0] position;
        input [7:0] epoch;
        input [15:0] transaction;
        input force_request;
        begin
            @(negedge clk);
            session_req_op = op;
            session_req_id = session_id;
            session_req_image = 8'h3;
            session_req_context = 20'd8191;
            session_req_position = position;
            session_req_epoch = epoch;
            session_req_transaction = transaction;
            session_req_force = force_request;
            session_req_valid = 1'b1;
            @(posedge clk);
            #1;
            captured_session_status = session_rsp_status;
            captured_session_hit = session_rsp_hit;
            captured_session_generation = session_rsp_generation;
            captured_session_position = session_rsp_position;
            captured_session_poison = session_rsp_poison;
            @(negedge clk);
            session_req_valid = 1'b0;
        end
    endtask

    // ------------------------------------------------------------------
    // Stage controller with explicit protocol models on every side.
    reg stage_cmd_valid = 1'b0;
    wire stage_cmd_ready;
    reg [7:0] stage_cmd_opcode = 8'h10;
    reg [15:0] stage_cmd_transaction = 16'b0;
    reg stage_quiesce = 1'b0;
    reg stage_admission_block = 1'b0;
    reg stage_abort_valid = 1'b0;
    reg [15:0] stage_abort_transaction = 16'b0;
    wire stage_session_req_valid;
    wire [2:0] stage_session_req_op;
    wire [23:0] stage_session_req_session;
    wire [7:0] stage_session_req_image;
    wire [19:0] stage_session_req_context;
    wire [19:0] stage_session_req_position;
    wire [7:0] stage_session_req_epoch;
    wire [15:0] stage_session_req_transaction;
    wire stage_session_req_force;
    reg stage_session_rsp_valid = 1'b0;
    reg [7:0] stage_session_rsp_status = 8'b0;
    reg stage_session_rsp_hit = 1'b1;
    reg [7:0] stage_session_rsp_generation = 8'h5;
    reg [19:0] stage_session_rsp_position = 20'b0;
    reg stage_session_rsp_poison = 1'b0;
    wire stage_credit_reserve_valid;
    reg stage_credit_reserve_ready = 1'b1;
    wire [1:0] stage_credit_reserve_mask;
    wire stage_credit_release_valid;
    wire [1:0] stage_credit_release_mask;
    wire stage_service_start_valid;
    reg stage_service_start_ready = 1'b1;
    wire [15:0] stage_service_transaction;
    wire [23:0] stage_service_session;
    wire [7:0] stage_service_generation;
    wire stage_service_poison;
    reg stage_service_done_valid = 1'b0;
    reg [7:0] stage_service_done_status = 8'b0;
    reg [7:0] stage_service_done_source = 8'b0;
    reg [3:0] stage_service_done_syndrome = 4'b0;
    reg stage_watchdog_timeout = 1'b0;
    wire stage_completion_valid;
    wire [7:0] stage_completion_status;
    wire [7:0] stage_completion_source;
    wire [3:0] stage_completion_syndrome;
    wire [15:0] stage_completion_transaction;
    wire stage_idle;
    wire stage_poison;
    integer stage_commit_requests = 0;
    integer stage_abort_requests = 0;
    integer stage_credit_releases = 0;
    integer stage_service_starts = 0;
    reg stage_abort_seen;
    reg stage_completion_seen;
    reg [7:0] captured_stage_status;
    reg [7:0] captured_stage_source;
    reg [3:0] captured_stage_syndrome;

    ot_stage_controller #(.SINKS(2),.STAGE_ID(0)) stage_dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(stage_cmd_valid),
        .cmd_ready(stage_cmd_ready), .cmd_opcode(stage_cmd_opcode),
        .cmd_flags(8'b0), .cmd_epoch(8'h1), .cmd_schedule(8'h2),
        .cmd_session(24'h123), .cmd_position(20'b0),
        .cmd_context_minus_one(20'd8191), .cmd_batch_minus_one(16'b0),
        .cmd_first_layer(7'b0), .cmd_last_layer(7'b0),
        .cmd_draft_tokens(4'b0), .cmd_image_slot(8'h3),
        .cmd_activation_address(48'b0), .cmd_cookie(32'hcafe_f00d),
        .cmd_transaction_id(stage_cmd_transaction), .quiesce(stage_quiesce),
        .admission_block(stage_admission_block),
        .abort_valid(stage_abort_valid),
        .abort_transaction_id(stage_abort_transaction),
        .session_req_valid(stage_session_req_valid),
        .session_req_ready(1'b1), .session_req_op(stage_session_req_op),
        .session_req_session(stage_session_req_session),
        .session_req_image_slot(stage_session_req_image),
        .session_req_context_minus_one(stage_session_req_context),
        .session_req_position(stage_session_req_position),
        .session_req_epoch(stage_session_req_epoch),
        .session_req_transaction(stage_session_req_transaction),
        .session_req_force(stage_session_req_force),
        .session_rsp_valid(stage_session_rsp_valid),
        .session_rsp_status(stage_session_rsp_status),
        .session_rsp_hit(stage_session_rsp_hit),
        .session_rsp_generation(stage_session_rsp_generation),
        .session_rsp_expected_position(stage_session_rsp_position),
        .session_rsp_poison(stage_session_rsp_poison),
        .credit_reserve_valid(stage_credit_reserve_valid),
        .credit_reserve_ready(stage_credit_reserve_ready),
        .credit_reserve_mask(stage_credit_reserve_mask),
        .credit_release_valid(stage_credit_release_valid),
        .credit_release_mask(stage_credit_release_mask),
        .service_start_valid(stage_service_start_valid),
        .service_start_ready(stage_service_start_ready),
        .service_transaction_id(stage_service_transaction),
        .service_session_id(stage_service_session),
        .service_session_generation(stage_service_generation),
        .service_first_layer(), .service_last_layer(),
        .service_batch_minus_one(), .service_draft_tokens(),
        .service_schedule_id(), .service_flags(),
        .service_activation_address(), .service_poison(stage_service_poison),
        .service_done_valid(stage_service_done_valid),
        .service_done_status(stage_service_done_status),
        .service_done_error_source(stage_service_done_source),
        .service_done_syndrome(stage_service_done_syndrome),
        .watchdog_timeout(stage_watchdog_timeout),
        .completion_valid(stage_completion_valid),
        .completion_status(stage_completion_status),
        .completion_error_source(stage_completion_source),
        .completion_syndrome(stage_completion_syndrome),
        .completion_transaction_id(stage_completion_transaction),
        .completion_session_id(), .completion_position(), .completion_cookie(),
        .stage_idle(stage_idle), .stage_poison(stage_poison)
    );

    always @(posedge clk) begin
        if (stage_session_req_valid && stage_session_req_op == 3'd3)
            stage_commit_requests <= stage_commit_requests + 1;
        if (stage_session_req_valid && stage_session_req_op == 3'd4)
            stage_abort_requests <= stage_abort_requests + 1;
        if (stage_credit_release_valid)
            stage_credit_releases <= stage_credit_releases + 1;
        if (stage_service_start_valid && stage_service_start_ready)
            stage_service_starts <= stage_service_starts + 1;
        if (stage_completion_valid) begin
            stage_completion_seen <= 1'b1;
            captured_stage_status <= stage_completion_status;
            captured_stage_source <= stage_completion_source;
            captured_stage_syndrome <= stage_completion_syndrome;
        end
    end

    task automatic stage_send_command;
        input [15:0] transaction;
        begin
            @(negedge clk);
            stage_cmd_transaction = transaction;
            stage_cmd_valid = 1'b1;
            while (!stage_cmd_ready)
                @(negedge clk);
            @(negedge clk);
            stage_cmd_valid = 1'b0;
        end
    endtask

    task automatic stage_respond_session;
        input [2:0] expected_op;
        input poison_response;
        integer cycles;
        begin
            cycles = 0;
            while (!stage_session_req_valid && cycles < 24) begin
                @(negedge clk);
                cycles = cycles + 1;
            end
            if (!stage_session_req_valid || stage_session_req_op != expected_op) begin
                $display("stage expected session op %0d, saw valid=%b op=%0d",
                         expected_op,stage_session_req_valid,stage_session_req_op);
                failures = failures + 1;
            end else begin
                if (expected_op == 3'd4)
                    stage_abort_seen = 1'b1;
                @(negedge clk);
                stage_session_rsp_status = 8'h00;
                stage_session_rsp_hit = 1'b1;
                stage_session_rsp_generation = 8'h5;
                stage_session_rsp_position = 20'b0;
                stage_session_rsp_poison = poison_response;
                stage_session_rsp_valid = 1'b1;
                @(negedge clk);
                stage_session_rsp_valid = 1'b0;
                stage_session_rsp_poison = 1'b0;
            end
        end
    endtask

    task automatic stage_wait_completion;
        integer cycles;
        begin
            cycles = 0;
            while (!stage_completion_seen && cycles < 40) begin
                @(negedge clk);
                cycles = cycles + 1;
            end
        end
    endtask

    task automatic stage_clear_inputs;
        begin
            stage_cmd_valid = 1'b0;
            stage_session_rsp_valid = 1'b0;
            stage_session_rsp_poison = 1'b0;
            stage_service_done_valid = 1'b0;
            stage_watchdog_timeout = 1'b0;
            stage_abort_valid = 1'b0;
            stage_credit_reserve_ready = 1'b1;
            stage_service_start_ready = 1'b1;
            stage_abort_seen = 1'b0;
            stage_completion_seen = 1'b0;
        end
    endtask

    integer commit_before;
    integer abort_before;
    integer release_before;
    integer service_before;
    integer wait_cycles;
    reg [7:0] generation_a;

    initial begin
        // Power qualification, service, throttling, quiescence, and fail-safe.
        reset_duts();
        repeat (2) @(negedge clk);
        check_site("FC-POWER-BOOT-QUALIFICATION", power_state == 4'd1 &&
                   power_core_reset_n && !power_service_enable && !power_safe);
        power_service_request = 1'b1;
        @(negedge clk);
        check_site("FC-POWER-SERVICE-ENABLE", power_state == 4'd2 &&
                   power_service_enable && !power_isolation);
        thermal_warning = 1'b1;
        @(negedge clk);
        check_site("FC-POWER-THERMAL-THROTTLE", power_state == 4'd3 &&
                   power_throttle && power_service_enable);
        thermal_warning = 1'b0;
        @(negedge clk);
        check_site("FC-POWER-THROTTLE-RECOVERY", power_state == 4'd2 &&
                   !power_throttle && power_service_enable);
        power_test_enable = 1'b1;
        @(negedge clk);
        check_site("FC-POWER-TEST-INTERLOCK", power_state == 4'd4 && power_safe &&
                   power_isolation && !power_service_enable &&
                   power_reset_cause == 8'h05);

        power_service_request = 1'b0;
        power_test_enable = 1'b0;
        requalify = 1'b1;
        @(negedge clk);
        requalify = 1'b0;
        repeat (2) @(negedge clk);
        check_site("FC-POWER-REQUALIFY", power_state == 4'd1 && !power_safe);

        reset_duts();
        thermal_fatal = 1'b1;
        @(negedge clk);
        check_site("FC-POWER-THERMAL-FATAL", power_safe && power_state == 4'd4 &&
                   power_reset_cause == 8'h03 && !power_core_reset_n);
        thermal_fatal = 1'b0;

        reset_duts();
        clock_stable = 1'b0;
        @(negedge clk);
        check_site("FC-POWER-CLOCK-LOSS", power_safe && power_state == 4'd4 &&
                   power_reset_cause == 8'h02 && !power_core_reset_n);
        clock_stable = 1'b1;

        reset_duts();
        repeat (2) @(negedge clk);
        power_service_request = 1'b1;
        @(negedge clk);
        power_quiesce_request = 1'b1;
        power_core_quiescent = 1'b1;
        @(negedge clk);
        check_site("FC-POWER-QUIESCE", power_quiesce_ack && power_state == 4'd1 &&
                   !power_service_enable);
        power_service_request = 1'b0;
        power_quiesce_request = 1'b0;
        power_core_quiescent = 1'b0;

        // Schedule completeness/range/manifest/quiescence/identity.
        reset_duts();
        schedule_write(2'd0,4'b0101);
        schedule_commit(1'b1);
        check_site("FC-SCHEDULE-PARTIAL", captured_schedule_error &&
                   !schedule_commit_pending && !schedule_valid);
        schedule_write(2'd1,4'b0011);
        check_site("FC-SCHEDULE-ILLEGAL-SOURCE", captured_schedule_error &&
                   !schedule_commit_pending);

        reset_duts();
        schedule_write(2'd0,4'b0101);
        schedule_write(2'd1,4'b1000);
        schedule_write(2'd2,4'b1000);
        schedule_commit(1'b0);
        check_site("FC-SCHEDULE-BAD-MANIFEST", captured_schedule_error &&
                   !schedule_commit_pending && !schedule_valid);
        schedule_commit_id = 8'h5a;
        schedule_commit(1'b1);
        repeat (2) @(negedge clk);
        check_site("FC-SCHEDULE-QUIESCENCE", schedule_commit_pending &&
                   !schedule_commit_ack && !schedule_valid && schedule_epoch == 0);
        schedule_quiescent = 1'b1;
        schedule_epoch_boundary = 1'b1;
        @(negedge clk);
        check_site("FC-SCHEDULE-IDENTITY", schedule_commit_ack && schedule_valid &&
                   schedule_epoch == 1 && schedule_active_id == 8'h5a);
        schedule_quiescent = 1'b0;
        schedule_epoch_boundary = 1'b0;
        schedule_active_slot = 2'd0;
        @(negedge clk);
        check_site("FC-SCHEDULE-LEGAL-SOURCE", schedule_active_slot_valid &&
                   schedule_active_source == 2'd1 && schedule_active_expect &&
                   !schedule_active_idle);

        // Session capacity, stale epochs/transactions, poison, and generation.
        reset_duts();
        session_request(3'd0,24'h10,20'd0,8'h1,16'h100,1'b0);
        generation_a = captured_session_generation;
        check_site("FC-SESSION-CONFIGURE", captured_session_status == 8'h00 &&
                   captured_session_hit && generation_a != 0);
        session_request(3'd0,24'h10,20'd0,8'h1,16'h101,1'b0);
        check_site("FC-SESSION-DUPLICATE", captured_session_status == 8'h05);
        session_request(3'd0,24'h20,20'd0,8'h1,16'h200,1'b0);
        session_request(3'd0,24'h30,20'd0,8'h1,16'h300,1'b0);
        check_site("FC-SESSION-CAPACITY", captured_session_status == 8'h09 &&
                   session_busy_bitmap == 0 && !session_integrity_error);

        session_request(3'd2,24'h10,20'd1,8'h1,16'h110,1'b0);
        check_site("FC-SESSION-EPOCH", captured_session_status == 8'h07 &&
                   session_busy_bitmap == 0);
        session_request(3'd2,24'h10,20'd0,8'h1,16'h111,1'b0);
        check_site("FC-SESSION-LOOKUP", captured_session_status == 8'h00 &&
                   captured_session_hit && session_busy_bitmap != 0);
        session_request(3'd3,24'h10,20'd0,8'h1,16'h112,1'b0);
        check_site("FC-SESSION-LATE-TRANSACTION", captured_session_status == 8'h07 &&
                   captured_session_position == 20'd0 && session_busy_bitmap != 0);
        session_request(3'd4,24'h10,20'd0,8'h1,16'h111,1'b0);
        check_site("FC-SESSION-POISON", captured_session_status == 8'h00 &&
                   captured_session_poison && session_busy_bitmap == 0);
        session_request(3'd2,24'h10,20'd0,8'h1,16'h113,1'b0);
        check_site("FC-SESSION-POISON-OBSERVED", captured_session_poison);
        session_request(3'd1,24'h10,20'd0,8'h1,16'h114,1'b1);
        session_request(3'd0,24'h30,20'd0,8'h1,16'h301,1'b0);
        check_site("FC-SESSION-REUSE-GENERATION",
                   captured_session_status == 8'h00 &&
                   captured_session_generation != generation_a);

        // Stage no-credit path must cancel the session and never retire it.
        stage_clear_inputs();
        reset_duts();
        commit_before = stage_commit_requests;
        abort_before = stage_abort_requests;
        release_before = stage_credit_releases;
        service_before = stage_service_starts;
        stage_credit_reserve_ready = 1'b0;
        stage_send_command(16'h4001);
        stage_respond_session(3'd2,1'b0);
        stage_respond_session(3'd4,1'b1);
        stage_wait_completion();
        check_site("FC-STAGE-NO-CREDIT", stage_completion_seen &&
                   captured_stage_status == 8'h06 && stage_abort_seen &&
                   stage_abort_requests > abort_before &&
                   stage_commit_requests == commit_before &&
                   stage_service_starts == service_before &&
                   stage_credit_releases == release_before);

        // A service error must poison/cancel the session, release credits, and
        // preserve source/syndrome without issuing retire.
        stage_clear_inputs();
        reset_duts();
        commit_before = stage_commit_requests;
        abort_before = stage_abort_requests;
        release_before = stage_credit_releases;
        service_before = stage_service_starts;
        stage_send_command(16'h4002);
        stage_respond_session(3'd2,1'b0);
        while (stage_service_starts == service_before)
            @(negedge clk);
        @(negedge clk);
        stage_service_done_status = 8'h0f;
        stage_service_done_source = 8'h22;
        stage_service_done_syndrome = 4'ha;
        stage_service_done_valid = 1'b1;
        @(negedge clk);
        stage_service_done_valid = 1'b0;
        stage_respond_session(3'd4,1'b1);
        stage_wait_completion();
        check_site("FC-STAGE-SERVICE-ERROR", stage_completion_seen &&
                   captured_stage_status == 8'h0f &&
                   captured_stage_source == 8'h22 &&
                   captured_stage_syndrome == 4'ha && stage_poison &&
                   stage_abort_requests > abort_before &&
                   stage_commit_requests == commit_before &&
                   stage_credit_releases > release_before);

        // Watchdog requests poisoned drain, then aborts the session and frees
        // credits without a retire operation.
        stage_clear_inputs();
        reset_duts();
        commit_before = stage_commit_requests;
        abort_before = stage_abort_requests;
        release_before = stage_credit_releases;
        service_before = stage_service_starts;
        stage_send_command(16'h4003);
        stage_respond_session(3'd2,1'b0);
        while (stage_service_starts == service_before)
            @(negedge clk);
        stage_watchdog_timeout = 1'b1;
        @(negedge clk);
        stage_watchdog_timeout = 1'b0;
        wait_cycles = 0;
        while (!stage_service_poison && wait_cycles < 12) begin
            @(negedge clk);
            wait_cycles = wait_cycles + 1;
        end
        stage_service_done_status = 8'h00;
        stage_service_done_source = 8'h00;
        stage_service_done_syndrome = 4'h0;
        stage_service_done_valid = 1'b1;
        @(negedge clk);
        stage_service_done_valid = 1'b0;
        stage_respond_session(3'd4,1'b1);
        stage_wait_completion();
        check_site("FC-STAGE-WATCHDOG", stage_completion_seen &&
                   captured_stage_status == 8'h0b && stage_poison &&
                   stage_abort_requests > abort_before &&
                   stage_commit_requests == commit_before &&
                   stage_credit_releases > release_before);

        // Matching host abort has the same no-commit and release guarantee.
        stage_clear_inputs();
        reset_duts();
        commit_before = stage_commit_requests;
        abort_before = stage_abort_requests;
        release_before = stage_credit_releases;
        service_before = stage_service_starts;
        stage_send_command(16'h4004);
        stage_respond_session(3'd2,1'b0);
        while (stage_service_starts == service_before)
            @(negedge clk);
        stage_abort_transaction = 16'h4004;
        stage_abort_valid = 1'b1;
        @(negedge clk);
        stage_abort_valid = 1'b0;
        stage_service_done_valid = 1'b1;
        @(negedge clk);
        stage_service_done_valid = 1'b0;
        stage_respond_session(3'd4,1'b1);
        stage_wait_completion();
        check_site("FC-STAGE-HOST-ABORT", stage_completion_seen &&
                   captured_stage_status == 8'h0e && stage_poison &&
                   stage_abort_requests > abort_before &&
                   stage_commit_requests == commit_before &&
                   stage_credit_releases > release_before);

        if (failures == 0) begin
            $display("PASS: directed control-plane fault sites");
            $finish;
        end else begin
            $fatal(1,"%0d directed control-plane fault sites failed",failures);
        end
    end
endmodule
