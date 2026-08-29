`timescale 1ns/1ps
module tb_qwen_ta_head_rmsnorm;
    localparam [63:0] Q_INPUT_BASE = 64'd6291456;
    localparam [63:0] K_INPUT_BASE = 64'd7340032;
    localparam [63:0] Q_WEIGHT_HBM = 64'd1295024128;
    localparam [63:0] K_WEIGHT_HBM = 64'd1295024384;
    localparam [63:0] Q_WEIGHT_SRAM = 64'd9437184;
    localparam [63:0] K_WEIGHT_SRAM = 64'd10485760;
    localparam [63:0] Q_OUTPUT_BASE = 64'd11534336;
    localparam [63:0] K_OUTPUT_BASE = 64'd12591104;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg cmd_valid = 1'b0;
    wire cmd_ready;
    reg cmd_last = 1'b0;
    reg [15:0] abi_major = 16'd2;
    reg [15:0] abi_minor = 16'd5;
    reg [31:0] expected_command_index = 0;
    reg [511:0] command_record = 0;
    wire hbm_request_valid;
    reg hbm_request_ready;
    wire [63:0] hbm_request_address;
    wire [15:0] hbm_request_bytes;
    reg hbm_response_valid = 1'b0;
    wire hbm_response_ready;
    reg [511:0] hbm_response_data = 0;
    reg [1:0] hbm_response_error = 0;
    wire sram_read_valid;
    reg sram_read_ready;
    wire [63:0] sram_read_address;
    reg sram_response_valid = 1'b0;
    wire sram_response_ready;
    reg [15:0] sram_response_data = 0;
    wire sram_write_valid;
    reg sram_write_ready;
    wire [63:0] sram_write_address;
    wire [127:0] sram_write_data;
    wire [15:0] sram_write_byte_enable;
    wire program_active;
    wire program_done_valid;
    reg program_done_ready = 1'b0;
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
    wire [31:0] program_done_row_count;
    wire [31:0] program_done_element_count;
    wire [31:0] program_done_normalized_saturation_count;
    wire [31:0] program_done_output_saturation_count;
    wire [31:0] program_done_mean_square_code;
    wire [31:0] program_done_inverse_rms_code;

    reg [511:0] commands [0:3];
    reg [15:0] q_input [0:4095];
    reg [15:0] k_input [0:1023];
    reg [15:0] q_weight [0:127];
    reg [15:0] k_weight [0:127];
    reg [15:0] q_staged_weight [0:127];
    reg [15:0] k_staged_weight [0:127];
    reg [15:0] q_expected [0:4095];
    reg [15:0] k_expected [0:1023];
    reg [31:0] k_mean [0:7];
    reg [31:0] k_inverse [0:7];

    integer cycle_count = 0;
    integer request_stalls = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer q_writes = 0;
    integer k_writes = 0;
    integer fault_cases = 0;
    integer hbm_delay = 0;
    integer sram_delay = 0;
    integer j;
    reg hbm_pending = 1'b0;
    reg sram_pending = 1'b0;

    ot_ta_dma_head_rmsnorm_sequencer dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .cmd_last(cmd_last), .abi_major(abi_major), .abi_minor(abi_minor),
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
        .sram_read_valid(sram_read_valid), .sram_read_ready(sram_read_ready),
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
        .program_done_failing_command_index(program_done_failing_command_index),
        .program_done_last_command_index(program_done_last_command_index),
        .program_done_commands_accepted(program_done_commands_accepted),
        .program_done_commands_completed(program_done_commands_completed),
        .program_done_hbm_request_count(program_done_hbm_request_count),
        .program_done_hbm_response_count(program_done_hbm_response_count),
        .program_done_hbm_bytes_read(program_done_hbm_bytes_read),
        .program_done_sram_read_count(program_done_sram_read_count),
        .program_done_sram_bytes_read(program_done_sram_bytes_read),
        .program_done_sram_write_count(program_done_sram_write_count),
        .program_done_sram_bytes_written(program_done_sram_bytes_written),
        .program_done_row_count(program_done_row_count),
        .program_done_element_count(program_done_element_count),
        .program_done_normalized_saturation_count(
            program_done_normalized_saturation_count
        ),
        .program_done_output_saturation_count(
            program_done_output_saturation_count
        ),
        .program_done_mean_square_code(program_done_mean_square_code),
        .program_done_inverse_rms_code(program_done_inverse_rms_code)
    );

    function automatic [15:0] sram_value(input [63:0] address);
        integer index;
        begin
            if (address >= Q_INPUT_BASE && address < Q_INPUT_BASE + 8192) begin
                index = (address - Q_INPUT_BASE) >> 1;
                sram_value = q_input[index];
            end else if (address >= K_INPUT_BASE && address < K_INPUT_BASE + 2048) begin
                index = (address - K_INPUT_BASE) >> 1;
                sram_value = k_input[index];
            end else if (address >= Q_WEIGHT_SRAM && address < Q_WEIGHT_SRAM + 256) begin
                index = (address - Q_WEIGHT_SRAM) >> 1;
                sram_value = q_staged_weight[index];
            end else if (address >= K_WEIGHT_SRAM && address < K_WEIGHT_SRAM + 256) begin
                index = (address - K_WEIGHT_SRAM) >> 1;
                sram_value = k_staged_weight[index];
            end else begin
                $fatal(1, "unexpected SRAM read address %0d", address);
                sram_value = 0;
            end
        end
    endfunction

    always @(*) begin
        hbm_request_ready = rst_n && !hbm_pending && !hbm_response_valid &&
                            ((cycle_count % 7) != 2);
        sram_read_ready = rst_n && !sram_pending && !sram_response_valid &&
                          ((cycle_count % 5) != 1);
        sram_write_ready = rst_n && ((cycle_count % 11) != 3);
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            cycle_count <= 0;
            request_stalls <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
            hbm_pending <= 1'b0;
            hbm_response_valid <= 1'b0;
            sram_pending <= 1'b0;
            sram_response_valid <= 1'b0;
            q_writes <= 0;
            k_writes <= 0;
        end else begin
            cycle_count <= cycle_count + 1;
            if (hbm_request_valid && !hbm_request_ready)
                request_stalls <= request_stalls + 1;
            if (sram_read_valid && !sram_read_ready)
                read_stalls <= read_stalls + 1;
            if (sram_write_valid && !sram_write_ready)
                write_stalls <= write_stalls + 1;

            if (hbm_request_valid && hbm_request_ready) begin
                if (hbm_request_bytes !== 16'd64)
                    $fatal(1, "HBM request size differs");
                if (hbm_request_address >= Q_WEIGHT_HBM &&
                    hbm_request_address < Q_WEIGHT_HBM + 256) begin
                    for (j = 0; j < 32; j = j + 1)
                        hbm_response_data[j*16 +: 16] <=
                            q_weight[((hbm_request_address - Q_WEIGHT_HBM) >> 1) + j];
                end else if (hbm_request_address >= K_WEIGHT_HBM &&
                             hbm_request_address < K_WEIGHT_HBM + 256) begin
                    for (j = 0; j < 32; j = j + 1)
                        hbm_response_data[j*16 +: 16] <=
                            k_weight[((hbm_request_address - K_WEIGHT_HBM) >> 1) + j];
                end else begin
                    $fatal(1, "unexpected HBM request address %0d", hbm_request_address);
                end
                hbm_pending <= 1'b1;
                hbm_delay <= (cycle_count % 3) + 1;
            end
            if (hbm_pending) begin
                if (hbm_delay == 0) begin
                    hbm_pending <= 1'b0;
                    hbm_response_valid <= 1'b1;
                end else begin
                    hbm_delay <= hbm_delay - 1;
                end
            end
            if (hbm_response_valid && hbm_response_ready)
                hbm_response_valid <= 1'b0;

            if (sram_read_valid && sram_read_ready) begin
                sram_response_data <= sram_value(sram_read_address);
                sram_pending <= 1'b1;
                sram_delay <= (cycle_count % 4) + 1;
            end
            if (sram_pending) begin
                if (sram_delay == 0) begin
                    sram_pending <= 1'b0;
                    sram_response_valid <= 1'b1;
                end else begin
                    sram_delay <= sram_delay - 1;
                end
            end
            if (sram_response_valid && sram_response_ready)
                sram_response_valid <= 1'b0;

            if (sram_write_valid && sram_write_ready) begin
                if (sram_write_byte_enable == 16'hffff &&
                    sram_write_address >= Q_WEIGHT_SRAM &&
                    sram_write_address < Q_WEIGHT_SRAM + 256) begin
                    for (j = 0; j < 8; j = j + 1)
                        q_staged_weight[((sram_write_address - Q_WEIGHT_SRAM) >> 1) + j]
                            <= sram_write_data[j*16 +: 16];
                end else if (sram_write_byte_enable == 16'hffff &&
                             sram_write_address >= K_WEIGHT_SRAM &&
                             sram_write_address < K_WEIGHT_SRAM + 256) begin
                    for (j = 0; j < 8; j = j + 1)
                        k_staged_weight[((sram_write_address - K_WEIGHT_SRAM) >> 1) + j]
                            <= sram_write_data[j*16 +: 16];
                end else if (sram_write_byte_enable == 16'h0003 &&
                             sram_write_address >= Q_OUTPUT_BASE &&
                             sram_write_address < Q_OUTPUT_BASE + 8192) begin
                    if (sram_write_data[15:0] !==
                        q_expected[(sram_write_address - Q_OUTPUT_BASE) >> 1])
                        $fatal(1, "Q output mismatch at address %0d", sram_write_address);
                    q_writes <= q_writes + 1;
                end else if (sram_write_byte_enable == 16'h0003 &&
                             sram_write_address >= K_OUTPUT_BASE &&
                             sram_write_address < K_OUTPUT_BASE + 2048) begin
                    if (sram_write_data[15:0] !==
                        k_expected[(sram_write_address - K_OUTPUT_BASE) >> 1])
                        $fatal(1, "K output mismatch at address %0d", sram_write_address);
                    k_writes <= k_writes + 1;
                end else begin
                    $fatal(1, "unexpected SRAM write address/enable %0d %h",
                           sram_write_address, sram_write_byte_enable);
                end
            end
            if (cycle_count > 1000000)
                $fatal(1, "head RMSNorm timeout");
        end
    end

    task automatic submit_command(input integer slot, input reg terminal);
        begin
            while (!cmd_ready) @(negedge clk);
            expected_command_index = 32'd3075 + slot;
            command_record = commands[slot];
            cmd_last = terminal;
            cmd_valid = 1'b1;
            @(negedge clk);
            cmd_valid = 1'b0;
            cmd_last = 1'b0;
        end
    endtask

    task automatic reset_dut;
        begin
            rst_n = 1'b0;
            cmd_valid = 1'b0;
            program_done_ready = 1'b0;
            repeat (4) @(negedge clk);
            rst_n = 1'b1;
            repeat (2) @(negedge clk);
        end
    endtask

    initial begin
        $readmemh("head_rmsnorm_commands.hex", commands);
        $readmemh("head_rmsnorm_q_input.hex", q_input);
        $readmemh("head_rmsnorm_k_input.hex", k_input);
        $readmemh("head_rmsnorm_q_weight.hex", q_weight);
        $readmemh("head_rmsnorm_k_weight.hex", k_weight);
        $readmemh("head_rmsnorm_q_output.hex", q_expected);
        $readmemh("head_rmsnorm_k_output.hex", k_expected);
        $readmemh("head_rmsnorm_k_mean.hex", k_mean);
        $readmemh("head_rmsnorm_k_inverse.hex", k_inverse);

        reset_dut();
        submit_command(0, 1'b1);
        while (!program_done_valid) @(negedge clk);
        if (program_done_error !== 8'd12 ||
            program_done_failing_command_index !== 32'd3075 ||
            program_done_commands_accepted !== 32'd1 ||
            program_done_commands_completed !== 32'd0 ||
            program_done_hbm_request_count !== 0 ||
            program_done_sram_write_count !== 0)
            $fatal(1, "early-terminal fail-stop differs");
        fault_cases = fault_cases + 1;
        program_done_ready = 1'b1;
        @(negedge clk);
        program_done_ready = 1'b0;

        reset_dut();
        submit_command(0, 1'b0);
        submit_command(1, 1'b0);
        submit_command(2, 1'b0);
        submit_command(3, 1'b1);
        while (!program_done_valid) @(negedge clk);
        if (program_done_error !== 0 ||
            program_done_failing_command_index !== 32'hffff_ffff ||
            program_done_last_command_index !== 32'd3078 ||
            program_done_commands_accepted !== 32'd4 ||
            program_done_commands_completed !== 32'd4 ||
            program_done_hbm_request_count !== 32'd8 ||
            program_done_hbm_response_count !== 32'd8 ||
            program_done_hbm_bytes_read !== 32'd512 ||
            program_done_sram_read_count !== 32'd10240 ||
            program_done_sram_bytes_read !== 32'd20480 ||
            program_done_sram_write_count !== 32'd5152 ||
            program_done_sram_bytes_written !== 32'd10752 ||
            program_done_row_count !== 32'd40 ||
            program_done_element_count !== 32'd5120 ||
            program_done_normalized_saturation_count !== 0 ||
            program_done_output_saturation_count !== 0 ||
            program_done_mean_square_code !== k_mean[7] ||
            program_done_inverse_rms_code !== k_inverse[7] ||
            q_writes !== 4096 || k_writes !== 1024)
            $fatal(1, "head RMSNorm completion/counters differ");
        for (j = 0; j < 128; j = j + 1) begin
            if (q_staged_weight[j] !== q_weight[j] ||
                k_staged_weight[j] !== k_weight[j])
                $fatal(1, "staged weight differs at %0d", j);
        end
        $display(
            "PASS: Qwen Q/K head RMSNorm RTL commands=4 rows=40 elements=5120 reductions=5080 rsqrt=40 outputs=5120 faults=1 cycles=%0d request_stalls=%0d read_stalls=%0d write_stalls=%0d vector_set=9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791",
            cycle_count, request_stalls, read_stalls, write_stalls
        );
        $finish;
    end
endmodule
