`timescale 1ns/1ps
module tb_qwen_ta_dma_rmsnorm;
    localparam integer ELEMENTS = 4096;
    localparam integer DMA_BYTES = 8192;
    localparam integer DMA_WRITES = 512;
    localparam [63:0] HBM_BASE = 64'd1244659712;
    localparam [63:0] INPUT_BASE = 64'd1048576;
    localparam [63:0] WEIGHT_BASE = 64'd2097152;
    localparam [63:0] DEST_BASE = 64'd3145728;
    localparam [511:0] DMA_RECORD =
        512'hb5d7c76d00000000000000000000000000002000000000000000000000000000002000000000000000000000000000004a300000000000010000000100000101;
    localparam [511:0] RMS_RECORD =
        512'hea9b35a400000000358637bd00001000000000010000000000000000000000000030000000000000002000000000000000100000000000010000000200000320;
    localparam [511:0] RMS_BAD_CRC_RECORD =
        512'h6a9b35a400000000358637bd00001000000000010000000000000000000000000030000000000000002000000000000000100000000000010000000200000320;

    localparam integer FAULT_NONE = 0;
    localparam integer FAULT_HBM = 1;
    localparam integer FAULT_INPUT_NONFINITE = 2;
    localparam integer FAULT_INPUT_OVERFLOW = 3;
    localparam integer FAULT_WEIGHT_NONFINITE = 4;
    localparam integer FAULT_WEIGHT_OVERFLOW = 5;

    reg clk = 0;
    reg rst_n = 0;
    reg cmd_valid = 0;
    wire cmd_ready;
    reg cmd_last = 0;
    reg [15:0] abi_major = 16'd2;
    reg [15:0] abi_minor = 16'd5;
    reg [31:0] expected_command_index = 0;
    reg [511:0] command_record = 0;
    wire hbm_request_valid;
    reg hbm_request_ready = 0;
    wire [63:0] hbm_request_address;
    wire [15:0] hbm_request_bytes;
    reg hbm_response_valid = 0;
    wire hbm_response_ready;
    reg [511:0] hbm_response_data = 0;
    reg [1:0] hbm_response_error = 0;
    wire sram_read_valid;
    reg sram_read_ready = 0;
    wire [63:0] sram_read_address;
    reg sram_response_valid = 0;
    wire sram_response_ready;
    reg [15:0] sram_response_data = 0;
    wire sram_write_valid;
    reg sram_write_ready = 0;
    wire [63:0] sram_write_address;
    wire [127:0] sram_write_data;
    wire [15:0] sram_write_byte_enable;
    wire program_active;
    wire program_done_valid;
    reg program_done_ready = 0;
    wire [7:0] program_done_error;
    wire [31:0] program_done_failing_command_index;
    wire [31:0] program_done_last_command_index;
    wire [31:0] program_done_commands_accepted;
    wire [31:0] program_done_commands_completed;
    wire [31:0] program_done_hbm_request_count;
    wire [31:0] program_done_hbm_response_count;
    wire [31:0] program_done_hbm_bytes_read;
    wire [31:0] program_done_sram_read_count;
    wire [31:0] program_done_sram_bytes_read;
    wire [31:0] program_done_sram_write_count;
    wire [31:0] program_done_sram_bytes_written;
    wire [31:0] program_done_element_count;
    wire [31:0] program_done_normalized_saturation_count;
    wire [31:0] program_done_output_saturation_count;
    wire [31:0] program_done_mean_square_code;
    wire [31:0] program_done_inverse_rms_code;

    reg [7:0] payload_mem [0:DMA_BYTES-1];
    reg [15:0] input_mem [0:ELEMENTS-1];
    reg [15:0] weight_mem [0:ELEMENTS-1];
    reg [15:0] expected_mem [0:ELEMENTS-1];
    reg [15:0] destination_mem [0:ELEMENTS-1];

    integer fault_mode = FAULT_NONE;
    reg pending_hbm = 0;
    integer pending_hbm_burst = 0;
    integer pending_hbm_delay = 0;
    reg pending_read = 0;
    reg [15:0] pending_read_data = 0;
    integer pending_read_delay = 0;
    integer cycles = 0;
    integer hbm_requests = 0;
    integer hbm_responses = 0;
    integer dma_writes = 0;
    integer input_reads = 0;
    integer weight_reads = 0;
    integer sram_read_responses = 0;
    integer rms_writes = 0;
    integer request_stalls = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer lane;
    integer index;
    integer timeout;

    always #5 clk = ~clk;

    ot_ta_dma_rmsnorm_sequencer dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready), .cmd_last(cmd_last),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record),
        .hbm_request_valid(hbm_request_valid),
        .hbm_request_ready(hbm_request_ready),
        .hbm_request_address(hbm_request_address),
        .hbm_request_bytes(hbm_request_bytes),
        .hbm_response_valid(hbm_response_valid),
        .hbm_response_ready(hbm_response_ready),
        .hbm_response_data(hbm_response_data),
        .hbm_response_error(hbm_response_error),
        .sram_read_valid(sram_read_valid),
        .sram_read_ready(sram_read_ready),
        .sram_read_address(sram_read_address),
        .sram_response_valid(sram_response_valid),
        .sram_response_ready(sram_response_ready),
        .sram_response_data(sram_response_data),
        .sram_write_valid(sram_write_valid),
        .sram_write_ready(sram_write_ready),
        .sram_write_address(sram_write_address),
        .sram_write_data(sram_write_data),
        .sram_write_byte_enable(sram_write_byte_enable),
        .program_active(program_active),
        .program_done_valid(program_done_valid),
        .program_done_ready(program_done_ready),
        .program_done_error(program_done_error),
        .program_done_failing_command_index(
            program_done_failing_command_index),
        .program_done_last_command_index(program_done_last_command_index),
        .program_done_commands_accepted(program_done_commands_accepted),
        .program_done_commands_completed(program_done_commands_completed),
        .program_done_hbm_request_count(program_done_hbm_request_count),
        .program_done_hbm_response_count(program_done_hbm_response_count),
        .program_done_hbm_bytes_read(program_done_hbm_bytes_read),
        .program_done_sram_read_count(program_done_sram_read_count),
        .program_done_sram_bytes_read(program_done_sram_bytes_read),
        .program_done_sram_write_count(program_done_sram_write_count),
        .program_done_sram_bytes_written(
            program_done_sram_bytes_written),
        .program_done_element_count(program_done_element_count),
        .program_done_normalized_saturation_count(
            program_done_normalized_saturation_count),
        .program_done_output_saturation_count(
            program_done_output_saturation_count),
        .program_done_mean_square_code(program_done_mean_square_code),
        .program_done_inverse_rms_code(program_done_inverse_rms_code)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hbm_request_ready <= 0;
            hbm_response_valid <= 0;
            hbm_response_data <= 0;
            hbm_response_error <= 0;
            sram_read_ready <= 0;
            sram_response_valid <= 0;
            sram_response_data <= 0;
            sram_write_ready <= 0;
            pending_hbm <= 0;
            pending_hbm_burst <= 0;
            pending_hbm_delay <= 0;
            pending_read <= 0;
            pending_read_data <= 0;
            pending_read_delay <= 0;
            cycles <= 0;
            hbm_requests <= 0;
            hbm_responses <= 0;
            dma_writes <= 0;
            input_reads <= 0;
            weight_reads <= 0;
            sram_read_responses <= 0;
            rms_writes <= 0;
            request_stalls <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
        end else begin
            cycles <= cycles + 1;
            hbm_request_ready <= (cycles % 5) != 1;
            sram_read_ready <= cycles[0];
            sram_write_ready <= (cycles % 7) != 3;

            if (hbm_request_valid && !hbm_request_ready)
                request_stalls <= request_stalls + 1;
            if (sram_read_valid && !sram_read_ready)
                read_stalls <= read_stalls + 1;
            if (sram_write_valid && !sram_write_ready)
                write_stalls <= write_stalls + 1;

            if (hbm_response_valid && hbm_response_ready) begin
                hbm_response_valid <= 0;
                hbm_response_error <= 0;
                hbm_responses <= hbm_responses + 1;
            end
            if (hbm_request_valid && hbm_request_ready) begin
                if (pending_hbm || hbm_response_valid)
                    $fatal(1, "more than one HBM request outstanding");
                if (hbm_request_address !== HBM_BASE + hbm_requests*64 ||
                    hbm_request_bytes !== 16'd64)
                    $fatal(1, "HBM request differs at %0d", hbm_requests);
                pending_hbm <= 1;
                pending_hbm_burst <= hbm_requests;
                pending_hbm_delay <= (hbm_requests % 4) + 1;
                hbm_requests <= hbm_requests + 1;
            end
            if (pending_hbm) begin
                if (pending_hbm_delay == 0 && !hbm_response_valid) begin
                    for (lane = 0; lane < 64; lane = lane + 1)
                        hbm_response_data[lane*8 +: 8] <=
                            payload_mem[pending_hbm_burst*64 + lane];
                    hbm_response_error <= fault_mode == FAULT_HBM
                                          ? 2'd1 : 2'd0;
                    hbm_response_valid <= 1;
                    pending_hbm <= 0;
                end else begin
                    pending_hbm_delay <= pending_hbm_delay - 1;
                end
            end

            if (sram_response_valid && sram_response_ready) begin
                sram_response_valid <= 0;
                sram_read_responses <= sram_read_responses + 1;
            end
            if (sram_read_valid && sram_read_ready) begin
                if (pending_read || sram_response_valid)
                    $fatal(1, "more than one SRAM read outstanding");
                if (dma_writes != DMA_WRITES)
                    $fatal(1, "RMSNorm read bypassed incomplete DMA");
                if (sram_read_address >= INPUT_BASE &&
                    sram_read_address < INPUT_BASE + DMA_BYTES) begin
                    index = (sram_read_address - INPUT_BASE) >> 1;
                    if (index != input_reads)
                        $fatal(1, "input read order differs at %0d", index);
                    if (index == 0 &&
                        fault_mode == FAULT_INPUT_NONFINITE)
                        pending_read_data <= 16'h7f80;
                    else if (index == 0 &&
                             fault_mode == FAULT_INPUT_OVERFLOW)
                        pending_read_data <= 16'h7f7f;
                    else
                        pending_read_data <= input_mem[index];
                    input_reads <= input_reads + 1;
                end else if (sram_read_address >= WEIGHT_BASE &&
                             sram_read_address < WEIGHT_BASE + DMA_BYTES) begin
                    index = (sram_read_address - WEIGHT_BASE) >> 1;
                    if (index != weight_reads)
                        $fatal(1, "weight read order differs at %0d", index);
                    if (index == 0 &&
                        fault_mode == FAULT_WEIGHT_NONFINITE)
                        pending_read_data <= 16'h7f80;
                    else if (index == 0 &&
                             fault_mode == FAULT_WEIGHT_OVERFLOW)
                        pending_read_data <= 16'h7f7f;
                    else
                        pending_read_data <= weight_mem[index];
                    weight_reads <= weight_reads + 1;
                end else begin
                    $fatal(1, "SRAM read outside RMSNorm operands");
                end
                pending_read <= 1;
                pending_read_delay <=
                    ((input_reads + weight_reads) % 3) + 1;
            end
            if (pending_read) begin
                if (pending_read_delay == 0 && !sram_response_valid) begin
                    sram_response_data <= pending_read_data;
                    sram_response_valid <= 1;
                    pending_read <= 0;
                end else begin
                    pending_read_delay <= pending_read_delay - 1;
                end
            end

            if (sram_write_valid && sram_write_ready) begin
                if (sram_write_address >= WEIGHT_BASE &&
                    sram_write_address < WEIGHT_BASE + DMA_BYTES) begin
                    if (sram_write_byte_enable !== 16'hffff ||
                        sram_write_address !== WEIGHT_BASE + dma_writes*16)
                        $fatal(1, "DMA SRAM write metadata differs");
                    for (lane = 0; lane < 8; lane = lane + 1) begin
                        index = dma_writes*8 + lane;
                        if (sram_write_data[lane*16 +: 16] !==
                            {payload_mem[index*2 + 1], payload_mem[index*2]})
                            $fatal(1, "DMA data differs at %0d", index);
                        weight_mem[index] <=
                            sram_write_data[lane*16 +: 16];
                    end
                    dma_writes <= dma_writes + 1;
                end else if (sram_write_address >= DEST_BASE &&
                             sram_write_address < DEST_BASE + DMA_BYTES) begin
                    index = (sram_write_address - DEST_BASE) >> 1;
                    if (input_reads != ELEMENTS ||
                        weight_reads != ELEMENTS)
                        $fatal(1, "write preceded complete numeric pass");
                    if (sram_write_byte_enable !== 16'h0003 ||
                        sram_write_data[15:0] !== expected_mem[index] ||
                        index != rms_writes)
                        $fatal(1, "RMSNorm write differs at %0d", index);
                    destination_mem[index] <= sram_write_data[15:0];
                    rms_writes <= rms_writes + 1;
                end else begin
                    $fatal(1, "SRAM write outside composed regions");
                end
            end

            if (cycles > 300000)
                $fatal(1, "campaign case timed out");
        end
    end

    task automatic reset_case(input integer selected_fault);
        integer clear_index;
        begin
            rst_n = 0;
            cmd_valid = 0;
            cmd_last = 0;
            program_done_ready = 0;
            fault_mode = selected_fault;
            for (clear_index = 0; clear_index < ELEMENTS;
                 clear_index = clear_index + 1) begin
                weight_mem[clear_index] = 0;
                destination_mem[clear_index] = 0;
            end
            repeat (3) @(posedge clk);
            @(negedge clk);
            rst_n = 1;
        end
    endtask

    task automatic submit_command(
        input [511:0] record,
        input [31:0] expected_index,
        input reg last
    );
        begin
            timeout = 0;
            while (!cmd_ready) begin
                @(posedge clk);
                timeout = timeout + 1;
                if (timeout > 300000)
                    $fatal(1, "command ready timeout");
            end
            @(negedge clk);
            command_record = record;
            expected_command_index = expected_index;
            cmd_last = last;
            cmd_valid = 1;
            @(posedge clk);
            if (!cmd_ready)
                $fatal(1, "command handshake disappeared");
            @(negedge clk);
            cmd_valid = 0;
        end
    endtask

    task automatic await_done;
        begin
            timeout = 0;
            while (!program_done_valid) begin
                @(posedge clk);
                timeout = timeout + 1;
                if (timeout > 300000)
                    $fatal(1, "program completion timeout");
            end
            if (cmd_ready || !program_active)
                $fatal(1, "completion/program-active protocol differs");
        end
    endtask

    task automatic acknowledge_done;
        begin
            repeat (3) begin
                @(posedge clk);
                if (!program_done_valid)
                    $fatal(1, "program completion was not stable");
            end
            @(negedge clk);
            program_done_ready = 1;
            @(posedge clk);
            @(negedge clk);
            program_done_ready = 0;
        end
    endtask

    task automatic require_common_dma_success;
        begin
            if (program_done_hbm_request_count != 128 ||
                program_done_hbm_response_count != 128 ||
                program_done_hbm_bytes_read != DMA_BYTES ||
                hbm_requests != 128 || hbm_responses != 128 ||
                dma_writes != DMA_WRITES)
                $fatal(1, "successful DMA accounting differs");
        end
    endtask

    task automatic prove_success;
        integer check_index;
        begin
            reset_case(FAULT_NONE);
            submit_command(DMA_RECORD, 32'd1, 0);
            submit_command(RMS_RECORD, 32'd2, 1);
            await_done();
            require_common_dma_success();
            if (program_done_error != 0 ||
                program_done_failing_command_index != 32'hffff_ffff ||
                program_done_last_command_index != 2 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 2 ||
                program_done_sram_read_count != 8192 ||
                program_done_sram_bytes_read != 16384 ||
                program_done_sram_write_count != 4608 ||
                program_done_sram_bytes_written != 16384 ||
                program_done_element_count != ELEMENTS ||
                program_done_normalized_saturation_count != 0 ||
                program_done_output_saturation_count != 0 ||
                program_done_mean_square_code != 32'h3a5bf2ca ||
                program_done_inverse_rms_code != 32'h420a0297 ||
                input_reads != ELEMENTS || weight_reads != ELEMENTS ||
                sram_read_responses != 8192 || rms_writes != ELEMENTS ||
                request_stalls == 0 || read_stalls == 0 ||
                write_stalls == 0 || pending_hbm || pending_read ||
                hbm_response_valid || sram_response_valid)
                $fatal(1, "successful program accounting differs");
            for (check_index = 0; check_index < ELEMENTS;
                 check_index = check_index + 1) begin
                if (weight_mem[check_index] !==
                    {payload_mem[check_index*2 + 1],
                     payload_mem[check_index*2]})
                    $fatal(1, "staged weight differs at %0d", check_index);
                if (destination_mem[check_index] !==
                    expected_mem[check_index])
                    $fatal(1, "destination differs at %0d", check_index);
            end
            acknowledge_done();
        end
    endtask

    task automatic prove_crc_fail_stop;
        begin
            reset_case(FAULT_NONE);
            submit_command(DMA_RECORD, 32'd1, 0);
            submit_command(RMS_BAD_CRC_RECORD, 32'd2, 1);
            await_done();
            require_common_dma_success();
            if (program_done_error != 1 ||
                program_done_failing_command_index != 2 ||
                program_done_last_command_index != 2 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 1 ||
                program_done_sram_read_count != 0 ||
                program_done_sram_write_count != DMA_WRITES ||
                program_done_sram_bytes_written != DMA_BYTES ||
                input_reads != 0 || weight_reads != 0 || rms_writes != 0)
                $fatal(1, "CRC fail-stop accounting differs");
            acknowledge_done();
        end
    endtask

    task automatic prove_hbm_fail_stop;
        begin
            reset_case(FAULT_HBM);
            submit_command(DMA_RECORD, 32'd1, 1);
            await_done();
            if (program_done_error != 11 ||
                program_done_failing_command_index != 1 ||
                program_done_last_command_index != 1 ||
                program_done_commands_accepted != 1 ||
                program_done_commands_completed != 0 ||
                program_done_hbm_request_count != 1 ||
                program_done_hbm_response_count != 1 ||
                program_done_hbm_bytes_read != 0 ||
                program_done_sram_read_count != 0 ||
                program_done_sram_write_count != 0 ||
                hbm_requests != 1 || hbm_responses != 1 ||
                dma_writes != 0 || rms_writes != 0)
                $fatal(1, "HBM fail-stop accounting differs");
            acknowledge_done();
        end
    endtask

    task automatic prove_order_fail_stop;
        begin
            reset_case(FAULT_NONE);
            submit_command(DMA_RECORD, 32'd1, 0);
            submit_command(RMS_RECORD, 32'd1, 1);
            await_done();
            require_common_dma_success();
            if (program_done_error != 12 ||
                program_done_failing_command_index != 1 ||
                program_done_last_command_index != 1 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 1 ||
                program_done_sram_read_count != 0 || rms_writes != 0)
                $fatal(1, "program-order fail-stop accounting differs");
            acknowledge_done();
        end
    endtask

    task automatic prove_numeric_fail_stop(
        input integer selected_fault,
        input [7:0] expected_error,
        input [31:0] expected_reads,
        input [31:0] expected_elements,
        input [31:0] expected_mean,
        input [31:0] expected_inverse
    );
        begin
            reset_case(selected_fault);
            submit_command(DMA_RECORD, 32'd1, 0);
            submit_command(RMS_RECORD, 32'd2, 1);
            await_done();
            require_common_dma_success();
            if (program_done_error != expected_error ||
                program_done_failing_command_index != 2 ||
                program_done_last_command_index != 2 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 1 ||
                program_done_sram_read_count != expected_reads ||
                program_done_sram_bytes_read != expected_reads*2 ||
                program_done_sram_write_count != DMA_WRITES ||
                program_done_sram_bytes_written != DMA_BYTES ||
                program_done_element_count != expected_elements ||
                program_done_normalized_saturation_count != 0 ||
                program_done_output_saturation_count != 0 ||
                program_done_mean_square_code != expected_mean ||
                program_done_inverse_rms_code != expected_inverse ||
                input_reads + weight_reads != expected_reads ||
                sram_read_responses != expected_reads || rms_writes != 0)
                $fatal(1, "numeric fail-stop accounting differs mode=%0d",
                       selected_fault);
            acknowledge_done();
        end
    endtask

    initial begin
        $readmemh("payload.hex", payload_mem);
        $readmemh("input.hex", input_mem);
        $readmemh("expected.hex", expected_mem);
        prove_success();
        prove_crc_fail_stop();
        prove_hbm_fail_stop();
        prove_order_fail_stop();
        prove_numeric_fail_stop(
            FAULT_INPUT_NONFINITE, 8'd9, 32'd1, 32'd1, 0, 0
        );
        prove_numeric_fail_stop(
            FAULT_INPUT_OVERFLOW, 8'd10, 32'd1, 32'd1, 0, 0
        );
        prove_numeric_fail_stop(
            FAULT_WEIGHT_NONFINITE, 8'd9, 32'd4097, 32'd1,
            32'h3a5bf2ca, 32'h420a0297
        );
        prove_numeric_fail_stop(
            FAULT_WEIGHT_OVERFLOW, 8'd10, 32'd4097, 32'd1,
            32'h3a5bf2ca, 32'h420a0297
        );
        $display("PASS: Qwen DMA+RMSNorm RTL sequence commands=2 elements=4096 faults=7 vector_set=ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81");
        $finish;
    end
endmodule
