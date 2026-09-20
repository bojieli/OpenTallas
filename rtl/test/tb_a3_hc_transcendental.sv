`timescale 1ns/1ps
// Independent exact-code scoreboard for the reusable HC_PRE exponential and
// direct logistic-sigmoid engine.  Simulation cycles are verification cost,
// not architectural model latency or TPOT.
module tb_a3_hc_transcendental;
    parameter integer CASES = 4200;
    parameter integer CASE_WORDS = 4;
    //: The engine's wide arithmetic is SEQUENTIAL: a series term is a carry-save
    //: multiply plus a restoring divide plus two register stages, and the sigmoid
    //: transform is one subtract per clock over a 328-bit numerator. A request
    //: therefore takes some 2,850 cycles rather than the seventy the single-cycle
    //: expression form took, which is the trade that let the module synthesise at
    //: all. This limit is the bench refusing to hang, not a latency target -- and
    //: the summary still publishes the observed maximum, so a regression that made
    //: a request slower would show up there rather than passing silently.
    parameter integer TIMEOUT_CYCLES = 8192;

    reg [31:0] cases [0:CASES*CASE_WORDS-1];
    reg [1023:0] cases_path;
    reg clk;
    reg rst_n = 1'b0;
    initial clk = 1'b0;
    always #5 clk = ~clk;

    reg in_valid = 1'b0;
    wire in_ready;
    reg operation = 1'b0;
    reg [31:0] argument_code = 0;
    wire out_valid;
    reg out_ready = 1'b0;
    wire [31:0] result_code;
    wire [1:0] result_error;

    ot_a3_fp32_transcendental_cr_rne dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .operation(operation),
        .argument_code(argument_code),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .result_code(result_code),
        .result_error(result_error)
    );

    integer ci;
    integer base;
    integer guard;
    integer failures;
    integer checks;
    integer accepted;
    integer refused;
    integer exp_cases;
    integer sigmoid_cases;
    integer stalls;
    integer maximum_cycles;
    integer reset_cycles;
    reg expected_operation;
    reg [31:0] expected_argument;
    reg [31:0] expected_result;
    reg [1:0] expected_error;
    reg [31:0] held_result;
    reg [1:0] held_error;

    task expect1;
        input [255:0] label;
        input got;
        input wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 30)
                    $display("FAIL case %0d %0s got=%b wanted=%b",
                             ci, label, got, wanted);
            end
        end
    endtask

    task expect2;
        input [255:0] label;
        input [1:0] got;
        input [1:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 30)
                    $display("FAIL case %0d %0s got=%0d wanted=%0d",
                             ci, label, got, wanted);
            end
        end
    endtask

    task expect32;
        input [255:0] label;
        input [31:0] got;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 30)
                    $display("FAIL case %0d %0s got=%h wanted=%h arg=%h op=%0d",
                             ci, label, got, wanted,
                             expected_argument, expected_operation);
            end
        end
    endtask

    task load_case;
        input integer index;
        begin
            base = index * CASE_WORDS;
            expected_operation = cases[base][0];
            expected_argument = cases[base + 1];
            expected_result = cases[base + 2];
            expected_error = cases[base + 3][1:0];
        end
    endtask

    task run_case;
        input integer index;
        integer hold_cycles;
        begin
            ci = index;
            load_case(index);
            operation = expected_operation;
            argument_code = expected_argument;
            out_ready = 0;
            @(negedge clk);
            expect1("input ready", in_ready, 1'b1);
            in_valid = 1;
            @(posedge clk);
            @(negedge clk);
            in_valid = 0;
            // Inputs are not a sideband authority after the handshake.
            operation = ~expected_operation;
            argument_code = expected_argument ^ 32'ha5a5_5a5a;

            guard = 0;
            while (!out_valid && guard < TIMEOUT_CYCLES) begin
                expect1("busy input refusal", in_ready, 1'b0);
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            if (guard > maximum_cycles)
                maximum_cycles = guard;
            if (guard >= TIMEOUT_CYCLES) begin
                failures = failures + 1;
                $display("FAIL case %0d timeout arg=%h op=%0d",
                         ci, expected_argument, expected_operation);
            end
            expect1("result valid", out_valid, 1'b1);
            expect2("result error", result_error, expected_error);
            expect32("result code", result_code, expected_result);

            hold_cycles = (index % 17 == 0) ? 3 :
                          (index % 5 == 0) ? 1 : 0;
            held_result = result_code;
            held_error = result_error;
            repeat (hold_cycles) begin
                expect1("stalled valid", out_valid, 1'b1);
                expect32("stalled result", result_code, held_result);
                expect2("stalled error", result_error, held_error);
                stalls = stalls + 1;
                @(posedge clk);
                @(negedge clk);
            end
            out_ready = 1;
            @(posedge clk);
            @(negedge clk);
            out_ready = 0;
            expect1("result consumed", out_valid, 1'b0);

            if (expected_operation)
                sigmoid_cases = sigmoid_cases + 1;
            else
                exp_cases = exp_cases + 1;
            if (expected_error == 0)
                accepted = accepted + 1;
            else
                refused = refused + 1;
        end
    endtask

    task run_active_reset;
        begin
            ci = -1;
            operation = 0;
            argument_code = 32'hc120_0000;
            out_ready = 0;
            @(negedge clk);
            in_valid = 1;
            @(posedge clk);
            @(negedge clk);
            in_valid = 0;
            repeat (23) begin
                expect1("reset precondition busy", in_ready, 1'b0);
                expect1("reset precondition no result", out_valid, 1'b0);
                reset_cycles = reset_cycles + 1;
                @(posedge clk);
                @(negedge clk);
            end
            rst_n = 0;
            #1;
            expect1("reset clears result", out_valid, 1'b0);
            expect32("reset clears code", result_code, 0);
            expect2("reset clears error", result_error, 0);
            repeat (2) @(posedge clk);
            @(negedge clk);
            rst_n = 1;
            #1;
            expect1("ready after reset", in_ready, 1'b1);
        end
    endtask

    initial begin
        failures = 0;
        checks = 0;
        accepted = 0;
        refused = 0;
        exp_cases = 0;
        sigmoid_cases = 0;
        stalls = 0;
        maximum_cycles = 0;
        reset_cycles = 0;
        if (!$value$plusargs("CASES=%s", cases_path))
            cases_path = "testdata/rtl/a3_hc_transcendental/cases.hex";
        $readmemh(cases_path, cases);

        repeat (4) @(posedge clk);
        @(negedge clk);
        rst_n = 1;
        run_active_reset;
        for (ci = 0; ci < CASES; ci = ci + 1)
            run_case(ci);

        $display("TRANS_SUMMARY cases=%0d exp=%0d sigmoid=%0d accepted=%0d refused=%0d stalls=%0d max_cycles=%0d reset_cycles=%0d",
                 CASES, exp_cases, sigmoid_cases, accepted, refused,
                 stalls, maximum_cycles, reset_cycles);
        if (failures != 0) begin
            $display("FAIL a3_hc_transcendental failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1);
        end
        $display("PASS a3_hc_transcendental checks=%0d", checks);
        $finish;
    end
endmodule
