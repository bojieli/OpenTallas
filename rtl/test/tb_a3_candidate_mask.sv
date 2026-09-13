`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for ROUTE.CANDIDATE_MASK.
//
// This checker does not trust the expectation image.  For every case it reads
// the chosen-block ids out of cm_ids.hex and DERIVES the admission mask itself,
// position by position, from the geometry the case named: position p is admitted
// when block p/BLOCK is in the id set or is the pinned last block, and never
// when p >= width.  It then requires three things to agree -- its own
// derivation, the reference image from
// runtime/reference/candidate_pool.py::select_candidate_mask, and the words the
// block actually wrote -- so a wrong shared assumption cannot pass as a
// correct one.
//
// It also measures the initiation interval rather than assuming it: the top
// counts the cycles between the first and the last out_we, and a run that
// emitted n words must have spanned exactly n-1 cycles.
//
// A divergence does not stop the run, so one wrong case does not hide the state
// of the others.  A second checker (rtl/test/a3_candidate_mask_harness.cpp) is
// written independently against the same top.
// ---------------------------------------------------------------------------
module tb_a3_candidate_mask;
    localparam integer CASE_STRIDE = 16;
    localparam integer WORD_BITS   = 32;
    localparam integer MAX_BLOCKS  = 1048576;   // BLOCK = 1 upper bound
    localparam integer GEOMS       = 5;
    localparam [31:0]  ABSENT_ID   = 32'hffff_ffff;
    localparam [31:0]  DONT_CHECK  = 32'hffff_ffff;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        run = 1'b0;
    reg [31:0] run_case = 32'd0;
    wire       busy, done;
    wire [7:0]  obs_error_code, obs_error_detail;
    wire [31:0] obs_error_slot, obs_error_value, obs_out_count, obs_population;
    wire [31:0] obs_blocks, obs_ids_consumed, obs_emit_gap_max;
    wire [31:0] obs_param_block, obs_param_max_width, obs_param_max_ids;
    wire [31:0] obs_param_word_bits, obs_param_pin_last;
    wire        obs_block_busy;
    wire [31:0] obs_pulses, obs_span, obs_addr_errors, obs_cycles;
    wire [31:0] obs_done_pulses, obs_timeout, obs_write_overflow, obs_id_reads;
    reg  [31:0] case_rd_addr = 32'd0, ids_rd_addr = 32'd0, expect_rd_addr = 32'd0;
    reg  [31:0] meta_rd_addr = 32'd0, cap_rd_addr = 32'd0;
    wire [31:0] case_rd_data, ids_rd_data, expect_rd_data, meta_rd_data, cap_rd_data;
    wire [31:0] geoms_param, case_stride_param;

    ot_a3_candidate_mask_top dut (
        .clk(clk), .rst_n(rst_n), .run(run), .run_case(run_case),
        .busy(busy), .done(done),
        .obs_error_code(obs_error_code), .obs_error_detail(obs_error_detail),
        .obs_error_slot(obs_error_slot), .obs_error_value(obs_error_value),
        .obs_out_count(obs_out_count), .obs_population(obs_population),
        .obs_blocks(obs_blocks), .obs_ids_consumed(obs_ids_consumed),
        .obs_emit_gap_max(obs_emit_gap_max),
        .obs_param_block(obs_param_block), .obs_param_max_width(obs_param_max_width),
        .obs_param_max_ids(obs_param_max_ids), .obs_param_word_bits(obs_param_word_bits),
        .obs_param_pin_last(obs_param_pin_last), .obs_block_busy(obs_block_busy),
        .obs_pulses(obs_pulses), .obs_span(obs_span),
        .obs_addr_errors(obs_addr_errors), .obs_cycles(obs_cycles),
        .obs_done_pulses(obs_done_pulses), .obs_timeout(obs_timeout),
        .obs_write_overflow(obs_write_overflow), .obs_id_reads(obs_id_reads),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .ids_rd_addr(ids_rd_addr), .ids_rd_data(ids_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .cap_rd_addr(cap_rd_addr), .cap_rd_data(cap_rd_data),
        .geoms_param(geoms_param), .case_stride_param(case_stride_param)
    );

    //: The geometry table, transcribed from the top's parameters and checked
    //: against what each instance says it elaborated.
    integer geom_block [0:GEOMS-1];
    integer geom_width [0:GEOMS-1];
    integer geom_ids   [0:GEOMS-1];
    integer geom_pin   [0:GEOMS-1];

    reg blk_flag [0:MAX_BLOCKS-1];

    integer base, case_count, meta_words, meta_ids, meta_refusals, meta_geoms;
    integer meta_population;
    integer checks, failures, code, index, value, word, bit_i;
    integer f_geom, f_subop, f_width, f_id_count, f_block, f_max_pop;
    integer f_ids_base, f_out_base, f_code, f_detail, f_slot, f_value;
    integer f_words, f_pop, f_blocks, f_expect_base;
    integer g_block, g_pin, block_count, last_block, tail_len, mask_words;
    integer der_pop, der_blocks, der_word, der_bit, expect_word, actual_word;
    integer id_slot, id_value, first_bad_slot, n, k, pos, total_words, total_pop;

    task read_case; input integer word_i; output integer value_o;
        begin case_rd_addr = base + word_i; #1; value_o = case_rd_data; end
    endtask
    task read_ids; input integer word_i; output integer value_o;
        begin ids_rd_addr = word_i; #1; value_o = ids_rd_data; end
    endtask
    task read_expect; input integer word_i; output integer value_o;
        begin expect_rd_addr = word_i; #1; value_o = expect_rd_data; end
    endtask
    task read_meta; input integer word_i; output integer value_o;
        begin meta_rd_addr = word_i; #1; value_o = meta_rd_data; end
    endtask
    task read_cap; input integer word_i; output integer value_o;
        begin cap_rd_addr = word_i; #1; value_o = cap_rd_data; end
    endtask
    task check_eq; input integer site; input integer actual; input integer expected;
        begin
            checks = checks + 1;
            if (actual !== expected && code == 0) code = site;
        end
    endtask

    //: All stimulus and all sampling happen on the FALLING edge.  Driving a
    //: one-cycle run pulse and clearing it immediately after the rising edge
    //: races the design's own sampling of it in the same time step, and a
    //: missed pulse looks exactly like a block that did nothing.
    initial begin
        geom_block[0] = 8;  geom_width[0] = 1048576; geom_ids[0] = 2048; geom_pin[0] = 1;
        geom_block[1] = 1;  geom_width[1] = 4096;    geom_ids[1] = 4096; geom_pin[1] = 1;
        geom_block[2] = 3;  geom_width[2] = 4095;    geom_ids[2] = 1365; geom_pin[2] = 1;
        geom_block[3] = 16; geom_width[3] = 8192;    geom_ids[3] = 512;  geom_pin[3] = 1;
        geom_block[4] = 8;  geom_width[4] = 4096;    geom_ids[4] = 2048; geom_pin[4] = 0;

        checks = 0;
        failures = 0;
        total_words = 0;
        total_pop = 0;
        repeat (6) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);

        read_meta(0, case_count);
        read_meta(1, meta_words);
        read_meta(2, meta_ids);
        read_meta(3, meta_refusals);
        read_meta(4, meta_geoms);
        read_meta(7, meta_population);
        if (case_count == 0) begin
            $display("FAIL: the case table is empty");
            $finish;
        end
        check_eq(29, geoms_param, meta_geoms);
        check_eq(30, case_stride_param, CASE_STRIDE);

        for (index = 0; index < case_count; index = index + 1) begin
            code = 0;
            base = index * CASE_STRIDE;
            read_case(0, f_geom);
            read_case(1, f_subop);
            read_case(2, f_width);
            read_case(3, f_id_count);
            read_case(4, f_block);
            read_case(5, f_max_pop);
            read_case(6, f_ids_base);
            read_case(7, f_out_base);
            read_case(8, f_code);
            read_case(9, f_detail);
            read_case(10, f_slot);
            read_case(11, f_value);
            read_case(12, f_words);
            read_case(13, f_pop);
            read_case(14, f_blocks);
            read_case(15, f_expect_base);

            g_block = geom_block[f_geom];
            g_pin = geom_pin[f_geom];

            // -- run it ------------------------------------------------------
            //: run is raised ON a falling edge and cleared on the NEXT falling
            //: edge, so it is high across exactly one rising edge whatever the
            //: reads above cost.  Raising it at an arbitrary time and clearing
            //: it at the next falling edge can span no rising edge at all, and
            //: a missed pulse reads as a block that ran the previous case.
            @(negedge clk);
            run_case = index;
            run = 1'b1;
            @(negedge clk);
            run = 1'b0;
            @(negedge clk);
            while (busy) @(negedge clk);
            @(negedge clk);

            // -- what the top and the block reported -------------------------
            check_eq(1, obs_timeout, 0);
            check_eq(2, obs_done_pulses, 1);
            check_eq(3, obs_error_code, f_code);
            check_eq(4, obs_error_detail, f_detail);
            check_eq(5, obs_error_slot, f_slot);
            check_eq(6, obs_error_value, f_value);
            check_eq(7, obs_out_count, f_words);
            check_eq(10, obs_pulses, f_words);
            check_eq(11, obs_addr_errors, 0);
            check_eq(12, obs_write_overflow, 0);
            check_eq(13, obs_param_block, g_block);
            check_eq(14, obs_param_max_width, geom_width[f_geom]);
            check_eq(15, obs_param_max_ids, geom_ids[f_geom]);
            check_eq(16, obs_param_word_bits, WORD_BITS);
            check_eq(17, obs_param_pin_last, g_pin);
            check_eq(26, obs_block_busy, 0);
            if (f_pop !== DONT_CHECK) check_eq(8, obs_population, f_pop);
            if (f_blocks !== DONT_CHECK) check_eq(9, obs_blocks, f_blocks);
            // Initiation interval, measured: n words in exactly n-1 cycles.
            if (f_words > 1) begin
                check_eq(18, obs_span, f_words - 1);
                check_eq(19, obs_emit_gap_max, 1);
            end
            // The ingest retires every id unless a refusal stopped it.
            if (f_code == 0) begin
                check_eq(25, obs_ids_consumed, f_id_count);
                check_eq(27, obs_id_reads, f_id_count);
            end else if (f_detail == 6) begin
                check_eq(25, obs_ids_consumed, f_slot + 1);
            end

            // -- derive the mask here, from the ids and nothing else ---------
            block_count = (f_width + g_block - 1) / g_block;
            last_block = block_count - 1;
            tail_len = f_width - last_block * g_block;
            mask_words = (f_width + WORD_BITS - 1) / WORD_BITS;
            first_bad_slot = -1;
            if (f_width > 0) begin
                for (k = 0; k < block_count; k = k + 1) blk_flag[k] = 1'b0;
                for (n = 0; n < f_id_count; n = n + 1) begin
                    read_ids(f_ids_base + n, id_value);
                    if (id_value !== ABSENT_ID) begin
                        if (id_value >= block_count) begin
                            if (first_bad_slot < 0) first_bad_slot = n;
                        end else if (first_bad_slot < 0) begin
                            blk_flag[id_value] = 1'b1;
                        end
                    end
                end
                if (g_pin != 0) blk_flag[last_block] = 1'b1;
                der_pop = 0;
                der_blocks = 0;
                for (k = 0; k < block_count; k = k + 1) begin
                    if (blk_flag[k]) begin
                        der_blocks = der_blocks + 1;
                        der_pop = der_pop + ((k == last_block) ? tail_len : g_block);
                    end
                end
                if (f_pop !== DONT_CHECK) check_eq(23, der_pop, f_pop);
                if (f_blocks !== DONT_CHECK) check_eq(24, der_blocks, f_blocks);
            end

            // -- every emitted word, three ways ------------------------------
            if (f_words > 0) begin
                for (word = 0; word < f_words; word = word + 1) begin
                    der_word = 0;
                    for (bit_i = 0; bit_i < WORD_BITS; bit_i = bit_i + 1) begin
                        pos = word * WORD_BITS + bit_i;
                        der_bit = 0;
                        if (pos < f_width) begin
                            if (blk_flag[pos / g_block]) der_bit = 1;
                        end
                        if (der_bit) der_word = der_word | (1 << bit_i);
                    end
                    read_expect(f_expect_base + word, expect_word);
                    read_cap(f_out_base + word, actual_word);
                    check_eq(20, actual_word, expect_word);
                    check_eq(21, actual_word, der_word);
                    check_eq(22, expect_word, der_word);
                end
                check_eq(7, mask_words, f_words);
            end

            if (code != 0) failures = failures + 1;
            total_words = total_words + f_words;
            if (f_pop !== DONT_CHECK) total_pop = total_pop + f_pop;
            $display("CMCASE %0d %s site=%0d geom=%0d block=%0d width=%0d ids=%0d words=%0d pop=%0d blocks=%0d code=%0d detail=%0d slot=%0d value=%0d pulses=%0d span=%0d gap=%0d cycles=%0d consumed=%0d",
                     index, (code == 0) ? "OK" : "DIVERGE", code, f_geom, g_block,
                     f_width, f_id_count, obs_out_count, obs_population, obs_blocks,
                     obs_error_code, obs_error_detail, obs_error_slot, obs_error_value,
                     obs_pulses, obs_span, obs_emit_gap_max, obs_cycles,
                     obs_ids_consumed);
        end

        check_eq(31, total_words, meta_words);
        check_eq(32, total_pop, meta_population);
        $display("CHECKS: %0d", checks);
        if (failures == 0)
            $display("PASS: A3 V41 candidate mask cases=%0d words=%0d population=%0d",
                     case_count, total_words, total_pop);
        else
            $display("FAIL: A3 V41 candidate mask cases=%0d diverged=%0d",
                     case_count, failures);
        $finish;
    end
endmodule
