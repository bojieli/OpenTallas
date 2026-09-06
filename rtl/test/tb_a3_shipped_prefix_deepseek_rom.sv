`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Focused Icarus checker for the DeepSeek ROM shipped-prefix multicast case.
//
// Qwen's complete layer-zero MATMUL prefix remains in the full Verilator
// replay.  This test runs only case 2 so interpreted Icarus independently
// covers the real sequencer, two gathers, embedding, transfer, exact 256-tile
// multicast, and the precise PC-15 VECTOR.MHC capability boundary.
// ---------------------------------------------------------------------------
module tb_a3_shipped_prefix_deepseek_rom;
    localparam integer CASE_INDEX = 2;
    localparam integer CASE_STRIDE = 80;
    localparam integer ISSUE_STRIDE = 4;
    localparam integer PAYLOAD_WORDS = 16384;
    localparam integer PARTICIPANTS = 256;

    reg [31:0] case_mem [0:4*CASE_STRIDE-1];
    reg [31:0] issue_mem [0:131];
    reg [31:0] expect_mem [0:91135];
    reg [31:0] record [0:CASE_STRIDE-1];
    initial begin
        $readmemh("p3_case.hex", case_mem);
        $readmemh("p3_issue.hex", issue_mem);
        $readmemh("p3_expect.hex", expect_mem);
    end

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] cfg_program_base = 0;
    reg [31:0] cfg_instruction_count = 0;
    reg [31:0] cfg_entry_pc = 0;
    reg [31:0] cfg_desc_base = 0;
    reg [31:0] cfg_desc_count = 0;
    reg        host_we = 1'b0;
    reg [1:0]  host_sel = 2'd0;
    reg [31:0] host_row = 32'd0;
    reg [5:0]  host_lane = 6'd0;
    reg [31:0] host_wdata = 32'd0;
    wire       host_ready;
    wire       host_write_refused;
    // The host's copies of the control images, written through the design's
    // load path (docs/CHIP_ARCHITECTURE_DESIGN.md section 13 item 12).
    reg [255:0]  image_program [0:4095];
    reg [1535:0] image_desc    [0:8191];
    reg [31:0]   image_symbol  [0:2047];
    integer host_row_index;
    integer host_lane_index;
    integer host_symbol_index;
    task host_write;
        input [1:0]  sel;
        input [31:0] row;
        input [5:0]  lane;
        input [31:0] data;
        begin
            host_sel = sel;
            host_row = row;
            host_lane = lane;
            host_wdata = data;
            host_we = 1'b1;
            @(negedge clk);
            host_we = 1'b0;
        end
    endtask
    task host_load_images;
        begin
            $readmemh("a3_program.hex", image_program);
            $readmemh("a3_descriptor.hex", image_desc);
            $readmemh("a3_symbol.hex", image_symbol);
            if (!host_ready) $fatal(1, "host path not ready before the load");
            for (host_row_index = 0; host_row_index < 4096; host_row_index = host_row_index + 1)
                for (host_lane_index = 0; host_lane_index < 8; host_lane_index = host_lane_index + 1)
                    host_write(2'd0, host_row_index, host_lane_index[5:0],
                               image_program[host_row_index][host_lane_index*32 +: 32]);
            for (host_row_index = 0; host_row_index < 8192; host_row_index = host_row_index + 1)
                for (host_lane_index = 0; host_lane_index < 48; host_lane_index = host_lane_index + 1)
                    host_write(2'd1, host_row_index, host_lane_index[5:0],
                               image_desc[host_row_index][host_lane_index*32 +: 32]);
            @(negedge clk);
            if (host_write_refused) $fatal(1, "a control-store write was refused");
        end
    endtask
    task host_bind_symbols;
        input [31:0] symbol_base;
        input [31:0] symbol_mask;
        begin
            for (host_symbol_index = 0; host_symbol_index < 16; host_symbol_index = host_symbol_index + 1) begin
                host_write(2'd2, host_symbol_index, 6'd0,
                           image_symbol[symbol_base + host_symbol_index]);
                host_write(2'd2, host_symbol_index, 6'd1, 32'd0);
                host_write(2'd2, host_symbol_index, 6'd2,
                           {31'd0, symbol_mask[host_symbol_index]});
            end
            if (host_write_refused) $fatal(1, "a symbol write was refused");
        end
    endtask
    reg [63:0] cfg_max_retired_work = 0;
    reg [31:0] cfg_state_count = 0;
    reg [31:0] cfg_index_base = 0;
    reg [31:0] cfg_source_base = 0;
    reg [31:0] cfg_source_launch_stride = 0;
    reg [31:0] cfg_embedding_source_base = 0;
    reg [31:0] cfg_transfer_index_base = 0;
    reg [31:0] cfg_transfer_source_base = 0;

    wire busy, done, complete, trapped;
    wire [15:0] trap_class;
    wire [31:0] first_fault_instruction;
    wire [31:0] count_fetched, count_retired, count_issued;
    wire [31:0] count_loop_iterations, count_wait_events, count_signals;
    wire [31:0] count_views_resolved;
    wire [31:0] real_launch_count, dma_gather_launch_count;
    wire [31:0] embedding_launch_count, dma_transfer_launch_count;
    wire [31:0] multicast_launch_count, multicast_fault_count;
    wire [31:0] capability_fault_count, descriptor_fault_count;
    wire [31:0] engine_fault_count;
    wire [31:0] output_write_count, writes_after_fault;
    wire operand_read_oob, result_write_oob;
    wire event_signal_error, state_apply_overflow;
    wire response_valid, response_fault;
    wire [15:0] response_trap_class;
    wire [7:0] response_family, response_sub;
    wire [31:0] response_descriptor_id, response_index;
    wire [31:0] last_response_index, last_response_descriptor_id;
    wire [7:0] last_response_family, last_response_sub;
    reg [31:0] result_read_addr = 0;
    wire [31:0] result_read_data;

    wire multicast_remote_write_valid, multicast_remote_write_ready;
    wire [31:0] multicast_remote_write_object_id;
    wire [15:0] multicast_remote_write_participant;
    wire [63:0] multicast_remote_write_offset;
    wire [31:0] multicast_remote_write_data;
    wire [7:0] multicast_tree_source;
    wire [31:0] multicast_source_read_count;
    wire [31:0] multicast_source_stall_cycles;
    wire [31:0] multicast_destination_stall_cycles;
    wire [31:0] multicast_remote_write_count;
    wire [31:0] multicast_messages_sent, multicast_messages_received;
    wire [63:0] multicast_bytes_sent, multicast_bytes_received;
    wire [31:0] multicast_payload_flits, multicast_wire_flits;
    wire [31:0] multicast_replayed_flits, multicast_retry_events;
    wire [31:0] multicast_credit_stall_cycles, multicast_crc_errors;
    wire [31:0] multicast_sequence_errors;
    wire [31:0] multicast_writes_after_completion;
    wire multicast_protocol_error;

    ot_a3_shipped_prefix_top #(
        .MATMUL_WEIGHT_BYTES(1), .ENABLE_EXACT_MULTICAST(1)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc), .cfg_desc_base(cfg_desc_base),
        .cfg_desc_count(cfg_desc_count),
        .host_we(host_we), .host_sel(host_sel), .host_row(host_row),
        .host_lane(host_lane), .host_wdata(host_wdata),
        .host_ready(host_ready), .host_write_refused(host_write_refused),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count), .cfg_index_base(cfg_index_base),
        .cfg_source_base(cfg_source_base),
        .cfg_source_launch_stride(cfg_source_launch_stride),
        .cfg_embedding_source_base(cfg_embedding_source_base),
        .cfg_transfer_index_base(cfg_transfer_index_base),
        .cfg_transfer_source_base(cfg_transfer_source_base),
        // The object placement table is deliberately left unbound here.
        // This bench's vector set is the retired 80-word case generation,
        // which carries no table, so there is nothing to bind and the bridge
        // refuses every operand it would have to place -- loudly, with a
        // DESCRIPTOR trap, rather than writing somewhere plausible.
        // Regenerating testdata/compiler/abi3_shipped_prefix_multicast from
        // the current base vector set is what makes this bench run again.
        .busy(busy), .done(done), .complete(complete), .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .count_fetched(count_fetched), .count_retired(count_retired),
        .count_issued(count_issued),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events), .count_signals(count_signals),
        .count_views_resolved(count_views_resolved),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .real_launch_count(real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .dma_transfer_launch_count(dma_transfer_launch_count),
        .multicast_launch_count(multicast_launch_count),
        .multicast_fault_count(multicast_fault_count),
        .capability_fault_count(capability_fault_count),
        .descriptor_fault_count(descriptor_fault_count),
        .engine_fault_count(engine_fault_count),
        .last_response_index(last_response_index),
        .last_response_family(last_response_family),
        .last_response_sub(last_response_sub),
        .last_response_descriptor_id(last_response_descriptor_id),
        .response_valid(response_valid), .response_fault(response_fault),
        .response_trap_class(response_trap_class),
        .response_family(response_family), .response_sub(response_sub),
        .response_descriptor_id(response_descriptor_id),
        .response_index(response_index),
        .output_write_count(output_write_count),
        .writes_after_fault(writes_after_fault),
        .operand_read_oob(operand_read_oob),
        .result_write_oob(result_write_oob),
        .multicast_remote_write_valid(multicast_remote_write_valid),
        .multicast_remote_write_ready(multicast_remote_write_ready),
        .multicast_remote_write_object_id(multicast_remote_write_object_id),
        .multicast_remote_write_participant(
            multicast_remote_write_participant),
        .multicast_remote_write_offset(multicast_remote_write_offset),
        .multicast_remote_write_data(multicast_remote_write_data),
        .multicast_tree_source(multicast_tree_source),
        .multicast_source_read_count(multicast_source_read_count),
        .multicast_source_stall_cycles(multicast_source_stall_cycles),
        .multicast_destination_stall_cycles(
            multicast_destination_stall_cycles),
        .multicast_remote_write_count(multicast_remote_write_count),
        .multicast_messages_sent(multicast_messages_sent),
        .multicast_messages_received(multicast_messages_received),
        .multicast_bytes_sent(multicast_bytes_sent),
        .multicast_bytes_received(multicast_bytes_received),
        .multicast_payload_flits(multicast_payload_flits),
        .multicast_wire_flits(multicast_wire_flits),
        .multicast_replayed_flits(multicast_replayed_flits),
        .multicast_retry_events(multicast_retry_events),
        .multicast_credit_stall_cycles(multicast_credit_stall_cycles),
        .multicast_crc_errors(multicast_crc_errors),
        .multicast_sequence_errors(multicast_sequence_errors),
        .multicast_writes_after_completion(
            multicast_writes_after_completion),
        .multicast_protocol_error(multicast_protocol_error),
        .result_read_addr(result_read_addr),
        .result_read_data(result_read_data)
    );

    function automatic [31:0] payload_word;
        input [13:0] index;
        reg [31:0] widened;
        begin
            widened = {18'd0, index};
            payload_word = 32'h9e37_79b9 ^
                (widened * 32'h045d_9f3b) ^ {index, index, index[3:0]};
        end
    endfunction

    function automatic [7:0] expected_tree_source;
        input [7:0] destination;
        integer power;
        begin
            power = 1;
            while ((power << 1) <= destination)
                power = power << 1;
            expected_tree_source = destination - power;
        end
    endfunction

    integer failures = 0;
    integer checks = 0;
    integer response_seen = 0;
    integer response_expected = 0;
    integer response_base = 0;
    integer observed_writes = 0;
    integer next_word [0:PARTICIPANTS-1];
    integer participant_writes [0:PARTICIPANTS-1];
    integer field, issue_word, participant, guard, word;

    task check_equal;
        input [1023:0] label;
        input [63:0] got;
        input [63:0] want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL: %0s got=%0d (0x%0x) want=%0d (0x%0x)",
                             label, got, got, want, want);
            end
        end
    endtask

    always @(posedge clk) begin
        if (rst_n && response_valid) begin
            issue_word = (response_base + response_seen) * ISSUE_STRIDE;
            check_equal("response opcode", {response_family, response_sub},
                        issue_mem[issue_word][15:0]);
            check_equal("response descriptor", response_descriptor_id,
                        issue_mem[issue_word + 1]);
            check_equal("response PC", response_index,
                        issue_mem[issue_word + 2]);
            check_equal("response trap", response_trap_class,
                        issue_mem[issue_word + 3]);
            check_equal("response fault", response_fault,
                        issue_mem[issue_word + 3] != 0);
            response_seen = response_seen + 1;
        end

        if (rst_n && multicast_remote_write_valid &&
            multicast_remote_write_ready) begin
            observed_writes = observed_writes + 1;
            checks = checks + 1;
            if ((multicast_remote_write_object_id !== 32'd366) ||
                (multicast_remote_write_offset[1:0] !== 2'd0) ||
                (multicast_remote_write_offset >= 64'd16777216) ||
                (multicast_remote_write_participant !==
                 {8'd0, multicast_remote_write_offset[23:16]}) ||
                (multicast_remote_write_data !==
                 payload_word(multicast_remote_write_offset[15:2]))) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL: multicast write %0d obj=%0d participant=%0d offset=%0d data=%h",
                             observed_writes-1,
                             multicast_remote_write_object_id,
                             multicast_remote_write_participant,
                             multicast_remote_write_offset,
                             multicast_remote_write_data);
            end
            participant = multicast_remote_write_participant[7:0];
            check_equal("ascending participant word",
                        multicast_remote_write_offset[15:2],
                        next_word[participant]);
            next_word[participant] = next_word[participant] + 1;
            participant_writes[participant] =
                participant_writes[participant] + 1;
            if (participant != 0)
                check_equal("binomial tree source", multicast_tree_source,
                            expected_tree_source(participant[7:0]));
        end
    end

    initial begin
        for (field = 0; field < CASE_STRIDE; field = field + 1)
            record[field] = case_mem[CASE_INDEX*CASE_STRIDE + field];
        for (participant = 0; participant < PARTICIPANTS;
             participant = participant + 1) begin
            next_word[participant] = 0;
            participant_writes[participant] = 0;
        end

        cfg_program_base = record[0];
        cfg_instruction_count = record[1];
        cfg_desc_base = record[2];
        cfg_desc_count = record[3];
        cfg_entry_pc = record[6];
        cfg_max_retired_work = {record[8], record[7]};
        cfg_state_count = record[9];
        cfg_index_base = record[10];
        cfg_source_base = record[11];
        cfg_source_launch_stride = record[12];
        cfg_embedding_source_base = record[32];
        cfg_transfer_index_base = record[42];
        cfg_transfer_source_base = record[43];
        response_expected = record[21];
        response_base = record[31];

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        host_load_images;
        host_bind_symbols(record[4], record[5]);
        result_read_addr = record[13]; #1;
        check_equal("result initially unwritten", result_read_data,
                    32'hdead_beef);

        @(negedge clk); start = 1'b1;
        @(negedge clk); start = 1'b0;
        guard = 0;
        while (!done && guard < 20000000) begin
            @(negedge clk);
            guard = guard + 1;
        end
        if (!done) begin
            failures = failures + 1;
            $display("FAIL: DeepSeek ROM case timed out guard=%0d", guard);
        end
        repeat (4) @(negedge clk);

        check_equal("response count", response_seen, response_expected);
        check_equal("busy at completion", busy, 0);
        check_equal("complete false", complete, 0);
        check_equal("transaction trapped", trapped, 1);
        check_equal("trap class", trap_class, 4);
        check_equal("first fault PC", first_fault_instruction, record[16]);
        check_equal("fetched", count_fetched, record[19]);
        check_equal("retired", count_retired, record[20]);
        check_equal("issued", count_issued, record[21]);
        check_equal("loop iterations", count_loop_iterations, record[22]);
        check_equal("wait events", count_wait_events, record[35]);
        check_equal("signals", count_signals, record[23]);
        check_equal("views", count_views_resolved, record[24]);
        check_equal("real launches", real_launch_count, record[14]);
        check_equal("gather launches", dma_gather_launch_count, record[33]);
        check_equal("embedding launches", embedding_launch_count, record[34]);
        check_equal("transfer launches", dma_transfer_launch_count, record[45]);
        check_equal("multicast launches", multicast_launch_count, record[79]);
        check_equal("multicast faults", multicast_fault_count, 0);
        check_equal("capability faults", capability_fault_count, record[29]);
        check_equal("descriptor faults", descriptor_fault_count, 0);
        check_equal("engine faults", engine_fault_count, 0);
        check_equal("last response PC", last_response_index, record[16]);
        check_equal("last response opcode",
                    {last_response_family, last_response_sub}, record[17]);
        check_equal("last response descriptor",
                    last_response_descriptor_id, record[18]);
        check_equal("result writes", output_write_count, record[15]);
        check_equal("writes after fault", writes_after_fault, 0);
        check_equal("operand OOB", operand_read_oob, 0);
        check_equal("result OOB", result_write_oob, 0);
        check_equal("event error", event_signal_error, 0);
        check_equal("state overflow", state_apply_overflow, 0);
        check_equal("source reads", multicast_source_read_count,
                    PAYLOAD_WORDS);
        check_equal("source stalls exercised",
                    multicast_source_stall_cycles != 0, 1);
        check_equal("destination stalls exercised",
                    multicast_destination_stall_cycles != 0, 1);
        check_equal("messages sent", multicast_messages_sent, 255);
        check_equal("messages received", multicast_messages_received, 255);
        check_equal("bytes sent", multicast_bytes_sent, 16711680);
        check_equal("bytes received", multicast_bytes_received, 16711680);
        check_equal("payload flits", multicast_payload_flits, 4177920);
        check_equal("adapter writes", multicast_remote_write_count, 4194304);
        check_equal("observed writes", observed_writes, 4194304);
        check_equal("CRC errors", multicast_crc_errors, 1);
        check_equal("retry exercised", multicast_retry_events != 0, 1);
        check_equal("replay exercised", multicast_replayed_flits != 0, 1);
        check_equal("sequence errors", multicast_sequence_errors, 4);
        check_equal("wire delivery relation", multicast_wire_flits,
                    multicast_payload_flits + multicast_crc_errors +
                    multicast_sequence_errors);
        check_equal("protocol error", multicast_protocol_error, 0);
        check_equal("writes after multicast completion",
                    multicast_writes_after_completion, 0);
        for (participant = 0; participant < PARTICIPANTS;
             participant = participant + 1)
            check_equal("participant write count",
                        participant_writes[participant], PAYLOAD_WORDS);

        for (word = 0; word < record[15]; word = word + 1) begin
            result_read_addr = record[13] + word; #1;
            check_equal("retained result word", result_read_data,
                        expect_mem[record[13] + word]);
        end

        if (failures != 0) begin
            $display("FAIL: DeepSeek ROM multicast failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1, "DeepSeek ROM multicast integration failed");
        end
        $display("CASE 2 OK launches=%0d words=%0d responses=%0d trap=%0d fault=%0d fetched=%0d retired=%0d issued=%0d views=%0d multicasts=%0d",
                 real_launch_count, output_write_count, response_seen,
                 trap_class, first_fault_instruction, count_fetched,
                 count_retired, count_issued, count_views_resolved,
                 multicast_launch_count);
        $display("PASS: ABI3 shipped-prefix DeepSeek-ROM multicast integration checks=%0d cycles=%0d",
                 checks, guard);
        $finish;
    end
endmodule
