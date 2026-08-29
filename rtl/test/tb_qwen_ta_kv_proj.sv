`timescale 1ns/1ps
module tb_qwen_ta_kv_proj;
    localparam integer OUTPUT_BLOCKS = 32;
    localparam integer K_TILES_PER_BLOCK = 16;
    localparam integer TOTAL_TILES = OUTPUT_BLOCKS * K_TILES_PER_BLOCK;
    localparam integer COMMANDS = TOTAL_TILES * 2;
    localparam integer INPUTS_PER_TILE = 256;
    localparam integer INPUTS = 4096;
    localparam integer OUTPUTS_PER_BLOCK = 64;
    localparam integer OUTPUTS = OUTPUT_BLOCKS * OUTPUTS_PER_BLOCK;
    localparam integer WEIGHTS_PER_TILE = 16384;
    localparam integer WEIGHTS = TOTAL_TILES * WEIGHTS_PER_TILE;
    localparam integer DMA_BYTES_PER_TILE = 32768;
    localparam integer DMA_BYTES = TOTAL_TILES * DMA_BYTES_PER_TILE;
    localparam integer HBM_REQUESTS_PER_TILE = DMA_BYTES_PER_TILE / 64;
    localparam integer HBM_REQUESTS = DMA_BYTES / 64;
    localparam integer DMA_WRITES_PER_TILE = DMA_BYTES_PER_TILE / 16;
    localparam integer DMA_WRITES = TOTAL_TILES * DMA_WRITES_PER_TILE;
    localparam integer ACC_READS_PER_RELOAD = OUTPUTS_PER_BLOCK * 2;
    localparam integer ACC_READS_PER_BLOCK =
        (K_TILES_PER_BLOCK - 1) * ACC_READS_PER_RELOAD;
    localparam integer ACC_READS = OUTPUT_BLOCKS * ACC_READS_PER_BLOCK;
    localparam integer INPUT_READS = TOTAL_TILES * INPUTS_PER_TILE;
    localparam integer ACC_WRITES = TOTAL_TILES * OUTPUTS_PER_BLOCK;
    localparam integer SRAM_READS = ACC_READS + INPUT_READS + WEIGHTS;
    localparam integer SRAM_WRITES = DMA_WRITES + ACC_WRITES + OUTPUTS;
    localparam integer SRAM_WRITE_BYTES = DMA_BYTES + ACC_WRITES*4 + OUTPUTS*2;
    localparam integer OUTPUTS_PER_PROJECTION = 1024;
    localparam [63:0] HBM_BASE = 64'd1278246912;
    localparam [63:0] INPUT_BASE = 64'd3145728;
    localparam [63:0] WEIGHT_BASE = 64'd4194304;
    localparam [63:0] ACCUMULATOR_BASE = 64'd5242880;
    localparam [63:0] K_AUXILIARY_BASE = 64'd7340032;
    localparam [63:0] V_AUXILIARY_BASE = 64'd8388608;

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
    wire [31:0] program_done_matmul_accumulator_read_count;
    wire [31:0] program_done_matmul_input_read_count;
    wire [31:0] program_done_matmul_weight_read_count;
    wire [31:0] program_done_matmul_multiply_count;
    wire [31:0] program_done_matmul_add_count;
    wire [31:0] program_done_matmul_output_count;
    wire [31:0] program_done_matmul_accumulator_write_count;
    wire [31:0] program_done_matmul_auxiliary_write_count;
    wire [31:0] program_done_matmul_output_saturation_count;

    reg [511:0] command_mem [0:COMMANDS-1];
    reg [7:0] payload_mem [0:DMA_BYTES_PER_TILE-1];
    reg [15:0] input_mem [0:INPUTS-1];
    reg [15:0] weight_mem [0:WEIGHTS_PER_TILE-1];
    reg [31:0] expected_acc_mem [0:ACC_WRITES-1];
    reg [15:0] expected_output_mem [0:OUTPUTS-1];
    reg [31:0] accumulator_mem [0:OUTPUTS_PER_BLOCK-1];
    reg [15:0] auxiliary_mem [0:OUTPUTS-1];

    integer payload_file;
    integer payload_read_count;
    integer loaded_tiles = 0;
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
    integer accumulator_reads = 0;
    integer input_reads = 0;
    integer weight_reads = 0;
    integer sram_read_responses = 0;
    integer accumulator_writes = 0;
    integer auxiliary_writes = 0;
    integer request_stalls = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer lane;
    integer index;
    integer command_offset;
    integer check_index;
    integer payload_index;
    integer timeout;

    always #5 clk = ~clk;

    ot_ta_dma_matmul_sequencer #(
        .FIRST_COMMAND_INDEX(32'd2051),
        .LAST_COMMAND_INDEX(32'd3074),
        .KERNEL0_INDEX(32'd3),
        .KERNEL0_LAST_COMMAND_INDEX(32'd2562),
        .KERNEL1_INDEX(32'd4),
        .KERNEL1_LAST_COMMAND_INDEX(32'd3074),
        .KERNEL2_INDEX(32'd4),
        .KERNEL2_LAST_COMMAND_INDEX(32'd3074)
    ) dut (
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
        .program_done_matmul_accumulator_read_count(
            program_done_matmul_accumulator_read_count),
        .program_done_matmul_input_read_count(
            program_done_matmul_input_read_count),
        .program_done_matmul_weight_read_count(
            program_done_matmul_weight_read_count),
        .program_done_matmul_multiply_count(
            program_done_matmul_multiply_count),
        .program_done_matmul_add_count(program_done_matmul_add_count),
        .program_done_matmul_output_count(program_done_matmul_output_count),
        .program_done_matmul_accumulator_write_count(
            program_done_matmul_accumulator_write_count),
        .program_done_matmul_auxiliary_write_count(
            program_done_matmul_auxiliary_write_count),
        .program_done_matmul_output_saturation_count(
            program_done_matmul_output_saturation_count)
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
            accumulator_reads <= 0;
            input_reads <= 0;
            weight_reads <= 0;
            sram_read_responses <= 0;
            accumulator_writes <= 0;
            auxiliary_writes <= 0;
            request_stalls <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
            loaded_tiles <= 0;
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
                if ((hbm_requests % HBM_REQUESTS_PER_TILE) == 0) begin
                    payload_read_count = $fread(
                        payload_mem, payload_file, 0, DMA_BYTES_PER_TILE);
                    if (payload_read_count != DMA_BYTES_PER_TILE)
                        $fatal(1, "weight tile %0d is truncated", loaded_tiles);
                    loaded_tiles <= loaded_tiles + 1;
                end
                pending_hbm <= 1;
                pending_hbm_burst <= hbm_requests;
                pending_hbm_delay <= (hbm_requests % 4) + 1;
                hbm_requests <= hbm_requests + 1;
            end
            if (pending_hbm) begin
                if (pending_hbm_delay == 0 && !hbm_response_valid) begin
                    for (lane = 0; lane < 64; lane = lane + 1)
                        hbm_response_data[lane*8 +: 8] <= payload_mem[
                            (pending_hbm_burst % HBM_REQUESTS_PER_TILE)*64 + lane
                        ];
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
                if (sram_read_address >= INPUT_BASE &&
                    sram_read_address < INPUT_BASE + INPUTS*2) begin
                    index = (sram_read_address - INPUT_BASE) >> 1;
                    if (index != (input_reads % INPUTS) ||
                        dma_writes != ((input_reads / INPUTS_PER_TILE) + 1) *
                                      DMA_WRITES_PER_TILE)
                        $fatal(1, "input read order differs at %0d", index);
                    pending_read_data <= input_mem[index];
                    input_reads <= input_reads + 1;
                end else if (sram_read_address >= WEIGHT_BASE &&
                             sram_read_address <
                             WEIGHT_BASE + DMA_BYTES_PER_TILE) begin
                    index = (sram_read_address - WEIGHT_BASE) >> 1;
                    if (index != (weight_reads % WEIGHTS_PER_TILE))
                        $fatal(1, "weight read order differs at %0d", index);
                    pending_read_data <= weight_mem[index];
                    weight_reads <= weight_reads + 1;
                end else if (sram_read_address >= ACCUMULATOR_BASE &&
                             sram_read_address <
                             ACCUMULATOR_BASE + OUTPUTS_PER_BLOCK*4) begin
                    index = (sram_read_address - ACCUMULATOR_BASE) >> 1;
                    if (index != (accumulator_reads % ACC_READS_PER_RELOAD))
                        $fatal(1, "accumulator reload order differs at %0d", index);
                    if (!index[0])
                        pending_read_data <= accumulator_mem[index >> 1][15:0];
                    else
                        pending_read_data <= accumulator_mem[index >> 1][31:16];
                    accumulator_reads <= accumulator_reads + 1;
                end else begin
                    $fatal(1, "SRAM read outside MATMUL operands");
                end
                pending_read <= 1;
                pending_read_delay <=
                    ((input_reads + weight_reads + accumulator_reads) % 3) + 1;
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
                    sram_write_address < WEIGHT_BASE + DMA_BYTES_PER_TILE) begin
                    index = dma_writes % DMA_WRITES_PER_TILE;
                    if (sram_write_byte_enable !== 16'hffff ||
                        sram_write_address !== WEIGHT_BASE + index*16)
                        $fatal(1, "DMA SRAM write metadata differs");
                    for (lane = 0; lane < 8; lane = lane + 1) begin
                        payload_index = index*16 + lane*2;
                        if (sram_write_data[lane*16 +: 16] !==
                            {payload_mem[payload_index + 1],
                             payload_mem[payload_index]})
                            $fatal(1, "DMA data differs at %0d", payload_index);
                        weight_mem[index*8 + lane] <=
                            sram_write_data[lane*16 +: 16];
                    end
                    dma_writes <= dma_writes + 1;
                end else if (sram_write_address >= ACCUMULATOR_BASE &&
                             sram_write_address <
                             ACCUMULATOR_BASE + OUTPUTS_PER_BLOCK*4) begin
                    index = (sram_write_address - ACCUMULATOR_BASE) >> 2;
                    if (sram_write_byte_enable !== 16'h000f ||
                        index != (accumulator_writes % OUTPUTS_PER_BLOCK) ||
                        sram_write_data[31:0] !==
                        expected_acc_mem[accumulator_writes])
                        $fatal(1, "accumulator write differs at %0d", index);
                    accumulator_mem[index] <= sram_write_data[31:0];
                    accumulator_writes <= accumulator_writes + 1;
                end else if ((sram_write_address >= K_AUXILIARY_BASE &&
                              sram_write_address < K_AUXILIARY_BASE +
                                                   OUTPUTS_PER_PROJECTION*2) ||
                             (sram_write_address >= V_AUXILIARY_BASE &&
                              sram_write_address < V_AUXILIARY_BASE +
                                                   OUTPUTS_PER_PROJECTION*2)) begin
                    if (sram_write_address >= V_AUXILIARY_BASE)
                        index = OUTPUTS_PER_PROJECTION +
                                ((sram_write_address - V_AUXILIARY_BASE) >> 1);
                    else
                        index = (sram_write_address - K_AUXILIARY_BASE) >> 1;
                    if (accumulator_writes !=
                            ((index / OUTPUTS_PER_BLOCK) + 1) *
                            K_TILES_PER_BLOCK * OUTPUTS_PER_BLOCK ||
                        sram_write_byte_enable !== 16'h0003 ||
                        index != auxiliary_writes ||
                        sram_write_data[15:0] !== expected_output_mem[index])
                        $fatal(1, "auxiliary write differs at %0d", index);
                    auxiliary_mem[index] <= sram_write_data[15:0];
                    auxiliary_writes <= auxiliary_writes + 1;
                end else begin
                    $fatal(1, "SRAM write outside composed regions");
                end
            end

            if (cycles > 200000000)
                $fatal(1,
                    "campaign timeout req=%0d rsp=%0d dma=%0d acc_r=%0d input=%0d weight=%0d acc_w=%0d aux_w=%0d",
                    hbm_requests, hbm_responses, dma_writes,
                    accumulator_reads, input_reads, weight_reads,
                    accumulator_writes, auxiliary_writes);
        end
    end

    task automatic reset_case;
        integer clear_index;
        begin
            rst_n = 0;
            cmd_valid = 0;
            cmd_last = 0;
            program_done_ready = 0;
            for (clear_index = 0; clear_index < WEIGHTS_PER_TILE;
                 clear_index = clear_index + 1)
                weight_mem[clear_index] = 0;
            for (clear_index = 0; clear_index < OUTPUTS_PER_BLOCK;
                 clear_index = clear_index + 1)
                accumulator_mem[clear_index] = 0;
            for (clear_index = 0; clear_index < OUTPUTS;
                 clear_index = clear_index + 1)
                auxiliary_mem[clear_index] = 0;
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
                if (timeout > 200000000)
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
                if (timeout > 200000000)
                    $fatal(1, "program completion timeout");
            end
            if (cmd_ready || !program_active)
                $fatal(1, "completion/program-active protocol differs");
        end
    endtask

    task automatic finish_done;
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

    initial begin
        $readmemh("kv_proj_commands.hex", command_mem);
        $readmemh("kv_proj_input.hex", input_mem);
        $readmemh("kv_proj_accumulators.hex", expected_acc_mem);
        $readmemh("kv_proj_output.hex", expected_output_mem);
        payload_file = $fopen("kv_proj_weights.bin", "rb");
        if (!payload_file)
            $fatal(1, "cannot open kv_proj_weights.bin");

        reset_case();
        submit_command(command_mem[0], 32'd2051, 1'b1);
        await_done();
        if (program_done_error !== 8'd12 ||
            program_done_failing_command_index !== 32'd2051 ||
            program_done_commands_accepted !== 32'd1 ||
            program_done_commands_completed !== 32'd0 ||
            hbm_requests !== 0 || dma_writes !== 0)
            $fatal(1, "early-terminal fail-stop behavior differs");
        finish_done();

        reset_case();
        for (command_offset = 0; command_offset < COMMANDS;
             command_offset = command_offset + 1)
            submit_command(command_mem[command_offset],
                           32'd2051 + command_offset,
                           command_offset == COMMANDS - 1);
        await_done();
        if (program_done_error !== 0 ||
            program_done_failing_command_index !== 32'hffff_ffff ||
            program_done_last_command_index !== 32'd3074 ||
            program_done_commands_accepted !== COMMANDS ||
            program_done_commands_completed !== COMMANDS ||
            program_done_hbm_request_count !== HBM_REQUESTS ||
            program_done_hbm_response_count !== HBM_REQUESTS ||
            program_done_hbm_bytes_read !== DMA_BYTES ||
            program_done_sram_read_count !== SRAM_READS ||
            program_done_sram_bytes_read !== SRAM_READS*2 ||
            program_done_sram_write_count !== SRAM_WRITES ||
            program_done_sram_bytes_written !== SRAM_WRITE_BYTES ||
            program_done_matmul_accumulator_read_count !== ACC_READS ||
            program_done_matmul_input_read_count !== INPUT_READS ||
            program_done_matmul_weight_read_count !== WEIGHTS ||
            program_done_matmul_multiply_count !== WEIGHTS ||
            program_done_matmul_add_count !== WEIGHTS ||
            program_done_matmul_output_count !== ACC_WRITES ||
            program_done_matmul_accumulator_write_count !== ACC_WRITES ||
            program_done_matmul_auxiliary_write_count !== OUTPUTS ||
            program_done_matmul_output_saturation_count !== 0 ||
            hbm_requests !== HBM_REQUESTS ||
            hbm_responses !== HBM_REQUESTS ||
            dma_writes !== DMA_WRITES ||
            accumulator_reads !== ACC_READS ||
            input_reads !== INPUT_READS || weight_reads !== WEIGHTS ||
            sram_read_responses !== SRAM_READS ||
            accumulator_writes !== ACC_WRITES ||
            auxiliary_writes !== OUTPUTS || loaded_tiles !== TOTAL_TILES ||
            request_stalls == 0 || read_stalls == 0 || write_stalls == 0 ||
            pending_hbm || pending_read || hbm_response_valid ||
            sram_response_valid)
            $fatal(1, "complete K/V projection accounting differs");
        for (check_index = 0; check_index < OUTPUTS;
             check_index = check_index + 1)
            if (auxiliary_mem[check_index] !== expected_output_mem[check_index])
                $fatal(1, "complete K/V projection BF16 output differs at %0d",
                       check_index);
        finish_done();
        if (program_done_valid || program_active)
            $fatal(1, "completion acknowledgement differs");
        $fclose(payload_file);
        $display(
            "PASS: complete Qwen K/V projections RTL commands=1024 blocks=32 tiles=512 inputs=131072 weights=8388608 accumulators=32768 bf16=2048 faults=1 cycles=%0d request_stalls=%0d read_stalls=%0d write_stalls=%0d vector_set=ee711ae0b31985d0215b9f0c14233c3a2cb0cade3f79809bfc00493d369d5873",
            cycles, request_stalls, read_stalls, write_stalls
        );
        $finish;
    end
endmodule
