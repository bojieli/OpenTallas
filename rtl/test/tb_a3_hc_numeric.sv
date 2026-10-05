`timescale 1ns/1ps
// Focused checker for the reusable ABI 3.0 finite divider and the atomic
// DeepSeek HC_PRE Sinkhorn tail.  Expected values come from the independent
// Fraction-based generator, never from RTL-visible lookup logic.
module tb_a3_hc_numeric;
    localparam integer DIV_MAX = 7000;
    localparam integer SINK_MAX = 96;
    localparam integer DIV_STRIDE = 4;
    localparam integer SINK_WORDS = 16;
    localparam integer SINK_EXPECT_STRIDE = 17;

    reg clk;
    reg rst_n;

    reg div_in_valid;
    wire div_in_ready;
    reg [31:0] div_numerator;
    reg [31:0] div_denominator;
    wire div_out_valid;
    reg div_out_ready;
    wire [31:0] div_result;
    wire [1:0] div_error;

    reg sink_in_valid;
    wire sink_in_ready;
    reg [511:0] sink_matrix;
    wire sink_out_valid;
    reg sink_out_ready;
    wire [511:0] sink_result;
    wire [1:0] sink_error;

    reg [31:0] meta [0:7];
    reg [31:0] div_vectors [0:DIV_MAX*DIV_STRIDE-1];
    reg [31:0] sink_inputs [0:SINK_MAX*SINK_WORDS-1];
    reg [31:0] sink_expected [0:SINK_MAX*SINK_EXPECT_STRIDE-1];

    reg [2047:0] meta_path;
    reg [2047:0] division_path;
    reg [2047:0] sink_input_path;
    reg [2047:0] sink_expected_path;

    integer failures;
    integer checks;
    integer div_cases;
    integer sink_cases;
    integer checkpoint_cases;
    integer div_backpressure_checks;
    integer div_stall_checks;
    integer div_max_cycles;
    integer sink_backpressure_checks;
    integer sink_stall_checks;
    integer sink_max_cycles;
    integer sink_successes;
    integer sink_errors;
    integer checkpoint_words;
    integer reset_checks;
    integer case_index;
    integer word_index;

    ot_a3_fp32_div_rne u_divider (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(div_in_valid),
        .in_ready(div_in_ready),
        .numerator_code(div_numerator),
        .denominator_code(div_denominator),
        .out_valid(div_out_valid),
        .out_ready(div_out_ready),
        .result_code(div_result),
        .result_error(div_error)
    );

    ot_a3_hc_sinkhorn20_rne u_sinkhorn (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(sink_in_valid),
        .in_ready(sink_in_ready),
        .matrix_codes(sink_matrix),
        .out_valid(sink_out_valid),
        .out_ready(sink_out_ready),
        .result_codes(sink_result),
        .result_error(sink_error)
    );

    always #5 clk = ~clk;

    task automatic tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect_equal;
        input [255:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 20)
                    $display(
                        "FAIL %0s got=%016x wanted=%016x",
                        label, got, wanted
                    );
            end
        end
    endtask

    task automatic run_division;
        input integer index;
        integer base;
        integer cycles;
        integer stall_cycles;
        integer attempt;
        reg [31:0] expected_result;
        reg [1:0] expected_error;
        reg [31:0] held_result;
        reg [1:0] held_error;
        begin
            base = index * DIV_STRIDE;
            expected_result = div_vectors[base + 2];
            expected_error = div_vectors[base + 3][1:0];
            div_out_ready = 1'b0;
            div_in_valid = 1'b0;
            repeat (index % 3)
                tick();
            while (!div_in_ready)
                tick();
            div_numerator = div_vectors[base];
            div_denominator = div_vectors[base + 1];
            div_in_valid = 1'b1;
            tick();
            div_in_valid = 1'b0;
            cycles = 1;

            // A finite, nonzero request enters the iterative search.  Present
            // a poison second request briefly and prove it cannot be accepted.
            if (expected_error != 2'd1 &&
                div_vectors[base][30:0] != 0) begin
                div_in_valid = 1'b1;
                div_numerator = 32'h7fc00001;
                div_denominator = 32'h00000000;
                for (attempt = 0; attempt < 2; attempt = attempt + 1) begin
                    expect_equal("divider busy in_ready", div_in_ready, 0);
                    div_backpressure_checks = div_backpressure_checks + 1;
                    tick();
                    cycles = cycles + 1;
                end
                div_in_valid = 1'b0;
            end

            while (!div_out_valid && cycles < 64) begin
                tick();
                cycles = cycles + 1;
            end
            expect_equal("divider bounded completion", div_out_valid, 1);
            if (cycles > div_max_cycles)
                div_max_cycles = cycles;
            expect_equal("divider error", div_error, expected_error);
            expect_equal("divider result", div_result, expected_result);

            held_result = div_result;
            held_error = div_error;
            stall_cycles = (index % 17 == 0) ? 3 : 1;
            for (attempt = 0; attempt < stall_cycles; attempt = attempt + 1) begin
                tick();
                expect_equal("divider stalled valid", div_out_valid, 1);
                expect_equal("divider stalled result", div_result, held_result);
                expect_equal("divider stalled error", div_error, held_error);
                expect_equal("divider stalled in_ready", div_in_ready, 0);
                div_stall_checks = div_stall_checks + 4;
            end
            div_out_ready = 1'b1;
            tick();
            expect_equal("divider output consumed", div_out_valid, 0);
            div_out_ready = 1'b0;
        end
    endtask

    task automatic load_sink_input;
        input integer index;
        integer item;
        begin
            for (item = 0; item < SINK_WORDS; item = item + 1)
                sink_matrix[32*item +: 32] =
                    sink_inputs[index*SINK_WORDS + item];
        end
    endtask

    task automatic run_sinkhorn;
        input integer index;
        integer expected_base;
        integer cycles;
        integer stall_cycles;
        integer attempt;
        integer item;
        reg [1:0] expected_error;
        reg [511:0] held_result;
        reg [1:0] held_error;
        begin
            expected_base = index * SINK_EXPECT_STRIDE;
            expected_error = sink_expected[expected_base + 16][1:0];
            sink_out_ready = 1'b0;
            sink_in_valid = 1'b0;
            repeat (index % 2)
                tick();
            while (!sink_in_ready)
                tick();
            load_sink_input(index);
            sink_in_valid = 1'b1;
            tick();
            sink_in_valid = 1'b0;
            cycles = 1;

            if (expected_error == 0) begin
                // Change the input bus while valid is refused.  The private
                // matrix accepted above must remain the only active request.
                sink_in_valid = 1'b1;
                sink_matrix[31:0] = 32'hbf800000;
                for (attempt = 0; attempt < 2; attempt = attempt + 1) begin
                    expect_equal("sinkhorn busy in_ready", sink_in_ready, 0);
                    sink_backpressure_checks = sink_backpressure_checks + 1;
                    tick();
                    cycles = cycles + 1;
                end
                sink_in_valid = 1'b0;
            end

            while (!sink_out_valid && cycles < 30000) begin
                tick();
                cycles = cycles + 1;
            end
            expect_equal("sinkhorn bounded completion", sink_out_valid, 1);
            if (cycles > sink_max_cycles)
                sink_max_cycles = cycles;
            expect_equal("sinkhorn error", sink_error, expected_error);
            if (expected_error == 0)
                sink_successes = sink_successes + 1;
            else
                sink_errors = sink_errors + 1;
            for (item = 0; item < SINK_WORDS; item = item + 1) begin
                expect_equal(
                    "sinkhorn output word",
                    sink_result[32*item +: 32],
                    sink_expected[expected_base + item]
                );
                if (index < checkpoint_cases)
                    checkpoint_words = checkpoint_words + 1;
            end

            held_result = sink_result;
            held_error = sink_error;
            stall_cycles = (index % 11 == 0) ? 3 : 1;
            for (attempt = 0; attempt < stall_cycles; attempt = attempt + 1) begin
                tick();
                expect_equal("sinkhorn stalled valid", sink_out_valid, 1);
                expect_equal("sinkhorn stalled error", sink_error, held_error);
                for (item = 0; item < SINK_WORDS; item = item + 1)
                    expect_equal(
                        "sinkhorn stalled output",
                        sink_result[32*item +: 32],
                        held_result[32*item +: 32]
                    );
                sink_stall_checks = sink_stall_checks + 18;
            end
            sink_out_ready = 1'b1;
            tick();
            expect_equal("sinkhorn output consumed", sink_out_valid, 0);
            sink_out_ready = 1'b0;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        div_in_valid = 1'b0;
        div_numerator = 0;
        div_denominator = 0;
        div_out_ready = 1'b0;
        sink_in_valid = 1'b0;
        sink_matrix = 0;
        sink_out_ready = 1'b0;
        failures = 0;
        checks = 0;
        div_backpressure_checks = 0;
        div_stall_checks = 0;
        div_max_cycles = 0;
        sink_backpressure_checks = 0;
        sink_stall_checks = 0;
        sink_max_cycles = 0;
        sink_successes = 0;
        sink_errors = 0;
        checkpoint_words = 0;
        reset_checks = 0;

        if (!$value$plusargs("META=%s", meta_path) ||
            !$value$plusargs("DIVISION=%s", division_path) ||
            !$value$plusargs("SINK_INPUT=%s", sink_input_path) ||
            !$value$plusargs("SINK_EXPECTED=%s", sink_expected_path))
            $fatal(1, "missing HC numeric vector plusargs");
        $readmemh(meta_path, meta);
        if (meta[0] !== 32'ha3c20020 || meta[1] !== 1)
            $fatal(1, "HC numeric vector metadata mismatch");
        div_cases = meta[2];
        sink_cases = meta[3];
        checkpoint_cases = meta[4];
        if (div_cases <= 0 || div_cases > DIV_MAX ||
            sink_cases <= 0 || sink_cases > SINK_MAX)
            $fatal(1, "HC numeric vector count outside testbench capacity");
        $readmemh(
            division_path, div_vectors, 0, div_cases*DIV_STRIDE-1
        );
        $readmemh(
            sink_input_path, sink_inputs, 0, sink_cases*SINK_WORDS-1
        );
        $readmemh(
            sink_expected_path, sink_expected, 0,
            sink_cases*SINK_EXPECT_STRIDE-1
        );

        repeat (4)
            tick();
        rst_n = 1'b1;
        repeat (2)
            tick();
        expect_equal("divider ready after reset", div_in_ready, 1);
        expect_equal("sinkhorn ready after reset", sink_in_ready, 1);

        for (case_index = 0; case_index < div_cases;
             case_index = case_index + 1)
            run_division(case_index);

        // Reset an in-flight finite divide and require clean recovery.
        div_numerator = 32'h3f800000;
        div_denominator = 32'h40400000;
        div_in_valid = 1'b1;
        tick();
        div_in_valid = 1'b0;
        repeat (4)
            tick();
        rst_n = 1'b0;
        tick();
        expect_equal("divider reset clears valid", div_out_valid, 0);
        reset_checks = reset_checks + 1;
        rst_n = 1'b1;
        tick();
        expect_equal("divider reset restores ready", div_in_ready, 1);
        reset_checks = reset_checks + 1;
        run_division(2);

        for (case_index = 0; case_index < sink_cases;
             case_index = case_index + 1)
            run_sinkhorn(case_index);

        // Reset a partially normalized matrix and prove no partial result can
        // escape.  Then rerun checkpoint case zero through completion.
        load_sink_input(0);
        sink_in_valid = 1'b1;
        tick();
        sink_in_valid = 1'b0;
        repeat (40)
            tick();
        rst_n = 1'b0;
        tick();
        expect_equal("sinkhorn reset clears valid", sink_out_valid, 0);
        reset_checks = reset_checks + 1;
        rst_n = 1'b1;
        tick();
        expect_equal("sinkhorn reset restores ready", sink_in_ready, 1);
        reset_checks = reset_checks + 1;
        run_sinkhorn(0);

        $display(
            "DIV_SUMMARY cases=%0d backpressure=%0d stalls=%0d max_cycles=%0d",
            div_cases, div_backpressure_checks, div_stall_checks,
            div_max_cycles
        );
        $display(
            "SINK_SUMMARY cases=%0d successes=%0d errors=%0d checkpoint_words=%0d backpressure=%0d stalls=%0d max_cycles=%0d",
            sink_cases, sink_successes, sink_errors, checkpoint_words,
            sink_backpressure_checks, sink_stall_checks, sink_max_cycles
        );
        $display(
            "RESET_SUMMARY checks=%0d", reset_checks
        );
        if (failures != 0)
            $fatal(1, "HC numeric failures=%0d checks=%0d", failures, checks);
        $display("PASS a3_hc_numeric checks=%0d", checks);
        $finish;
    end
endmodule
