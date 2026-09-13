`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact-code scoreboard for ot_a3_vector_fp4kv_dequant, the V4.1 main-KV FP4
// dequantize block, under the contract fp4_e2m1_s16_e4m3_to_fp8_v1.
//
// Every expected word comes from runtime/reference/fp4_kv.py through
// tools/build_a3_v41_fp4kv_vectors.py.  The same vectors are driven into THREE
// instances with LANES = 1, 4 and 8, which is how the claim "a wider instance
// is a parameter change and nothing else" is checked rather than asserted: the
// dequantized words must be identical at every lane count, the retired-beat
// count must be count/LANES, and stall_cycles must be zero, which is the
// measured form of II=1.
//
// Cycle counts here are verification cost.  They are not architectural
// latency, not a frequency claim and not TPOT.
// ---------------------------------------------------------------------------
module a3_v41_fp4kv_harness #(
    parameter integer LANES     = 4,
    parameter integer LANE_SLOT = 1        // column of the per-lane expectation
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        go,
    output reg         finished,
    output reg [31:0]  failures,
    output reg [31:0]  checks,
    output reg [31:0]  legal_cases,
    output reg [31:0]  refused_cases,
    output reg [31:0]  words_compared,
    output reg [31:0]  elements_compared,
    output reg [31:0]  sentinel_words_checked,
    output reg [31:0]  worst_stall,
    output reg [31:0]  worst_cycles
);
    localparam integer CASE_MAX      = 64;
    localparam integer CASE_WORDS    = 16;
    localparam integer CODE_MAX      = 4096;
    localparam integer SCALE_MAX     = 2048;
    localparam integer PASS_MAX      = 2048;
    localparam integer EXPECTED_MAX  = 4096;
    localparam integer OUT_MAX       = 8192;
    localparam integer META_WORDS    = 12;
    localparam integer TIMEOUT       = 32768;
    localparam integer REGION_ALIGN  = 8;
    localparam integer MAX_ELEMENTS  = 2048;
    localparam integer GROUP_DEFAULT = 16;

    localparam integer A_PORT_BITS  = (LANES * 4 > 32) ? LANES * 4 : 32;
    localparam integer O_PORT_BITS  = (LANES * 8 > 32) ? LANES * 8 : 32;
    localparam integer A_PORT_WORDS = A_PORT_BITS / 32;
    localparam integer O_PORT_WORDS = O_PORT_BITS / 32;

    reg [31:0] meta        [0:META_WORDS-1];
    reg [31:0] case_words  [0:CASE_MAX*CASE_WORDS-1];
    reg [31:0] code_mem    [0:CODE_MAX-1];
    reg [31:0] scale_mem   [0:SCALE_MAX-1];
    reg [31:0] pass_mem    [0:PASS_MAX-1];
    reg [31:0] expected    [0:EXPECTED_MAX-1];
    reg [31:0] out_mem     [0:OUT_MAX-1];

    reg [2047:0] meta_path, cases_path, code_path, scale_path, pass_path,
                 expected_path;

    integer cases;
    integer sentinel;
    integer case_index;
    integer word_index;

    reg         start;
    reg [31:0]  cfg_count, cfg_group, cfg_passthrough;
    reg [31:0]  cfg_code_base, cfg_scale_base, cfg_pass_base, cfg_out_base;

    wire                    a_rd_en;
    wire [31:0]             a_rd_addr;
    reg  [A_PORT_BITS-1:0]  a_rd_data;
    wire                    s_rd_en;
    wire [31:0]             s_rd_addr;
    reg  [31:0]             s_rd_data;
    wire                    p_rd_en;
    wire [31:0]             p_rd_addr;
    reg  [O_PORT_BITS-1:0]  p_rd_data;
    wire                    out_we;
    wire [31:0]             out_addr;
    wire [O_PORT_BITS-1:0]  out_data;
    wire                    busy, done;
    wire [7:0]              error_code;
    wire [31:0]             out_count, element_count, saturation_count,
                            issue_beats, stall_cycles, scan_cycles;

    ot_a3_vector_fp4kv_dequant #(
        .LANES(LANES),
        .SCALE_GROUP_DEFAULT(GROUP_DEFAULT),
        .MAX_ELEMENTS(MAX_ELEMENTS)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(cfg_count), .cfg_group(cfg_group),
        .cfg_passthrough(cfg_passthrough),
        .cfg_code_base(cfg_code_base), .cfg_scale_base(cfg_scale_base),
        .cfg_pass_base(cfg_pass_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .s_rd_en(s_rd_en), .s_rd_addr(s_rd_addr), .s_rd_data(s_rd_data),
        .p_rd_en(p_rd_en), .p_rd_addr(p_rd_addr), .p_rd_data(p_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .element_count(element_count),
        .saturation_count(saturation_count), .issue_beats(issue_beats),
        .stall_cycles(stall_cycles), .scan_cycles(scan_cycles)
    );

    // Synchronous operand memories: one cycle of read latency, exactly the
    // contract the block's fetch pipeline is written against.
    integer port_word;
    always @(posedge clk) begin
        if (a_rd_en)
            for (port_word = 0; port_word < A_PORT_WORDS;
                 port_word = port_word + 1)
                a_rd_data[32*port_word +: 32] <=
                    code_mem[(a_rd_addr + port_word) % CODE_MAX];
        if (s_rd_en)
            s_rd_data <= scale_mem[s_rd_addr % SCALE_MAX];
        if (p_rd_en)
            for (port_word = 0; port_word < O_PORT_WORDS;
                 port_word = port_word + 1)
                p_rd_data[32*port_word +: 32] <=
                    pass_mem[(p_rd_addr + port_word) % PASS_MAX];
        if (out_we)
            for (port_word = 0; port_word < O_PORT_WORDS;
                 port_word = port_word + 1)
                out_mem[(out_addr + port_word) % OUT_MAX] <=
                    out_data[32*port_word +: 32];
    end

    task automatic tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect_equal;
        input [255:0] label;
        input [63:0]  got;
        input [63:0]  wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display("FAIL lanes=%0d case=%0d %0s got=%0d wanted=%0d",
                             LANES, case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect_word;
        input [255:0] label;
        input [31:0]  got;
        input [31:0]  wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display("FAIL lanes=%0d case=%0d %0s got=%08x wanted=%08x",
                             LANES, case_index, label, got, wanted);
            end
        end
    endtask

    task automatic run_case;
        input integer index;
        integer base;
        integer expected_error;
        integer expected_beats;
        integer expected_words;
        integer expected_saturations;
        integer expected_offset;
        integer region;
        integer cycles;
        integer item;
        begin
            case_index = index;
            base = index * CASE_WORDS;
            cfg_count       = case_words[base + 0];
            cfg_group       = case_words[base + 1];
            cfg_passthrough = case_words[base + 2];
            cfg_code_base   = case_words[base + 3];
            cfg_scale_base  = case_words[base + 4];
            cfg_pass_base   = case_words[base + 5];
            cfg_out_base    = case_words[base + 6];
            expected_offset = case_words[base + 7];
            expected_words  = case_words[base + 8];
            expected_saturations = case_words[base + 9];
            expected_error  = case_words[base + 10 + LANE_SLOT];
            expected_beats  = case_words[base + 13 + LANE_SLOT];
            region = (expected_words > REGION_ALIGN)
                     ? expected_words : REGION_ALIGN;

            expect_equal("idle before start", busy, 0);
            start = 1'b1;
            tick();
            start = 1'b0;
            cycles = 1;
            while (!done && cycles < TIMEOUT) begin
                tick();
                cycles = cycles + 1;
            end
            expect_equal("bounded completion", done, 1);
            if (cycles > worst_cycles)
                worst_cycles = cycles;
            expect_equal("error code", {56'b0, error_code},
                         {32'b0, expected_error[31:0]});
            if (stall_cycles > worst_stall)
                worst_stall = stall_cycles;

            if (expected_error == 0) begin
                legal_cases = legal_cases + 1;
                expect_equal("output word count", {32'b0, out_count},
                             {32'b0, expected_words[31:0]});
                expect_equal("element count", {32'b0, element_count},
                             {32'b0, cfg_count});
                expect_equal("saturation count", {32'b0, saturation_count},
                             {32'b0, expected_saturations[31:0]});
                // The initiation-interval claim, measured: LANES elements
                // retire per cycle and no cycle stalls once the fetch
                // pipeline is full.
                expect_equal("issue beats", {32'b0, issue_beats},
                             {32'b0, expected_beats[31:0]});
                expect_equal("stall cycles", {32'b0, stall_cycles}, 64'd0);
                for (item = 0; item < expected_words; item = item + 1) begin
                    expect_word("dequantized word",
                                out_mem[cfg_out_base + item],
                                expected[expected_offset + item]);
                    words_compared = words_compared + 1;
                end
                elements_compared = elements_compared + cfg_count;
                for (item = 0; item < REGION_ALIGN; item = item + 1) begin
                    expect_word("guard word past the destination",
                                out_mem[cfg_out_base + region + item],
                                sentinel[31:0]);
                    sentinel_words_checked = sentinel_words_checked + 1;
                end
            end else begin
                refused_cases = refused_cases + 1;
                expect_equal("refusal writes nothing", {32'b0, out_count}, 64'd0);
                expect_equal("refusal retires nothing",
                             {32'b0, element_count}, 64'd0);
                expect_equal("refusal saturates nothing",
                             {32'b0, saturation_count}, 64'd0);
                for (item = 0; item < region + REGION_ALIGN;
                     item = item + 1) begin
                    expect_word("refused destination untouched",
                                out_mem[cfg_out_base + item], sentinel[31:0]);
                    sentinel_words_checked = sentinel_words_checked + 1;
                end
            end
            $display(
                "CASE_SUMMARY lanes=%0d case=%0d error=%0d out_words=%0d elements=%0d saturations=%0d beats=%0d stalls=%0d scan=%0d",
                LANES, index, error_code, out_count, element_count,
                saturation_count, issue_beats, stall_cycles, scan_cycles
            );
        end
    endtask

    initial begin
        finished = 1'b0;
        failures = 0;
        checks = 0;
        legal_cases = 0;
        refused_cases = 0;
        words_compared = 0;
        elements_compared = 0;
        sentinel_words_checked = 0;
        worst_stall = 0;
        worst_cycles = 0;
        start = 1'b0;
        cfg_count = 0;
        cfg_group = 0;
        cfg_passthrough = 0;
        cfg_code_base = 0;
        cfg_scale_base = 0;
        cfg_pass_base = 0;
        cfg_out_base = 0;
        a_rd_data = 0;
        s_rd_data = 0;
        p_rd_data = 0;
        case_index = -1;

        if (!$value$plusargs("META=%s", meta_path) ||
            !$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("CODE=%s", code_path) ||
            !$value$plusargs("SCALE=%s", scale_path) ||
            !$value$plusargs("PASSTHROUGH=%s", pass_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path))
            $fatal(1, "missing a3_v41_fp4kv vector plusargs");
        $readmemh(meta_path, meta);
        if (meta[0] !== 32'ha341_f4d0 || meta[1] !== 32'd1)
            $fatal(1, "a3_v41_fp4kv vector metadata mismatch");
        cases    = meta[2];
        sentinel = meta[11];
        if (meta[3] !== CASE_WORDS || cases <= 0 || cases > CASE_MAX ||
            meta[4] > CODE_MAX || meta[5] > SCALE_MAX ||
            meta[6] > PASS_MAX || meta[7] > EXPECTED_MAX ||
            meta[8] > OUT_MAX || meta[9] !== MAX_ELEMENTS ||
            meta[10] !== GROUP_DEFAULT)
            $fatal(1, "a3_v41_fp4kv vector geometry does not fit the harness");
        $readmemh(cases_path, case_words, 0, cases*CASE_WORDS-1);
        $readmemh(code_path, code_mem, 0, meta[4]-1);
        $readmemh(scale_path, scale_mem, 0, meta[5]-1);
        $readmemh(pass_path, pass_mem, 0, meta[6]-1);
        $readmemh(expected_path, expected, 0, meta[7]-1);
        for (word_index = 0; word_index < OUT_MAX; word_index = word_index + 1)
            out_mem[word_index] = sentinel[31:0];

        wait (go);
        tick();
        for (case_index = 0; case_index < cases; case_index = case_index + 1)
            run_case(case_index);
        $display(
            "LANE_SUMMARY lanes=%0d cases=%0d legal=%0d refused=%0d checks=%0d failures=%0d words=%0d elements=%0d sentinels=%0d worst_stall=%0d worst_cycles=%0d",
            LANES, cases, legal_cases, refused_cases, checks, failures,
            words_compared, elements_compared, sentinel_words_checked,
            worst_stall, worst_cycles
        );
        finished = 1'b1;
    end
endmodule


module tb_a3_v41_fp4kv_dequant;
    reg clk;
    reg rst_n;
    reg go;

    wire        finished1, finished4, finished8;
    wire [31:0] failures1, checks1, legal1, refused1, words1, elements1,
                sentinels1, stall1, cycles1;
    wire [31:0] failures4, checks4, legal4, refused4, words4, elements4,
                sentinels4, stall4, cycles4;
    wire [31:0] failures8, checks8, legal8, refused8, words8, elements8,
                sentinels8, stall8, cycles8;

    a3_v41_fp4kv_harness #(.LANES(1), .LANE_SLOT(0)) h1 (
        .clk(clk), .rst_n(rst_n), .go(go), .finished(finished1),
        .failures(failures1), .checks(checks1), .legal_cases(legal1),
        .refused_cases(refused1), .words_compared(words1),
        .elements_compared(elements1), .sentinel_words_checked(sentinels1),
        .worst_stall(stall1), .worst_cycles(cycles1)
    );
    a3_v41_fp4kv_harness #(.LANES(4), .LANE_SLOT(1)) h4 (
        .clk(clk), .rst_n(rst_n), .go(go), .finished(finished4),
        .failures(failures4), .checks(checks4), .legal_cases(legal4),
        .refused_cases(refused4), .words_compared(words4),
        .elements_compared(elements4), .sentinel_words_checked(sentinels4),
        .worst_stall(stall4), .worst_cycles(cycles4)
    );
    a3_v41_fp4kv_harness #(.LANES(8), .LANE_SLOT(2)) h8 (
        .clk(clk), .rst_n(rst_n), .go(go), .finished(finished8),
        .failures(failures8), .checks(checks8), .legal_cases(legal8),
        .refused_cases(refused8), .words_compared(words8),
        .elements_compared(elements8), .sentinel_words_checked(sentinels8),
        .worst_stall(stall8), .worst_cycles(cycles8)
    );

    always #5 clk = ~clk;

    integer total_failures;
    integer total_checks;
    integer total_words;
    integer total_elements;

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        go = 1'b0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);
        go = 1'b1;
        wait (finished1 && finished4 && finished8);
        total_failures = failures1 + failures4 + failures8;
        total_checks   = checks1 + checks4 + checks8;
        total_words    = words1 + words4 + words8;
        total_elements = elements1 + elements4 + elements8;
        if (total_failures != 0) begin
            $display("FAIL a3_v41_fp4kv failures=%0d checks=%0d",
                     total_failures, total_checks);
            $fatal(1);
        end
        $display(
            "PASS a3_v41_fp4kv lane_counts=3 cases=%0d checks=%0d word_checks=%0d element_checks=%0d",
            legal1 + refused1, total_checks, total_words, total_elements
        );
        $finish;
    end
endmodule
