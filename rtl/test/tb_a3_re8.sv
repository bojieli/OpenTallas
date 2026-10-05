`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the RE8 pairwise-tree endpoint (results/rtl/abi3_re8.json).
//
// This file and rtl/test/a3_re8_harness.cpp are two independently written
// checkers over the same RTL and the same generated images.  For every case
// the checker presents the case's leaf vectors to the endpoint -- back to
// back, one per cycle, in stream mode; one at a time, waiting for each
// result, in single-step mode -- collects every output in order and
// compares it with the vector's expected code, then compares the number of
// outputs, the adds and combines counter deltas, and the sticky fault
// registers (class, detail, level, tag) with the record; a fault case ends
// with a clear pulse.  The rate case reports the first input edge, the
// first and last output edges and the latency, and the campaign tool
// derives combines per cycle from them.
//
// Cycle accounting: the checker drives inputs at the falling edge, so a
// vector driven at cycle c is sampled at rising edge c + 1; an output first
// seen at falling edge c_out became valid at rising edge c_out.  latency =
// c_out - (c_in + 1) is the number of rising edges from the edge that
// sampled the vector to the edge at which its result is registered
// (1 + 3 L: unpack, three levels of L, output register).
//
// Case record layout (32-bit words, stride 16):
//    0 case id        1 vec_base      2 vec_count     3 flags (bit0 stream, bit1 fault, bit2 rate, bit3 single)
//    4 error_code     5 error_detail  6 error_level   7 error_tag
//    8 outputs        9 adds         10 combines     11 leaves in chain
// Vector layout (stride 12): 0 count, 1 tag, 2 flags (bit0 last, bit1 expect), 3..10 leaves, 11 expected code.
// ---------------------------------------------------------------------------
module tb_a3_re8 #(
    parameter integer ADDER_STAGES = 3,
    parameter integer LEAVES = 8
);
    localparam integer CASE_STRIDE = 16;
    localparam integer VEC_STRIDE = 12;
    localparam [31:0]  FLAG_STREAM = 32'h1;
    localparam [31:0]  FLAG_FAULT  = 32'h2;
    localparam [31:0]  FLAG_RATE   = 32'h4;
    localparam [31:0]  FLAG_SINGLE = 32'h8;
    localparam [31:0]  VFLAG_LAST   = 32'h1;
    localparam [31:0]  VFLAG_EXPECT = 32'h2;
    localparam integer DRAIN = 32;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg              in_valid = 1'b0;
    reg [3:0]        in_leaf_count = 4'b0;
    reg [32*LEAVES-1:0] in_leaf = {32*LEAVES{1'b0}};
    reg [15:0]       in_tag = 16'b0;
    reg              in_last = 1'b0;
    reg              clear = 1'b0;
    wire             out_valid, out_last, busy;
    wire [31:0]      out_data, adds_count, combines_count;
    wire [15:0]      out_tag, error_tag;
    wire [7:0]       error_code, error_detail;
    wire [1:0]       error_level;
    reg  [31:0]      vec_rd_addr = 32'b0, case_rd_addr = 32'b0, meta_rd_addr = 32'b0;
    wire [31:0]      vec_rd_data, case_rd_data, meta_rd_data, adder_stages, leaves;

    ot_a3_re8_top #(.LEAVES(LEAVES), .ADDER_STAGES(ADDER_STAGES)) dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_leaf_count(in_leaf_count), .in_leaf(in_leaf),
        .in_tag(in_tag), .in_last(in_last), .clear(clear),
        .out_valid(out_valid), .out_data(out_data), .out_tag(out_tag), .out_last(out_last),
        .error_code(error_code), .error_detail(error_detail), .error_level(error_level),
        .error_tag(error_tag), .busy(busy), .adds_count(adds_count), .combines_count(combines_count),
        .vec_rd_addr(vec_rd_addr), .vec_rd_data(vec_rd_data),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .adder_stages(adder_stages), .leaves(leaves)
    );

    integer failures = 0;
    integer checks = 0;
    integer counted_cases = 0, counted_vectors = 0, counted_outputs = 0, counted_faults = 0;
    integer counted_adds = 0, counted_combines = 0;
    integer meta_cases, meta_vectors, meta_outputs, meta_faults, meta_adds, meta_combines;
    integer meta_case_stride, meta_vec_stride;

    localparam integer MAX_VECTORS = 1024;   // per case; the image builder keeps cases below this
    integer record [0:CASE_STRIDE-1];
    integer vec [0:VEC_STRIDE-1];
    // The case's vectors, read back before the case runs: the read-back port
    // needs settling delays that must not straddle a clock edge mid-stream.
    integer vbuf [0:MAX_VECTORS*VEC_STRIDE-1];
    integer case_index, field, v, k, cycle, guard;
    integer got_outputs, expect_index, first_in, first_out, last_out;
    integer adds_before, combines_before;
    reg [31:0] want;

    task check_equal(input [1023:0] label, input [63:0] got, input [63:0] want_value);
        begin
            checks = checks + 1;
            if (got !== want_value) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL: case %0d %0s got %0d want %0d", record[0], label, got, want_value);
            end
        end
    endtask

    task read_meta;
        begin
            meta_rd_addr = 0; #1; meta_cases = meta_rd_data;
            meta_rd_addr = 1; #1; meta_vectors = meta_rd_data;
            meta_rd_addr = 2; #1; meta_outputs = meta_rd_data;
            meta_rd_addr = 3; #1; meta_faults = meta_rd_data;
            meta_rd_addr = 4; #1; meta_adds = meta_rd_data;
            meta_rd_addr = 5; #1; meta_combines = meta_rd_data;
            meta_rd_addr = 6; #1; meta_case_stride = meta_rd_data;
            meta_rd_addr = 7; #1; meta_vec_stride = meta_rd_data;
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

    task preload_vectors(input integer base, input integer count);
        integer vi;
        begin
            if (count > MAX_VECTORS) begin
                failures = failures + 1;
                $display("FAIL: case %0d has %0d vectors, above the checker's %0d", record[0], count, MAX_VECTORS);
            end
            for (vi = 0; vi < count && vi < MAX_VECTORS; vi = vi + 1) begin
                for (field = 0; field < VEC_STRIDE; field = field + 1) begin
                    vec_rd_addr = (base + vi) * VEC_STRIDE + field;
                    #1;
                    vbuf[vi * VEC_STRIDE + field] = vec_rd_data;
                end
            end
        end
    endtask

    // Vector ``index`` of the current case, from the preloaded buffer (no delay).
    task load_vector(input integer index);
        begin
            for (field = 0; field < VEC_STRIDE; field = field + 1)
                vec[field] = vbuf[index * VEC_STRIDE + field];
        end
    endtask

    task drive_vector;
        begin
            in_valid = 1'b1;
            in_leaf_count = vec[0][3:0];
            in_tag = vec[1][15:0];
            in_last = vec[2][0];
            for (k = 0; k < LEAVES; k = k + 1)
                in_leaf[32*k +: 32] = vec[3 + k];
        end
    endtask

    // The expected code of output number ``expect_index`` of the case: the
    // vectors flagged expect, in order.
    task next_expected;
        integer ve;
        begin
            want = 32'hdead_beef;
            for (ve = expect_index; ve < record[2]; ve = ve + 1) begin
                if ((vbuf[ve * VEC_STRIDE + 2] & VFLAG_EXPECT) != 0) begin
                    want = vbuf[ve * VEC_STRIDE + 11];
                    expect_index = ve + 1;
                    ve = record[2];
                end
            end
        end
    endtask

    // Sample the output port at this falling edge.
    task sample_output;
        begin
            if (out_valid) begin
                if (first_out < 0) first_out = cycle;
                last_out = cycle;
                got_outputs = got_outputs + 1;
                next_expected;
                checks = checks + 1;
                if (out_data !== want) begin
                    failures = failures + 1;
                    if (failures < 40)
                        $display("FAIL: case %0d output %0d tag %0d got %08x want %08x",
                                 record[0], got_outputs - 1, out_tag, out_data, want);
                end
            end
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        read_meta;
        record[0] = -1;
        check_equal("leaf count in image", leaves, LEAVES);
        check_equal("case stride", meta_case_stride, CASE_STRIDE);
        check_equal("vector stride", meta_vec_stride, VEC_STRIDE);

        for (case_index = 0; case_index < meta_cases; case_index = case_index + 1) begin
            load_record(case_index);
            preload_vectors(record[1], record[2]);
            got_outputs = 0;
            expect_index = 0;
            first_in = -1;
            first_out = -1;
            last_out = -1;
            adds_before = adds_count;
            combines_before = combines_count;
            cycle = 0;
            counted_cases = counted_cases + 1;
            counted_vectors = counted_vectors + record[2];
            if (record[4] != 0) counted_faults = counted_faults + 1;

            if ((record[3] & FLAG_SINGLE) != 0) begin
                // One vector at a time: present it, wait for its result or the drain.
                for (v = 0; v < record[2]; v = v + 1) begin
                    load_vector(v);
                    @(negedge clk);
                    sample_output;
                    drive_vector;
                    if (first_in < 0) first_in = cycle;
                    cycle = cycle + 1;
                    @(negedge clk);
                    sample_output;
                    in_valid = 1'b0;
                    cycle = cycle + 1;
                    for (guard = 0; guard < DRAIN; guard = guard + 1) begin
                        @(negedge clk);
                        sample_output;
                        cycle = cycle + 1;
                    end
                end
            end else begin
                // Stream: one vector per cycle, then drain.
                for (v = 0; v < record[2]; v = v + 1) begin
                    load_vector(v);
                    @(negedge clk);
                    sample_output;
                    drive_vector;
                    if (first_in < 0) first_in = cycle;
                    cycle = cycle + 1;
                end
                @(negedge clk);
                sample_output;
                in_valid = 1'b0;
                cycle = cycle + 1;
                for (guard = 0; guard < DRAIN; guard = guard + 1) begin
                    @(negedge clk);
                    sample_output;
                    cycle = cycle + 1;
                end
            end

            check_equal("outputs", got_outputs, record[8]);
            check_equal("adds", adds_count - adds_before, record[9]);
            check_equal("combines", combines_count - combines_before, record[10]);
            check_equal("error_code", {56'b0, error_code}, record[4]);
            check_equal("error_detail", {56'b0, error_detail}, record[5]);
            check_equal("error_level", {62'b0, error_level}, record[6]);
            check_equal("error_tag", {48'b0, error_tag}, record[7]);
            check_equal("busy after drain", busy, 0);
            counted_outputs = counted_outputs + got_outputs;
            counted_adds = counted_adds + (adds_count - adds_before);
            counted_combines = counted_combines + (combines_count - combines_before);

            if ((record[3] & FLAG_RATE) != 0) begin
                $display("RATE: case=%0d vectors=%0d outputs=%0d first_in=%0d first_out=%0d last_out=%0d latency_cycles=%0d window_cycles=%0d",
                         record[0], record[2], got_outputs, first_in, first_out, last_out,
                         first_out - (first_in + 1), (got_outputs > 0) ? (last_out - first_out + 1) : 0);
            end

            if (record[4] != 0) begin
                @(negedge clk);
                clear = 1'b1;
                @(negedge clk);
                clear = 1'b0;
                @(negedge clk);
                check_equal("error_code after clear", {56'b0, error_code}, 0);
            end
        end

        record[0] = -1;
        check_equal("case count", counted_cases, meta_cases);
        check_equal("vector count", counted_vectors, meta_vectors);
        check_equal("output count", counted_outputs, meta_outputs);
        check_equal("fault case count", counted_faults, meta_faults);
        check_equal("adds total", counted_adds, meta_adds);
        check_equal("combines total", counted_combines, meta_combines);

        if (failures == 0) begin
            $display("PASS: ABI3 re8 cases=%0d vectors=%0d outputs=%0d faults=%0d adds=%0d combines=%0d leaves=%0d adder_stages=%0d",
                     counted_cases, counted_vectors, counted_outputs, counted_faults, counted_adds,
                     counted_combines, LEAVES, ADDER_STAGES);
            $display("checks=%0d", checks);
            $finish;
        end else begin
            $display("FAILURES: %0d after checks=%0d", failures, checks);
            $fatal(1);
        end
    end
endmodule
