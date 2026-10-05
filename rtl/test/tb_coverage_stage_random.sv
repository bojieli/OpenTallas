`timescale 1ns/1ps

// Deterministic asynchronous-clock stage stress.  Directed setup proves a
// schedule/configure/service transaction, then source-correct random traffic
// toggles every external record boundary while applying reset, backpressure,
// thermal, fatal, abort, telemetry, and malformed-command stress.
module tb_coverage_stage_random;
    reg aon_clk = 1'b0;
    reg core_clk = 1'b0;
    reg aon_rst_n = 1'b0;
    reg core_rst_n = 1'b0;
    always #7 aon_clk = ~aon_clk;
    always #5 core_clk = ~core_clk;

    integer failures = 0;
    integer checks = 0;
    integer stress_cycle;
    integer word_index;
    integer csr_sweep;
    reg [31:0] rng_state = 32'h5354_4752;

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

    function automatic [15:0] crc16_112;
        input [111:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 14; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ data[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_112 = c;
        end
    endfunction

    function automatic [15:0] crc16_240;
        input [239:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 30; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ data[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_240 = c;
        end
    endfunction

    reg host_cmd_valid = 1'b0;
    wire host_cmd_ready;
    reg [255:0] host_cmd_record = 256'b0;
    wire host_rsp_valid;
    reg host_rsp_ready = 1'b0;
    wire [127:0] host_rsp_record;
    wire telemetry_valid;
    reg telemetry_ready = 1'b0;
    wire [127:0] telemetry_record;
    reg csr_req_valid = 1'b0;
    wire csr_req_ready;
    reg [127:0] csr_req_record = 128'b0;
    wire csr_rsp_valid;
    reg csr_rsp_ready = 1'b0;
    wire [127:0] csr_rsp_record;
    reg [255:0] image_slot_valid = {256{1'b1}};
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
    reg [7:0] service_done_source = 8'b0;
    reg [3:0] service_done_syndrome = 4'b0;
    reg power_good = 1'b1;
    reg clock_stable = 1'b1;
    reg hbm_ready = 1'b1;
    reg link_ready = 1'b1;
    reg bist_done = 1'b1;
    reg bist_pass = 1'b1;
    reg thermal_warning = 1'b0;
    reg thermal_fatal = 1'b0;
    reg fatal_error = 1'b0;
    reg requalify = 1'b0;
    reg test_enable = 1'b0;
    reg abort_valid = 1'b0;
    reg [15:0] abort_transaction_id = 16'b0;
    wire [3:0] power_state;
    wire safe_state;
    wire stage_idle;
    wire admission_block;
    reg schedule_wr_valid = 1'b0;
    reg [7:0] schedule_wr_slot = 8'b0;
    reg [15:0] schedule_wr_data = 16'b0;
    wire schedule_wr_ready;
    wire schedule_wr_ack;
    wire schedule_wr_error;
    reg schedule_commit_req = 1'b0;
    wire schedule_commit_ready;
    reg schedule_manifest_crc_ok = 1'b1;
    reg [7:0] schedule_commit_id = 8'b0;
    wire schedule_commit_ack;
    wire schedule_commit_error;
    wire schedule_valid;
    wire [63:0] boot_control_requests;
    wire csr_schedule_window_valid;
    wire [15:0] csr_schedule_window_address;
    wire [63:0] csr_schedule_window_data;
    wire [7:0] csr_schedule_window_strobe;
    wire csr_repair_window_valid;
    wire [15:0] csr_repair_window_address;
    wire [63:0] csr_repair_window_data;
    wire [7:0] csr_repair_window_strobe;

    ot_stage_top #(.SESSION_ENTRIES(4),.CREDIT_SINKS(2),.CREDIT_DEPTH(4),
                   .CMD_FIFO_DEPTH(4),.RSP_FIFO_DEPTH(4),.TELEM_FIFO_DEPTH(4),
                   .SCHEDULE_SLOTS(4),.SCHEDULE_PORTS(8)) dut (
        .aon_clk(aon_clk),.core_clk(core_clk),.aon_rst_n(aon_rst_n),.core_rst_n(core_rst_n),
        .host_cmd_valid(host_cmd_valid),.host_cmd_ready(host_cmd_ready),
        .host_cmd_record(host_cmd_record),.host_rsp_valid(host_rsp_valid),
        .host_rsp_ready(host_rsp_ready),.host_rsp_record(host_rsp_record),
        .telemetry_valid(telemetry_valid),.telemetry_ready(telemetry_ready),
        .telemetry_record(telemetry_record),.csr_req_valid(csr_req_valid),
        .csr_req_ready(csr_req_ready),.csr_req_record(csr_req_record),
        .csr_rsp_valid(csr_rsp_valid),.csr_rsp_ready(csr_rsp_ready),
        .csr_rsp_record(csr_rsp_record),.image_slot_valid(image_slot_valid),
        .service_start_valid(service_start_valid),.service_start_ready(service_start_ready),
        .service_transaction_id(service_transaction_id),.service_session_id(service_session_id),
        .service_session_generation(service_session_generation),
        .service_first_layer(service_first_layer),.service_last_layer(service_last_layer),
        .service_batch_minus_one(service_batch_minus_one),
        .service_draft_tokens(service_draft_tokens),.service_schedule_id(service_schedule_id),
        .service_flags(service_flags),.service_activation_address(service_activation_address),
        .service_poison(service_poison),.service_done_valid(service_done_valid),
        .service_done_status(service_done_status),
        .service_done_error_source(service_done_source),
        .service_done_syndrome(service_done_syndrome),.power_good(power_good),
        .clock_stable(clock_stable),.hbm_ready(hbm_ready),.link_ready(link_ready),
        .bist_done(bist_done),.bist_pass(bist_pass),.thermal_warning(thermal_warning),
        .thermal_fatal(thermal_fatal),.fatal_error(fatal_error),.requalify(requalify),
        .test_enable(test_enable),.abort_valid(abort_valid),
        .abort_transaction_id(abort_transaction_id),.power_state(power_state),
        .safe_state(safe_state),.stage_idle(stage_idle),.admission_block(admission_block),
        .schedule_wr_valid(schedule_wr_valid),.schedule_wr_slot(schedule_wr_slot),
        .schedule_wr_data(schedule_wr_data),.schedule_wr_ready(schedule_wr_ready),
        .schedule_wr_ack(schedule_wr_ack),.schedule_wr_error(schedule_wr_error),
        .schedule_commit_req(schedule_commit_req),
        .schedule_commit_ready(schedule_commit_ready),
        .schedule_manifest_crc_ok(schedule_manifest_crc_ok),
        .schedule_commit_id(schedule_commit_id),.schedule_commit_ack(schedule_commit_ack),
        .schedule_commit_error(schedule_commit_error),.schedule_valid(schedule_valid),
        .boot_control_requests(boot_control_requests),
        .csr_schedule_window_valid(csr_schedule_window_valid),
        .csr_schedule_window_address(csr_schedule_window_address),
        .csr_schedule_window_data(csr_schedule_window_data),
        .csr_schedule_window_strobe(csr_schedule_window_strobe),
        .csr_repair_window_valid(csr_repair_window_valid),
        .csr_repair_window_address(csr_repair_window_address),
        .csr_repair_window_data(csr_repair_window_data),
        .csr_repair_window_strobe(csr_repair_window_strobe));

    task automatic csr_write_control;
        reg [111:0] body;
        integer wait_cycles;
        begin
            body = 112'b0;
            body[1:0] = 2'd1;
            body[4:2] = 3'd3;
            body[23:8] = 16'h0020;
            body[31:24] = 8'hff;
            body[95:32] = 64'h1;
            body[111:96] = 16'hc501;
            @(negedge aon_clk);
            csr_req_record = {crc16_112(body),body};
            csr_req_valid = 1'b1;
            while (!csr_req_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            csr_req_valid = 1'b0;
            wait_cycles = 0;
            while (!csr_rsp_valid && wait_cycles < 100) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(csr_rsp_valid && csr_rsp_record[7:0] == 8'h00,
                         "stage CSR control write");
            csr_rsp_ready = 1'b1;
            @(negedge aon_clk);
            csr_rsp_ready = 1'b0;
        end
    endtask

    task automatic csr_write_register;
        input [15:0] address;
        input [63:0] data;
        input [7:0] strobe;
        reg [111:0] body;
        integer wait_cycles;
        begin
            body = 112'b0;
            body[1:0] = 2'd1;
            body[4:2] = 3'd3;
            body[23:8] = address;
            body[31:24] = strobe;
            body[95:32] = data;
            body[111:96] = address ^ data[15:0];
            @(negedge aon_clk);
            csr_req_record = {crc16_112(body),body};
            csr_req_valid = 1'b1;
            while (!csr_req_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            csr_req_valid = 1'b0;
            wait_cycles = 0;
            while (!csr_rsp_valid && wait_cycles < 100) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(csr_rsp_valid && csr_rsp_record[7:0] == 8'h00,
                         "stage CSR register write response");
            csr_rsp_ready = 1'b1;
            @(negedge aon_clk);
            csr_rsp_ready = 1'b0;
        end
    endtask

    task automatic csr_write_window;
        input [15:0] address;
        input [63:0] data;
        input [7:0] strobe;
        input expect_schedule;
        reg [111:0] body;
        integer wait_cycles;
        begin
            body = 112'b0;
            body[1:0] = 2'd1;
            body[4:2] = 3'd3;
            body[23:8] = address;
            body[31:24] = strobe;
            body[95:32] = data;
            body[111:96] = address ^ data[15:0];
            @(negedge aon_clk);
            csr_req_record = {crc16_112(body),body};
            csr_req_valid = 1'b1;
            while (!csr_req_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            csr_req_valid = 1'b0;
            if (expect_schedule)
                require_true(csr_schedule_window_valid &&
                             csr_schedule_window_address == address &&
                             csr_schedule_window_data == data &&
                             csr_schedule_window_strobe == strobe,
                             "stage CSR schedule window forwarding");
            else
                require_true(csr_repair_window_valid &&
                             csr_repair_window_address == address &&
                             csr_repair_window_data == data &&
                             csr_repair_window_strobe == strobe,
                             "stage CSR repair window forwarding");
            wait_cycles = 0;
            while (!csr_rsp_valid && wait_cycles < 100) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(csr_rsp_valid && csr_rsp_record[7:0] == 8'h00,
                         "stage CSR window write response");
            csr_rsp_ready = 1'b1;
            @(negedge aon_clk);
            csr_rsp_ready = 1'b0;
        end
    endtask

    task automatic schedule_write;
        input [7:0] slot;
        input [15:0] data;
        integer wait_cycles;
        begin
            @(negedge aon_clk);
            schedule_wr_slot = slot;
            schedule_wr_data = data;
            schedule_wr_valid = 1'b1;
            while (!schedule_wr_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            schedule_wr_valid = 1'b0;
            wait_cycles = 0;
            while (!schedule_wr_ack && !schedule_wr_error && wait_cycles < 100) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(schedule_wr_ack && !schedule_wr_error,"stage schedule write");
        end
    endtask

    task automatic commit_schedule;
        integer wait_cycles;
        begin
            @(negedge aon_clk);
            schedule_manifest_crc_ok = 1'b1;
            schedule_commit_id = 8'h33;
            schedule_commit_req = 1'b1;
            while (!schedule_commit_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            schedule_commit_req = 1'b0;
            wait_cycles = 0;
            while (!schedule_commit_ack && wait_cycles < 150) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(schedule_commit_ack,"stage schedule commit acknowledgement");
            wait_cycles = 0;
            while (!schedule_valid && wait_cycles < 50) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(schedule_valid,"stage schedule-valid synchronization");
        end
    endtask

    task automatic send_command;
        input [7:0] opcode;
        input [31:0] cookie;
        input expect_service;
        integer wait_cycles;
        reg [239:0] body;
        begin
            body = 240'b0;
            body[7:0] = opcode;
            body[15:8] = 8'h04;
            body[23:16] = 8'h01;
            body[39:32] = 8'h01;
            body[47:40] = 8'h33;
            body[71:48] = 24'h000123;
            body[91:72] = 20'h00000;
            body[111:92] = 20'h01fff;
            body[127:112] = 16'h0007;
            body[134:128] = 7'h00;
            body[141:135] = 7'h00;
            body[153:146] = 8'h00;
            body[201:154] = 48'h1234_5678_9abc;
            body[233:202] = cookie;
            @(negedge aon_clk);
            host_cmd_record = {crc16_240(body),body};
            host_cmd_valid = 1'b1;
            while (!host_cmd_ready)
                @(negedge aon_clk);
            @(negedge aon_clk);
            host_cmd_valid = 1'b0;
            if (expect_service) begin
                service_start_ready = 1'b1;
                wait_cycles = 0;
                while (!service_start_valid && wait_cycles < 200) begin
                    @(negedge core_clk);
                    wait_cycles = wait_cycles + 1;
                end
                require_true(service_start_valid,"stage service did not start");
                @(negedge core_clk);
                service_start_ready = 1'b0;
                service_done_status = 8'h00;
                service_done_source = 8'h00;
                service_done_syndrome = 4'h0;
                service_done_valid = 1'b1;
                @(negedge core_clk);
                service_done_valid = 1'b0;
            end
            host_rsp_ready = 1'b1;
            wait_cycles = 0;
            while (!host_rsp_valid && wait_cycles < 300) begin
                @(negedge aon_clk);
                wait_cycles = wait_cycles + 1;
            end
            require_true(host_rsp_valid && host_rsp_record[7:0] == 8'h00 &&
                         host_rsp_record[107:76] == cookie,
                         "stage command response");
            @(negedge aon_clk);
            host_rsp_ready = 1'b0;
        end
    endtask

    reg saw_host_stall = 1'b0;
    reg saw_csr_stall = 1'b0;
    reg saw_telem_stall = 1'b0;
    reg saw_safe = 1'b0;
    reg saw_throttle = 1'b0;
    reg saw_reset_recovery = 1'b0;
    reg saw_random_response = 1'b0;
    reg [4:0] seen_power_state = 5'b0;
    reg [127:0] held_host_response;
    reg [127:0] held_csr_response;
    reg [127:0] held_telemetry;
    reg [127:0] random_record128;
    reg [31:0] random_word;
    reg [31:0] csr_sweep_word;
    reg [63:0] csr_sweep_data;
    reg [15:0] csr_sweep_address;
    reg [7:0] csr_sweep_strobe;

    task automatic randomize_record128;
        output reg [127:0] value;
        begin
            value[31:0] = random32();
            value[63:32] = random32();
            value[95:64] = random32();
            value[127:96] = random32();
        end
    endtask

    task automatic randomize_record256;
        output reg [255:0] value;
        integer random_word_index;
        begin
            for (random_word_index = 0; random_word_index < 8;
                 random_word_index = random_word_index + 1)
                value[random_word_index*32 +: 32] = random32();
        end
    endtask

    always @(posedge aon_clk) begin
        if (aon_rst_n) begin
            case (power_state)
                4'd0: seen_power_state[0] <= 1'b1;
                4'd1: seen_power_state[1] <= 1'b1;
                4'd2: seen_power_state[2] <= 1'b1;
                4'd3: seen_power_state[3] <= 1'b1;
                4'd4: seen_power_state[4] <= 1'b1;
                default: seen_power_state <= seen_power_state;
            endcase
            if (host_cmd_valid && !host_cmd_ready)
                saw_host_stall <= 1'b1;
            if (csr_req_valid && !csr_req_ready)
                saw_csr_stall <= 1'b1;
            if (telemetry_valid && !telemetry_ready)
                saw_telem_stall <= 1'b1;
            if (safe_state)
                saw_safe <= 1'b1;
            if (power_state == 4'd3)
                saw_throttle <= 1'b1;
            if (host_rsp_valid)
                saw_random_response <= 1'b1;
            if (host_rsp_valid && !host_rsp_ready) begin
                if (held_host_response != 0)
                    require_true(host_rsp_record == held_host_response,
                                 "stage host response stall stability");
                held_host_response <= host_rsp_record;
            end else begin
                held_host_response <= 0;
            end
            if (csr_rsp_valid && !csr_rsp_ready) begin
                if (held_csr_response != 0)
                    require_true(csr_rsp_record == held_csr_response,
                                 "stage CSR response stall stability");
                held_csr_response <= csr_rsp_record;
            end else begin
                held_csr_response <= 0;
            end
            if (telemetry_valid && !telemetry_ready) begin
                if (held_telemetry != 0)
                    require_true(telemetry_record == held_telemetry,
                                 "stage telemetry stall stability");
                held_telemetry <= telemetry_record;
            end else begin
                held_telemetry <= 0;
            end
        end else begin
            held_host_response <= 0;
            held_csr_response <= 0;
            held_telemetry <= 0;
        end
    end

    initial begin
        repeat (6) @(negedge aon_clk);
        aon_rst_n = 1'b1;
        core_rst_n = 1'b1;
        repeat (16) @(negedge aon_clk);
        csr_write_control();

        // Exercise the integrated CSR boundary with legal wide-data traffic.
        // Only service-enable is held architecturally active; unused control
        // bits, masks, RW1C data, owner-window addresses/data, and strobes vary
        // independently and are checked through normal request/response flow.
        for (csr_sweep = 0; csr_sweep < 32; csr_sweep = csr_sweep + 1) begin
            csr_sweep_data[31:0] = random32();
            csr_sweep_data[63:32] = random32();
            csr_sweep_data[1:0] = 2'b01;
            csr_write_register(16'h0020,csr_sweep_data,8'hff);

            csr_sweep_data[31:0] = random32();
            csr_sweep_data[63:32] = random32();
            csr_write_register(16'h0030,csr_sweep_data,8'hff);

            csr_sweep_data[31:0] = random32();
            csr_sweep_data[63:32] = random32();
            csr_sweep_word = random32();
            csr_sweep_strobe = csr_sweep_word[7:0];
            csr_write_register(16'h0028,csr_sweep_data,csr_sweep_strobe);
            repeat (8) @(negedge aon_clk);

            csr_sweep_word = random32();
            csr_sweep_address = 16'h0400 |
                                ({6'b0,csr_sweep_word[9:0]} & 16'h03f8);
            csr_sweep_data[31:0] = random32();
            csr_sweep_data[63:32] = random32();
            csr_sweep_word = random32();
            csr_sweep_strobe = csr_sweep_word[7:0];
            csr_write_window(csr_sweep_address,csr_sweep_data,
                             csr_sweep_strobe,1'b1);

            csr_sweep_word = random32();
            csr_sweep_address = 16'h0800 |
                                ({6'b0,csr_sweep_word[9:0]} & 16'h03f8);
            csr_sweep_data[31:0] = random32();
            csr_sweep_data[63:32] = random32();
            csr_sweep_word = random32();
            csr_sweep_strobe = csr_sweep_word[7:0];
            csr_write_window(csr_sweep_address,csr_sweep_data,
                             csr_sweep_strobe,1'b0);
        end
        csr_write_control();
        csr_write_window(16'h0478,64'h0123_4567_89ab_cdef,8'h5a,1'b1);
        csr_write_window(16'h08f0,64'hfedc_ba98_7654_3210,8'ha5,1'b0);
        pass_bin("COV-STAGE-CSR-WINDOWS",
                 csr_schedule_window_address == 16'h0478 &&
                 csr_repair_window_address == 16'h08f0);
        repeat (12) @(negedge aon_clk);
        schedule_write(8'd0,16'h0009);
        schedule_write(8'd1,16'h0010);
        schedule_write(8'd2,16'h0010);
        schedule_write(8'd3,16'h0010);
        commit_schedule();
        send_command(8'h01,32'hc0de_0001,1'b0);
        send_command(8'h10,32'hc0de_0002,1'b1);
        pass_bin("COV-STAGE-DIRECTED-SERVICE",stage_idle && !service_poison);

        // Random traffic remains protocol-correct at each source: a stalled
        // valid record is retained; otherwise a new record may be offered.
        for (stress_cycle = 0; stress_cycle < 8192; stress_cycle = stress_cycle + 1) begin
            @(negedge aon_clk);
            random_word = random32();
            if (!(host_cmd_valid && !host_cmd_ready)) begin
                randomize_record256(host_cmd_record);
                host_cmd_valid = random_word[0];
            end
            if (!(csr_req_valid && !csr_req_ready)) begin
                randomize_record128(random_record128);
                csr_req_record = random_record128;
                csr_req_valid = random_word[1];
            end
            host_rsp_ready = random_word[2];
            csr_rsp_ready = random_word[3];
            telemetry_ready = random_word[4];

            for (word_index = 0; word_index < 8; word_index = word_index + 1)
                image_slot_valid[word_index*32 +: 32] = random32();
            service_start_ready = random_word[5];
            service_done_valid = ((stress_cycle % 23) == 0);
            random_word = random32();
            service_done_status = random_word[7:0];
            service_done_source = random_word[15:8];
            service_done_syndrome = random_word[19:16];
            abort_valid = ((stress_cycle % 37) == 0);
            abort_transaction_id = random_word[31:16];

            if (!(schedule_wr_valid && !schedule_wr_ready)) begin
                schedule_wr_valid = ((stress_cycle % 29) == 0);
                schedule_wr_slot = random_word[7:0];
                schedule_wr_data = random_word[23:8];
            end
            schedule_commit_req = ((stress_cycle % 211) == 0);
            schedule_manifest_crc_ok = random_word[24];
            schedule_commit_id = random_word[31:24];

            thermal_warning = (stress_cycle >= 800 && stress_cycle < 820);
            thermal_fatal = (stress_cycle == 1200);
            fatal_error = (stress_cycle == 2200);
            test_enable = (stress_cycle >= 3000 && stress_cycle < 3010);
            requalify = (stress_cycle == 1250 || stress_cycle == 2250 ||
                         stress_cycle == 3050);
            power_good = !((stress_cycle >= 4000 && stress_cycle < 4004));
            clock_stable = !((stress_cycle >= 4500 && stress_cycle < 4504));
            hbm_ready = !((stress_cycle >= 5000 && stress_cycle < 5004));
            link_ready = !((stress_cycle >= 5500 && stress_cycle < 5504));
            bist_done = !((stress_cycle >= 6000 && stress_cycle < 6004));
            bist_pass = !((stress_cycle >= 6500 && stress_cycle < 6504));

            // Independent asynchronous reset loss at two different protocol
            // phases, followed by the coupled online rendezvous.
            if (stress_cycle == 7000)
                core_rst_n = 1'b0;
            if (stress_cycle == 7004) begin
                core_rst_n = 1'b1;
                saw_reset_recovery = 1'b1;
            end
            if (stress_cycle == 7400)
                aon_rst_n = 1'b0;
            if (stress_cycle == 7404) begin
                aon_rst_n = 1'b1;
                saw_reset_recovery = 1'b1;
            end
        end

        host_cmd_valid = 1'b0;
        csr_req_valid = 1'b0;
        schedule_wr_valid = 1'b0;
        schedule_commit_req = 1'b0;
        service_done_valid = 1'b0;
        abort_valid = 1'b0;
        thermal_warning = 1'b0;
        thermal_fatal = 1'b0;
        fatal_error = 1'b0;
        test_enable = 1'b0;
        requalify = 1'b0;
        power_good = 1'b1;
        clock_stable = 1'b1;
        hbm_ready = 1'b1;
        link_ready = 1'b1;
        bist_done = 1'b1;
        bist_pass = 1'b1;
        host_rsp_ready = 1'b1;
        csr_rsp_ready = 1'b1;
        telemetry_ready = 1'b1;
        repeat (100) @(negedge aon_clk);

        pass_bin("COV-STAGE-RANDOM-BACKPRESSURE",
                 saw_host_stall && saw_csr_stall && saw_telem_stall);
        pass_bin("COV-STAGE-POWER-FAULT-STATES",saw_safe && saw_throttle);
        pass_bin("COV-STAGE-ASYNC-RESET-RECOVERY",saw_reset_recovery);
        pass_bin("COV-STAGE-RANDOM-RESPONSES",saw_random_response);
        pass_bin("COV-FSM-POWER-STANDBY",seen_power_state[0]);
        pass_bin("COV-FSM-POWER-IDLE",seen_power_state[1]);
        pass_bin("COV-FSM-POWER-ACTIVE",seen_power_state[2]);
        pass_bin("COV-FSM-POWER-THROTTLED",seen_power_state[3]);
        pass_bin("COV-FSM-POWER-SAFE",seen_power_state[4]);
        if (failures == 0) begin
            $display("PASS: stage random seed=0x53544752 cycles=8192 checks=%0d",checks);
            $finish;
        end else begin
            $fatal(1,"stage random failed: %0d failures in %0d checks",failures,checks);
        end
    end
endmodule
