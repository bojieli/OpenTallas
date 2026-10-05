`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the LQ8 lane block (results/rtl/abi3_lq8.json).
//
// This file and rtl/test/a3_lq8_harness.cpp are two independently written
// checkers over the same RTL and the same generated images.  For every case
// each checker runs the block once, then -- where the record says so -- runs
// the single qualified lane once per block lane on that lane's own images,
// and compares: every block lane's output word and binary32 accumulator
// against the expectation image; every reference run's against the same
// expectation; and the block lane against its reference run directly, element
// by element, wherever both wrote.  Counters, error classes, error details
// and the faulting lane index are compared as well, the unwritten sentinel is
// verified on every element no lane was expected to write, and the top's
// lockstep monitor must read zero after every case.
//
// The block rate is measured: the checker sums the block's per-cycle retire
// count between the first and the last cycle with a retirement and prints the
// window, the total, and the lane count; the campaign tool divides them.
//
// Case record layout (32-bit words, stride 128):
//    0 rows            1 cols (block)   2 depth          3 dtype_a
//    4 dtype_b         5 group          6 a_base         7 w_base
//    8 scale_a         9 scale_b       10 block_a       11 block_b
//   12 block_rows_a   13 block_rows_b  14 scale_a_base  15 ws_base
//   16 out_base       17 out_fp32
//   18 block error_code   19 block error_detail  20 block error_lane
//   21 block out_count    22 block saturations   23 block lane_ops
//   24 block products     25 run_reference       26 cols per lane
//   27 expect offset      28 flags (bit0 rate, bit1 fault, bit2 block refused)
//   29 case id            30 output window per lane (rows * cols per lane)
//   31 lanes
//   32 + i  b_base[i]        40 + i  scale_b_base[i]   48 + i  written[i]
//   56 + i  error_code[i]    64 + i  error_detail[i]   72 + i  lane_ops[i]
//   80 + i  products[i]      88 + i  out_count[i]      96 + i  saturations[i]
// Expect image: for lane i and element e, words
//   expect_offset + i * 2 * window + 2 * e      the output word
//   expect_offset + i * 2 * window + 2 * e + 1  the binary32 accumulator
// Result read-back address: lane * region_words + out_base + e.
// ---------------------------------------------------------------------------
module tb_a3_lq8 #(
    parameter integer ADDER_STAGES = 3,
    parameter integer LANES = 8
);
    localparam integer CASE_STRIDE = 128;
    localparam [31:0]  UNWRITTEN   = 32'hdead_beef;
    localparam [31:0]  FLAG_RATE   = 32'h1;
    localparam [31:0]  FLAG_FAULT  = 32'h2;
    localparam [31:0]  FLAG_BLOCK_REFUSED = 32'h4;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        start_dut = 1'b0;
    reg        start_ref = 1'b0;
    reg [15:0] cfg_rows = 16'b0;
    reg [15:0] cfg_cols = 16'b0;
    reg [15:0] cfg_depth = 16'b0;
    reg [7:0]  cfg_dtype_a = 8'b0;
    reg [7:0]  cfg_dtype_b = 8'b0;
    reg [7:0]  cfg_group = 8'b0;
    reg [31:0] cfg_a_base = 32'b0;
    reg        cfg_scale_a = 1'b0;
    reg [15:0] cfg_block_a = 16'b0;
    reg [15:0] cfg_block_rows_a = 16'b0;
    reg [31:0] cfg_scale_a_base = 32'b0;
    reg        cfg_scale_b = 1'b0;
    reg [15:0] cfg_block_b = 16'b0;
    reg [31:0] cfg_out_base = 32'b0;
    reg        cfg_out_fp32 = 1'b0;
    reg [31:0] cfg_w_base = 32'b0;
    reg [31:0] cfg_ws_base = 32'b0;
    reg [15:0] ref_cfg_cols = 16'b0;
    reg [31:0] ref_cfg_b_base = 32'b0;
    reg [31:0] ref_cfg_scale_b_base = 32'b0;
    reg [3:0]  ref_lane = 4'b0;
    reg [3:0]  lane_rd_sel = 4'b0;

    wire        dut_busy, dut_done;
    wire [7:0]  dut_error_code, dut_error_detail, dut_error_lane;
    wire [31:0] dut_out_count, dut_saturation_count, dut_mac_count, dut_product_count;
    wire [3:0]  dut_retire_count;
    wire [31:0] lockstep_violations;
    wire [31:0] lane_rd_error_code, lane_rd_error_detail, lane_rd_out_count;
    wire [31:0] lane_rd_saturation_count, lane_rd_mac_count, lane_rd_product_count;
    wire        ref_busy, ref_done;
    wire [7:0]  ref_error_code, ref_error_detail;
    wire [31:0] ref_out_count, ref_saturation_count, ref_mac_count, ref_product_count;

    reg  [31:0] case_rd_addr = 32'b0;
    wire [31:0] case_rd_data;
    reg  [31:0] expect_rd_addr = 32'b0;
    wire [31:0] expect_rd_data;
    reg  [31:0] meta_rd_addr = 32'b0;
    wire [31:0] meta_rd_data;
    reg  [31:0] res_rd_addr = 32'b0;
    wire [31:0] dut_res_rd_data, dut_acc_rd_data, ref_res_rd_data, ref_acc_rd_data;
    wire [31:0] adder_stages, lanes, region_words;

    ot_a3_lq8_top #(.LANES(LANES), .ADDER_STAGES(ADDER_STAGES)) dut (
        .clk(clk), .rst_n(rst_n),
        .start_dut(start_dut), .start_ref(start_ref),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
        .cfg_a_base(cfg_a_base), .cfg_scale_a(cfg_scale_a),
        .cfg_block_a(cfg_block_a), .cfg_block_rows_a(cfg_block_rows_a),
        .cfg_scale_a_base(cfg_scale_a_base),
        .cfg_scale_b(cfg_scale_b), .cfg_block_b(cfg_block_b),
        .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
        .cfg_w_base(cfg_w_base), .cfg_ws_base(cfg_ws_base),
        .ref_cfg_cols(ref_cfg_cols), .ref_cfg_b_base(ref_cfg_b_base),
        .ref_cfg_scale_b_base(ref_cfg_scale_b_base), .ref_lane(ref_lane),
        .dut_busy(dut_busy), .dut_done(dut_done),
        .dut_error_code(dut_error_code), .dut_error_detail(dut_error_detail),
        .dut_error_lane(dut_error_lane),
        .dut_out_count(dut_out_count), .dut_saturation_count(dut_saturation_count),
        .dut_mac_count(dut_mac_count), .dut_product_count(dut_product_count),
        .dut_retire_count(dut_retire_count), .lockstep_violations(lockstep_violations),
        .lane_rd_sel(lane_rd_sel),
        .lane_rd_error_code(lane_rd_error_code), .lane_rd_error_detail(lane_rd_error_detail),
        .lane_rd_out_count(lane_rd_out_count), .lane_rd_saturation_count(lane_rd_saturation_count),
        .lane_rd_mac_count(lane_rd_mac_count), .lane_rd_product_count(lane_rd_product_count),
        .ref_busy(ref_busy), .ref_done(ref_done),
        .ref_error_code(ref_error_code), .ref_error_detail(ref_error_detail),
        .ref_out_count(ref_out_count), .ref_saturation_count(ref_saturation_count),
        .ref_mac_count(ref_mac_count), .ref_product_count(ref_product_count),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .res_rd_addr(res_rd_addr),
        .dut_res_rd_data(dut_res_rd_data), .dut_acc_rd_data(dut_acc_rd_data),
        .ref_res_rd_data(ref_res_rd_data), .ref_acc_rd_data(ref_acc_rd_data),
        .adder_stages(adder_stages), .lanes(lanes), .region_words(region_words)
    );

    integer failures = 0;
    integer checks = 0;
    integer counted_cases = 0;
    integer counted_lane_ops = 0;
    integer counted_products = 0;
    integer counted_outputs = 0;
    integer counted_faults = 0;
    integer counted_reference = 0;
    integer counted_ref_outputs = 0;
    integer counted_identity = 0;

    integer meta_cases, meta_lane_ops, meta_products, meta_outputs;
    integer meta_faults, meta_reference, meta_stride, meta_ref_outputs, meta_lanes;

    integer record [0:CASE_STRIDE-1];
    integer case_index;
    integer field;
    integer lane;
    integer element;
    integer guard;
    integer cycle;
    integer first_retire;
    integer last_retire;
    integer retired;
    integer total_cycles;
    integer window;
    integer refused;
    reg [31:0] want_out, want_acc;
    reg [31:0] got_out, got_acc, got_ref_out, got_ref_acc;

    task fail(input [1023:0] message);
        begin
            failures = failures + 1;
            $display("FAIL: %0s", message);
        end
    endtask

    task check_equal(input [1023:0] label, input [63:0] got, input [63:0] want);
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL: case %0d lane %0d %0s got %0d want %0d",
                             record[29], lane, label, got, want);
            end
        end
    endtask

    task read_meta;
        begin
            meta_rd_addr = 0; #1; meta_cases = meta_rd_data;
            meta_rd_addr = 1; #1; meta_lane_ops = meta_rd_data;
            meta_rd_addr = 2; #1; meta_products = meta_rd_data;
            meta_rd_addr = 3; #1; meta_outputs = meta_rd_data;
            meta_rd_addr = 4; #1; meta_faults = meta_rd_data;
            meta_rd_addr = 5; #1; meta_reference = meta_rd_data;
            meta_rd_addr = 6; #1; meta_stride = meta_rd_data;
            meta_rd_addr = 7; #1; meta_ref_outputs = meta_rd_data;
            meta_rd_addr = 8; #1; meta_lanes = meta_rd_data;
        end
    endtask

    task load_record(input integer index);
        begin
            for (field = 0; field < CASE_STRIDE; field = field + 1) begin
                case_rd_addr = index * CASE_STRIDE + field;
                #1;
                record[field] = case_rd_data;
            end
        end
    endtask

    task drive_record;
        begin
            cfg_rows         = record[0][15:0];
            cfg_cols         = record[1][15:0];
            cfg_depth        = record[2][15:0];
            cfg_dtype_a      = record[3][7:0];
            cfg_dtype_b      = record[4][7:0];
            cfg_group        = record[5][7:0];
            cfg_a_base       = record[6];
            cfg_w_base       = record[7];
            cfg_scale_a      = record[8][0];
            cfg_scale_b      = record[9][0];
            cfg_block_a      = record[10][15:0];
            cfg_block_b      = record[11][15:0];
            cfg_block_rows_a = record[12][15:0];
            cfg_scale_a_base = record[14];
            cfg_ws_base      = record[15];
            cfg_out_base     = record[16];
            cfg_out_fp32     = record[17][0];
        end
    endtask

    // Run the block to completion, summing the per-cycle retire count.  The
    // clock is sampled at its negative edge so every registered output is
    // stable when it is read.
    task launch_dut;
        begin
            @(negedge clk);
            start_dut = 1'b1;
            @(negedge clk);
            start_dut = 1'b0;
            cycle = 0;
            retired = 0;
            first_retire = -1;
            last_retire = -1;
            guard = 0;
            while (!dut_done && guard < 60000000) begin
                if (dut_retire_count != 4'd0) begin
                    retired = retired + dut_retire_count;
                    if (first_retire < 0)
                        first_retire = cycle;
                    last_retire = cycle;
                end
                @(negedge clk);
                cycle = cycle + 1;
                guard = guard + 1;
            end
            total_cycles = cycle;
            if (!dut_done) fail("lane block never completed");
        end
    endtask

    task launch_ref;
        begin
            @(negedge clk);
            start_ref = 1'b1;
            @(negedge clk);
            start_ref = 1'b0;
            guard = 0;
            while (!ref_done && guard < 60000000) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!ref_done) fail("reference lane never completed");
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        read_meta;
        lane = -1;
        check_equal("lane count in image", meta_lanes, lanes);

        for (case_index = 0; case_index < meta_cases; case_index = case_index + 1) begin
            load_record(case_index);
            drive_record;
            lane = -1;
            launch_dut;
            window = record[30];
            refused = (record[28] & FLAG_BLOCK_REFUSED) != 0;

            counted_cases = counted_cases + 1;
            if (record[18] != 0)
                counted_faults = counted_faults + 1;

            check_equal("block error_code", {56'b0, dut_error_code}, record[18]);
            check_equal("block error_detail", {56'b0, dut_error_detail}, record[19]);
            check_equal("block error_lane", {56'b0, dut_error_lane}, record[20]);
            check_equal("block out_count", {32'b0, dut_out_count}, record[21]);
            check_equal("block saturation_count", {32'b0, dut_saturation_count}, record[22]);
            check_equal("block mac_count", {32'b0, dut_mac_count}, record[23]);
            check_equal("block product_count", {32'b0, dut_product_count}, record[24]);
            check_equal("block retired lane-ops", retired, record[23]);
            check_equal("lockstep violations", {32'b0, lockstep_violations}, 0);
            counted_lane_ops = counted_lane_ops + dut_mac_count;
            counted_products = counted_products + dut_product_count;

            if (record[28] & FLAG_RATE) begin
                $display("RATE: case=%0d lane_ops=%0d products=%0d total_cycles=%0d window_cycles=%0d first_retire=%0d last_retire=%0d lanes=%0d",
                         record[29], retired, dut_product_count, total_cycles,
                         (retired > 0) ? (last_retire - first_retire + 1) : 0,
                         first_retire, last_retire, LANES);
            end

            // Every block lane: its counters, then every element of its window.
            for (lane = 0; lane < LANES; lane = lane + 1) begin
                lane_rd_sel = lane[3:0];
                #1;
                // The block's per-lane class and detail are gated off after a
                // refusal (expected zero); the counters read through the
                // hierarchy are lane internals and are only meaningful for
                // an operation that reached the lanes.
                check_equal("lane error_code", {32'b0, lane_rd_error_code}, record[56 + lane]);
                check_equal("lane error_detail", {32'b0, lane_rd_error_detail}, record[64 + lane]);
                if (!refused) begin
                    check_equal("lane out_count", {32'b0, lane_rd_out_count}, record[88 + lane]);
                    check_equal("lane saturation_count", {32'b0, lane_rd_saturation_count}, record[96 + lane]);
                    check_equal("lane mac_count", {32'b0, lane_rd_mac_count}, record[72 + lane]);
                    check_equal("lane product_count", {32'b0, lane_rd_product_count}, record[80 + lane]);
                end
                for (element = 0; element < window; element = element + 1) begin
                    res_rd_addr = lane * region_words + record[16] + element;
                    expect_rd_addr = record[27] + lane * 2 * window + 2 * element;
                    #1;
                    want_out = expect_rd_data;
                    expect_rd_addr = record[27] + lane * 2 * window + 2 * element + 1;
                    #1;
                    want_acc = expect_rd_data;
                    got_out = dut_res_rd_data;
                    got_acc = dut_acc_rd_data;
                    checks = checks + 2;
                    if (element < record[48 + lane]) begin
                        counted_outputs = counted_outputs + 1;
                        if (got_out !== want_out || got_acc !== want_acc) begin
                            failures = failures + 1;
                            if (failures < 40)
                                $display("FAIL: case %0d lane %0d element %0d block got %08x/%08x want %08x/%08x",
                                         record[29], lane, element, got_out, got_acc, want_out, want_acc);
                        end
                    end else if (got_out !== UNWRITTEN || got_acc !== UNWRITTEN) begin
                        failures = failures + 1;
                        if (failures < 40)
                            $display("FAIL: case %0d lane %0d element %0d written by the block after a refusal: %08x/%08x",
                                     record[29], lane, element, got_out, got_acc);
                    end
                end
            end

            // The single lane, once per block lane, on that lane's own images.
            if (record[25] != 0) begin
                counted_reference = counted_reference + 1;
                for (lane = 0; lane < LANES; lane = lane + 1) begin
                    ref_cfg_cols = record[26][15:0];
                    ref_cfg_b_base = record[32 + lane];
                    ref_cfg_scale_b_base = record[40 + lane];
                    ref_lane = lane[3:0];
                    launch_ref;
                    check_equal("ref error_code", {56'b0, ref_error_code}, record[56 + lane]);
                    check_equal("ref error_detail", {56'b0, ref_error_detail}, record[64 + lane]);
                    check_equal("ref out_count", {32'b0, ref_out_count}, record[88 + lane]);
                    check_equal("ref saturation_count", {32'b0, ref_saturation_count}, record[96 + lane]);
                    check_equal("ref mac_count", {32'b0, ref_mac_count}, record[72 + lane]);
                    check_equal("ref product_count", {32'b0, ref_product_count}, record[80 + lane]);
                    lane_rd_sel = lane[3:0];
                    #1;
                    check_equal("ref and block lane error class", {56'b0, ref_error_code},
                                {32'b0, lane_rd_error_code});
                    check_equal("ref and block lane error detail", {56'b0, ref_error_detail},
                                {32'b0, lane_rd_error_detail});
                    for (element = 0; element < window; element = element + 1) begin
                        res_rd_addr = lane * region_words + record[16] + element;
                        expect_rd_addr = record[27] + lane * 2 * window + 2 * element;
                        #1;
                        want_out = expect_rd_data;
                        expect_rd_addr = record[27] + lane * 2 * window + 2 * element + 1;
                        #1;
                        want_acc = expect_rd_data;
                        got_out = dut_res_rd_data;
                        got_acc = dut_acc_rd_data;
                        got_ref_out = ref_res_rd_data;
                        got_ref_acc = ref_acc_rd_data;
                        checks = checks + 2;
                        if (element < record[48 + lane]) begin
                            counted_ref_outputs = counted_ref_outputs + 1;
                            if (got_ref_out !== want_out || got_ref_acc !== want_acc) begin
                                failures = failures + 1;
                                if (failures < 40)
                                    $display("FAIL: case %0d lane %0d element %0d ref got %08x/%08x want %08x/%08x",
                                             record[29], lane, element, got_ref_out, got_ref_acc, want_out, want_acc);
                            end
                            // Bit identity: the block lane and the single lane, directly.
                            checks = checks + 2;
                            counted_identity = counted_identity + 1;
                            if (got_out !== got_ref_out || got_acc !== got_ref_acc) begin
                                failures = failures + 1;
                                if (failures < 40)
                                    $display("FAIL: case %0d lane %0d element %0d block %08x/%08x differs from ref %08x/%08x",
                                             record[29], lane, element, got_out, got_acc, got_ref_out, got_ref_acc);
                            end
                        end else if (got_ref_out !== UNWRITTEN || got_ref_acc !== UNWRITTEN) begin
                            failures = failures + 1;
                            if (failures < 40)
                                $display("FAIL: case %0d lane %0d element %0d written by ref after a refusal: %08x/%08x",
                                         record[29], lane, element, got_ref_out, got_ref_acc);
                        end
                    end
                end
            end
        end

        lane = -1;
        check_equal("case count", counted_cases, meta_cases);
        check_equal("lane-op count", counted_lane_ops, meta_lane_ops);
        check_equal("product count", counted_products, meta_products);
        check_equal("output count", counted_outputs, meta_outputs);
        check_equal("fault case count", counted_faults, meta_faults);
        check_equal("reference case count", counted_reference, meta_reference);
        check_equal("reference output count", counted_ref_outputs, meta_ref_outputs);
        check_equal("case stride", meta_stride, CASE_STRIDE);
        check_equal("final lockstep violations", {32'b0, lockstep_violations}, 0);

        if (failures == 0) begin
            $display("PASS: ABI3 lq8 cases=%0d lane_ops=%0d products=%0d outputs=%0d faults=%0d reference_cases=%0d reference_outputs=%0d identity=%0d lanes=%0d adder_stages=%0d",
                     counted_cases, counted_lane_ops, counted_products, counted_outputs,
                     counted_faults, counted_reference, counted_ref_outputs,
                     counted_identity, LANES, ADDER_STAGES);
            $display("checks=%0d", checks);
            $finish;
        end else begin
            $display("FAILURES: %0d after checks=%0d", failures, checks);
            $fatal(1);
        end
    end
endmodule
