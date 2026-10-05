`timescale 1ns/1ps

// Deterministic control-plane functional coverage.  This bench drives the
// command, CSR, and session blocks through legal, malformed, capacity, wrap,
// backpressure, and recovery cases using independent CRC/status models.
module tb_coverage_control;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer failures = 0;
    integer checks = 0;
    reg [31:0] rng_state = 32'h4356_4354;

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

    // ------------------------------------------------------------------
    // Command frontend.
    reg cmd_valid = 1'b0;
    wire cmd_ready;
    reg [255:0] cmd_record = 256'b0;
    wire dispatch_valid;
    reg dispatch_ready = 1'b0;
    wire [7:0] dispatch_opcode;
    wire [7:0] dispatch_flags;
    wire [7:0] dispatch_epoch;
    wire [7:0] dispatch_schedule;
    wire [23:0] dispatch_session;
    wire [19:0] dispatch_position;
    wire [19:0] dispatch_context;
    wire [15:0] dispatch_batch;
    wire [6:0] dispatch_first;
    wire [6:0] dispatch_last;
    wire [3:0] dispatch_draft;
    wire [7:0] dispatch_image;
    wire [47:0] dispatch_address;
    wire [31:0] dispatch_cookie;
    wire [15:0] dispatch_transaction;
    reg completion_valid = 1'b0;
    reg [7:0] completion_status = 8'b0;
    reg [7:0] completion_source = 8'b0;
    reg [3:0] completion_syndrome = 4'b0;
    reg [7:0] active_epoch = 8'h21;
    reg [7:0] active_schedule = 8'h43;
    reg [255:0] image_slot_valid = {256{1'b1}};
    reg service_enable = 1'b1;
    reg quiesce = 1'b0;
    wire cmd_rsp_valid;
    reg cmd_rsp_ready = 1'b0;
    wire [127:0] cmd_rsp_record;
    wire [31:0] bad_crc_count;
    wire [31:0] bad_field_count;
    wire [31:0] accepted_count;
    wire [31:0] transaction_counter;
    ot_cmd_frontend #(.RSP_DEPTH(4),.MAX_LAYERS(64),.MAX_CONTEXT(65536),
                      .MAX_BATCH(1024)) cmd_dut (
        .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_record(cmd_record),.dispatch_valid(dispatch_valid),
        .dispatch_ready(dispatch_ready),.dispatch_opcode(dispatch_opcode),
        .dispatch_flags(dispatch_flags),.dispatch_epoch(dispatch_epoch),
        .dispatch_schedule(dispatch_schedule),.dispatch_session(dispatch_session),
        .dispatch_position(dispatch_position),.dispatch_context_minus_one(dispatch_context),
        .dispatch_batch_minus_one(dispatch_batch),.dispatch_first_layer(dispatch_first),
        .dispatch_last_layer(dispatch_last),.dispatch_draft_tokens(dispatch_draft),
        .dispatch_image_slot(dispatch_image),.dispatch_activation_address(dispatch_address),
        .dispatch_cookie(dispatch_cookie),.dispatch_transaction_id(dispatch_transaction),
        .completion_valid(completion_valid),.completion_status(completion_status),
        .completion_error_source(completion_source),.completion_syndrome(completion_syndrome),
        .active_epoch(active_epoch),.active_schedule(active_schedule),
        .image_slot_valid(image_slot_valid),.service_enable(service_enable),
        .quiesce(quiesce),.rsp_valid(cmd_rsp_valid),.rsp_ready(cmd_rsp_ready),
        .rsp_record(cmd_rsp_record),.bad_crc_count(bad_crc_count),
        .bad_field_count(bad_field_count),.accepted_count(accepted_count),
        .transaction_counter(transaction_counter));

    task automatic make_base_command;
        input [7:0] opcode;
        input [31:0] cookie;
        output reg [239:0] body;
        begin
            body = 240'b0;
            body[7:0] = opcode;
            body[15:8] = 8'h04;
            body[23:16] = 8'h01;
            body[31:24] = 8'h00;
            body[39:32] = active_epoch;
            body[47:40] = active_schedule;
            body[71:48] = 24'h55aa01;
            body[91:72] = 20'd7;
            body[111:92] = 20'd8191;
            body[127:112] = 16'd7;
            body[134:128] = 7'd3;
            body[141:135] = 7'd9;
            body[145:142] = (opcode == 8'h11) ? 4'd3 : 4'd0;
            body[153:146] = 8'h02;
            body[201:154] = 48'h0123_4567_89ab;
            body[233:202] = cookie;
        end
    endtask

    task automatic issue_command;
        input [239:0] body;
        input corrupt_crc;
        input [7:0] expected_status;
        input successful_dispatch;
        input stall_response;
        integer wait_cycles;
        reg [127:0] held_response;
        begin
            @(negedge clk);
            cmd_record = {crc16_240(body) ^ (corrupt_crc ? 16'h0001 : 16'h0000),body};
            cmd_valid = 1'b1;
            wait_cycles = 0;
            while (!cmd_ready && wait_cycles < 100) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!cmd_ready)
                $fatal(1,"command ready timeout");
            @(negedge clk);
            cmd_valid = 1'b0;

            if (successful_dispatch) begin
                wait_cycles = 0;
                while (!dispatch_valid && wait_cycles < 100) begin
                    @(negedge clk);
                    wait_cycles = wait_cycles + 1;
                end
                require_true(dispatch_valid,"legal command did not dispatch");
                require_true(dispatch_cookie == body[233:202] &&
                             dispatch_opcode == body[7:0] &&
                             dispatch_session == body[71:48],
                             "command parsed payload mismatch");
                dispatch_ready = 1'b1;
                @(negedge clk);
                dispatch_ready = 1'b0;
                completion_status = expected_status;
                completion_source = body[39:32] ^ body[47:40];
                completion_syndrome = body[145:142];
                completion_valid = 1'b1;
                @(negedge clk);
                completion_valid = 1'b0;
            end

            wait_cycles = 0;
            while (!cmd_rsp_valid && wait_cycles < 100) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!cmd_rsp_valid)
                $fatal(1,"command response timeout expected status=%h",expected_status);
            held_response = cmd_rsp_record;
            require_true(cmd_rsp_record[7:0] == expected_status,"command response status");
            require_true(cmd_rsp_record[107:76] == body[233:202],"command response cookie");
            require_true(cmd_rsp_record[127:112] == crc16_112(cmd_rsp_record[111:0]),
                         "command response CRC");
            if (stall_response) begin
                repeat (3) begin
                    @(negedge clk);
                    require_true(cmd_rsp_valid && cmd_rsp_record == held_response,
                                 "command response stall stability");
                end
            end
            cmd_rsp_ready = 1'b1;
            @(negedge clk);
            cmd_rsp_ready = 1'b0;
        end
    endtask

    task automatic test_commands;
        reg [239:0] body;
        reg [31:0] random_word;
        integer sample;
        begin
            make_base_command(8'h10,32'h1000_0001,body);
            issue_command(body,1'b1,8'h04,1'b0,1'b1);
            pass_bin("COV-CTRL-CMD-BAD-CRC",bad_crc_count == 1);

            make_base_command(8'h10,32'h1000_0002,body);
            body[23:16] = 8'h02;
            issue_command(body,1'b0,8'h02,1'b0,1'b0);
            pass_bin("COV-CTRL-CMD-BAD-VERSION",bad_field_count >= 1);

            make_base_command(8'h55,32'h1000_0003,body);
            issue_command(body,1'b0,8'h01,1'b0,1'b0);
            pass_bin("COV-CTRL-CMD-BAD-OPCODE",cmd_rsp_record[7:0] == 8'h01 || !cmd_rsp_valid);

            make_base_command(8'h10,32'h1000_0004,body);
            body[239:234] = 6'h3f;
            issue_command(body,1'b0,8'h03,1'b0,1'b0);
            pass_bin("COV-CTRL-CMD-BAD-FIELD",bad_field_count >= 3);

            make_base_command(8'h10,32'h1000_0005,body);
            image_slot_valid[2] = 1'b0;
            issue_command(body,1'b0,8'h08,1'b0,1'b0);
            image_slot_valid[2] = 1'b1;
            pass_bin("COV-CTRL-CMD-IMAGE-REJECT",1'b1);

            make_base_command(8'h10,32'h1000_0006,body);
            body[39:32] = active_epoch ^ 8'h80;
            issue_command(body,1'b0,8'h07,1'b0,1'b0);
            make_base_command(8'h10,32'h1000_0007,body);
            body[47:40] = active_schedule ^ 8'h40;
            issue_command(body,1'b0,8'h07,1'b0,1'b0);
            pass_bin("COV-CTRL-CMD-EPOCH-SCHEDULE",1'b1);

            make_base_command(8'h10,32'h1000_0008,body);
            service_enable = 1'b0;
            issue_command(body,1'b0,8'h0c,1'b0,1'b0);
            service_enable = 1'b1;
            pass_bin("COV-CTRL-CMD-STATE-REJECT",1'b1);

            // Legal no-op commands randomize every retained payload field and
            // wrap all three response-queue pointers under backpressure.
            for (sample = 0; sample < 96; sample = sample + 1) begin
                random_word = random32();
                make_base_command(8'h00,random_word,body);
                body[15:8] = {3'b000,random_word[4:0]};
                random_word = random32();
                body[39:32] = random_word[7:0];
                body[47:40] = random_word[15:8];
                body[71:48] = random_word[23:0];
                random_word = random32();
                body[91:72] = random_word[19:0] & 20'h0ffff;
                body[111:92] = 20'h0ffff;
                body[127:112] = random_word[31:16] & 16'h03ff;
                body[134:128] = random_word[6:0] & 7'h3f;
                body[141:135] = body[134:128] | 7'h20;
                body[153:146] = random_word[15:8];
                image_slot_valid[body[153:146]] = 1'b1;
                body[185:154] = random32();
                random_word = random32();
                body[201:186] = random_word[15:0];
                issue_command(body,1'b0,8'h00,1'b1,(sample % 11) == 0);
            end
            pass_bin("COV-CTRL-CMD-LEGAL-WRAP",
                     accepted_count == 96 && transaction_counter >= 104);
        end
    endtask

    // ------------------------------------------------------------------
    // CSR block.
    reg csr_req_valid = 1'b0;
    wire csr_req_ready;
    reg [127:0] csr_req_record = 128'b0;
    wire csr_rsp_valid;
    reg csr_rsp_ready = 1'b0;
    wire [127:0] csr_rsp_record;
    reg [63:0] csr_capabilities = 64'h0123_4567_89ab_cdef;
    reg [63:0] csr_status = 64'h1111_2222_3333_4444;
    reg [63:0] csr_heartbeat = 64'h5555_6666_7777_8888;
    reg [63:0] csr_power = 64'h9999_aaaa_bbbb_cccc;
    reg [255:0] csr_image = 256'h0123456789abcdef_fedcba9876543210_13579bdf2468ace0_0f1e2d3c4b5a6978;
    reg [63:0] csr_first_error = 64'hdead_beef_0123_4567;
    reg [63:0] csr_error_status = 64'h89ab_cdef_7654_3210;
    reg [63:0] csr_ras_dft = 64'h55aa_33cc_f00f_0ff0;
    wire [63:0] csr_control;
    wire [63:0] csr_error_mask;
    wire [63:0] csr_error_clear;
    wire csr_schedule_valid;
    wire [15:0] csr_schedule_address;
    wire [63:0] csr_schedule_data;
    wire [7:0] csr_schedule_strobe;
    wire csr_repair_valid;
    wire [15:0] csr_repair_address;
    wire [63:0] csr_repair_data;
    wire [7:0] csr_repair_strobe;
    wire [31:0] csr_bad_count;
    ot_csr_block csr_dut (
        .clk(clk),.rst_n(rst_n),.req_valid(csr_req_valid),.req_ready(csr_req_ready),
        .req_record(csr_req_record),.rsp_valid(csr_rsp_valid),.rsp_ready(csr_rsp_ready),
        .rsp_record(csr_rsp_record),.capabilities(csr_capabilities),.status_in(csr_status),
        .heartbeat(csr_heartbeat),.power_thermal_state(csr_power),.image_identity(csr_image),
        .first_error(csr_first_error),.error_status_in(csr_error_status),
        .ras_dft_status(csr_ras_dft),.control(csr_control),.error_mask(csr_error_mask),
        .error_status_clear(csr_error_clear),.schedule_window_valid(csr_schedule_valid),
        .schedule_window_address(csr_schedule_address),.schedule_window_data(csr_schedule_data),
        .schedule_window_strobe(csr_schedule_strobe),.repair_window_valid(csr_repair_valid),
        .repair_window_address(csr_repair_address),.repair_window_data(csr_repair_data),
        .repair_window_strobe(csr_repair_strobe),.bad_request_count(csr_bad_count));

    task automatic csr_request;
        input [1:0] operation;
        input [15:0] address;
        input [63:0] write_data;
        input [7:0] strobe;
        input corrupt_crc;
        input [7:0] expected_status;
        input stall_response;
        integer wait_cycles;
        reg [111:0] body;
        reg [15:0] tag;
        reg [127:0] held_response;
        begin
            tag = address ^ write_data[15:0];
            body = 112'b0;
            body[1:0] = operation;
            body[4:2] = 3'd3;
            body[23:8] = address;
            body[31:24] = strobe;
            body[95:32] = write_data;
            body[111:96] = tag;
            @(negedge clk);
            csr_req_record = {crc16_112(body) ^ (corrupt_crc ? 16'h0080 : 16'h0000),body};
            csr_req_valid = 1'b1;
            while (!csr_req_ready)
                @(negedge clk);
            @(negedge clk);
            csr_req_valid = 1'b0;
            wait_cycles = 0;
            while (!csr_rsp_valid && wait_cycles < 50) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!csr_rsp_valid)
                $fatal(1,"CSR response timeout address=%h",address);
            held_response = csr_rsp_record;
            require_true(csr_rsp_record[7:0] == expected_status,"CSR response status");
            require_true(csr_rsp_record[95:80] == tag,"CSR response tag");
            require_true(csr_rsp_record[127:112] == crc16_112(csr_rsp_record[111:0]),
                         "CSR response CRC");
            if (stall_response)
                repeat (3) begin
                    @(negedge clk);
                    require_true(csr_rsp_valid && csr_rsp_record == held_response,
                                 "CSR response stall stability");
                end
            csr_rsp_ready = 1'b1;
            @(negedge clk);
            csr_rsp_ready = 1'b0;
        end
    endtask

    task automatic test_csrs;
        integer index;
        integer sweep;
        reg [15:0] read_addresses [0:18];
        reg [31:0] random_word;
        reg [63:0] random_data;
        reg [15:0] random_address;
        reg [7:0] random_strobe;
        begin
            read_addresses[0]=16'h0000; read_addresses[1]=16'h0008;
            read_addresses[2]=16'h0010; read_addresses[3]=16'h0018;
            read_addresses[4]=16'h0020; read_addresses[5]=16'h0028;
            read_addresses[6]=16'h0030; read_addresses[7]=16'h0038;
            read_addresses[8]=16'h0040; read_addresses[9]=16'h0048;
            read_addresses[10]=16'h0050; read_addresses[11]=16'h0058;
            read_addresses[12]=16'h0060; read_addresses[13]=16'h0068;
            read_addresses[14]=16'h0c00; read_addresses[15]=16'h0100;
            read_addresses[16]=16'h0400; read_addresses[17]=16'h0800;
            read_addresses[18]=16'h0ff8;
            for (index = 0; index < 19; index = index + 1) begin
                random_word = random32();
                csr_capabilities = {random_word,random32()};
                csr_status = {random32(),random32()};
                csr_heartbeat = {random32(),random32()};
                csr_power = {random32(),random32()};
                csr_error_status = {random32(),random32()};
                csr_first_error = {random32(),random32()};
                csr_ras_dft = {random32(),random32()};
                csr_image[31:0] = random32();
                csr_image[63:32] = random32();
                csr_image[95:64] = random32();
                csr_image[127:96] = random32();
                csr_image[159:128] = random32();
                csr_image[191:160] = random32();
                csr_image[223:192] = random32();
                csr_image[255:224] = random32();
                csr_request(2'd0,read_addresses[index],64'b0,8'b0,1'b0,
                            (index == 18) ? 8'h03 : 8'h00,(index % 5) == 0);
            end
            pass_bin("COV-CTRL-CSR-READ-MAP",csr_bad_count == 1);

            random_data = {random32(),random32()};
            csr_request(2'd1,16'h0020,random_data,8'hff,1'b0,8'h00,1'b0);
            require_true(csr_control == random_data,"CSR control write");
            random_data = {random32(),random32()};
            csr_request(2'd1,16'h0030,random_data,8'hff,1'b0,8'h00,1'b0);
            require_true(csr_error_mask == random_data,"CSR error mask write");
            random_data = {random32(),random32()};
            csr_request(2'd1,16'h0028,random_data,8'hff,1'b0,8'h00,1'b0);
            require_true(csr_error_clear == 0,"CSR RW1C pulse returned low");
            random_data = {random32(),random32()};
            csr_request(2'd1,16'h0478,random_data,8'h5a,1'b0,8'h00,1'b0);
            random_data = {random32(),random32()};
            csr_request(2'd1,16'h08f0,random_data,8'ha5,1'b0,8'h00,1'b0);
            csr_request(2'd1,16'h0000,64'h1,8'hff,1'b0,8'h03,1'b0);
            csr_request(2'd0,16'h0010,64'b0,8'b0,1'b1,8'h04,1'b0);

            // Repeated legal writes exercise both transition directions on
            // every retained CSR/window bit.  Addresses remain naturally
            // aligned and inside their architected owner windows.
            for (sweep = 0; sweep < 64; sweep = sweep + 1) begin
                random_data = {random32(),random32()};
                csr_request(2'd1,16'h0020,random_data,8'hff,1'b0,8'h00,
                            (sweep % 17) == 0);
                require_true(csr_control == random_data,
                             "CSR randomized control retention");

                random_data = {random32(),random32()};
                csr_request(2'd1,16'h0030,random_data,8'hff,1'b0,8'h00,1'b0);
                require_true(csr_error_mask == random_data,
                             "CSR randomized error-mask retention");

                random_data = {random32(),random32()};
                random_word = random32();
                random_strobe = random_word[7:0];
                csr_request(2'd1,16'h0028,random_data,random_strobe,
                            1'b0,8'h00,1'b0);
                require_true(csr_error_clear == 0,
                             "CSR randomized RW1C pulse returned low");

                random_word = random32();
                random_address = 16'h0400 |
                                 ({6'b0,random_word[9:0]} & 16'h03f8);
                random_data = {random32(),random32()};
                random_word = random32();
                random_strobe = random_word[7:0];
                csr_request(2'd1,random_address,random_data,random_strobe,
                            1'b0,8'h00,1'b0);

                random_word = random32();
                random_address = 16'h0800 |
                                 ({6'b0,random_word[9:0]} & 16'h03f8);
                random_data = {random32(),random32()};
                random_word = random32();
                random_strobe = random_word[7:0];
                csr_request(2'd1,random_address,random_data,random_strobe,
                            1'b0,8'h00,1'b0);
            end
            pass_bin("COV-CTRL-CSR-WRITE-WINDOWS",csr_bad_count == 3);
        end
    endtask

    // ------------------------------------------------------------------
    // Session table.
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
    wire [3:0] session_rsp_generation;
    wire [19:0] session_rsp_position;
    wire session_rsp_poison;
    wire [3:0] session_busy;
    wire session_integrity_error;
    reg [23:0] sweep_session_id [0:3];
    reg [7:0] sweep_image [0:3];
    reg [19:0] sweep_context [0:3];
    reg [19:0] sweep_position [0:3];
    reg [7:0] sweep_epoch [0:3];
    reg [15:0] sweep_transaction [0:3];
    ot_session_table #(.ENTRIES(4),.GENERATION_W(4)) session_dut (
        .clk(clk),.rst_n(rst_n),.req_valid(session_req_valid),.req_ready(session_req_ready),
        .req_op(session_req_op),.req_session_id(session_req_id),
        .req_image_slot(session_req_image),.req_context_minus_one(session_req_context),
        .req_position(session_req_position),.req_epoch_id(session_req_epoch),
        .req_transaction_id(session_req_transaction),.req_force(session_req_force),
        .rsp_valid(session_rsp_valid),.rsp_status(session_rsp_status),.rsp_hit(session_rsp_hit),
        .rsp_generation(session_rsp_generation),.rsp_expected_position(session_rsp_position),
        .rsp_poison(session_rsp_poison),.busy_bitmap(session_busy),
        .integrity_error(session_integrity_error));

    task automatic session_request;
        input [2:0] operation;
        input [23:0] session_id;
        input [7:0] image;
        input [19:0] context_m1;
        input [19:0] position;
        input [7:0] epoch;
        input [15:0] transaction;
        input force_request;
        input [7:0] expected_status;
        begin
            @(negedge clk);
            session_req_op = operation;
            session_req_id = session_id;
            session_req_image = image;
            session_req_context = context_m1;
            session_req_position = position;
            session_req_epoch = epoch;
            session_req_transaction = transaction;
            session_req_force = force_request;
            session_req_valid = 1'b1;
            @(negedge clk);
            session_req_valid = 1'b0;
            require_true(session_rsp_valid,"session response missing");
            require_true(session_rsp_status == expected_status,"session response status");
        end
    endtask

    task automatic test_sessions;
        integer iteration;
        integer entry_index;
        reg [3:0] first_generation;
        reg [31:0] random_word;
        reg [31:0] random_context;
        begin
            session_request(3'd1,24'hffffff,8'h01,20'hfffff,20'hfffff,8'hff,16'hffff,1'b0,8'h03);
            session_request(3'd2,24'heeeeee,8'h02,20'h12345,20'h100,8'h12,16'h1111,1'b0,8'h03);
            session_request(3'd3,24'hdddddd,8'h03,20'h23456,20'h200,8'h23,16'h2222,1'b0,8'h03);
            session_request(3'd4,24'hcccccc,8'h04,20'h34567,20'h300,8'h34,16'h3333,1'b0,8'h03);
            session_request(3'd7,24'hbbbbbb,8'h05,20'h45678,20'h400,8'h45,16'h4444,1'b0,8'h03);
            pass_bin("COV-CTRL-SESSION-MISS-ILLEGAL",!session_rsp_hit);

            session_request(3'd0,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1001,1'b0,8'h00);
            first_generation = session_rsp_generation;
            session_request(3'd2,24'h000101,8'h12,20'h01000,20'h20,8'h21,16'h1002,1'b0,8'h07);
            session_request(3'd2,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1002,1'b0,8'h00);
            session_request(3'd2,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1003,1'b0,8'h05);
            session_request(3'd1,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1003,1'b0,8'h05);
            session_request(3'd3,24'h000101,8'h11,20'h01000,20'h21,8'h21,16'h1002,1'b0,8'h07);
            session_request(3'd4,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h9999,1'b0,8'h07);
            session_request(3'd4,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h9999,1'b1,8'h00);
            session_request(3'd3,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1002,1'b0,8'h0f);
            session_request(3'd1,24'h000101,8'h11,20'h01000,20'h20,8'h21,16'h1002,1'b1,8'h00);
            pass_bin("COV-CTRL-SESSION-BUSY-POISON-FORCE",first_generation != 0);

            // Repeated allocation/release wraps the four-bit allocation
            // generation without ever aliasing generation zero.
            for (iteration = 0; iteration < 20; iteration = iteration + 1) begin
                random_word = random32();
                random_context = random32();
                session_request(3'd0,random_word[23:0],random_word[31:24],
                                random_context[19:0],20'b0,random_word[15:8],
                                random_word[15:0],1'b0,8'h00);
                require_true(session_rsp_generation != 0,"session generation zero");
                session_request(3'd1,random_word[23:0],random_word[31:24],
                                session_req_context,20'b0,random_word[15:8],
                                random_word[15:0],1'b1,8'h00);
            end
            pass_bin("COV-CTRL-SESSION-GENERATION-WRAP",
                     session_dut.allocation_generation != 0 && !session_integrity_error);

            // Fill every physical entry before touching any of them, then
            // exercise lookup, ordered retire, and release.  Repetition with
            // independent values toggles all retained state on every entry.
            for (iteration = 0; iteration < 24; iteration = iteration + 1) begin
                for (entry_index = 0; entry_index < 4;
                     entry_index = entry_index + 1) begin
                    random_word = random32();
                    sweep_session_id[entry_index] =
                        {random_word[23:8],iteration[5:0],entry_index[1:0]};
                    random_word = random32();
                    sweep_image[entry_index] = random_word[7:0];
                    sweep_epoch[entry_index] = random_word[15:8];
                    sweep_transaction[entry_index] = random_word[31:16];
                    random_word = random32();
                    sweep_context[entry_index] = random_word[19:0];
                    random_word = random32();
                    sweep_position[entry_index] = random_word[19:0];
                    session_request(3'd0,sweep_session_id[entry_index],
                                    sweep_image[entry_index],sweep_context[entry_index],
                                    sweep_position[entry_index],sweep_epoch[entry_index],
                                    sweep_transaction[entry_index],1'b0,8'h00);
                end
                require_true(session_dut.entry_valid == 4'hf,
                             "session all-entry allocation");
                for (entry_index = 0; entry_index < 4;
                     entry_index = entry_index + 1) begin
                    sweep_transaction[entry_index] =
                        sweep_transaction[entry_index] ^ 16'h5aa5;
                    session_request(3'd2,sweep_session_id[entry_index],
                                    sweep_image[entry_index],sweep_context[entry_index],
                                    sweep_position[entry_index],sweep_epoch[entry_index],
                                    sweep_transaction[entry_index],1'b0,8'h00);
                    require_true(session_busy[entry_index],
                                 "session all-entry lookup busy");
                    session_request(3'd3,sweep_session_id[entry_index],
                                    sweep_image[entry_index],sweep_context[entry_index],
                                    sweep_position[entry_index],sweep_epoch[entry_index],
                                    sweep_transaction[entry_index],1'b0,8'h00);
                    require_true(session_rsp_position ==
                                 (sweep_position[entry_index] + 20'd1),
                                 "session all-entry ordered retire");
                    session_request(3'd1,sweep_session_id[entry_index],
                                    sweep_image[entry_index],sweep_context[entry_index],
                                    sweep_position[entry_index] + 20'd1,
                                    sweep_epoch[entry_index],
                                    sweep_transaction[entry_index],1'b1,8'h00);
                end
                require_true(session_dut.entry_valid == 4'h0 && session_busy == 4'h0,
                             "session all-entry release");
            end
            pass_bin("COV-CTRL-SESSION-ALL-ENTRY-DATA",
                     !session_integrity_error && session_dut.entry_valid == 0);

            session_request(3'd0,24'h100001,8'h01,20'h100,20'h0,8'h1,16'h1,1'b0,8'h00);
            session_request(3'd0,24'h200002,8'h02,20'h200,20'h0,8'h2,16'h2,1'b0,8'h00);
            session_request(3'd0,24'h300003,8'h03,20'h300,20'h0,8'h3,16'h3,1'b0,8'h00);
            session_request(3'd0,24'h400004,8'h04,20'h400,20'h0,8'h4,16'h4,1'b0,8'h00);
            session_request(3'd0,24'h500005,8'h05,20'h500,20'h0,8'h5,16'h5,1'b0,8'h09);
            pass_bin("COV-CTRL-SESSION-CAPACITY",session_busy == 0);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        test_commands();
        test_csrs();
        test_sessions();
        if (failures == 0) begin
            $display("PASS: coverage control seed=0x43564354 checks=%0d",checks);
            $finish;
        end else begin
            $fatal(1,"coverage control failed: %0d failures in %0d checks",failures,checks);
        end
    end
endmodule
