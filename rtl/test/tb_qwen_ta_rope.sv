`timescale 1ns/1ps
module tb_qwen_ta_rope;
    localparam [63:0] TABLE_BASE = 64'd16384425984;
    localparam [63:0] INDEX_BASE = 64'd4;
    localparam [63:0] COEFFICIENT_BASE = 64'd13631488;
    localparam [63:0] Q_INPUT_BASE = 64'd11534336;
    localparam [63:0] K_INPUT_BASE = 64'd12591104;
    localparam [63:0] Q_OUTPUT_BASE = 64'd14680064;
    localparam [63:0] K_OUTPUT_BASE = 64'd15728640;
    localparam [63:0] ROW7999_BASE = 64'd16388521472;

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
    wire [31:0] program_done_logical_index;
    wire [63:0] program_done_selected_hbm_address;
    wire [31:0] program_done_hbm_request_count;
    wire [31:0] program_done_hbm_response_count;
    wire [31:0] program_done_hbm_bytes_read;
    wire [31:0] program_done_sram_read_count;
    wire [31:0] program_done_sram_bytes_read;
    wire [31:0] program_done_sram_write_count;
    wire [31:0] program_done_sram_bytes_written;
    wire [31:0] program_done_element_count;
    wire [31:0] program_done_multiplication_count;
    wire [31:0] program_done_addition_count;
    wire [31:0] program_done_multiplication_saturation_count;
    wire [31:0] program_done_addition_saturation_count;

    reg [511:0] commands [0:1];
    reg [15:0] q_input [0:4095];
    reg [15:0] k_input [0:1023];
    reg [15:0] coefficient0 [0:255];
    reg [15:0] coefficient7999 [0:255];
    reg [15:0] staged_coefficient [0:255];
    reg [15:0] q_expected0 [0:4095];
    reg [15:0] k_expected0 [0:1023];
    reg [15:0] q_expected7999 [0:4095];
    reg [15:0] k_expected7999 [0:1023];

    integer cycle_count = 0;
    integer request_stalls = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer hbm_requests = 0;
    integer hbm_responses = 0;
    integer index_reads = 0;
    integer coefficient_reads = 0;
    integer q_reads = 0;
    integer k_reads = 0;
    integer dma_writes = 0;
    integer q_writes = 0;
    integer k_writes = 0;
    integer fault_cases = 0;
    integer completed_positions = 0;
    integer hbm_delay = 0;
    integer sram_delay = 0;
    integer j;
    reg hbm_pending = 1'b0;
    reg sram_pending = 1'b0;
    reg pending_hbm_error = 1'b0;
    reg inject_hbm_error = 1'b0;
    reg [31:0] current_position = 0;

    ot_ta_dma_rope_sequencer dut (
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
        .program_done_logical_index(program_done_logical_index),
        .program_done_selected_hbm_address(program_done_selected_hbm_address),
        .program_done_hbm_request_count(program_done_hbm_request_count),
        .program_done_hbm_response_count(program_done_hbm_response_count),
        .program_done_hbm_bytes_read(program_done_hbm_bytes_read),
        .program_done_sram_read_count(program_done_sram_read_count),
        .program_done_sram_bytes_read(program_done_sram_bytes_read),
        .program_done_sram_write_count(program_done_sram_write_count),
        .program_done_sram_bytes_written(program_done_sram_bytes_written),
        .program_done_element_count(program_done_element_count),
        .program_done_multiplication_count(program_done_multiplication_count),
        .program_done_addition_count(program_done_addition_count),
        .program_done_multiplication_saturation_count(
            program_done_multiplication_saturation_count
        ),
        .program_done_addition_saturation_count(
            program_done_addition_saturation_count
        )
    );

    function automatic [15:0] sram_value(input [63:0] address);
        integer index;
        begin
            if (address == INDEX_BASE) begin
                sram_value = current_position[15:0];
            end else if (address == INDEX_BASE + 2) begin
                sram_value = current_position[31:16];
            end else if (address >= COEFFICIENT_BASE &&
                         address < COEFFICIENT_BASE + 512) begin
                index = (address - COEFFICIENT_BASE) >> 1;
                sram_value = staged_coefficient[index];
            end else if (address >= Q_INPUT_BASE &&
                         address < Q_INPUT_BASE + 8192) begin
                index = (address - Q_INPUT_BASE) >> 1;
                sram_value = q_input[index];
            end else if (address >= K_INPUT_BASE &&
                         address < K_INPUT_BASE + 2048) begin
                index = (address - K_INPUT_BASE) >> 1;
                sram_value = k_input[index];
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
            hbm_requests <= 0;
            hbm_responses <= 0;
            index_reads <= 0;
            coefficient_reads <= 0;
            q_reads <= 0;
            k_reads <= 0;
            dma_writes <= 0;
            q_writes <= 0;
            k_writes <= 0;
            hbm_pending <= 1'b0;
            hbm_response_valid <= 1'b0;
            hbm_response_error <= 0;
            sram_pending <= 1'b0;
            sram_response_valid <= 1'b0;
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
                if (hbm_request_address >= TABLE_BASE &&
                    hbm_request_address < TABLE_BASE + 512) begin
                    for (j = 0; j < 32; j = j + 1)
                        hbm_response_data[j*16 +: 16] <= coefficient0[
                            ((hbm_request_address - TABLE_BASE) >> 1) + j
                        ];
                end else if (hbm_request_address >= ROW7999_BASE &&
                             hbm_request_address < ROW7999_BASE + 512) begin
                    for (j = 0; j < 32; j = j + 1)
                        hbm_response_data[j*16 +: 16] <= coefficient7999[
                            ((hbm_request_address - ROW7999_BASE) >> 1) + j
                        ];
                end else begin
                    $fatal(1, "unexpected HBM request address %0d",
                           hbm_request_address);
                end
                pending_hbm_error <= inject_hbm_error && hbm_requests == 3;
                hbm_requests <= hbm_requests + 1;
                hbm_pending <= 1'b1;
                hbm_delay <= (cycle_count % 3) + 1;
            end
            if (hbm_pending) begin
                if (hbm_delay == 0) begin
                    hbm_pending <= 1'b0;
                    hbm_response_valid <= 1'b1;
                    hbm_response_error <= pending_hbm_error ? 2'd1 : 2'd0;
                end else begin
                    hbm_delay <= hbm_delay - 1;
                end
            end
            if (hbm_response_valid && hbm_response_ready) begin
                hbm_response_valid <= 1'b0;
                hbm_response_error <= 0;
                hbm_responses <= hbm_responses + 1;
            end

            if (sram_read_valid && sram_read_ready) begin
                sram_response_data <= sram_value(sram_read_address);
                if (sram_read_address == INDEX_BASE ||
                    sram_read_address == INDEX_BASE + 2)
                    index_reads <= index_reads + 1;
                else if (sram_read_address >= COEFFICIENT_BASE &&
                         sram_read_address < COEFFICIENT_BASE + 512)
                    coefficient_reads <= coefficient_reads + 1;
                else if (sram_read_address >= Q_INPUT_BASE &&
                         sram_read_address < Q_INPUT_BASE + 8192)
                    q_reads <= q_reads + 1;
                else
                    k_reads <= k_reads + 1;
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
                    sram_write_address >= COEFFICIENT_BASE &&
                    sram_write_address < COEFFICIENT_BASE + 512) begin
                    for (j = 0; j < 8; j = j + 1)
                        staged_coefficient[
                            ((sram_write_address - COEFFICIENT_BASE) >> 1) + j
                        ] <= sram_write_data[j*16 +: 16];
                    dma_writes <= dma_writes + 1;
                end else if (sram_write_byte_enable == 16'h0003 &&
                             sram_write_address >= Q_OUTPUT_BASE &&
                             sram_write_address < Q_OUTPUT_BASE + 8192) begin
                    if (sram_write_data[15:0] !==
                        (current_position == 0
                         ? q_expected0[(sram_write_address-Q_OUTPUT_BASE)>>1]
                         : q_expected7999[(sram_write_address-Q_OUTPUT_BASE)>>1]))
                        $fatal(1, "Q output mismatch at %0d", sram_write_address);
                    q_writes <= q_writes + 1;
                end else if (sram_write_byte_enable == 16'h0003 &&
                             sram_write_address >= K_OUTPUT_BASE &&
                             sram_write_address < K_OUTPUT_BASE + 2048) begin
                    if (sram_write_data[15:0] !==
                        (current_position == 0
                         ? k_expected0[(sram_write_address-K_OUTPUT_BASE)>>1]
                         : k_expected7999[(sram_write_address-K_OUTPUT_BASE)>>1]))
                        $fatal(1, "K output mismatch at %0d", sram_write_address);
                    k_writes <= k_writes + 1;
                end else begin
                    $fatal(1, "unexpected SRAM write address/enable %0d %h",
                           sram_write_address, sram_write_byte_enable);
                end
            end
            if (cycle_count > 1000000)
                $fatal(1, "RoPE timeout");
        end
    end

    task automatic submit_command(input integer slot, input reg terminal);
        begin
            while (!cmd_ready) @(negedge clk);
            expected_command_index = 32'd3079 + slot;
            command_record = commands[slot];
            cmd_last = terminal;
            cmd_valid = 1'b1;
            @(negedge clk);
            cmd_valid = 1'b0;
            cmd_last = 1'b0;
        end
    endtask

    task automatic reset_dut;
        integer index;
        begin
            rst_n = 1'b0;
            cmd_valid = 1'b0;
            program_done_ready = 1'b0;
            for (index = 0; index < 256; index = index + 1)
                staged_coefficient[index] = 16'hdead;
            repeat (4) @(negedge clk);
            rst_n = 1'b1;
            repeat (2) @(negedge clk);
        end
    endtask

    task automatic acknowledge_done;
        begin
            repeat (3) begin
                if (!program_done_valid)
                    $fatal(1, "completion did not remain stable");
                @(negedge clk);
            end
            program_done_ready = 1'b1;
            @(negedge clk);
            program_done_ready = 1'b0;
        end
    endtask

    task automatic prove_success(input [31:0] position);
        integer index;
        begin
            current_position = position;
            inject_hbm_error = 1'b0;
            reset_dut();
            submit_command(0, 1'b0);
            submit_command(1, 1'b1);
            while (!program_done_valid) @(negedge clk);
            if (program_done_error !== 0 ||
                program_done_failing_command_index !== 32'hffff_ffff ||
                program_done_last_command_index !== 32'd3080 ||
                program_done_commands_accepted !== 32'd2 ||
                program_done_commands_completed !== 32'd2 ||
                program_done_logical_index !== position ||
                program_done_selected_hbm_address !==
                    TABLE_BASE + position * 512 ||
                program_done_hbm_request_count !== 32'd8 ||
                program_done_hbm_response_count !== 32'd8 ||
                program_done_hbm_bytes_read !== 32'd512 ||
                program_done_sram_read_count !== 32'd5378 ||
                program_done_sram_bytes_read !== 32'd10756 ||
                program_done_sram_write_count !== 32'd5152 ||
                program_done_sram_bytes_written !== 32'd10752 ||
                program_done_element_count !== 32'd5120 ||
                program_done_multiplication_count !== 32'd10240 ||
                program_done_addition_count !== 32'd5120 ||
                program_done_multiplication_saturation_count !== 0 ||
                program_done_addition_saturation_count !== 0 ||
                hbm_requests !== 8 || hbm_responses !== 8 ||
                index_reads !== 2 || coefficient_reads !== 256 ||
                q_reads !== 4096 || k_reads !== 1024 || dma_writes !== 32 ||
                q_writes !== 4096 || k_writes !== 1024 ||
                request_stalls == 0 || read_stalls == 0 || write_stalls == 0)
                $fatal(1, "position-%0d RoPE accounting differs", position);
            for (index = 0; index < 256; index = index + 1)
                if (staged_coefficient[index] !==
                    (position == 0 ? coefficient0[index] : coefficient7999[index]))
                    $fatal(1, "staged coefficient differs at %0d", index);
            completed_positions = completed_positions + 1;
            acknowledge_done();
        end
    endtask

    initial begin
        $readmemh("rope_commands.hex", commands);
        $readmemh("rope_q_input.hex", q_input);
        $readmemh("rope_k_input.hex", k_input);
        $readmemh("rope_coefficient_0.hex", coefficient0);
        $readmemh("rope_coefficient_7999.hex", coefficient7999);
        $readmemh("rope_q_output_0.hex", q_expected0);
        $readmemh("rope_k_output_0.hex", k_expected0);
        $readmemh("rope_q_output_7999.hex", q_expected7999);
        $readmemh("rope_k_output_7999.hex", k_expected7999);

        current_position = 0;
        reset_dut();
        submit_command(0, 1'b1);
        while (!program_done_valid) @(negedge clk);
        if (program_done_error !== 8'd12 ||
            program_done_failing_command_index !== 32'd3079 ||
            program_done_commands_accepted !== 32'd1 ||
            program_done_commands_completed !== 0 || hbm_requests !== 0 ||
            dma_writes !== 0)
            $fatal(1, "early-terminal fail-stop differs");
        fault_cases = fault_cases + 1;
        acknowledge_done();

        current_position = 8000;
        reset_dut();
        submit_command(0, 1'b0);
        while (!program_done_valid) @(negedge clk);
        if (program_done_error !== 8'd9 ||
            program_done_failing_command_index !== 32'd3079 ||
            program_done_commands_completed !== 0 || index_reads !== 2 ||
            hbm_requests !== 0 || dma_writes !== 0)
            $fatal(1, "indexed-DMA range fail-stop differs");
        fault_cases = fault_cases + 1;
        acknowledge_done();

        current_position = 7999;
        inject_hbm_error = 1'b1;
        reset_dut();
        submit_command(0, 1'b0);
        while (!program_done_valid) @(negedge clk);
        if (program_done_error !== 8'd11 ||
            program_done_failing_command_index !== 32'd3079 ||
            program_done_commands_completed !== 0 || index_reads !== 2 ||
            hbm_requests !== 4 || hbm_responses !== 4 || dma_writes !== 0)
            $fatal(1, "indexed-DMA HBM atomic fail-stop differs");
        fault_cases = fault_cases + 1;
        acknowledge_done();

        prove_success(0);
        prove_success(7999);
        $display(
            "PASS: Qwen indexed RoPE RTL commands=2 positions=2 elements=10240 multiplications=20480 additions=10240 outputs=10240 faults=3 cycles=%0d request_stalls=%0d read_stalls=%0d write_stalls=%0d vector_set=3a792b0dec8dd7277540841409accca66521f2f05f977c1cd6b6d9e5361f4f76",
            cycle_count, request_stalls, read_stalls, write_stalls
        );
        $finish;
    end
endmodule
