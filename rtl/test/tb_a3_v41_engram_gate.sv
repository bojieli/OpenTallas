`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact-code scoreboard for VECTOR.ENGRAM_GATE, contract engram_gate_fp32_v1.
//
// Every expected word comes from runtime/reference/engram.py::engram_gate via
// tools/build_a3_v41_engram_gate_vectors.py.  The testbench knows no arithmetic:
// it drives requests, models the operand memory, and compares codes.
//
// GEOMETRY IS A PARAMETER of this testbench, overridden per simulator leg
// (iverilog -P, verilator -G), so the same cases run on several
// (VECTOR_WIDTH, LANES, ACC_EXP_MAX) instances and the campaign can require that
// changing the geometry changes no computed code.  The expectation file for the
// leg is passed as a plusarg.
//
// The reported cycle counts are verification cost.  They are not architectural
// latency, not a frequency claim and not a TPOT.
// ---------------------------------------------------------------------------
module tb_a3_v41_engram_gate #(
    parameter integer GATE_VECTOR_WIDTH = 256,
    parameter integer GATE_LANES = 4,
    parameter integer GATE_ACC_EXP_MIN = -126,
    parameter integer GATE_ACC_EXP_MAX = 64
);
    //: Storage bounds only.  Every real bound is read from the vector metadata
    //: and checked against these.
    localparam integer CASE_LIMIT   = 256;
    localparam integer VECTOR_SPACE = 512;
    localparam integer MEMORY_SPACE = 8 * VECTOR_SPACE;
    localparam integer CASE_WORDS   = 8;
    localparam integer EXPECT_SCALARS = 16;
    localparam integer TIMEOUT_CYCLES = 200000;

    reg clk;
    reg rst_n;
    reg start;
    reg [31:0] cfg_count;
    reg [31:0] cfg_h_base;
    reg [31:0] cfg_key_base;
    reg [31:0] cfg_value_base;
    reg [31:0] cfg_q_base;
    reg [31:0] cfg_k_base;
    reg [31:0] cfg_out_base;

    wire        r0_rd_en;
    wire [31:0] r0_rd_addr;
    reg  [GATE_LANES*32-1:0] r0_rd_data;
    wire        r1_rd_en;
    wire [31:0] r1_rd_addr;
    reg  [GATE_LANES*32-1:0] r1_rd_data;
    wire        r2_rd_en;
    wire [31:0] r2_rd_addr;
    reg  [GATE_LANES*32-1:0] r2_rd_data;

    wire [GATE_LANES-1:0]    out_we;
    wire [31:0]              out_addr;
    wire [GATE_LANES*32-1:0] out_data;

    wire        busy;
    wire        done;
    wire [7:0]  error_code;
    wire [3:0]  refusal_stage;
    wire [31:0] out_count;
    wire [31:0] reduce_count;
    wire [7:0]  sub_opcode;
    wire [31:0] dbg_dot_code;
    wire [31:0] dbg_norm_q_square_code;
    wire [31:0] dbg_norm_k_square_code;
    wire [31:0] dbg_norm_q_code;
    wire [31:0] dbg_norm_k_code;
    wire [31:0] dbg_denominator_raw_code;
    wire [31:0] dbg_denominator_code;
    wire [31:0] dbg_cosine_code;
    wire [31:0] dbg_signed_sqrt_code;
    wire [31:0] dbg_gate_code;
    wire        dbg_clamped;

    ot_a3_vector_engram_gate #(
        .VECTOR_WIDTH(GATE_VECTOR_WIDTH),
        .LANES(GATE_LANES),
        .ACC_EXP_MIN(GATE_ACC_EXP_MIN),
        .ACC_EXP_MAX(GATE_ACC_EXP_MAX)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(cfg_count),
        .cfg_h_base(cfg_h_base), .cfg_key_base(cfg_key_base),
        .cfg_value_base(cfg_value_base), .cfg_q_base(cfg_q_base),
        .cfg_k_base(cfg_k_base), .cfg_out_base(cfg_out_base),
        .r0_rd_en(r0_rd_en), .r0_rd_addr(r0_rd_addr), .r0_rd_data(r0_rd_data),
        .r1_rd_en(r1_rd_en), .r1_rd_addr(r1_rd_addr), .r1_rd_data(r1_rd_data),
        .r2_rd_en(r2_rd_en), .r2_rd_addr(r2_rd_addr), .r2_rd_data(r2_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .refusal_stage(refusal_stage),
        .out_count(out_count), .reduce_count(reduce_count),
        .sub_opcode(sub_opcode),
        .dbg_dot_code(dbg_dot_code),
        .dbg_norm_q_square_code(dbg_norm_q_square_code),
        .dbg_norm_k_square_code(dbg_norm_k_square_code),
        .dbg_norm_q_code(dbg_norm_q_code),
        .dbg_norm_k_code(dbg_norm_k_code),
        .dbg_denominator_raw_code(dbg_denominator_raw_code),
        .dbg_denominator_code(dbg_denominator_code),
        .dbg_cosine_code(dbg_cosine_code),
        .dbg_signed_sqrt_code(dbg_signed_sqrt_code),
        .dbg_gate_code(dbg_gate_code),
        .dbg_clamped(dbg_clamped)
    );

    always #5 clk = ~clk;

    // ---- the operand memory: one word-addressed array with three registered
    // ---- read ports LANES words wide, and one lane-masked write port.
    reg [31:0] memory [0:MEMORY_SPACE-1];
    integer lane;

    always @(posedge clk) begin
        if (r0_rd_en)
            for (lane = 0; lane < GATE_LANES; lane = lane + 1)
                r0_rd_data[32*lane +: 32] <= memory[r0_rd_addr + lane];
        if (r1_rd_en)
            for (lane = 0; lane < GATE_LANES; lane = lane + 1)
                r1_rd_data[32*lane +: 32] <= memory[r1_rd_addr + lane];
        if (r2_rd_en)
            for (lane = 0; lane < GATE_LANES; lane = lane + 1)
                r2_rd_data[32*lane +: 32] <= memory[r2_rd_addr + lane];
        for (lane = 0; lane < GATE_LANES; lane = lane + 1)
            if (out_we[lane])
                memory[out_addr + lane] <= out_data[32*lane +: 32];
    end

    // ---- vectors -----------------------------------------------------------
    reg [31:0] meta [0:7];
    reg [31:0] requests [0:CASE_LIMIT*CASE_WORDS-1];
    reg [31:0] inputs [0:CASE_LIMIT*5*VECTOR_SPACE-1];
    reg [31:0] expected [0:CASE_LIMIT*(EXPECT_SCALARS+VECTOR_SPACE)-1];
    reg [2047:0] meta_path;
    reg [2047:0] request_path;
    reg [2047:0] input_path;
    reg [2047:0] expect_path;

    integer cases;
    integer vector_limit;
    integer memory_words;
    integer sentinel;
    integer case_index;
    integer failures;
    integer checks;
    integer retiring_cases;
    integer refused_cases;
    integer clamped_cases;
    integer scalar_checks;
    integer output_word_checks;
    integer sentinel_checks;
    integer elements_reduced;
    integer output_words_written;
    integer maximum_cycles;
    integer write_beats;
    integer illegal_write_checks;
    integer initiation_interval_checks;

    integer reduce_issues;
    integer reduce_first_issue;
    integer reduce_last_issue;
    integer combine_issues;
    integer combine_first_issue;
    integer combine_last_issue;
    integer write_cycles;
    integer first_write_cycle;
    integer last_write_cycle;
    integer groups;

    integer request_base;
    integer expect_base;
    integer input_base;
    integer width;
    integer cycles;
    integer index;
    integer address;

    task automatic tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect_equal;
        input [255:0] label;
        input [31:0] got;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display("FAIL case=%0d %0s got=%h wanted=%h",
                             case_index, label, got, wanted);
            end
        end
    endtask

    //: Load one case's five operand rows and fill the output region with the
    //: sentinel, so an output word the block must NOT write is detectable.
    task automatic load_case;
        input integer selected;
        integer operand;
        integer item;
        begin
            input_base = selected * 5 * vector_limit;
            for (operand = 0; operand < 5; operand = operand + 1) begin
                case (operand)
                    0: address = requests[selected*CASE_WORDS + 1];
                    1: address = requests[selected*CASE_WORDS + 2];
                    2: address = requests[selected*CASE_WORDS + 3];
                    3: address = requests[selected*CASE_WORDS + 4];
                    default: address = requests[selected*CASE_WORDS + 5];
                endcase
                for (item = 0; item < vector_limit; item = item + 1)
                    memory[address + item] =
                        inputs[input_base + operand*vector_limit + item];
            end
            address = requests[selected*CASE_WORDS + 6];
            for (item = 0; item < vector_limit; item = item + 1)
                memory[address + item] = sentinel[31:0];
        end
    endtask

    task automatic run_case;
        input integer selected;
        integer item;
        begin
            case_index = selected;
            request_base = selected * CASE_WORDS;
            expect_base = selected * (EXPECT_SCALARS + vector_limit);
            width = requests[request_base];
            load_case(selected);

            cfg_count = requests[request_base + 0];
            cfg_h_base = requests[request_base + 1];
            cfg_key_base = requests[request_base + 2];
            cfg_value_base = requests[request_base + 3];
            cfg_q_base = requests[request_base + 4];
            cfg_k_base = requests[request_base + 5];
            cfg_out_base = requests[request_base + 6];

            //: A request is issued for exactly one cycle, and the request bus is
            //: then replaced with poison: only the latched request may influence
            //: the transaction.
            start = 1'b1;
            tick();
            start = 1'b0;
            cfg_count = 32'hffff_ffff;
            cfg_h_base = 32'hdead_0000;
            cfg_key_base = 32'hdead_0001;
            cfg_value_base = 32'hdead_0002;
            cfg_q_base = 32'hdead_0003;
            cfg_k_base = 32'hdead_0004;
            cfg_out_base = 32'hdead_0005;

            cycles = 0;
            reduce_issues = 0;
            reduce_first_issue = 0;
            reduce_last_issue = 0;
            combine_issues = 0;
            combine_first_issue = 0;
            combine_last_issue = 0;
            write_cycles = 0;
            first_write_cycle = 0;
            last_write_cycle = 0;
            while (!done && cycles < TIMEOUT_CYCLES) begin
                //: The two streaming phases are told apart by their port use:
                //: the reduction reads q and k on ports 0 and 1, and the combine
                //: also reads value on port 2.  Counting the issue cycles of each
                //: is how the II = 1 claim is MEASURED rather than asserted.
                if (r0_rd_en && !r2_rd_en) begin
                    if (reduce_issues == 0)
                        reduce_first_issue = cycles;
                    reduce_last_issue = cycles;
                    reduce_issues = reduce_issues + 1;
                end
                if (r2_rd_en) begin
                    if (combine_issues == 0)
                        combine_first_issue = cycles;
                    combine_last_issue = cycles;
                    combine_issues = combine_issues + 1;
                end
                if (|out_we) begin
                    if (write_cycles == 0)
                        first_write_cycle = cycles;
                    last_write_cycle = cycles;
                    write_cycles = write_cycles + 1;
                end
                if (busy) begin
                    for (item = 0; item < GATE_LANES; item = item + 1)
                        if (out_we[item]) begin
                            write_beats = write_beats + 1;
                            //: A write may only land inside the output region of
                            //: this case.
                            illegal_write_checks = illegal_write_checks + 1;
                            if ((out_addr + item <
                                 requests[request_base + 6]) ||
                                (out_addr + item >=
                                 requests[request_base + 6] + width)) begin
                                failures = failures + 1;
                                $display("FAIL case=%0d write outside the output region addr=%0d",
                                         selected, out_addr + item);
                            end
                        end
                end
                tick();
                cycles = cycles + 1;
            end
            if (cycles >= TIMEOUT_CYCLES) begin
                $display("FAIL case=%0d timed out", selected);
                failures = failures + 1;
            end
            if (cycles > maximum_cycles)
                maximum_cycles = cycles;

            expect_equal("error code", {24'b0, error_code},
                         expected[expect_base + 0]);
            expect_equal("refusal site", {28'b0, refusal_stage},
                         expected[expect_base + 1]);
            expect_equal("written words", out_count,
                         expected[expect_base + 2]);
            expect_equal("reduced elements", reduce_count,
                         expected[expect_base + 3]);
            expect_equal("dot code", dbg_dot_code, expected[expect_base + 4]);
            expect_equal("norm q square", dbg_norm_q_square_code,
                         expected[expect_base + 5]);
            expect_equal("norm k square", dbg_norm_k_square_code,
                         expected[expect_base + 6]);
            expect_equal("norm q", dbg_norm_q_code, expected[expect_base + 7]);
            expect_equal("norm k", dbg_norm_k_code, expected[expect_base + 8]);
            expect_equal("denominator raw", dbg_denominator_raw_code,
                         expected[expect_base + 9]);
            expect_equal("denominator", dbg_denominator_code,
                         expected[expect_base + 10]);
            expect_equal("cosine", dbg_cosine_code,
                         expected[expect_base + 11]);
            expect_equal("signed sqrt", dbg_signed_sqrt_code,
                         expected[expect_base + 12]);
            expect_equal("gate", dbg_gate_code, expected[expect_base + 13]);
            expect_equal("clamped", {31'b0, dbg_clamped},
                         expected[expect_base + 14]);
            scalar_checks = scalar_checks + 15;

            if (expected[expect_base + 15] == 32'd1) begin
                retiring_cases = retiring_cases + 1;
                //: A transaction that retires issued every group of both phases.
                //: One issue per cycle means the number of issues equals the
                //: number of groups AND they occupied that many consecutive
                //: cycles: a pipeline that stalled for one cycle would widen the
                //: span without changing the count, and one that skipped a group
                //: would change the count without widening the span.
                groups = (width + GATE_LANES - 1) / GATE_LANES;
                expect_equal("reduce issue count", reduce_issues, groups);
                expect_equal("reduce issue span",
                             reduce_last_issue - reduce_first_issue + 1, groups);
                expect_equal("combine issue count", combine_issues, groups);
                expect_equal("combine issue span",
                             combine_last_issue - combine_first_issue + 1,
                             groups);
                //: And the write port retires at the same rate it was fed, so
                //: the II is one at both ends of the combine pipeline rather
                //: than one at the operand port and something else at the
                //: result port.
                expect_equal("write span",
                             last_write_cycle - first_write_cycle + 1, groups);
                initiation_interval_checks = initiation_interval_checks + 5;
            end else begin
                refused_cases = refused_cases + 1;
            end
            if (expected[expect_base + 14] == 32'd1)
                clamped_cases = clamped_cases + 1;
            elements_reduced = elements_reduced + expected[expect_base + 3];
            output_words_written =
                output_words_written + expected[expect_base + 2];

            //: Every word of the output region: the computed codes where the
            //: block was permitted to write, and the untouched sentinel
            //: everywhere else.
            address = requests[request_base + 6];
            for (item = 0; item < vector_limit; item = item + 1) begin
                expect_equal("output word", memory[address + item],
                             expected[expect_base + EXPECT_SCALARS + item]);
                if (item < expected[expect_base + 2])
                    output_word_checks = output_word_checks + 1;
                else
                    sentinel_checks = sentinel_checks + 1;
            end
            expect_equal("idle after transaction", {31'b0, busy}, 32'b0);
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        start = 1'b0;
        cfg_count = 32'b0;
        cfg_h_base = 32'b0;
        cfg_key_base = 32'b0;
        cfg_value_base = 32'b0;
        cfg_q_base = 32'b0;
        cfg_k_base = 32'b0;
        cfg_out_base = 32'b0;
        r0_rd_data = {(GATE_LANES*32){1'b0}};
        r1_rd_data = {(GATE_LANES*32){1'b0}};
        r2_rd_data = {(GATE_LANES*32){1'b0}};
        failures = 0;
        checks = 0;
        retiring_cases = 0;
        refused_cases = 0;
        clamped_cases = 0;
        scalar_checks = 0;
        output_word_checks = 0;
        sentinel_checks = 0;
        elements_reduced = 0;
        output_words_written = 0;
        maximum_cycles = 0;
        write_beats = 0;
        illegal_write_checks = 0;
        initiation_interval_checks = 0;
        reduce_issues = 0;
        reduce_first_issue = 0;
        reduce_last_issue = 0;
        combine_issues = 0;
        combine_first_issue = 0;
        combine_last_issue = 0;
        groups = 0;
        case_index = -1;

        if (!$value$plusargs("META=%s", meta_path) ||
            !$value$plusargs("REQUESTS=%s", request_path) ||
            !$value$plusargs("INPUTS=%s", input_path) ||
            !$value$plusargs("EXPECTED=%s", expect_path))
            $fatal(1, "missing a3_v41_engram_gate vector plusargs");
        $readmemh(meta_path, meta);
        if (meta[0] !== 32'ha341_e9a7 || meta[1] !== 32'd1)
            $fatal(1, "a3_v41_engram_gate vector metadata mismatch");
        cases = meta[2];
        vector_limit = meta[3];
        memory_words = meta[6];
        sentinel = meta[7];
        if (cases <= 0 || cases > CASE_LIMIT ||
            vector_limit <= 0 || vector_limit > VECTOR_SPACE ||
            meta[4] !== CASE_WORDS || meta[5] !== EXPECT_SCALARS ||
            memory_words > MEMORY_SPACE)
            $fatal(1, "a3_v41_engram_gate vector bounds are malformed");
        $readmemh(request_path, requests, 0, cases*CASE_WORDS-1);
        $readmemh(input_path, inputs, 0, cases*5*vector_limit-1);
        $readmemh(expect_path, expected, 0,
                  cases*(EXPECT_SCALARS+vector_limit)-1);
        for (index = 0; index < MEMORY_SPACE; index = index + 1)
            memory[index] = 32'b0;

        repeat (4)
            tick();
        rst_n = 1'b1;
        repeat (2)
            tick();
        expect_equal("idle after reset", {31'b0, busy}, 32'b0);
        expect_equal("no error after reset", {24'b0, error_code}, 32'b0);
        expect_equal("no site after reset", {28'b0, refusal_stage}, 32'b0);
        //: VECTOR.ENGRAM_GATE is sub-opcode 0x0d under AM-E10.  The block reads
        //: it from ot_a3_pkg; this is the only place the number is written down
        //: independently, so the two cannot drift apart silently.
        expect_equal("sub opcode", {24'b0, sub_opcode}, 32'h0000_000d);

        for (case_index = 0; case_index < cases; case_index = case_index + 1)
            run_case(case_index);

        $display("ENGRAM_GATE_SUMMARY geometry_width=%0d geometry_lanes=%0d acc_exp_min=%0d acc_exp_max=%0d cases=%0d retiring=%0d refused=%0d clamped=%0d scalar_checks=%0d output_word_checks=%0d sentinel_checks=%0d elements_reduced=%0d output_words_written=%0d write_beats=%0d illegal_write_checks=%0d initiation_interval_checks=%0d max_cycles=%0d",
                 GATE_VECTOR_WIDTH, GATE_LANES, GATE_ACC_EXP_MIN,
                 GATE_ACC_EXP_MAX, cases, retiring_cases, refused_cases,
                 clamped_cases, scalar_checks, output_word_checks,
                 sentinel_checks, elements_reduced, output_words_written,
                 write_beats, illegal_write_checks,
                 initiation_interval_checks, maximum_cycles);
        if (failures != 0) begin
            $display("FAIL a3_v41_engram_gate failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1);
        end
        $display("PASS a3_v41_engram_gate cases=%0d checks=%0d", cases, checks);
        $finish;
    end
endmodule
