`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the exact shipped ABI 3.0 sequencer/engine prefix.
//
// The checker owns its expectations.  It observes every completion response,
// compares every real result word, checks the precise unsupported boundary,
// and rejects any post-fault write or nonzero compatibility-state activity.
// ---------------------------------------------------------------------------
module tb_a3_shipped_prefix;
    localparam integer CASES = 4;
    localparam integer CASE_STRIDE = 80;
    localparam integer ISSUE_STRIDE = 4;
    localparam integer RESULT_WORDS = 98304;
    localparam [31:0] UNWRITTEN = 32'hdead_beef;

    reg [31:0] case_mem [0:CASES*CASE_STRIDE-1];
    reg [31:0] issue_mem [0:127];
    reg [31:0] expect_mem [0:91135];
    reg [31:0] meta_mem [0:25];
    initial begin
        $readmemh("p3_case.hex", case_mem);
        $readmemh("p3_issue.hex", issue_mem);
        $readmemh("p3_expect.hex", expect_mem);
        $readmemh("p3_meta.hex", meta_mem);
    end

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg start = 1'b0;
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
    wire [31:0] count_fetched, count_retired, count_predicated_off;
    wire [31:0] count_issued, count_branches, count_loop_iterations;
    wire [31:0] count_wait_events, count_signals, count_views_resolved;
    wire [31:0] count_state_prepares, count_state_commits;
    wire [31:0] count_state_discards, count_state_reads;
    wire [31:0] count_state_generation_advances;
    wire [31:0] count_state_commits_applied, count_state_rows_committed;
    wire [63:0] count_state_bytes_written;
    wire event_signal_error, state_apply_overflow;
    wire [31:0] real_launch_count, capability_fault_count;
    wire [31:0] dma_gather_launch_count, embedding_launch_count;
    wire [31:0] rms_norm_launch_count, head_rms_norm_launch_count;
    wire [31:0] rope_launch_count;
    wire [31:0] dma_transfer_launch_count;
    wire [31:0] matmul_launch_count;
    wire [31:0] descriptor_fault_count, engine_fault_count;
    wire [31:0] last_response_index, last_response_descriptor_id;
    wire [7:0] last_response_family, last_response_sub;
    wire response_valid, response_fault;
    wire [15:0] response_trap_class;
    wire [7:0] response_family, response_sub;
    wire [31:0] response_descriptor_id, response_index;
    wire [7:0] engine_error_code;
    wire [31:0] engine_result_count, engine_work_count;
    wire [31:0] output_write_count, writes_after_fault;
    wire operand_read_oob, result_write_oob;
    reg [31:0] result_read_addr = 0;
    wire [31:0] result_read_data;

    ot_a3_shipped_prefix_top dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_desc_base(cfg_desc_base), .cfg_desc_count(cfg_desc_count),
        .host_we(host_we), .host_sel(host_sel), .host_row(host_row),
        .host_lane(host_lane), .host_wdata(host_wdata),
        .host_ready(host_ready), .host_write_refused(host_write_refused),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .cfg_index_base(cfg_index_base), .cfg_source_base(cfg_source_base),
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
        .count_predicated_off(count_predicated_off),
        .count_issued(count_issued), .count_branches(count_branches),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events), .count_signals(count_signals),
        .count_views_resolved(count_views_resolved),
        .count_state_prepares(count_state_prepares),
        .count_state_commits(count_state_commits),
        .count_state_discards(count_state_discards),
        .count_state_reads(count_state_reads),
        .count_state_generation_advances(count_state_generation_advances),
        .count_state_commits_applied(count_state_commits_applied),
        .count_state_rows_committed(count_state_rows_committed),
        .count_state_bytes_written(count_state_bytes_written),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .real_launch_count(real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .rms_norm_launch_count(rms_norm_launch_count),
        .head_rms_norm_launch_count(head_rms_norm_launch_count),
        .rope_launch_count(rope_launch_count),
        .dma_transfer_launch_count(dma_transfer_launch_count),
        .matmul_launch_count(matmul_launch_count),
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
        .engine_error_code(engine_error_code),
        .engine_result_count(engine_result_count),
        .engine_work_count(engine_work_count),
        .output_write_count(output_write_count),
        .writes_after_fault(writes_after_fault),
        .operand_read_oob(operand_read_oob),
        .result_write_oob(result_write_oob),
        .result_read_addr(result_read_addr),
        .result_read_data(result_read_data)
    );

    reg [31:0] record [0:CASE_STRIDE-1];
    integer checks = 0;
    integer failures = 0;
    integer response_seen = 0;
    integer response_base = 0;
    integer response_expected = 0;
    integer total_responses = 0;
    integer total_launches = 0;
    integer total_gathers = 0;
    integer total_embeddings = 0;
    integer total_rms_norms = 0;
    integer total_head_rms_norms = 0;
    integer total_ropes = 0;
    integer total_rope_words = 0;
    integer total_transfers = 0;
    integer total_matmuls = 0;
    integer total_words = 0;
    integer total_views = 0;
    integer field, case_index, word, guard, issue_word;

    task check_equal;
        input [1023:0] label;
        input [63:0] got;
        input [63:0] want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                $display("FAIL: %0s got=%0d (0x%0x) want=%0d (0x%0x)",
                         label, got, got, want, want);
            end
        end
    endtask

    task load_case;
        input integer index;
        begin
            for (field = 0; field < CASE_STRIDE; field = field + 1)
                record[field] = case_mem[index * CASE_STRIDE + field];
        end
    endtask

    always @(posedge clk) begin
        if (rst_n && response_valid) begin
            if (response_seen >= response_expected) begin
                failures = failures + 1;
                $display("FAIL: response overflow in case %0d", case_index);
            end else begin
                issue_word = (response_base + response_seen) * ISSUE_STRIDE;
                check_equal("response opcode", {response_family, response_sub},
                            issue_mem[issue_word][15:0]);
                check_equal("response descriptor", response_descriptor_id,
                            issue_mem[issue_word + 1]);
                check_equal("response PC", response_index,
                            issue_mem[issue_word + 2]);
                check_equal("response trap", response_trap_class,
                            issue_mem[issue_word + 3]);
                check_equal("response fault bit", response_fault,
                            issue_mem[issue_word + 3] != 0);
            end
            response_seen = response_seen + 1;
            total_responses = total_responses + 1;
        end
    end

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        host_load_images;

        check_equal("meta case count", meta_mem[0], CASES);
        check_equal("meta case stride", meta_mem[4], CASE_STRIDE);
        check_equal("meta result memory", meta_mem[7], RESULT_WORDS);
        check_equal("meta DMA gathers", meta_mem[8], 6);
        check_equal("meta embedding launches", meta_mem[9], 4);
        check_equal("meta RoPE coefficient gather words", meta_mem[10], 1024);
        check_equal("meta selected checkpoint bytes", meta_mem[11], 100713472);
        check_equal("meta RMSNorm launches", meta_mem[12], 2);
        check_equal("meta transfer launches", meta_mem[13], 2);
        check_equal("meta RMSNorm words", meta_mem[14], 8192);
        check_equal("meta transfer words", meta_mem[15], 32768);
        check_equal("meta MATMUL launches", meta_mem[16], 6);
        check_equal("meta MATMUL words", meta_mem[17], 12288);
        check_equal("meta MATMUL MACs", meta_mem[18], 50331648);
        check_equal("meta MATMUL checkpoint bytes", meta_mem[19], 100663296);
        check_equal("meta head RMSNorm launches", meta_mem[20], 4);
        check_equal("meta head RMSNorm words", meta_mem[21], 10240);
        check_equal("meta head RMSNorm checkpoint bytes", meta_mem[22], 1024);
        check_equal("meta all RMSNorm launches", meta_mem[23], 6);
        check_equal("meta RoPE launches", meta_mem[24], 4);
        check_equal("meta RoPE output words", meta_mem[25], 10240);

        for (case_index = 0; case_index < CASES;
             case_index = case_index + 1) begin
            load_case(case_index);
            cfg_program_base = record[0];
            cfg_instruction_count = record[1];
            cfg_desc_base = record[2];
            cfg_desc_count = record[3];
            host_bind_symbols(record[4], record[5]);
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
            response_seen = 0;

            // Each case owns a disjoint result interval, so this proves the
            // result is produced by this transaction rather than a prior one.
            result_read_addr = record[13]; #1;
            check_equal("result initially unwritten", result_read_data,
                        UNWRITTEN);

            @(negedge clk); start = 1'b1;
            @(negedge clk); start = 1'b0;
            guard = 0;
            while (!done && guard < 150000000) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                failures = failures + 1;
                $display("FAIL: case %0d timed out", case_index);
            end

            check_equal("response count", response_seen, response_expected);
            check_equal("busy at completion", busy, 0);
            check_equal("complete must remain false", complete, 0);
            check_equal("transaction trapped", trapped, 1);
            check_equal("trap class", trap_class, 4);
            check_equal("first fault PC", first_fault_instruction, record[16]);
            check_equal("fetched", count_fetched, record[19]);
            check_equal("retired", count_retired, record[20]);
            check_equal("issued", count_issued, record[21]);
            check_equal("loop iterations", count_loop_iterations, record[22]);
            check_equal("signals", count_signals, record[23]);
            check_equal("views resolved", count_views_resolved, record[24]);
            check_equal("predicated off", count_predicated_off, 0);
            check_equal("branches", count_branches, 0);
            check_equal("wait events", count_wait_events, record[35]);
            check_equal("real engine launches", real_launch_count, record[14]);
            check_equal("DMA gather launches", dma_gather_launch_count,
                        record[33]);
            check_equal("embedding launches", embedding_launch_count,
                        record[34]);
            check_equal("RMSNorm launches", rms_norm_launch_count,
                        record[44]);
            check_equal("head RMSNorm launches", head_rms_norm_launch_count,
                        record[66]);
            check_equal("RoPE launches", rope_launch_count, record[77]);
            check_equal("DMA transfer launches", dma_transfer_launch_count,
                        record[45]);
            check_equal("MATMUL launches", matmul_launch_count, record[55]);
            check_equal("capability responses", capability_fault_count,
                        record[29]);
            check_equal("descriptor faults", descriptor_fault_count, 0);
            check_equal("engine faults", engine_fault_count, 0);
            check_equal("last response PC", last_response_index, record[16]);
            check_equal("last response opcode",
                        {last_response_family, last_response_sub},
                        record[17][15:0]);
            check_equal("last response descriptor",
                        last_response_descriptor_id, record[18]);
            check_equal("engine error", engine_error_code, 0);
            check_equal("last engine result count", engine_result_count,
                        record[67]);
            check_equal("last engine work count", engine_work_count,
                        record[68]);
            check_equal("result write count", output_write_count, record[15]);
            check_equal("writes after capability fault", writes_after_fault, 0);
            check_equal("operand read in bounds", operand_read_oob, 0);
            check_equal("result write in bounds", result_write_oob, 0);
            check_equal("event scoreboard error", event_signal_error, 0);
            check_equal("state apply overflow", state_apply_overflow, 0);
            check_equal("state prepares", count_state_prepares, 0);
            check_equal("state commits", count_state_commits, 0);
            check_equal("state discards", count_state_discards, 0);
            check_equal("state reads", count_state_reads, 0);
            check_equal("state generation advances",
                        count_state_generation_advances, 0);
            check_equal("state commits applied", count_state_commits_applied, 0);
            check_equal("state rows committed", count_state_rows_committed, 0);
            check_equal("state bytes written", count_state_bytes_written, 0);

            for (word = 0; word < record[15]; word = word + 1) begin
                result_read_addr = record[13] + word; #1;
                check_equal("real result word", result_read_data,
                            expect_mem[record[13] + word]);
            end
            total_launches = total_launches + real_launch_count;
            total_gathers = total_gathers + dma_gather_launch_count;
            total_embeddings = total_embeddings + embedding_launch_count;
            total_rms_norms = total_rms_norms + rms_norm_launch_count;
            total_head_rms_norms = total_head_rms_norms +
                head_rms_norm_launch_count;
            total_ropes = total_ropes + rope_launch_count;
            total_rope_words = total_rope_words + record[78];
            total_transfers = total_transfers + dma_transfer_launch_count;
            total_matmuls = total_matmuls + matmul_launch_count;
            total_words = total_words + output_write_count;
            total_views = total_views + count_views_resolved;
            $display("CASE %0d OK launches=%0d words=%0d responses=%0d trap=%0d fault=%0d fetched=%0d retired=%0d issued=%0d views=%0d",
                     case_index, real_launch_count, output_write_count,
                     response_seen, trap_class, first_fault_instruction,
                     count_fetched, count_retired, count_issued,
                     count_views_resolved);
            @(negedge clk);
        end

        check_equal("total responses", total_responses,
                    meta_mem[0] + meta_mem[1]);
        check_equal("total launches", total_launches, meta_mem[1]);
        check_equal("total DMA gathers", total_gathers, meta_mem[8]);
        check_equal("total embedding launches", total_embeddings, meta_mem[9]);
        check_equal("total RMSNorm launches", total_rms_norms, meta_mem[12]);
        check_equal("total head RMSNorm launches", total_head_rms_norms,
                    meta_mem[20]);
        check_equal("total RoPE launches", total_ropes, meta_mem[24]);
        check_equal("total RoPE output words", total_rope_words,
                    meta_mem[25]);
        check_equal("total transfer launches", total_transfers, meta_mem[13]);
        check_equal("total MATMUL launches", total_matmuls, meta_mem[16]);
        check_equal("total result words", total_words, meta_mem[2]);
        check_equal("total resolved views", total_views, meta_mem[3]);
        for (word = 0; word < meta_mem[2]; word = word + 1) begin
            result_read_addr = word; #1;
            check_equal("final retained result", result_read_data,
                        expect_mem[word]);
        end
        for (word = meta_mem[2]; word < RESULT_WORDS; word = word + 1) begin
            result_read_addr = word; #1;
            check_equal("unwritten result tail", result_read_data, UNWRITTEN);
        end

        if (failures != 0) begin
            $display("FAILURES: %0d checks=%0d", failures, checks);
            $fatal(1, "ABI3 shipped-prefix engine integration failed");
        end
        $display("PASS: ABI3 shipped-prefix engine integration cases=4 launches=28 words=91136 capability_faults=4 checks=%0d", checks);
        $finish;
    end
endmodule
