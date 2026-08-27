`timescale 1ns/1ps

// Randomized data-boundary coverage for wide records and state that directed
// fault tests intentionally keep constant.  Every random source is deterministic
// and every transaction is checked against an independent behavioral model.
module tb_coverage_data_boundary;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer failures = 0;
    integer checks = 0;
    integer sample;
    integer index;
    integer wait_cycles;
    reg [31:0] rng_state = 32'h4441_5441;

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

    task automatic pulse_reset;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            repeat (3) @(negedge clk);
            rst_n = 1'b1;
            repeat (2) @(negedge clk);
        end
    endtask

    // ------------------------------------------------------------------
    // Tagged HBM boundary.
    reg hbm_req_valid = 1'b0;
    wire hbm_req_ready;
    reg [63:0] hbm_req_address = 64'b0;
    reg [23:0] hbm_req_session = 24'b0;
    reg [11:0] hbm_req_tag = 12'b0;
    reg [15:0] hbm_req_beats_m1 = 16'b0;
    reg [1:0] hbm_req_operation = 2'b0;
    reg [5:0] hbm_req_size = 6'b0;
    reg [3:0] hbm_req_stage = 4'b0;
    wire hbm_req_accepted;
    reg hbm_rsp_valid = 1'b0;
    wire hbm_rsp_ready;
    reg [511:0] hbm_rsp_data = 512'b0;
    reg [63:0] hbm_rsp_byte_valid = 64'b0;
    reg [11:0] hbm_rsp_tag = 12'b0;
    reg hbm_rsp_last = 1'b0;
    reg [2:0] hbm_rsp_error = 3'b0;
    reg [15:0] hbm_rsp_crc = 16'b0;
    wire hbm_complete_valid;
    wire [11:0] hbm_complete_tag;
    wire [23:0] hbm_complete_session;
    wire hbm_complete_poison;
    wire [2:0] hbm_complete_error;
    wire hbm_protocol_error;
    wire [3:0] hbm_outstanding;

    ot_hbm_frontend #(.TAGS(8),.MAX_OUTSTANDING(4),.TAG_W(3),.CHECK_CRC(1)) hbm_dut (
        .clk(clk),.rst_n(rst_n),.req_valid(hbm_req_valid),.req_ready(hbm_req_ready),
        .req_byte_address(hbm_req_address),.req_session_id(hbm_req_session),
        .req_tag(hbm_req_tag),.req_burst_beats_minus_one(hbm_req_beats_m1),
        .req_operation(hbm_req_operation),.req_size_log2_bytes(hbm_req_size),
        .req_stage_id(hbm_req_stage),.req_accepted(hbm_req_accepted),
        .rsp_valid(hbm_rsp_valid),.rsp_ready(hbm_rsp_ready),.rsp_data(hbm_rsp_data),
        .rsp_byte_valid(hbm_rsp_byte_valid),.rsp_tag(hbm_rsp_tag),
        .rsp_last(hbm_rsp_last),.rsp_error(hbm_rsp_error),.rsp_crc(hbm_rsp_crc),
        .complete_valid(hbm_complete_valid),.complete_tag(hbm_complete_tag),
        .complete_session_id(hbm_complete_session),
        .complete_poison(hbm_complete_poison),.complete_error(hbm_complete_error),
        .protocol_error(hbm_protocol_error),.outstanding_count(hbm_outstanding));

    function automatic [15:0] crc16_592;
        input [591:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 74; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ data[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_592 = c;
        end
    endfunction

    task automatic hbm_issue;
        input [11:0] tag;
        input [15:0] beats_minus_one;
        input [23:0] session_id;
        reg [31:0] random_word;
        begin
            random_word = random32();
            hbm_req_address = {random32(),random32()} & 64'hffff_ffff_ffff_ffc0;
            hbm_req_session = session_id;
            hbm_req_tag = tag;
            hbm_req_beats_m1 = beats_minus_one;
            hbm_req_operation = random_word[1:0];
            hbm_req_size = random_word[7:2];
            hbm_req_stage = random_word[11:8];
            while (!hbm_req_ready)
                @(negedge clk);
            hbm_req_valid = 1'b1;
            @(negedge clk);
            require_true(hbm_req_accepted,"HBM request acceptance pulse");
            hbm_req_valid = 1'b0;
        end
    endtask

    task automatic hbm_respond;
        input [11:0] tag;
        input last;
        input [2:0] error_code;
        input corrupt_crc;
        integer word_index;
        reg [591:0] body;
        begin
            for (word_index = 0; word_index < 16; word_index = word_index + 1)
                hbm_rsp_data[word_index*32 +: 32] = random32();
            hbm_rsp_byte_valid = {random32(),random32()};
            hbm_rsp_tag = tag;
            hbm_rsp_last = last;
            hbm_rsp_error = error_code;
            body = {hbm_rsp_error,hbm_rsp_last,hbm_rsp_tag,
                    hbm_rsp_byte_valid,hbm_rsp_data};
            hbm_rsp_crc = crc16_592(body) ^ (corrupt_crc ? 16'h0001 : 16'h0000);
            hbm_rsp_valid = 1'b1;
            @(negedge clk);
            require_true(hbm_rsp_ready,"HBM response reservation");
            hbm_rsp_valid = 1'b0;
        end
    endtask

    task automatic test_hbm;
        integer beat;
        integer burst_length;
        reg [23:0] expected_session;
        reg [31:0] random_word;
        reg [11:0] loop_tag;
        reg [15:0] loop_beats_minus_one;
        reg [23:0] loop_session;
        begin
            // Legal traffic toggles every request/response data field and all
            // tags while preserving in-tag order.
            for (sample = 0; sample < 128; sample = sample + 1) begin
                burst_length = (sample % 4) + 1;
                random_word = random32();
                expected_session = random_word[23:0];
                loop_tag = sample[11:0] & 12'h007;
                loop_beats_minus_one = burst_length[15:0] - 16'd1;
                hbm_issue(loop_tag,loop_beats_minus_one,expected_session);
                for (beat = 0; beat < burst_length; beat = beat + 1)
                    hbm_respond(loop_tag,beat == burst_length-1,3'b000,1'b0);
                require_true(hbm_complete_valid && hbm_complete_tag == loop_tag &&
                             hbm_complete_session == expected_session &&
                             !hbm_complete_poison && hbm_complete_error == 0,
                             "HBM randomized legal completion");
            end
            pass_bin("COV-DATA-HBM-LEGAL-RANDOM",hbm_outstanding == 0 && !hbm_protocol_error);

            // Fill the outstanding limit, complete out of issue order, and
            // verify that admission re-opens after every retired tag.
            for (index = 0; index < 4; index = index + 1) begin
                loop_tag = index[11:0];
                loop_session = 24'h800000 + index[23:0];
                hbm_issue(loop_tag,16'd0,loop_session);
            end
            require_true(hbm_outstanding == 4,"HBM maximum outstanding count");
            hbm_req_tag = 12'd4;
            hbm_req_valid = 1'b1;
            @(negedge clk);
            require_true(!hbm_req_ready && !hbm_req_accepted,"HBM capacity backpressure");
            hbm_req_valid = 1'b0;
            for (index = 3; index >= 0; index = index - 1) begin
                loop_tag = index[11:0];
                hbm_respond(loop_tag,1'b1,3'b000,1'b0);
                require_true(hbm_complete_valid && hbm_complete_tag == loop_tag,
                             "HBM interleaved completion");
            end
            pass_bin("COV-DATA-HBM-INTERLEAVE",hbm_outstanding == 0 && hbm_req_ready);

            // Independent protocol classifications.
            hbm_respond(12'hfff,1'b1,3'b000,1'b0);
            require_true(hbm_complete_valid && hbm_complete_poison &&
                         hbm_complete_error == 3'b111,"HBM unknown tag response");
            hbm_issue(0,0,24'h010101);
            hbm_respond(0,1'b1,3'b000,1'b1);
            require_true(hbm_complete_poison && hbm_complete_error == 3'b110,
                         "HBM CRC classification");
            hbm_issue(1,1,24'h020202);
            hbm_respond(1,1'b1,3'b000,1'b0);
            require_true(hbm_complete_poison && hbm_complete_error == 3'b111,
                         "HBM early-last classification");
            hbm_issue(2,0,24'h030303);
            hbm_respond(2,1'b0,3'b000,1'b0);
            require_true(hbm_complete_poison && hbm_complete_error == 3'b111,
                         "HBM missing-last classification");
            hbm_issue(3,0,24'h040404);
            hbm_respond(3,1'b1,3'b101,1'b0);
            require_true(hbm_complete_poison && hbm_complete_error == 3'b101,
                         "HBM responder error classification");
            pass_bin("COV-DATA-HBM-ERRORS",hbm_protocol_error && hbm_outstanding == 0);
        end
    endtask

    // ------------------------------------------------------------------
    // Immutable ROM wrapper with translation and ECC hook.
    reg rom_req_valid = 1'b0;
    wire rom_req_ready;
    reg [2:0] rom_logical_addr = 3'b0;
    reg [15:0] rom_transaction = 16'b0;
    reg [7:0] rom_sequence = 8'b0;
    reg [7:0] rom_repair_valid = 8'b0;
    reg [31:0] rom_repair_map = 32'b0;
    reg rom_inject_fault = 1'b0;
    reg [3:0] rom_inject_addr = 4'b0;
    reg [63:0] rom_inject_mask = 64'b0;
    wire rom_rsp_valid;
    wire [63:0] rom_rsp_data;
    wire [15:0] rom_rsp_transaction;
    wire [7:0] rom_rsp_sequence;
    wire [1:0] rom_rsp_syndrome;
    wire rom_rsp_poison;

    ot_rom_wrapper #(.LOGICAL_DEPTH(8),.PHYS_DEPTH(12),.DATA_W(64),
                     .READ_LATENCY(3),.TAG_W(16),.SEQ_W(8)) rom_dut (
        .clk(clk),.rst_n(rst_n),.req_valid(rom_req_valid),.req_ready(rom_req_ready),
        .logical_addr(rom_logical_addr),.transaction_id(rom_transaction),
        .seq_id(rom_sequence),.repair_valid(rom_repair_valid),
        .repair_map(rom_repair_map),.inject_fault(rom_inject_fault),
        .inject_fault_addr(rom_inject_addr),.inject_fault_mask(rom_inject_mask),
        .rsp_valid(rom_rsp_valid),.rsp_data(rom_rsp_data),
        .rsp_transaction_id(rom_rsp_transaction),.rsp_sequence(rom_rsp_sequence),
        .rsp_syndrome(rom_rsp_syndrome),.rsp_poison(rom_rsp_poison));

    task automatic rom_issue_and_check;
        input [2:0] logical_address;
        input [63:0] expected_data;
        input [1:0] expected_syndrome;
        input expected_poison;
        reg [15:0] expected_transaction;
        reg [7:0] expected_sequence;
        reg [31:0] random_word;
        begin
            random_word = random32();
            expected_transaction = random_word[15:0];
            random_word = random32();
            expected_sequence = random_word[7:0];
            @(negedge clk);
            rom_logical_addr = logical_address;
            rom_transaction = expected_transaction;
            rom_sequence = expected_sequence;
            rom_req_valid = 1'b1;
            @(negedge clk);
            require_true(rom_req_ready,"ROM fixed-latency ready");
            rom_req_valid = 1'b0;
            wait_cycles = 0;
            while (!rom_rsp_valid && wait_cycles < 12) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(rom_rsp_valid && rom_rsp_transaction == expected_transaction &&
                         rom_rsp_sequence == expected_sequence,"ROM response tag/sequence");
            if (!(rom_rsp_data == expected_data &&
                  rom_rsp_syndrome == expected_syndrome &&
                  rom_rsp_poison == expected_poison))
                $display("ROM_MISMATCH addr=%0d got_data=%h exp_data=%h got_syn=%b exp_syn=%b got_poison=%b exp_poison=%b",
                         logical_address,rom_rsp_data,expected_data,rom_rsp_syndrome,
                         expected_syndrome,rom_rsp_poison,expected_poison);
            require_true(rom_rsp_data == expected_data &&
                         rom_rsp_syndrome == expected_syndrome &&
                         rom_rsp_poison == expected_poison,"ROM data/syndrome response");
        end
    endtask

    task automatic test_rom;
        reg [3:0] physical_address;
        reg [63:0] expected_word;
        begin
            for (index = 0; index < 12; index = index + 1)
                rom_dut.mem[index] = {random32(),random32()};
            rom_repair_valid = 8'b0;
            for (sample = 0; sample < 64; sample = sample + 1) begin
                index = sample % 8;
                rom_issue_and_check(index[2:0],rom_dut.mem[index],2'b00,1'b0);
            end

            // Translate every logical row among the four physical spares.
            rom_repair_valid = 8'hff;
            for (index = 0; index < 8; index = index + 1)
                rom_repair_map[index*4 +: 4] =
                    4'd8 + {2'b00,index[1:0]};
            for (sample = 0; sample < 64; sample = sample + 1) begin
                index = sample % 8;
                physical_address = rom_repair_map[index*4 +: 4];
                rom_issue_and_check(index[2:0],rom_dut.mem[physical_address],2'b00,1'b0);
            end
            pass_bin("COV-DATA-ROM-RANDOM-REPAIR",rom_rsp_valid && !rom_rsp_poison);

            // Invalid repair, zero-mask, corrected single-bit, and poisoned
            // multi-bit injection are independently observable.
            rom_repair_map[0 +: 4] = 4'hf;
            rom_issue_and_check(3'd0,64'b0,2'b00,1'b1);
            rom_repair_valid = 8'b0;
            rom_inject_fault = 1'b1;
            rom_inject_addr = 4'd3;
            rom_inject_mask = 64'b0;
            rom_issue_and_check(3'd3,rom_dut.mem[3],2'b00,1'b0);
            rom_inject_mask = 64'h0000_0000_0000_0001;
            rom_issue_and_check(3'd3,rom_dut.mem[3],2'b01,1'b0);
            rom_inject_mask = 64'h8000_0000_0000_0001;
            expected_word = rom_dut.mem[3] ^ rom_inject_mask;
            rom_issue_and_check(3'd3,expected_word,2'b10,1'b1);
            rom_inject_fault = 1'b0;
            rom_inject_mask = 64'b0;
            pass_bin("COV-DATA-ROM-ECC",rom_rsp_syndrome == 2'b10 && rom_rsp_poison);
        end
    endtask

    // ------------------------------------------------------------------
    // BIST data/signature activity and DFT ownership.
    reg bist_start = 1'b0;
    reg bist_abort = 1'b0;
    reg bist_resource_ready = 1'b1;
    reg bist_fault = 1'b0;
    reg [31:0] bist_observed = 32'b0;
    reg [31:0] bist_expected = 32'b0;
    wire bist_busy;
    wire bist_done;
    wire bist_pass;
    wire [31:0] bist_signature;
    wire [3:0] bist_failing_address;
    wire bist_timeout;
    wire bist_owner;
    reg [2:0] seen_bist_state = 3'b0;
    ot_bist_controller #(.DEPTH(16),.ADDR_W(4),.TIMEOUT(32)) bist_dut (
        .clk(clk),.rst_n(rst_n),.start(bist_start),.abort(bist_abort),
        .resource_ready(bist_resource_ready),.fault_inject(bist_fault),
        .observed_word(bist_observed),.expected_word(bist_expected),
        .busy(bist_busy),.done(bist_done),.pass(bist_pass),
        .signature(bist_signature),.failing_address(bist_failing_address),
        .timeout(bist_timeout),.owner_test_mode(bist_owner));

    always @(posedge clk) begin
        case (bist_dut.state)
            2'd0: seen_bist_state[0] <= 1'b1;
            2'd1: seen_bist_state[1] <= 1'b1;
            2'd2: seen_bist_state[2] <= 1'b1;
            default: seen_bist_state <= seen_bist_state;
        endcase
    end

    reg timeout_bist_start = 1'b0;
    wire timeout_bist_done;
    wire timeout_bist_timeout;
    ot_bist_controller #(.DEPTH(16),.ADDR_W(4),.TIMEOUT(3)) timeout_bist_dut (
        .clk(clk),.rst_n(rst_n),.start(timeout_bist_start),.abort(1'b0),
        .resource_ready(1'b1),.fault_inject(1'b0),.observed_word(32'h1357_9bdf),
        .expected_word(32'h1357_9bdf),.busy(),.done(timeout_bist_done),.pass(),
        .signature(),.failing_address(),.timeout(timeout_bist_timeout),.owner_test_mode());

    task automatic start_normal_bist;
        begin
            @(negedge clk);
            bist_start = 1'b1;
            @(negedge clk);
            bist_start = 1'b0;
        end
    endtask

    task automatic test_bist;
        reg [31:0] random_word;
        begin
            start_normal_bist();
            while (!bist_busy) @(negedge clk);
            while (!bist_done) begin
                random_word = random32();
                bist_observed = random_word;
                bist_expected = random_word;
                @(negedge clk);
            end
            require_true(bist_pass && !bist_timeout && bist_signature != 0,
                         "BIST randomized full traversal");
            pass_bin("COV-DATA-BIST-FULL",bist_failing_address == 0 && !bist_owner);

            pulse_reset();
            start_normal_bist();
            while (!bist_busy) @(negedge clk);
            while (!bist_done) begin
                bist_observed = random32();
                bist_expected = ~bist_observed;
                @(negedge clk);
            end
            require_true(!bist_pass && bist_failing_address == 4'd15,
                         "BIST mismatch address traversal");
            pulse_reset();
            start_normal_bist();
            while (!bist_busy) @(negedge clk);
            bist_fault = 1'b1;
            @(negedge clk);
            bist_fault = 1'b0;
            bist_abort = 1'b1;
            @(negedge clk);
            bist_abort = 1'b0;
            while (!bist_done) @(negedge clk);
            require_true(!bist_pass,"BIST fault/abort containment");

            pulse_reset();
            timeout_bist_start = 1'b1;
            @(negedge clk);
            timeout_bist_start = 1'b0;
            while (!timeout_bist_done) @(negedge clk);
            pass_bin("COV-DATA-BIST-FAIL-ABORT-TIMEOUT",timeout_bist_timeout);
            pass_bin("COV-FSM-BIST-IDLE",seen_bist_state[0]);
            pass_bin("COV-FSM-BIST-RUN",seen_bist_state[1]);
            pass_bin("COV-FSM-BIST-DONE",seen_bist_state[2]);
        end
    endtask

    reg dft_test_request = 1'b0;
    reg dft_service_active = 1'b0;
    reg dft_service_quiesced = 1'b0;
    reg dft_scan_request = 1'b0;
    reg dft_bist_request = 1'b0;
    reg dft_bist_busy = 1'b0;
    reg dft_bist_done = 1'b0;
    reg dft_bypass = 1'b0;
    wire dft_test_mode;
    wire dft_scan_enable;
    wire dft_bist_start;
    wire dft_grant;
    wire dft_isolated;
    wire [31:0] dft_idcode;
    wire dft_bypass_active;
    reg [2:0] seen_dft_state = 3'b0;
    ot_dft_controller #(.IDCODE(32'ha5c3_5a3c)) dft_dut (
        .clk(clk),.rst_n(rst_n),.test_request(dft_test_request),
        .service_active(dft_service_active),.service_quiesced(dft_service_quiesced),
        .scan_enable_request(dft_scan_request),.bist_start_request(dft_bist_request),
        .bist_busy(dft_bist_busy),.bist_done(dft_bist_done),.bypass_select(dft_bypass),
        .test_mode(dft_test_mode),.scan_enable(dft_scan_enable),.bist_start(dft_bist_start),
        .test_access_grant(dft_grant),.service_isolated(dft_isolated),
        .idcode(dft_idcode),.bypass_active(dft_bypass_active));

    always @(posedge clk) begin
        case (dft_dut.state)
            2'd0: seen_dft_state[0] <= 1'b1;
            2'd1: seen_dft_state[1] <= 1'b1;
            2'd2: seen_dft_state[2] <= 1'b1;
            default: seen_dft_state <= seen_dft_state;
        endcase
    end

    task automatic test_dft;
        begin
            pulse_reset();
            dft_bypass = 1'b1;
            #1;
            require_true(dft_bypass_active && dft_idcode == 32'ha5c3_5a3c,
                         "DFT IDCODE and bypass");
            dft_service_active = 1'b1;
            dft_test_request = 1'b1;
            repeat (3) @(negedge clk);
            require_true(!dft_grant,"DFT active-service interlock");
            dft_service_active = 1'b0;
            dft_service_quiesced = 1'b1;
            repeat (3) @(negedge clk);
            require_true(dft_grant && dft_test_mode && dft_isolated,
                         "DFT quiescent grant");
            for (sample = 0; sample < 32; sample = sample + 1) begin
                dft_scan_request = sample[0];
                dft_bist_request = sample[1];
                dft_bist_busy = sample[2];
                dft_bist_done = sample[3];
                dft_bypass = sample[4];
                @(negedge clk);
            end
            dft_scan_request = 1'b0;
            dft_bist_request = 1'b0;
            dft_bist_busy = 1'b0;
            dft_bist_done = 1'b1;
            dft_test_request = 1'b0;
            repeat (3) @(negedge clk);
            pass_bin("COV-DATA-DFT-OWNERSHIP",!dft_grant && !dft_test_mode);
            pass_bin("COV-FSM-DFT-FUNC",seen_dft_state[0]);
            pass_bin("COV-FSM-DFT-ARM",seen_dft_state[1]);
            pass_bin("COV-FSM-DFT-TEST",seen_dft_state[2]);
        end
    endtask

    // ------------------------------------------------------------------
    // Legacy wordline-mask/ROM/MAC pipeline and non-power-of-two mask bound.
    reg legacy_in_valid = 1'b0;
    reg [3:0] legacy_expert_ids = 4'b0;
    reg [1:0] legacy_selected_valid = 2'b0;
    reg [1:0] legacy_word_index = 2'b0;
    reg [31:0] legacy_activations = 32'b0;
    wire legacy_out_valid;
    wire signed [31:0] legacy_partial_sum;
    opentallas_tile #(.NUM_EXPERTS(4),.TOP_K(2),.WORDS_PER_EXPERT(4),
                      .LANES(4),.ACT_W(8),.WEIGHT_W(8),.ACC_W(32)) legacy_dut (
        .clk(clk),.rst_n(rst_n),.in_valid(legacy_in_valid),
        .selected_expert_ids(legacy_expert_ids),
        .selected_valid(legacy_selected_valid),.word_index(legacy_word_index),
        .activations(legacy_activations),.out_valid(legacy_out_valid),
        .partial_sum(legacy_partial_sum));

    reg [3:0] bounded_ids = 4'b0;
    reg [1:0] bounded_valid = 2'b0;
    wire [2:0] bounded_mask;
    expert_mask_controller #(.NUM_EXPERTS(3),.TOP_K(2),.EXPERT_ID_W(2)) bounded_mask_dut (
        .selected_expert_ids(bounded_ids),.selected_valid(bounded_valid),
        .expert_mask(bounded_mask));

    task automatic legacy_issue_and_check;
        integer expert;
        integer lane;
        integer signed expected_sum;
        reg [3:0] expected_mask;
        reg [31:0] random_word;
        reg signed [7:0] activation_value;
        reg signed [7:0] weight_value;
        begin
            random_word = random32();
            legacy_expert_ids = random_word[3:0];
            legacy_selected_valid = random_word[5:4];
            legacy_word_index = random_word[7:6];
            legacy_activations = random32();
            expected_mask = 4'b0;
            if (legacy_selected_valid[0])
                expected_mask[legacy_expert_ids[1:0]] = 1'b1;
            if (legacy_selected_valid[1])
                expected_mask[legacy_expert_ids[3:2]] = 1'b1;
            expected_sum = 0;
            for (expert = 0; expert < 4; expert = expert + 1)
                if (expected_mask[expert])
                    for (lane = 0; lane < 4; lane = lane + 1) begin
                        activation_value = legacy_activations[lane*8 +: 8];
                        weight_value = legacy_dut.weight_rom.mem[
                            legacy_word_index*4+expert][lane*8 +: 8];
                        expected_sum = expected_sum + activation_value * weight_value;
                    end
            legacy_in_valid = 1'b1;
            @(negedge clk);
            legacy_in_valid = 1'b0;
            wait_cycles = 0;
            while (!legacy_out_valid && wait_cycles < 8) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(legacy_out_valid && legacy_partial_sum == expected_sum,
                         "legacy randomized ROM/MAC result");
        end
    endtask

    task automatic test_legacy;
        reg [31:0] random_word;
        begin
            pulse_reset();
            for (index = 0; index < 16; index = index + 1)
                legacy_dut.weight_rom.mem[index] = random32();
            for (sample = 0; sample < 512; sample = sample + 1) begin
                @(negedge clk);
                legacy_issue_and_check();
                random_word = random32();
                bounded_ids = random_word[3:0];
                random_word = random32();
                bounded_valid = random_word[1:0];
                #1;
                require_true(!bounded_mask[0] ||
                             ((bounded_valid[0] && bounded_ids[1:0] == 0) ||
                              (bounded_valid[1] && bounded_ids[3:2] == 0)),
                             "bounded expert mask mapping");
            end
            bounded_ids = 4'b1111;
            bounded_valid = 2'b11;
            #1;
            require_true(bounded_mask == 0,"non-power-of-two expert bound");
            pass_bin("COV-DATA-LEGACY-RANDOM",legacy_out_valid && checks > 500);
        end
    endtask

    initial begin
        pulse_reset();
        test_hbm();
        test_rom();
        test_bist();
        test_dft();
        test_legacy();
        if (failures == 0) begin
            $display("PASS: coverage data boundary seed=0x44415441 checks=%0d",checks);
            $finish;
        end else begin
            $fatal(1,"coverage data boundary failed: %0d failures in %0d checks",
                   failures,checks);
        end
    end
endmodule
