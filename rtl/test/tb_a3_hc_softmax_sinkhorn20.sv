`timescale 1ns/1ps
// Exact-code and protocol scoreboard for the atomic HC stable-softmax plus
// Sinkhorn-20 composition. Expected values come from independent exact
// arithmetic, never from RTL-visible lookup logic. Controller cycles are
// verification cost, not an architectural latency or TPOT measurement.
module tb_a3_hc_softmax_sinkhorn20;
    localparam integer CASE_MAX = 900;
    localparam integer INPUT_WORDS = 16;
    localparam integer EXPECTED_WORDS = 17;
    localparam integer TIMEOUT_CYCLES = 32768;

    reg clk;
    reg rst_n;
    reg in_valid;
    wire in_ready;
    reg [511:0] matrix_codes;
    wire out_valid;
    reg out_ready;
    wire [511:0] result_codes;
    wire [1:0] result_error;

    reg [31:0] meta [0:7];
    reg [31:0] matrix_inputs [0:CASE_MAX*INPUT_WORDS-1];
    reg [31:0] matrix_expected [0:CASE_MAX*EXPECTED_WORDS-1];
    reg [2047:0] meta_path;
    reg [2047:0] input_path;
    reg [2047:0] expected_path;

    integer total_cases;
    integer checkpoint_total;
    integer directed_total;
    integer expected_success_total;
    integer expected_error_total;
    integer t1_case;
    integer run_start;
    integer run_cases;
    integer run_end;
    integer case_index;
    integer failures;
    integer checks;
    integer successes;
    integer errors;
    integer argument_errors;
    integer overflow_errors;
    integer checkpoint_cases;
    integer directed_cases;
    integer checkpoint_words;
    integer t1_words;
    integer sinkhorn_entries;
    integer output_stalls;
    integer maximum_cycles;
    integer reset_cycles;
    integer active_resets;
    integer busy_atomic_checks;

    ot_a3_hc_stable_softmax_sinkhorn20_rne dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .matrix_codes(matrix_codes),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .result_codes(result_codes),
        .result_error(result_error)
    );

    always #5 clk = ~clk;

    task automatic tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect1;
        input [255:0] label;
        input got;
        input wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display("FAIL case=%0d %0s got=%b wanted=%b",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect2;
        input [255:0] label;
        input [1:0] got;
        input [1:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display("FAIL case=%0d %0s got=%0d wanted=%0d",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect512;
        input [255:0] label;
        input [511:0] got;
        input [511:0] wanted;
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

    task automatic check_private_output;
        begin
            checks = checks + 1;
            busy_atomic_checks = busy_atomic_checks + 1;
            if ({in_ready, out_valid, result_error, result_codes} !== 0) begin
                failures = failures + 1;
                if (failures <= 24)
                    $display(
                        "FAIL case=%0d in-flight state became visible ready=%b valid=%b error=%0d matrix=%h",
                        case_index, in_ready, out_valid, result_error,
                        result_codes
                    );
            end
        end
    endtask

    task automatic load_input;
        input integer index;
        integer item;
        begin
            for (item = 0; item < INPUT_WORDS; item = item + 1)
                matrix_codes[32*item +: 32] =
                    matrix_inputs[index*INPUT_WORDS + item];
        end
    endtask

    task automatic run_case;
        input integer index;
        integer expected_base;
        integer cycles;
        integer hold_cycles;
        integer attempt;
        integer item;
        reg [1:0] wanted_error;
        reg saw_sinkhorn;
        reg [511:0] held_result;
        reg [1:0] held_error;
        begin
            case_index = index;
            expected_base = index * EXPECTED_WORDS;
            wanted_error = matrix_expected[expected_base + 16][1:0];
            out_ready = 1'b0;
            in_valid = 1'b0;
            repeat (index % 2)
                tick();
            while (!in_ready)
                tick();

            load_input(index);
            in_valid = 1'b1;
            tick();
            cycles = 1;
            saw_sinkhorn = 1'b0;

            // Keep presenting a poison second request throughout the active
            // transaction. The wrapper and both child blocks must retain the
            // accepted matrix and refuse this replacement until final commit.
            matrix_codes = {16{32'h7fc0_0001}};
            while (!out_valid && cycles < TIMEOUT_CYCLES) begin
                if (dut.sinkhorn_in_valid && dut.sinkhorn_in_ready)
                    saw_sinkhorn = 1'b1;
                check_private_output();
                tick();
                cycles = cycles + 1;
            end
            in_valid = 1'b0;
            expect1("bounded completion", out_valid, 1);
            if (cycles > maximum_cycles)
                maximum_cycles = cycles;
            expect2("result error", result_error, wanted_error);
            expect1("Sinkhorn stage entry", saw_sinkhorn,
                    wanted_error == 0);
            if (wanted_error == 0) begin
                successes = successes + 1;
                if (saw_sinkhorn)
                    sinkhorn_entries = sinkhorn_entries + 1;
            end else begin
                errors = errors + 1;
                if (wanted_error == 1)
                    argument_errors = argument_errors + 1;
                else if (wanted_error == 2)
                    overflow_errors = overflow_errors + 1;
            end
            if (index < checkpoint_total) begin
                checkpoint_cases = checkpoint_cases + 1;
                checkpoint_words = checkpoint_words + INPUT_WORDS;
            end else begin
                directed_cases = directed_cases + 1;
            end
            for (item = 0; item < INPUT_WORDS; item = item + 1) begin
                expect512(
                    "composed output word",
                    {{480{1'b0}}, result_codes[32*item +: 32]},
                    {{480{1'b0}}, matrix_expected[expected_base + item]}
                );
                if (index == t1_case)
                    t1_words = t1_words + 1;
            end
            if (wanted_error != 0)
                expect512("failure is atomically all zero", result_codes, 0);

            held_result = result_codes;
            held_error = result_error;
            hold_cycles = (index % 19 == 0) ? 3 :
                          (index % 7 == 0) ? 1 : 0;
            for (attempt = 0; attempt < hold_cycles; attempt = attempt + 1) begin
                tick();
                expect1("stalled output valid", out_valid, 1);
                expect512("stalled output matrix", result_codes, held_result);
                expect2("stalled output error", result_error, held_error);
                expect1("stalled output refuses input", in_ready, 0);
                output_stalls = output_stalls + 1;
            end
            out_ready = 1'b1;
            tick();
            out_ready = 1'b0;
            expect1("output consumed", out_valid, 0);
            expect512("consumed output matrix clears", result_codes, 0);
            expect2("consumed output error clears", result_error, 0);
            expect1("ready after output consumption", in_ready, 1);
        end
    endtask

    task automatic run_active_reset_in_sinkhorn;
        integer guard;
        integer attempt;
        begin
            case_index = -1;
            while (!in_ready)
                tick();
            load_input(t1_case);
            in_valid = 1'b1;
            tick();
            matrix_codes = {16{32'h7fc0_0001}};
            guard = 0;
            while (!(dut.sinkhorn_in_valid && dut.sinkhorn_in_ready) &&
                   guard < TIMEOUT_CYCLES) begin
                check_private_output();
                tick();
                guard = guard + 1;
            end
            if (guard >= TIMEOUT_CYCLES)
                $fatal(1, "active-reset probe never reached Sinkhorn");
            check_private_output();
            tick();
            for (attempt = 0; attempt < 31; attempt = attempt + 1) begin
                check_private_output();
                reset_cycles = reset_cycles + 1;
                tick();
            end
            rst_n = 1'b0;
            #1;
            in_valid = 1'b0;
            expect1("active reset clears valid", out_valid, 0);
            expect512("active reset clears matrix", result_codes, 0);
            expect2("active reset clears error", result_error, 0);
            repeat (2)
                tick();
            rst_n = 1'b1;
            #1;
            expect1("ready after active reset", in_ready, 1);
            active_resets = active_resets + 1;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        in_valid = 1'b0;
        matrix_codes = 0;
        out_ready = 1'b0;
        failures = 0;
        checks = 0;
        successes = 0;
        errors = 0;
        argument_errors = 0;
        overflow_errors = 0;
        checkpoint_cases = 0;
        directed_cases = 0;
        checkpoint_words = 0;
        t1_words = 0;
        sinkhorn_entries = 0;
        output_stalls = 0;
        maximum_cycles = 0;
        reset_cycles = 0;
        active_resets = 0;
        busy_atomic_checks = 0;
        case_index = -1;

        if (!$value$plusargs("META=%s", meta_path) ||
            !$value$plusargs("INPUT=%s", input_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path))
            $fatal(1, "missing composed HC vector plusargs");
        $readmemh(meta_path, meta);
        if (meta[0] !== 32'ha3c5_2020 || meta[1] !== 1)
            $fatal(1, "composed HC vector metadata mismatch");
        total_cases = meta[2];
        checkpoint_total = meta[3];
        directed_total = meta[4];
        expected_success_total = meta[5];
        expected_error_total = meta[6];
        t1_case = meta[7];
        if (!$value$plusargs("START_CASE=%d", run_start))
            run_start = 0;
        if (!$value$plusargs("CASE_COUNT=%d", run_cases))
            run_cases = total_cases - run_start;
        run_end = run_start + run_cases;
        if (total_cases <= 0 || total_cases > CASE_MAX ||
            checkpoint_total < 1 || checkpoint_total > total_cases ||
            directed_total != total_cases - checkpoint_total ||
            expected_success_total + expected_error_total != total_cases ||
            t1_case < 0 || t1_case >= checkpoint_total ||
            run_start < 0 || run_cases <= 0 || run_end > total_cases)
            $fatal(1, "composed HC vector counts are malformed");
        $readmemh(
            input_path, matrix_inputs, 0, total_cases*INPUT_WORDS-1
        );
        $readmemh(
            expected_path, matrix_expected, 0,
            total_cases*EXPECTED_WORDS-1
        );

        repeat (4)
            tick();
        rst_n = 1'b1;
        repeat (2)
            tick();
        expect1("input ready after reset", in_ready, 1);
        expect1("output invalid after reset", out_valid, 0);
        expect512("matrix zero after reset", result_codes, 0);
        expect2("error zero after reset", result_error, 0);

        if (run_start == 0)
            run_active_reset_in_sinkhorn();
        for (case_index = run_start; case_index < run_end;
             case_index = case_index + 1)
            run_case(case_index);

        $display("COMPOSE_SUMMARY start=%0d cases=%0d checkpoint=%0d directed=%0d success=%0d errors=%0d argument_errors=%0d overflow_errors=%0d checkpoint_words=%0d t1_words=%0d sinkhorn_entries=%0d stalls=%0d max_cycles=%0d reset_cycles=%0d active_resets=%0d busy_atomic_checks=%0d",
                 run_start, run_cases, checkpoint_cases, directed_cases,
                 successes, errors, argument_errors, overflow_errors,
                 checkpoint_words, t1_words, sinkhorn_entries, output_stalls,
                 maximum_cycles, reset_cycles, active_resets,
                 busy_atomic_checks);
        if (failures != 0) begin
            $display("FAIL a3_hc_softmax_sinkhorn20 failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1);
        end
        $display("PASS a3_hc_softmax_sinkhorn20 checks=%0d", checks);
        $finish;
    end
endmodule
