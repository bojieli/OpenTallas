`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the ABI 3.0 engine datapaths.
//
// This file and rtl/test/a3_engine_harness.cpp are two independently written
// checkers over the same RTL and the same generated images.  Neither reads the
// other's expectations and neither derives its counts from the other: both
// walk the case image, execute every case on the design, compare every result
// word against the bytes the functional simulator's engine wrote, count what
// they actually checked, and refuse to print the marker unless their own
// counts equal the totals the image declares.
//
// The marker is therefore not an echo of the image.  A checker that skipped a
// case, or that compared fewer words than the case declares, fails its own
// count before it reaches the comparison.
// ---------------------------------------------------------------------------
module tb_a3_engine;
    localparam integer RESULT_WORDS = 40960;
    localparam integer DECODE_WORDS = 16384;
    localparam integer ARITH_WORDS  = 65536;
    localparam integer ARITH_STRIDE = 8;
    localparam integer CASE_STRIDE  = 32;
    localparam [31:0]  UNWRITTEN    = 32'hdead_beef;

    localparam [7:0] ERR_NONE  = 8'd0;
    localparam [7:0] ERR_SHAPE = 8'd7;

    localparam [31:0] FLAG_COMPARE_WORK       = 32'h1;
    localparam [31:0] FLAG_COMPARE_TOKEN      = 32'h2;
    localparam [31:0] FLAG_EXPECT_UNTOUCHED   = 32'h4;
    localparam [31:0] FLAG_COMPARE_SATURATION = 32'h8;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        start = 1'b0;
    reg [7:0]  cfg_family = 8'b0;
    reg [7:0]  cfg_sub = 8'b0;
    reg [15:0] cfg_rows = 16'b0;
    reg [15:0] cfg_cols = 16'b0;
    reg [15:0] cfg_depth = 16'b0;
    reg [31:0] cfg_count = 32'b0;
    reg [7:0]  cfg_dtype_a = 8'b0;
    reg [7:0]  cfg_dtype_b = 8'b0;
    reg [31:0] cfg_a_base = 32'b0;
    reg [31:0] cfg_b_base = 32'b0;
    reg [31:0] cfg_c_base = 32'b0;
    reg [31:0] cfg_out_base = 32'b0;
    reg        cfg_scale_a = 1'b0;
    reg        cfg_scale_b = 1'b0;
    reg [15:0] cfg_block_a = 16'b0;
    reg [15:0] cfg_block_b = 16'b0;
    reg [15:0] cfg_block_rows_a = 16'b0;
    reg [15:0] cfg_block_rows_b = 16'b0;
    reg [31:0] cfg_scale_a_base = 32'b0;
    reg [31:0] cfg_scale_b_base = 32'b0;
    reg [31:0] cfg_slots = 32'b0;
    reg [31:0] cfg_trailing = 32'b0;
    reg [31:0] cfg_extent = 32'b0;

    wire        busy;
    wire        done;
    wire [7:0]  error_code;
    wire [31:0] result_count;
    wire [31:0] saturation_count;
    wire [31:0] work_count;
    wire [31:0] token;
    wire [31:0] tie_multiplicity;

    reg  [31:0] case_rd_addr = 32'b0;
    wire [31:0] case_rd_data;
    reg  [31:0] res_rd_addr = 32'b0;
    wire [31:0] res_rd_data;
    reg  [31:0] meta_rd_addr = 32'b0;
    wire [31:0] meta_rd_data;
    reg  [7:0]  probe_format = 8'b0;
    reg  [31:0] probe_word = 32'b0;
    wire [33:0] probe_result;
    reg  [31:0] arith_a = 32'b0;
    reg  [31:0] arith_b = 32'b0;
    wire [33:0] arith_add;
    wire [33:0] arith_mul;
    wire [18:0] arith_bf16;

    ot_a3_engine_top dut (
        .clk(clk), .rst_n(rst_n),
        .start(start),
        .cfg_family(cfg_family), .cfg_sub(cfg_sub),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_count(cfg_count),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_c_base(cfg_c_base), .cfg_out_base(cfg_out_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a),
        .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base),
        .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing),
        .cfg_extent(cfg_extent),
        .busy(busy), .done(done), .error_code(error_code),
        .result_count(result_count), .saturation_count(saturation_count),
        .work_count(work_count), .token(token),
        .tie_multiplicity(tie_multiplicity),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .res_rd_addr(res_rd_addr), .res_rd_data(res_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .probe_format(probe_format), .probe_word(probe_word),
        .probe_result(probe_result),
        .arith_a(arith_a), .arith_b(arith_b),
        .arith_add(arith_add), .arith_mul(arith_mul),
        .arith_bf16(arith_bf16)
    );

    // The checker keeps its own copy of the expected images.  It never reads
    // them through the design.
    reg [31:0] expect_mem [0:RESULT_WORDS-1];
    reg [31:0] decode_mem [0:DECODE_WORDS-1];
    reg [31:0] arith_mem  [0:ARITH_WORDS-1];

    integer failures = 0;
    integer checks = 0;
    integer counted_cases = 0;
    integer counted_results = 0;
    integer counted_faults = 0;
    integer counted_decodes = 0;
    integer counted_arith = 0;
    integer counted_macs = 0;
    integer family_seen [0:65535];
    integer counted_families = 0;

    integer meta_cases, meta_families, meta_results, meta_macs;
    integer meta_faults, meta_decodes, meta_stride, meta_arith;

    integer record [0:CASE_STRIDE-1];
    integer case_index;
    integer field;
    integer word;
    integer entry;
    integer guard;
    integer pair;

    task fail(input [1023:0] message);
        begin
            failures = failures + 1;
            $display("FAIL: %0s", message);
        end
    endtask

    task check_equal(input [1023:0] label, input [63:0] got,
                     input [63:0] want);
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                $display("FAIL: %0s got %0d want %0d", label, got, want);
            end
        end
    endtask

    task read_meta;
        begin
            meta_rd_addr = 0; #1; meta_cases = meta_rd_data;
            meta_rd_addr = 1; #1; meta_families = meta_rd_data;
            meta_rd_addr = 2; #1; meta_results = meta_rd_data;
            meta_rd_addr = 3; #1; meta_macs = meta_rd_data;
            meta_rd_addr = 4; #1; meta_faults = meta_rd_data;
            meta_rd_addr = 5; #1; meta_decodes = meta_rd_data;
            meta_rd_addr = 6; #1; meta_stride = meta_rd_data;
            meta_rd_addr = 7; #1; meta_arith = meta_rd_data;
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
            cfg_family       = record[0][7:0];
            cfg_sub          = record[1][7:0];
            cfg_rows         = record[2][15:0];
            cfg_cols         = record[3][15:0];
            cfg_depth        = record[4][15:0];
            cfg_count        = record[5];
            cfg_dtype_a      = record[6][7:0];
            cfg_dtype_b      = record[7][7:0];
            cfg_a_base       = record[8];
            cfg_b_base       = record[9];
            cfg_c_base       = record[10];
            cfg_out_base     = record[11];
            cfg_scale_a      = record[12][0];
            cfg_scale_b      = record[13][0];
            cfg_block_a      = record[14][15:0];
            cfg_block_b      = record[15][15:0];
            cfg_block_rows_a = record[16][15:0];
            cfg_block_rows_b = record[17][15:0];
            cfg_scale_a_base = record[18];
            cfg_scale_b_base = record[19];
            cfg_slots        = record[20];
            cfg_trailing     = record[21];
            cfg_extent       = record[22];
        end
    endtask

    task launch;
        begin
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            guard = 0;
            while (!done && guard < 40000000) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) fail("engine never completed");
        end
    endtask

    initial begin
        $readmemh("e3_expect.hex", expect_mem);
        $readmemh("e3_decode.hex", decode_mem);
        $readmemh("e3_arith.hex", arith_mem);
        for (pair = 0; pair < 65536; pair = pair + 1)
            family_seen[pair] = 0;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        read_meta;

        for (case_index = 0; case_index < meta_cases; case_index = case_index + 1) begin
            load_record(case_index);
            drive_record;
            launch;

            counted_cases = counted_cases + 1;
            pair = (record[0] << 8) | record[1];
            if (family_seen[pair] == 0) begin
                family_seen[pair] = 1;
                counted_families = counted_families + 1;
            end
            if (record[0] == 8'h20)
                counted_macs = counted_macs + record[2] * record[3] * record[4];
            if (record[23] != ERR_NONE)
                counted_faults = counted_faults + 1;

            check_equal("fault code", {56'b0, error_code}, {32'b0, record[23]});
            check_equal("result count", {32'b0, result_count}, {32'b0, record[24]});
            if (record[31] & FLAG_COMPARE_SATURATION)
                check_equal("saturations", {32'b0, saturation_count},
                            {32'b0, record[25]});
            if (record[31] & FLAG_COMPARE_WORK)
                check_equal("work", {32'b0, work_count}, {32'b0, record[26]});
            if (record[31] & FLAG_COMPARE_TOKEN) begin
                check_equal("token", {32'b0, token}, {32'b0, record[27]});
                check_equal("tie multiplicity", {32'b0, tie_multiplicity},
                            {32'b0, record[28]});
            end

            // Every declared result word, compared against the bytes the
            // functional engine wrote.  A refused case declares the same
            // window filled with the unwritten sentinel, so "no partial
            // result" is checked rather than assumed.
            for (word = 0; word < record[30]; word = word + 1) begin
                res_rd_addr = record[11] + word;
                #1;
                checks = checks + 1;
                counted_results = counted_results + 1;
                if (res_rd_data !== expect_mem[record[29] + word]) begin
                    failures = failures + 1;
                    if (failures < 20)
                        $display("FAIL: case %0d word %0d got %08x want %08x",
                                 case_index, word, res_rd_data,
                                 expect_mem[record[29] + word]);
                end
            end
        end

        // Fail-closed dispatch: an operation this array does not implement is
        // refused, not routed to whichever datapath happened to be wired up.
        cfg_family = 8'h40;      // ATTENTION, which this array does not carry
        cfg_sub = 8'h00;
        cfg_rows = 16'd1; cfg_cols = 16'd1; cfg_depth = 16'd1;
        cfg_count = 32'd1;
        launch;
        check_equal("unimplemented operation is refused",
                    {56'b0, error_code}, {56'b0, ERR_SHAPE});
        check_equal("unimplemented operation writes nothing",
                    {32'b0, result_count}, 64'd0);

        // Exhaustive storage-format decode against runtime.sim.formats.
        for (entry = 0; entry < meta_decodes; entry = entry + 1) begin
            probe_format = decode_mem[entry * 4][7:0];
            probe_word = decode_mem[entry * 4 + 1];
            #1;
            counted_decodes = counted_decodes + 1;
            checks = checks + 2;
            if (probe_result[33:32] !== decode_mem[entry * 4 + 2][1:0]) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL: decode %0d format %02x word %08x error %0d want %0d",
                             entry, probe_format, probe_word,
                             probe_result[33:32], decode_mem[entry * 4 + 2]);
            end
            if (decode_mem[entry * 4 + 2] == 0 &&
                probe_result[31:0] !== decode_mem[entry * 4 + 3]) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL: decode %0d format %02x word %08x got %08x want %08x",
                             entry, probe_format, probe_word,
                             probe_result[31:0], decode_mem[entry * 4 + 3]);
            end
        end

        // Binary32 add, multiply and BF16 rounding against the exact
        // fractions.Fraction reference, on the distribution that breaks a
        // floating-point unit rather than the one real operands produce.
        for (entry = 0; entry < meta_arith; entry = entry + 1) begin
            arith_a = arith_mem[entry * ARITH_STRIDE];
            arith_b = arith_mem[entry * ARITH_STRIDE + 1];
            #1;
            counted_arith = counted_arith + 1;
            checks = checks + 3;
            if (arith_add[33:32] !== arith_mem[entry * ARITH_STRIDE + 2][1:0] ||
                ((arith_mem[entry * ARITH_STRIDE + 2] == 0) &&
                 (arith_add[31:0] !== arith_mem[entry * ARITH_STRIDE + 3]))) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL: add %0d a=%08x b=%08x got %0d:%08x want %0d:%08x",
                             entry, arith_a, arith_b, arith_add[33:32],
                             arith_add[31:0], arith_mem[entry * ARITH_STRIDE + 2],
                             arith_mem[entry * ARITH_STRIDE + 3]);
            end
            if (arith_mul[33:32] !== arith_mem[entry * ARITH_STRIDE + 4][1:0] ||
                ((arith_mem[entry * ARITH_STRIDE + 4] == 0) &&
                 (arith_mul[31:0] !== arith_mem[entry * ARITH_STRIDE + 5]))) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL: mul %0d a=%08x b=%08x got %0d:%08x want %0d:%08x",
                             entry, arith_a, arith_b, arith_mul[33:32],
                             arith_mul[31:0], arith_mem[entry * ARITH_STRIDE + 4],
                             arith_mem[entry * ARITH_STRIDE + 5]);
            end
            if (arith_bf16[18:16] !== arith_mem[entry * ARITH_STRIDE + 6][2:0] ||
                ((arith_mem[entry * ARITH_STRIDE + 6] < 2) &&
                 (arith_bf16[15:0] !== arith_mem[entry * ARITH_STRIDE + 7][15:0]))) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL: bf16 %0d a=%08x got %0d:%04x want %0d:%04x",
                             entry, arith_a, arith_bf16[18:16], arith_bf16[15:0],
                             arith_mem[entry * ARITH_STRIDE + 6],
                             arith_mem[entry * ARITH_STRIDE + 7]);
            end
        end

        // The checker's own counts must equal the totals the image declares
        // before it is allowed to print them.
        check_equal("case count", counted_cases, meta_cases);
        check_equal("family count", counted_families, meta_families);
        check_equal("result word count", counted_results, meta_results);
        check_equal("mac count", counted_macs, meta_macs);
        check_equal("fault case count", counted_faults, meta_faults);
        check_equal("decode probe count", counted_decodes, meta_decodes);
        check_equal("arithmetic probe count", counted_arith, meta_arith);
        check_equal("case stride", meta_stride, CASE_STRIDE);

        if (failures == 0) begin
            $display("PASS: ABI3 RTL engine datapaths cases=%0d families=%0d results=%0d macs=%0d faults=%0d decodes=%0d arith=%0d",
                     counted_cases, counted_families, counted_results,
                     counted_macs, counted_faults, counted_decodes,
                     counted_arith);
            $display("checks=%0d", checks);
            $finish;
        end else begin
            $display("FAILURES: %0d after checks=%0d", failures, checks);
            $fatal(1);
        end
    end
endmodule
