`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the pipelined contraction lane (gates D1, D2, D5).
//
// This file and rtl/test/a3_lane_pipelined_harness.cpp are two independently
// written checkers over the same RTL and the same generated images.  Neither
// reads the other's expectations: both walk the case image, run every case on
// the design under test and, where the record says so, on the untouched
// sequential reference lane; compare every output word and every binary32
// accumulator against the expectation image and against each other; count
// what they actually checked; and refuse to print the marker unless their own
// counts equal the totals the image declares.
//
// Gate D2 is measured, not derived: for a rate case the checker counts the
// clock cycles between the first and the last retired lane-op and the number
// of lane-ops retired in that window, and prints both.  The campaign tool
// divides them.  It also prints the whole run's cycle count so the fill and
// drain latency is on the record beside the steady-state rate.
//
// Case record layout (32-bit words, stride 40):
//    0 rows          1 cols          2 depth         3 dtype_a
//    4 dtype_b       5 group         6 a_base        7 b_base
//    8 scale_a       9 scale_b      10 block_a      11 block_b
//   12 block_rows_a 13 block_rows_b 14 scale_a_base 15 scale_b_base
//   16 out_base     17 out_fp32
//   18 dut error_code   19 dut error_detail  20 dut out_count
//   21 dut saturations  22 dut lane_ops      23 dut products
//   24 dut written elements (leading, row-major)
//   25 run_reference    26 ref error_code    27 ref out_count
//   28 ref saturations  29 ref mac_count     30 ref written elements
//   31 expect offset    32 flags (bit0 rate case, bit1 fault case)
//   33 case id          34 output window (rows * cols)
// Expect image: two words per output element, [output word, accumulator].
// ---------------------------------------------------------------------------
module tb_a3_lane_pipelined #(
    parameter integer ADDER_STAGES = 3
);
    localparam integer CASE_STRIDE = 40;
    localparam [31:0]  UNWRITTEN   = 32'hdead_beef;
    localparam [31:0]  FLAG_RATE   = 32'h1;
    localparam [31:0]  FLAG_FAULT  = 32'h2;

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
    reg [31:0] cfg_b_base = 32'b0;
    reg        cfg_scale_a = 1'b0;
    reg        cfg_scale_b = 1'b0;
    reg [15:0] cfg_block_a = 16'b0;
    reg [15:0] cfg_block_b = 16'b0;
    reg [15:0] cfg_block_rows_a = 16'b0;
    reg [15:0] cfg_block_rows_b = 16'b0;
    reg [31:0] cfg_scale_a_base = 32'b0;
    reg [31:0] cfg_scale_b_base = 32'b0;
    reg [31:0] cfg_out_base = 32'b0;
    reg        cfg_out_fp32 = 1'b0;

    wire        dut_busy, dut_done, dut_op_retire, dut_out_we;
    wire [7:0]  dut_error_code, dut_error_detail;
    wire [31:0] dut_out_count, dut_saturation_count, dut_mac_count, dut_product_count;
    wire        ref_busy, ref_done;
    wire [7:0]  ref_error_code;
    wire [31:0] ref_out_count, ref_saturation_count, ref_mac_count;

    reg  [31:0] case_rd_addr = 32'b0;
    wire [31:0] case_rd_data;
    reg  [31:0] expect_rd_addr = 32'b0;
    wire [31:0] expect_rd_data;
    reg  [31:0] meta_rd_addr = 32'b0;
    wire [31:0] meta_rd_data;
    reg  [31:0] res_rd_addr = 32'b0;
    wire [31:0] dut_res_rd_data, dut_acc_rd_data, ref_res_rd_data, ref_acc_rd_data;
    wire [31:0] adder_stages;

    ot_a3_lane_pipelined_top #(.ADDER_STAGES(ADDER_STAGES)) dut (
        .clk(clk), .rst_n(rst_n),
        .start_dut(start_dut), .start_ref(start_ref),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
        .dut_busy(dut_busy), .dut_done(dut_done),
        .dut_error_code(dut_error_code), .dut_error_detail(dut_error_detail),
        .dut_out_count(dut_out_count), .dut_saturation_count(dut_saturation_count),
        .dut_mac_count(dut_mac_count), .dut_product_count(dut_product_count),
        .dut_op_retire(dut_op_retire), .dut_out_we(dut_out_we),
        .ref_busy(ref_busy), .ref_done(ref_done), .ref_error_code(ref_error_code),
        .ref_out_count(ref_out_count), .ref_saturation_count(ref_saturation_count),
        .ref_mac_count(ref_mac_count),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .res_rd_addr(res_rd_addr),
        .dut_res_rd_data(dut_res_rd_data), .dut_acc_rd_data(dut_acc_rd_data),
        .ref_res_rd_data(ref_res_rd_data), .ref_acc_rd_data(ref_acc_rd_data),
        .adder_stages(adder_stages)
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
    integer meta_faults, meta_reference, meta_stride, meta_ref_outputs;

    integer record [0:CASE_STRIDE-1];
    integer case_index;
    integer field;
    integer element;
    integer guard;
    integer cycle;
    integer first_retire;
    integer last_retire;
    integer retired;
    integer total_cycles;
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
                    $display("FAIL: case %0d %0s got %0d want %0d", record[33], label, got, want);
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
            cfg_b_base       = record[7];
            cfg_scale_a      = record[8][0];
            cfg_scale_b      = record[9][0];
            cfg_block_a      = record[10][15:0];
            cfg_block_b      = record[11][15:0];
            cfg_block_rows_a = record[12][15:0];
            cfg_block_rows_b = record[13][15:0];
            cfg_scale_a_base = record[14];
            cfg_scale_b_base = record[15];
            cfg_out_base     = record[16];
            cfg_out_fp32     = record[17][0];
        end
    endtask

    // Run the design under test to completion, counting cycles and retired
    // lane-ops on the way.  The clock is sampled at its negative edge so that
    // every registered output is stable when it is read.
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
                if (dut_op_retire) begin
                    retired = retired + 1;
                    if (first_retire < 0)
                        first_retire = cycle;
                    last_retire = cycle;
                end
                @(negedge clk);
                cycle = cycle + 1;
                guard = guard + 1;
            end
            total_cycles = cycle;
            if (!dut_done) fail("pipelined lane never completed");
        end
    endtask

    task launch_ref;
        begin
            @(negedge clk);
            start_ref = 1'b1;
            @(negedge clk);
            start_ref = 1'b0;
            guard = 0;
            while (!ref_done && guard < 400000000) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!ref_done) fail("sequential reference lane never completed");
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        read_meta;

        for (case_index = 0; case_index < meta_cases; case_index = case_index + 1) begin
            load_record(case_index);
            drive_record;
            launch_dut;

            counted_cases = counted_cases + 1;
            if (record[18] != 0)
                counted_faults = counted_faults + 1;

            check_equal("dut error_code", {56'b0, dut_error_code}, record[18]);
            check_equal("dut error_detail", {56'b0, dut_error_detail}, record[19]);
            check_equal("dut out_count", {32'b0, dut_out_count}, record[20]);
            check_equal("dut saturation_count", {32'b0, dut_saturation_count}, record[21]);
            check_equal("dut mac_count", {32'b0, dut_mac_count}, record[22]);
            check_equal("dut product_count", {32'b0, dut_product_count}, record[23]);
            check_equal("dut retired lane-ops", retired, record[22]);
            counted_lane_ops = counted_lane_ops + dut_mac_count;
            counted_products = counted_products + dut_product_count;

            if (record[32] & FLAG_RATE) begin
                $display("RATE: case=%0d lane_ops=%0d products=%0d total_cycles=%0d window_cycles=%0d first_retire=%0d last_retire=%0d",
                         record[33], retired, dut_product_count, total_cycles,
                         (retired > 0) ? (last_retire - first_retire + 1) : 0,
                         first_retire, last_retire);
            end

            // Every element of the output window: the expected value where the
            // lane is expected to have written, the unwritten sentinel elsewhere.
            for (element = 0; element < record[34]; element = element + 1) begin
                res_rd_addr = record[16] + element;
                expect_rd_addr = record[31] + 2 * element;
                #1;
                want_out = expect_rd_data;
                expect_rd_addr = record[31] + 2 * element + 1;
                #1;
                want_acc = expect_rd_data;
                got_out = dut_res_rd_data;
                got_acc = dut_acc_rd_data;
                checks = checks + 2;
                if (element < record[24]) begin
                    counted_outputs = counted_outputs + 1;
                    if (got_out !== want_out || got_acc !== want_acc) begin
                        failures = failures + 1;
                        if (failures < 40)
                            $display("FAIL: case %0d element %0d dut got %08x/%08x want %08x/%08x",
                                     record[33], element, got_out, got_acc, want_out, want_acc);
                    end
                end else if (got_out !== UNWRITTEN || got_acc !== UNWRITTEN) begin
                    failures = failures + 1;
                    if (failures < 40)
                        $display("FAIL: case %0d element %0d written by dut after a refusal: %08x/%08x",
                                 record[33], element, got_out, got_acc);
                end
            end

            if (record[25] != 0) begin
                launch_ref;
                counted_reference = counted_reference + 1;
                check_equal("ref error_code", {56'b0, ref_error_code}, record[26]);
                check_equal("ref out_count", {32'b0, ref_out_count}, record[27]);
                check_equal("ref saturation_count", {32'b0, ref_saturation_count}, record[28]);
                check_equal("ref mac_count", {32'b0, ref_mac_count}, record[29]);
                check_equal("ref and dut error class", {56'b0, ref_error_code}, {56'b0, dut_error_code});
                for (element = 0; element < record[34]; element = element + 1) begin
                    res_rd_addr = record[16] + element;
                    expect_rd_addr = record[31] + 2 * element;
                    #1;
                    want_out = expect_rd_data;
                    expect_rd_addr = record[31] + 2 * element + 1;
                    #1;
                    want_acc = expect_rd_data;
                    got_out = dut_res_rd_data;
                    got_acc = dut_acc_rd_data;
                    got_ref_out = ref_res_rd_data;
                    got_ref_acc = ref_acc_rd_data;
                    checks = checks + 2;
                    if (element < record[30]) begin
                        counted_ref_outputs = counted_ref_outputs + 1;
                        if (got_ref_out !== want_out || got_ref_acc !== want_acc) begin
                            failures = failures + 1;
                            if (failures < 40)
                                $display("FAIL: case %0d element %0d ref got %08x/%08x want %08x/%08x",
                                         record[33], element, got_ref_out, got_ref_acc, want_out, want_acc);
                        end
                    end else if (got_ref_out !== UNWRITTEN || got_ref_acc !== UNWRITTEN) begin
                        failures = failures + 1;
                        if (failures < 40)
                            $display("FAIL: case %0d element %0d written by ref after a refusal: %08x/%08x",
                                     record[33], element, got_ref_out, got_ref_acc);
                    end
                    // Bit identity: the two lanes, directly, wherever both wrote.
                    if ((element < record[24]) && (element < record[30])) begin
                        checks = checks + 2;
                        counted_identity = counted_identity + 1;
                        if (got_out !== got_ref_out || got_acc !== got_ref_acc) begin
                            failures = failures + 1;
                            if (failures < 40)
                                $display("FAIL: case %0d element %0d dut %08x/%08x differs from ref %08x/%08x",
                                         record[33], element, got_out, got_acc, got_ref_out, got_ref_acc);
                        end
                    end
                end
            end
        end

        // The checker's own counts must equal the totals the image declares
        // before it is allowed to print them.
        check_equal("case count", counted_cases, meta_cases);
        check_equal("lane-op count", counted_lane_ops, meta_lane_ops);
        check_equal("product count", counted_products, meta_products);
        check_equal("output count", counted_outputs, meta_outputs);
        check_equal("fault case count", counted_faults, meta_faults);
        check_equal("reference case count", counted_reference, meta_reference);
        check_equal("reference output count", counted_ref_outputs, meta_ref_outputs);
        check_equal("case stride", meta_stride, CASE_STRIDE);

        if (failures == 0) begin
            $display("PASS: ABI3 pipelined lane cases=%0d lane_ops=%0d products=%0d outputs=%0d faults=%0d reference_cases=%0d reference_outputs=%0d identity=%0d adder_stages=%0d",
                     counted_cases, counted_lane_ops, counted_products, counted_outputs,
                     counted_faults, counted_reference, counted_ref_outputs,
                     counted_identity, ADDER_STAGES);
            $display("checks=%0d", checks);
            $finish;
        end else begin
            $display("FAILURES: %0d after checks=%0d", failures, checks);
            $fatal(1);
        end
    end
endmodule
