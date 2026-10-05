`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for PC64, the partial collector.
//
// The top (rtl/test/a3_collector_top.sv) presents ot_a3_tile64's partial port
// to the collector and captures every leaf vector the collector emits and
// every root the endpoint on its leaf port retires.  This checker runs every
// case, compares the emitted vectors against the partial image directly --
// vector v is slot (lane = v / elems, element = v mod elems) and its leaf k is
// K-block k's partial of that slot -- compares the roots against the AM-E1
// reference, and requires every fault to be the one the case table names.
//
// A divergence does not stop the run, so one wrong case does not hide the
// state of the others.  A second checker (rtl/test/a3_collector_harness.cpp)
// is written independently against the same top.
// ---------------------------------------------------------------------------
module tb_a3_collector;
    localparam integer CASE_STRIDE = 24;
    localparam integer TILE_LANES  = 64;
    localparam integer LEAVES      = 8;
    localparam integer VEC_STRIDE  = LEAVES + 2;
    localparam integer GUARD       = 2000000;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        run = 1'b0;
    reg [31:0] run_case = 32'd0;
    wire       busy, done;
    wire [31:0] obs_timeout, obs_done_pulses, obs_vectors, obs_roots;
    wire [7:0]  obs_error_code, obs_error_detail;
    wire [15:0] obs_error_lane;
    wire [31:0] obs_error_slot, obs_captured, obs_vectors_count;
    wire        obs_busy;
    wire [7:0]  obs_tree_error_code;
    wire [31:0] obs_tag_order_errors;
    reg  [31:0] part_rd_addr = 32'd0, case_rd_addr = 32'd0, expect_rd_addr = 32'd0;
    reg  [31:0] meta_rd_addr = 32'd0, vec_rd_addr = 32'd0, root_rd_addr = 32'd0;
    wire [31:0] part_rd_data, case_rd_data, expect_rd_data, meta_rd_data;
    wire [31:0] vec_rd_data, root_rd_data;
    wire [31:0] slot_elems_param, leaves_param, adder_stages_param;

    ot_a3_collector_top dut (
        .clk(clk), .rst_n(rst_n), .run(run), .run_case(run_case),
        .busy(busy), .done(done),
        .obs_timeout(obs_timeout), .obs_done_pulses(obs_done_pulses),
        .obs_vectors(obs_vectors), .obs_roots(obs_roots),
        .obs_error_code(obs_error_code), .obs_error_detail(obs_error_detail),
        .obs_error_lane(obs_error_lane), .obs_error_slot(obs_error_slot),
        .obs_captured(obs_captured), .obs_vectors_count(obs_vectors_count),
        .obs_busy(obs_busy), .obs_tree_error_code(obs_tree_error_code),
        .obs_tag_order_errors(obs_tag_order_errors),
        .part_rd_addr(part_rd_addr), .part_rd_data(part_rd_data),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .vec_rd_addr(vec_rd_addr), .vec_rd_data(vec_rd_data),
        .root_rd_addr(root_rd_addr), .root_rd_data(root_rd_data),
        .slot_elems_param(slot_elems_param), .leaves_param(leaves_param),
        .adder_stages_param(adder_stages_param)
    );

    integer case_count, index, guard, checks, failures, code, base;
    integer blocks, elems, out_base, part_base, mode, inject;
    integer e_code, e_detail, e_lane, e_slot, e_vectors, e_captured, e_roots, root_base;
    integer v, k, lane, elem, expect_leaf, got_leaf, expect_root, got_root;
    integer total_vectors, total_roots;

    task read_case; input integer word; output integer value;
        begin case_rd_addr = base + word; @(negedge clk); value = case_rd_data; end
    endtask
    task read_part; input integer word; output integer value;
        begin part_rd_addr = word; @(negedge clk); value = part_rd_data; end
    endtask
    task read_expect; input integer word; output integer value;
        begin expect_rd_addr = word; @(negedge clk); value = expect_rd_data; end
    endtask
    task read_vec; input integer word; output integer value;
        begin vec_rd_addr = word; @(negedge clk); value = vec_rd_data; end
    endtask
    task read_root; input integer word; output integer value;
        begin root_rd_addr = word; @(negedge clk); value = root_rd_data; end
    endtask
    task check_eq; input integer site; input integer actual; input integer expected;
        begin
            checks = checks + 1;
            if (actual !== expected && code == 0) code = site;
        end
    endtask

    initial begin
        checks = 0; failures = 0; total_vectors = 0; total_roots = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);
        meta_rd_addr = 0; @(negedge clk); case_count = meta_rd_data;
        for (index = 0; index < case_count; index = index + 1) begin
            base = index * CASE_STRIDE;
            code = 0;
            read_case(0, blocks); read_case(1, elems); read_case(2, out_base);
            read_case(3, part_base); read_case(4, mode); read_case(5, inject);
            read_case(8, e_code); read_case(9, e_detail); read_case(10, e_lane);
            read_case(11, e_slot); read_case(12, e_vectors); read_case(13, e_captured);
            read_case(14, e_roots); read_case(15, root_base);
            @(negedge clk);
            run_case = index; run = 1'b1;
            @(posedge clk); #1; run = 1'b0;
            guard = 0;
            while (!done && guard < GUARD) begin @(posedge clk); guard = guard + 1; end
            @(negedge clk);
            check_eq(1, obs_error_code, e_code);
            check_eq(2, obs_error_detail, e_detail);
            check_eq(3, obs_error_lane, e_lane);
            check_eq(4, obs_error_slot, e_slot);
            check_eq(5, obs_vectors, e_vectors);
            check_eq(6, obs_captured, e_captured);
            check_eq(7, obs_roots, e_roots);
            check_eq(8, obs_vectors_count, e_vectors);
            check_eq(9, obs_tag_order_errors, 0);
            check_eq(10, obs_timeout, 0);
            check_eq(11, obs_done_pulses, 1);
            check_eq(12, obs_tree_error_code, 0);
            check_eq(13, obs_busy, 0);
            for (v = 0; v < obs_vectors && v < e_vectors; v = v + 1) begin
                lane = v / elems;
                elem = v % elems;
                for (k = 0; k < blocks; k = k + 1) begin
                    read_part(part_base + (k * elems + elem) * TILE_LANES + lane, expect_leaf);
                    read_vec(v * VEC_STRIDE + k, got_leaf);
                    check_eq(14, got_leaf, expect_leaf);
                end
                read_vec(v * VEC_STRIDE + LEAVES, got_leaf);
                check_eq(15, got_leaf, v);
                read_vec(v * VEC_STRIDE + LEAVES + 1, got_leaf);
                check_eq(16, got_leaf, blocks);
                total_vectors = total_vectors + 1;
            end
            for (v = 0; v < obs_roots && v < e_roots; v = v + 1) begin
                read_expect(root_base + 2 * v, expect_root);
                read_root(2 * v, got_root);
                check_eq(17, got_root, expect_root);
                read_expect(root_base + 2 * v + 1, expect_root);
                read_root(2 * v + 1, got_root);
                check_eq(18, got_root, expect_root);
                total_roots = total_roots + 1;
            end
            if (guard >= GUARD && code == 0) code = 19;
            if (code != 0) failures = failures + 1;
            $display("CCASE %0d %0s site=%0d vectors=%0d roots=%0d captured=%0d code=%0d detail=%0d lane=%0d slot=%0d blocks=%0d elems=%0d mode=%0d inject=%0d",
                     index, (code == 0) ? "OK" : "DIVERGE", code, obs_vectors, obs_roots,
                     obs_captured, obs_error_code, obs_error_detail, obs_error_lane,
                     obs_error_slot, blocks, elems, mode, inject);
        end
        $display("CHECKS: %0d", checks);
        if (failures != 0) begin
            $display("FAILURES: %0d", failures);
            $finish;
        end
        $display("PASS: ABI3 partial collector cases=%0d vectors=%0d roots=%0d",
                 case_count, total_vectors, total_roots);
        $finish;
    end
endmodule
