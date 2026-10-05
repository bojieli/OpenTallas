`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for OR64, the operand receiver.
//
// The top (rtl/test/a3_receiver_top.sv) presents binary32 roots with the tags
// the collector would have given them and holds an activation array with
// ot_a3_tile64's own write semantics.  This checker runs every case, compares
// the delivered activation window word for word with the expectation image,
// requires every fault to be the one the case table names, and reports the
// measured readiness delay -- the cycles from a slice's last root to the cycle
// act_ready_kblocks names that slice -- without predicting it.
//
// A divergence does not stop the run.  A second checker
// (rtl/test/a3_receiver_harness.cpp) is written independently against the same
// top.
// ---------------------------------------------------------------------------
module tb_a3_receiver;
    localparam integer CASE_STRIDE = 24;
    localparam integer GUARD       = 200000;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        run = 1'b0;
    reg [31:0] run_case = 32'd0;
    wire       busy, done;
    wire [31:0] obs_timeout, obs_done_pulses;
    wire [7:0]  obs_error_code, obs_error_detail;
    wire [15:0] obs_error_tag;
    wire [31:0] obs_roots_count, obs_words_written;
    wire [15:0] obs_slices_ready;
    wire [31:0] obs_saturation_count;
    wire [15:0] obs_act_ready_kblocks;
    wire        obs_busy;
    wire [31:0] obs_scale_writes;
    reg  [31:0] case_rd_addr = 32'd0, root_rd_addr = 32'd0, expect_rd_addr = 32'd0;
    reg  [31:0] meta_rd_addr = 32'd0, act_rd_addr = 32'd0, trace_rd_addr = 32'd0;
    wire [31:0] case_rd_data, root_rd_data, expect_rd_data, meta_rd_data;
    wire [31:0] act_rd_data, trace_rd_data, act_words_param;

    ot_a3_receiver_top dut (
        .clk(clk), .rst_n(rst_n), .run(run), .run_case(run_case),
        .busy(busy), .done(done),
        .obs_timeout(obs_timeout), .obs_done_pulses(obs_done_pulses),
        .obs_error_code(obs_error_code), .obs_error_detail(obs_error_detail),
        .obs_error_tag(obs_error_tag), .obs_roots_count(obs_roots_count),
        .obs_words_written(obs_words_written), .obs_slices_ready(obs_slices_ready),
        .obs_saturation_count(obs_saturation_count),
        .obs_act_ready_kblocks(obs_act_ready_kblocks), .obs_busy(obs_busy),
        .obs_scale_writes(obs_scale_writes),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .root_rd_addr(root_rd_addr), .root_rd_data(root_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .act_rd_addr(act_rd_addr), .act_rd_data(act_rd_data),
        .trace_rd_addr(trace_rd_addr), .trace_rd_data(trace_rd_data),
        .act_words_param(act_words_param)
    );

    integer case_count, index, guard, checks, failures, code, base;
    integer trace_word;
    integer blocks, slice_words, group, gap, inject, act_base, act_expect_base, act_window;
    integer e_code, e_detail, e_tag, e_words, e_slices, e_roots, e_sat;
    integer w, got, want;
    reg [31:0] delay;
    integer total_words, total_slices;

    task read_case; input integer word; output integer value;
        begin case_rd_addr = base + word; @(negedge clk); value = case_rd_data; end
    endtask
    task read_expect; input integer word; output integer value;
        begin expect_rd_addr = word; @(negedge clk); value = expect_rd_data; end
    endtask
    task read_act; input integer word; output integer value;
        begin act_rd_addr = word; @(negedge clk); value = act_rd_data; end
    endtask
    task read_trace; input integer word; output integer value;
        begin trace_rd_addr = word; @(negedge clk); value = trace_rd_data; end
    endtask
    task check_eq; input integer site; input integer actual; input integer expected;
        begin
            checks = checks + 1;
            if (actual !== expected && code == 0) code = site;
        end
    endtask

    initial begin
        checks = 0; failures = 0; total_words = 0; total_slices = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);
        meta_rd_addr = 0; @(negedge clk); case_count = meta_rd_data;
        for (index = 0; index < case_count; index = index + 1) begin
            base = index * CASE_STRIDE;
            code = 0;
            read_case(0, blocks); read_case(1, slice_words); read_case(2, group);
            read_case(5, act_base); read_case(9, inject);
            read_case(10, e_code); read_case(11, e_detail); read_case(12, e_tag);
            read_case(13, e_words); read_case(14, e_slices); read_case(15, e_roots);
            read_case(16, e_sat); read_case(17, act_expect_base); read_case(18, act_window);
            read_case(20, gap);
            @(negedge clk);
            run_case = index; run = 1'b1;
            @(posedge clk); #1; run = 1'b0;
            guard = 0;
            while (!done && guard < GUARD) begin @(posedge clk); guard = guard + 1; end
            @(negedge clk);
            check_eq(1, obs_error_code, e_code);
            check_eq(2, obs_error_detail, e_detail);
            check_eq(3, obs_error_tag, e_tag);
            check_eq(4, obs_words_written, e_words);
            check_eq(5, obs_slices_ready, e_slices);
            check_eq(6, obs_act_ready_kblocks, e_slices);
            check_eq(7, obs_roots_count, e_roots);
            check_eq(8, obs_saturation_count, e_sat);
            check_eq(9, obs_timeout, 0);
            check_eq(10, obs_done_pulses, 1);
            check_eq(11, obs_busy, 0);
            check_eq(12, obs_scale_writes, 0);
            for (w = 0; w < act_window; w = w + 1) begin
                read_act(2 * (act_base + w), got);
                read_expect(act_expect_base + 2 * w, want);
                check_eq(13, got, want);
                read_act(2 * (act_base + w) + 1, got);
                read_expect(act_expect_base + 2 * w + 1, want);
                check_eq(14, got, want);
            end
            read_trace(0, trace_word);
            delay = trace_word[31:0];
            if (e_slices > 0) begin
                checks = checks + 1;
                if (delay === 32'hffffffff && code == 0) code = 15;
            end
            total_words = total_words + e_words;
            total_slices = total_slices + e_slices;
            if (guard >= GUARD && code == 0) code = 16;
            if (code != 0) failures = failures + 1;
            $display("RCASE %0d %0s site=%0d words=%0d slices=%0d roots=%0d sat=%0d code=%0d detail=%0d tag=%0d ready=%0d delay=%0d blocks=%0d group=%0d gap=%0d inject=%0d",
                     index, (code == 0) ? "OK" : "DIVERGE", code, obs_words_written,
                     obs_slices_ready, obs_roots_count, obs_saturation_count,
                     obs_error_code, obs_error_detail, obs_error_tag,
                     obs_act_ready_kblocks, delay, blocks, group, gap, inject);
        end
        $display("CHECKS: %0d", checks);
        if (failures != 0) begin
            $display("FAILURES: %0d", failures);
            $finish;
        end
        $display("PASS: ABI3 operand receiver cases=%0d words=%0d slices=%0d",
                 case_count, total_words, total_slices);
        $finish;
    end
endmodule
