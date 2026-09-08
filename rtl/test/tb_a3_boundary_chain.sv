`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the two-tile dependent chain (section 13 item 13).
//
// The top (rtl/test/a3_boundary_chain_top.sv) runs one dependent pair per
// case -- producing tile, partial collector, K-block tree endpoint, operand
// receiver, consuming tile -- and stamps the span from the producer's last
// partial write to the consumer's first lane-op.  This checker requires the
// composition to be numerically exact at every stage (roots, delivered
// activation words, the consumer's own partials, all against the AM-E1
// reference), requires the structural invariants (no fault anywhere, no
// consumer lane-op before its operand landed, the legs telescoping to the
// span), and PREDICTS NO CYCLE COUNT: the boundary is the measurement.
//
// A second checker (rtl/test/a3_boundary_chain_harness.cpp) is written
// independently against the same top, and the campaign requires the two
// simulators to report the same cycles.
// ---------------------------------------------------------------------------
module tb_a3_boundary_chain;
    localparam integer CASE_STRIDE = 32;
    localparam integer TILE_LANES  = 64;
    localparam integer GUARD       = 4000000;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        run = 1'b0;
    reg [31:0] run_case = 32'd0;
    wire       busy, done;
    wire [31:0] boundary_cycles, boundary_to_kblock_cycles;
    wire [31:0] leg_collect, leg_tree, leg_receive, leg_readiness, leg_admit;
    wire [31:0] leg_lane_admission, endpoint_first_root_cycles, leaf_span_cycles;
    wire [31:0] producer_cycles, producer_kblock_cycles, obs_timeout;
    wire [7:0]  obs_prod_error_code, obs_prod_error_detail;
    wire [7:0]  obs_cons_error_code, obs_cons_error_detail;
    wire [7:0]  obs_coll_error_code, obs_coll_error_detail;
    wire [7:0]  obs_tree_error_code, obs_recv_error_code, obs_recv_error_detail;
    wire [31:0] obs_coll_vectors, obs_recv_words;
    wire [15:0] obs_act_ready;
    wire [31:0] obs_prod_out_count, obs_cons_out_count;
    wire [31:0] obs_prod_underruns, obs_cons_underruns;
    wire [31:0] obs_roots, obs_laneop_before_ready;
    reg  [31:0] case_rd_addr = 32'd0, expect_rd_addr = 32'd0, meta_rd_addr = 32'd0;
    reg  [31:0] root_rd_addr = 32'd0, act_rd_addr = 32'd0, res_rd_addr = 32'd0;
    wire [31:0] case_rd_data, expect_rd_data, meta_rd_data;
    wire [31:0] root_rd_data, act_rd_data, res_rd_data, adder_stages_param;

    ot_a3_boundary_chain_top dut (
        .clk(clk), .rst_n(rst_n), .run(run), .run_case(run_case),
        .busy(busy), .done(done),
        .boundary_cycles(boundary_cycles),
        .boundary_to_kblock_cycles(boundary_to_kblock_cycles),
        .leg_collect(leg_collect), .leg_tree(leg_tree), .leg_receive(leg_receive),
        .leg_readiness(leg_readiness), .leg_admit(leg_admit),
        .leg_lane_admission(leg_lane_admission),
        .endpoint_first_root_cycles(endpoint_first_root_cycles),
        .leaf_span_cycles(leaf_span_cycles),
        .producer_cycles(producer_cycles),
        .producer_kblock_cycles(producer_kblock_cycles),
        .obs_timeout(obs_timeout),
        .obs_prod_error_code(obs_prod_error_code),
        .obs_prod_error_detail(obs_prod_error_detail),
        .obs_cons_error_code(obs_cons_error_code),
        .obs_cons_error_detail(obs_cons_error_detail),
        .obs_coll_error_code(obs_coll_error_code),
        .obs_coll_error_detail(obs_coll_error_detail),
        .obs_tree_error_code(obs_tree_error_code),
        .obs_recv_error_code(obs_recv_error_code),
        .obs_recv_error_detail(obs_recv_error_detail),
        .obs_coll_vectors(obs_coll_vectors), .obs_recv_words(obs_recv_words),
        .obs_act_ready(obs_act_ready),
        .obs_prod_out_count(obs_prod_out_count), .obs_cons_out_count(obs_cons_out_count),
        .obs_prod_underruns(obs_prod_underruns), .obs_cons_underruns(obs_cons_underruns),
        .obs_roots(obs_roots), .obs_laneop_before_ready(obs_laneop_before_ready),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .root_rd_addr(root_rd_addr), .root_rd_data(root_rd_data),
        .act_rd_addr(act_rd_addr), .act_rd_data(act_rd_data),
        .res_rd_addr(res_rd_addr), .res_rd_data(res_rd_data),
        .adder_stages_param(adder_stages_param)
    );

    integer case_count, index, guard, checks, failures, code, base;
    integer blocks, expect_base, lane, got, want;
    integer total_checks;

    task read_case; input integer word; output integer value;
        begin case_rd_addr = base + word; @(negedge clk); value = case_rd_data; end
    endtask
    task read_expect; input integer word; output integer value;
        begin expect_rd_addr = word; @(negedge clk); value = expect_rd_data; end
    endtask
    task read_root; input integer word; output integer value;
        begin root_rd_addr = word; @(negedge clk); value = root_rd_data; end
    endtask
    task read_act; input integer word; output integer value;
        begin act_rd_addr = word; @(negedge clk); value = act_rd_data; end
    endtask
    task read_res; input integer word; output integer value;
        begin res_rd_addr = word; @(negedge clk); value = res_rd_data; end
    endtask
    task check_eq; input integer site; input integer actual; input integer expected;
        begin
            checks = checks + 1;
            if (actual !== expected && code == 0) code = site;
        end
    endtask

    initial begin
        checks = 0; failures = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);
        meta_rd_addr = 0; @(negedge clk); case_count = meta_rd_data;
        for (index = 0; index < case_count; index = index + 1) begin
            base = index * CASE_STRIDE;
            code = 0;
            read_case(4, blocks);
            read_case(26, expect_base);
            @(negedge clk);
            run_case = index; run = 1'b1;
            @(posedge clk); #1; run = 1'b0;
            guard = 0;
            while (!done && guard < GUARD) begin @(posedge clk); guard = guard + 1; end
            @(negedge clk);
            check_eq(1, obs_prod_error_code, 0);
            check_eq(2, obs_cons_error_code, 0);
            check_eq(3, obs_coll_error_code, 0);
            check_eq(4, obs_tree_error_code, 0);
            check_eq(5, obs_recv_error_code, 0);
            check_eq(6, obs_prod_out_count, blocks * TILE_LANES);
            check_eq(7, obs_cons_out_count, TILE_LANES);
            check_eq(8, obs_coll_vectors, TILE_LANES);
            check_eq(9, obs_recv_words, TILE_LANES);
            check_eq(10, obs_act_ready, 1);
            check_eq(11, obs_roots, TILE_LANES);
            check_eq(12, obs_laneop_before_ready, 0);
            check_eq(13, obs_timeout, 0);
            check_eq(14, obs_prod_underruns, 0);
            check_eq(15, obs_cons_underruns, 0);
            for (lane = 0; lane < TILE_LANES; lane = lane + 1) begin
                read_expect(expect_base + lane, want);
                read_root(lane, got);
                check_eq(16, got, want);
                read_expect(expect_base + TILE_LANES + lane, want);
                read_act(2 * lane, got);
                check_eq(17, got & 32'hffff, want);
                read_expect(expect_base + 2 * TILE_LANES + lane, want);
                read_res(4 * lane, got);
                check_eq(18, got, want);
            end
            checks = checks + 1;
            if (boundary_cycles == 0 && code == 0) code = 19;
            check_eq(20, leg_collect + leg_tree + leg_receive + leg_readiness +
                         leg_admit + leg_lane_admission, boundary_cycles);
            check_eq(21, leg_collect + leg_tree + leg_receive + leg_readiness +
                         leg_admit, boundary_to_kblock_cycles);
            checks = checks + 1;
            if (producer_kblock_cycles == 0 && code == 0) code = 22;
            if (guard >= GUARD && code == 0) code = 23;
            if (code != 0) failures = failures + 1;
            $display("XCASE %0d %0s site=%0d blocks=%0d boundary=%0d kblock=%0d collect=%0d tree=%0d receive=%0d ready=%0d admit=%0d laneadmit=%0d firstroot=%0d leafspan=%0d prodcycles=%0d prodkblock=%0d roots=%0d words=%0d stages=%0d",
                     index, (code == 0) ? "OK" : "DIVERGE", code, blocks,
                     boundary_cycles, boundary_to_kblock_cycles, leg_collect, leg_tree,
                     leg_receive, leg_readiness, leg_admit, leg_lane_admission,
                     endpoint_first_root_cycles, leaf_span_cycles, producer_cycles,
                     producer_kblock_cycles, obs_roots, obs_recv_words,
                     adder_stages_param);
        end
        $display("CHECKS: %0d", checks);
        if (failures != 0) begin
            $display("FAILURES: %0d", failures);
            $finish;
        end
        $display("PASS: ABI3 two-tile dependent chain cases=%0d", case_count);
        $finish;
    end
endmodule
