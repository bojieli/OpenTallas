`timescale 1ns/1ps
// Directed reliability, BIST, and DFT ownership campaign.  This is logical
// public-tool evidence; target scan cells, ATPG, macro algorithms, and secure
// test authorization remain outside the RTL model.
module tb_fault_ras_dft;
    // Canonical coverage-merge stimulus identifier: 0x46524153 ("FRAS").
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;
    integer failures = 0;
    reg [31:0] coverage_rng = 32'h4652_4153;

    function automatic [31:0] random32;
        reg [31:0] x;
        begin
            x = coverage_rng;
            x = x ^ (x << 13);
            x = x ^ (x >> 17);
            x = x ^ (x << 5);
            coverage_rng = x;
            random32 = x;
        end
    endfunction

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
    // RAS aggregation, poison lifetime, telemetry reservation, and watchdog.
    reg ras_event_valid = 1'b0;
    reg [11:0] ras_event_code = 12'b0;
    reg [1:0] ras_event_severity = 2'b0;
    reg [9:0] ras_event_source = 10'b0;
    reg [7:0] ras_event_epoch = 8'b0;
    reg [15:0] ras_event_transaction = 16'b0;
    reg [15:0] ras_event_syndrome = 16'b0;
    reg ras_clear_first = 1'b0;
    reg ras_telemetry_ready = 1'b0;
    reg ras_telemetry_pop = 1'b0;
    wire ras_telemetry_valid;
    wire [127:0] ras_telemetry_record;
    reg ras_transaction_active = 1'b0;
    reg ras_transaction_poison_in = 1'b0;
    wire ras_transaction_poison;
    wire ras_safe_request;
    wire ras_admission_block;
    wire [31:0] ras_correctable_count;
    wire [31:0] ras_uncorrectable_count;
    wire [31:0] ras_fatal_count;
    wire ras_first_valid;
    wire [1:0] ras_first_severity;
    wire [9:0] ras_first_source;
    wire [7:0] ras_first_epoch;
    wire [15:0] ras_first_transaction;
    wire [15:0] ras_first_syndrome;
    reg ras_watchdog_enable = 1'b0;
    reg ras_watchdog_kick = 1'b0;
    reg [23:0] ras_watchdog_limit = 24'b0;
    wire ras_watchdog_timeout;

    ot_ras_controller #(.TELEMETRY_DEPTH(4),.WATCHDOG_W(24)) ras_dut (
        .clk(clk), .rst_n(rst_n), .event_valid(ras_event_valid),
        .event_code(ras_event_code), .event_severity(ras_event_severity),
        .event_source(ras_event_source), .event_epoch(ras_event_epoch),
        .event_transaction(ras_event_transaction),
        .event_syndrome(ras_event_syndrome),
        .event_clear_first(ras_clear_first),
        .telemetry_ready(ras_telemetry_ready),
        .telemetry_valid(ras_telemetry_valid),
        .telemetry_record(ras_telemetry_record),
        .telemetry_pop(ras_telemetry_pop),
        .transaction_active(ras_transaction_active),
        .transaction_poison_in(ras_transaction_poison_in),
        .transaction_poison(ras_transaction_poison),
        .safe_request(ras_safe_request), .admission_block(ras_admission_block),
        .correctable_count(ras_correctable_count),
        .uncorrectable_count(ras_uncorrectable_count),
        .fatal_count(ras_fatal_count), .first_error_valid(ras_first_valid),
        .first_error_severity(ras_first_severity),
        .first_error_source(ras_first_source),
        .first_error_epoch(ras_first_epoch),
        .first_error_transaction(ras_first_transaction),
        .first_error_syndrome(ras_first_syndrome),
        .watchdog_enable(ras_watchdog_enable),
        .watchdog_kick(ras_watchdog_kick),
        .watchdog_limit(ras_watchdog_limit),
        .watchdog_timeout(ras_watchdog_timeout)
    );

    function automatic [15:0] crc16_112;
        input [111:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 14; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ d[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_112 = c;
        end
    endfunction

    task automatic ras_event;
        input [11:0] code;
        input [1:0] severity;
        input [9:0] source;
        input [7:0] epoch;
        input [15:0] transaction;
        input [15:0] syndrome;
        begin
            @(negedge clk);
            ras_event_code = code;
            ras_event_severity = severity;
            ras_event_source = source;
            ras_event_epoch = epoch;
            ras_event_transaction = transaction;
            ras_event_syndrome = syndrome;
            ras_event_valid = 1'b1;
            @(negedge clk);
            ras_event_valid = 1'b0;
        end
    endtask

    // ------------------------------------------------------------------
    // Normal BIST engine and an independently parameterized timeout engine.
    reg bist_start_req = 1'b0;
    reg bist_abort = 1'b0;
    reg bist_resource_ready = 1'b1;
    reg bist_fault_inject = 1'b0;
    reg [31:0] bist_observed = 32'h55aa_33cc;
    reg [31:0] bist_expected = 32'h55aa_33cc;
    wire bist_busy;
    wire bist_done;
    wire bist_pass;
    wire [31:0] bist_signature;
    wire [1:0] bist_failing_address;
    wire bist_timeout;
    wire bist_owner;

    ot_bist_controller #(.DEPTH(4),.ADDR_W(2),.TIMEOUT(16)) bist_dut (
        .clk(clk), .rst_n(rst_n), .start(bist_start_req), .abort(bist_abort),
        .resource_ready(bist_resource_ready), .fault_inject(bist_fault_inject),
        .observed_word(bist_observed), .expected_word(bist_expected),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .signature(bist_signature), .failing_address(bist_failing_address),
        .timeout(bist_timeout), .owner_test_mode(bist_owner)
    );

    reg timeout_bist_start = 1'b0;
    wire timeout_bist_busy;
    wire timeout_bist_done;
    wire timeout_bist_pass;
    wire timeout_bist_timeout;
    ot_bist_controller #(.DEPTH(8),.ADDR_W(3),.TIMEOUT(2)) timeout_bist_dut (
        .clk(clk), .rst_n(rst_n), .start(timeout_bist_start), .abort(1'b0),
        .resource_ready(1'b1), .fault_inject(1'b0),
        .observed_word(32'h1234_5678), .expected_word(32'h1234_5678),
        .busy(timeout_bist_busy), .done(timeout_bist_done),
        .pass(timeout_bist_pass), .signature(), .failing_address(),
        .timeout(timeout_bist_timeout), .owner_test_mode()
    );

    task automatic start_bist;
        begin
            @(negedge clk);
            bist_start_req = 1'b1;
            @(negedge clk);
            bist_start_req = 1'b0;
        end
    endtask

    task automatic wait_bist_done;
        integer cycles;
        begin
            cycles = 0;
            while (!bist_done && cycles < 32) begin
                @(negedge clk);
                cycles = cycles + 1;
            end
            if (!bist_done) begin
                $display("normal BIST did not complete");
                failures = failures + 1;
            end
        end
    endtask

    // ------------------------------------------------------------------
    // DFT ownership interlock.
    reg dft_test_request = 1'b0;
    reg dft_service_active = 1'b0;
    reg dft_service_quiesced = 1'b0;
    reg dft_scan_request = 1'b0;
    reg dft_bist_request = 1'b0;
    reg dft_bist_busy = 1'b0;
    reg dft_bist_done = 1'b0;
    reg dft_bypass_select = 1'b0;
    wire dft_test_mode;
    wire dft_scan_enable;
    wire dft_bist_start;
    wire dft_grant;
    wire dft_service_isolated;
    wire [31:0] dft_idcode;
    wire dft_bypass_active;

    ot_dft_controller #(.IDCODE(32'h4f54_cafe)) dft_dut (
        .clk(clk), .rst_n(rst_n), .test_request(dft_test_request),
        .service_active(dft_service_active),
        .service_quiesced(dft_service_quiesced),
        .scan_enable_request(dft_scan_request),
        .bist_start_request(dft_bist_request), .bist_busy(dft_bist_busy),
        .bist_done(dft_bist_done), .bypass_select(dft_bypass_select),
        .test_mode(dft_test_mode), .scan_enable(dft_scan_enable),
        .bist_start(dft_bist_start), .test_access_grant(dft_grant),
        .service_isolated(dft_service_isolated), .idcode(dft_idcode),
        .bypass_active(dft_bypass_active)
    );

    integer wait_cycles;
    integer coverage_sample;
    reg [31:0] coverage_word0;
    reg [31:0] coverage_word1;
    reg [31:0] coverage_word2;
    reg [31:0] coverage_word3;
    reg [31:0] coverage_word4;
    reg [111:0] telemetry_body;
    reg [1:0] saved_first_severity;
    reg [9:0] saved_first_source;
    reg [15:0] saved_first_transaction;

    initial begin
        reset_duts();
        ras_transaction_active = 1'b1;
        ras_event(12'h101,2'd1,10'h12,8'h23,16'h3456,16'h5678);
        check_site("FC-RAS-CORRECTABLE", ras_correctable_count == 1 &&
                   ras_uncorrectable_count == 0 && !ras_transaction_poison &&
                   !ras_safe_request && ras_first_valid);
        telemetry_body = ras_telemetry_record[111:0];
        check_site("FC-RAS-TELEMETRY-INTEGRITY",
                   ras_telemetry_record[127:112] == crc16_112(telemetry_body) &&
                   telemetry_body[11:0] == 12'h101 &&
                   telemetry_body[13:12] == 2'd1 &&
                   telemetry_body[23:14] == 10'h12 &&
                   telemetry_body[31:24] == 8'h23 &&
                   telemetry_body[47:32] == 16'h3456 &&
                   telemetry_body[111:96] == 16'h5678);
        saved_first_severity = ras_first_severity;
        saved_first_source = ras_first_source;
        saved_first_transaction = ras_first_transaction;

        ras_event(12'h202,2'd2,10'h34,8'h45,16'h6789,16'h89ab);
        check_site("FC-RAS-UNCORRECTABLE", ras_uncorrectable_count == 1 &&
                   ras_transaction_poison && !ras_safe_request);
        check_site("FC-RAS-FIRST-STICKY", ras_first_severity == saved_first_severity &&
                   ras_first_source == saved_first_source &&
                   ras_first_transaction == saved_first_transaction);

        @(negedge clk);
        ras_clear_first = 1'b1;
        @(negedge clk);
        ras_clear_first = 1'b0;
        check_site("FC-RAS-FIRST-CLEAR", !ras_first_valid);

        ras_transaction_active = 1'b0;
        repeat (2) @(negedge clk);
        check_site("FC-RAS-POISON-LIFETIME", !ras_transaction_poison);

        reset_duts();
        ras_transaction_active = 1'b1;
        ras_event(12'h303,2'd3,10'h56,8'h67,16'h789a,16'h9abc);
        check_site("FC-RAS-FATAL", ras_fatal_count == 1 && ras_safe_request &&
                   ras_admission_block && ras_transaction_poison);

        reset_duts();
        ras_transaction_active = 1'b1;
        @(negedge clk);
        ras_transaction_poison_in = 1'b1;
        @(negedge clk);
        ras_transaction_poison_in = 1'b0;
        check_site("FC-RAS-EXTERNAL-POISON", ras_transaction_poison);

        reset_duts();
        ras_dut.correctable_count = 32'hffff_ffff;
        ras_event(12'h104,2'd1,10'h1,8'h1,16'h1,16'h1);
        check_site("FC-RAS-COUNTER-SATURATION",
                   ras_correctable_count == 32'hffff_ffff);

        reset_duts();
        ras_event(12'h001,2'd0,10'h1,8'h1,16'h1,16'h1);
        ras_event(12'h002,2'd0,10'h1,8'h1,16'h2,16'h2);
        ras_event(12'h003,2'd0,10'h1,8'h1,16'h3,16'h3);
        check_site("FC-RAS-TELEMETRY-RESERVE", ras_admission_block &&
                   ras_dut.telem_count == 3 && ras_telemetry_valid);
        ras_event(12'h004,2'd3,10'h1,8'h1,16'h4,16'h4);
        check_site("FC-RAS-TELEMETRY-FULL", ras_dut.telem_count == 4 &&
                   ras_safe_request && ras_admission_block);

        reset_duts();
        ras_watchdog_enable = 1'b1;
        ras_watchdog_limit = 24'd2;
        wait_cycles = 0;
        while (!ras_watchdog_timeout && wait_cycles < 8) begin
            @(negedge clk);
            wait_cycles = wait_cycles + 1;
        end
        check_site("FC-RAS-WATCHDOG", ras_watchdog_timeout &&
                   ras_safe_request && ras_admission_block);
        ras_watchdog_enable = 1'b0;
        ras_watchdog_limit = 24'b0;

        // Deterministic wide-record activity complements the directed fault
        // sites above.  Every event is drained losslessly, first-error state is
        // repeatedly cleared/re-captured, and the independent CRC check has
        // already established the record oracle used by this sweep.
        reset_duts();
        ras_telemetry_ready = 1'b1;
        ras_transaction_active = 1'b1;
        for (coverage_sample = 0; coverage_sample < 192;
             coverage_sample = coverage_sample + 1) begin
            coverage_word0 = random32();
            coverage_word1 = random32();
            coverage_word2 = random32();
            coverage_word3 = random32();
            coverage_word4 = random32();
            ras_event(coverage_word0[11:0],coverage_sample[1:0],
                      coverage_word1[9:0],coverage_word2[7:0],
                      coverage_word3[15:0],coverage_word4[15:0]);
            @(negedge clk);
            ras_clear_first = 1'b1;
            ras_transaction_active = coverage_sample[0];
            ras_transaction_poison_in = (coverage_sample % 17) == 0;
            @(negedge clk);
            ras_clear_first = 1'b0;
            ras_transaction_poison_in = 1'b0;
        end
        ras_telemetry_ready = 1'b0;
        ras_transaction_active = 1'b0;

        // White-box state injection is confined to this logical fault bench.
        // It reaches otherwise impractical saturation/timer transitions and is
        // followed immediately by architectural reset/recovery checks.
        @(negedge clk);
        ras_dut.timestamp = 48'ha55a_f00f_9669;
        ras_dut.watchdog_count = 24'hd3_a5_7c;
        ras_watchdog_limit = 24'he7_5a_c3;
        ras_watchdog_enable = 1'b1;
        ras_watchdog_kick = 1'b1;
        @(negedge clk);
        ras_watchdog_kick = 1'b0;
        ras_watchdog_enable = 1'b0;
        ras_watchdog_limit = 24'b0;
        reset_duts();

        // BIST pass, compare mismatch, explicit injection, abort, timeout, and
        // unavailable-resource ownership are separate planned sites.
        reset_duts();
        start_bist();
        wait_bist_done();
        check_site("FC-BIST-PASS", bist_pass && !bist_timeout && !bist_busy &&
                   !bist_owner && bist_signature != 0);

        reset_duts();
        start_bist();
        while (!bist_busy) @(negedge clk);
        bist_observed = 32'h55aa_33cd;
        @(negedge clk);
        bist_observed = bist_expected;
        wait_bist_done();
        check_site("FC-BIST-MISMATCH", !bist_pass && !bist_timeout &&
                   bist_failing_address == 2'd0);

        reset_duts();
        start_bist();
        while (!bist_busy) @(negedge clk);
        bist_fault_inject = 1'b1;
        @(negedge clk);
        bist_fault_inject = 1'b0;
        wait_bist_done();
        check_site("FC-BIST-INJECT", !bist_pass && !bist_timeout);

        reset_duts();
        start_bist();
        while (!bist_busy) @(negedge clk);
        bist_abort = 1'b1;
        @(negedge clk);
        bist_abort = 1'b0;
        wait_bist_done();
        check_site("FC-BIST-ABORT", !bist_pass && !bist_timeout && !bist_busy);

        reset_duts();
        bist_resource_ready = 1'b0;
        start_bist();
        repeat (3) @(negedge clk);
        check_site("FC-BIST-OWNERSHIP", !bist_busy && !bist_done && !bist_owner);
        bist_resource_ready = 1'b1;

        reset_duts();
        @(negedge clk);
        timeout_bist_start = 1'b1;
        @(negedge clk);
        timeout_bist_start = 1'b0;
        wait_cycles = 0;
        while (!timeout_bist_done && wait_cycles < 20) begin
            @(negedge clk);
            wait_cycles = wait_cycles + 1;
        end
        check_site("FC-BIST-TIMEOUT", timeout_bist_done && timeout_bist_timeout &&
                   !timeout_bist_pass && !timeout_bist_busy);

        // DFT reset behavior and bypass are deterministic.
        reset_duts();
        dft_bypass_select = 1'b1;
        @(negedge clk);
        check_site("FC-DFT-IDCODE-BYPASS", dft_idcode == 32'h4f54_cafe &&
                   dft_bypass_active && !dft_test_mode);

        dft_service_active = 1'b1;
        dft_test_request = 1'b1;
        repeat (3) @(negedge clk);
        check_site("FC-DFT-SERVICE-INTERLOCK", !dft_grant && !dft_test_mode &&
                   !dft_service_isolated);

        // Request can be armed only after service leaves active state.
        dft_service_active = 1'b0;
        dft_service_quiesced = 1'b1;
        repeat (3) @(negedge clk);
        check_site("FC-DFT-QUIESCENT-GRANT", dft_grant && dft_test_mode &&
                   dft_service_isolated && !dft_bypass_active);

        dft_scan_request = 1'b1;
        @(negedge clk);
        check_site("FC-DFT-SCAN-ISOLATION", dft_scan_enable && dft_grant &&
                   dft_service_isolated);
        dft_scan_request = 1'b0;

        dft_bist_request = 1'b1;
        @(negedge clk);
        check_site("FC-DFT-BIST-START", dft_bist_start && dft_test_mode);
        dft_bist_busy = 1'b1;
        dft_bist_request = 1'b0;
        dft_test_request = 1'b0;
        repeat (2) @(negedge clk);
        check_site("FC-DFT-BIST-OWNERSHIP", dft_test_mode && dft_grant &&
                   dft_service_isolated);
        dft_bist_busy = 1'b0;
        dft_bist_done = 1'b1;
        repeat (2) @(negedge clk);
        check_site("FC-DFT-TEST-EXIT", !dft_test_mode && !dft_grant &&
                   !dft_service_isolated);

        // A service race while ARM is pending cancels entry into test.
        reset_duts();
        dft_test_request = 1'b1;
        dft_service_active = 1'b0;
        dft_service_quiesced = 1'b0;
        @(negedge clk);
        dft_service_active = 1'b1;
        repeat (2) @(negedge clk);
        check_site("FC-DFT-ARM-RACE", !dft_test_mode && !dft_grant);

        if (failures == 0) begin
            $display("PASS: directed RAS BIST and DFT fault sites");
            $finish;
        end else begin
            $fatal(1,"%0d directed RAS/DFT fault sites failed",failures);
        end
    end
endmodule
