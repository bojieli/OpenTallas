`timescale 1ns/1ps
// Exact arithmetic, descriptor-parity, and atomic-protocol scoreboard for the
// fixed T=1 DeepSeek HC_PRE integration.  All expected values are supplied by
// independent exact arithmetic and authenticated checkpoint vectors.  The
// observed controller cycles are verification cost, never token latency/TPOT.
module tb_a3_hc_pre_t1;
    localparam integer WIDTH = 16384;
    localparam integer FIELDS = 24;
    localparam integer CONFIG_WORDS = 128;
    localparam integer FMA_CASE_MAX = 5000;
    localparam integer FMA_CASE_WORDS = 5;
    localparam integer EXPECTED_WORDS = 74;
    localparam integer TIMEOUT_CYCLES = 400000;

    reg clk;
    reg rst_n;
    reg in_valid;
    wire in_ready;
    reg [CONFIG_WORDS*32-1:0] config_words;
    reg [767:0] base_codes;
    reg [95:0] scale_codes;

    wire hidden_rd_en;
    wire [13:0] hidden_rd_k;
    reg [15:0] hidden_rd_data;
    wire weight_rd_en;
    wire [4:0] weight_rd_field_base;
    wire [13:0] weight_rd_k;
    reg [255:0] weight_rd_data;

    wire out_valid;
    reg out_ready;
    wire [255:0] result_weight_codes;
    wire [511:0] result_combination_codes;
    wire [7:0] result_error;
    wire [63:0] scheduler_projection_tiles;
    wire [63:0] scheduler_commit_tiles;
    wire [63:0] scheduler_logical_fmas;
    wire [63:0] scheduler_logical_outputs;
    wire [31:0] arithmetic_square_count;
    wire [31:0] arithmetic_reduction_add_count;
    wire [31:0] arithmetic_fma_count;

    reg [31:0] meta [0:7];
    reg [31:0] fma_mem [0:FMA_CASE_MAX*FMA_CASE_WORDS-1];
    reg [15:0] hidden_mem [0:WIDTH-1];
    reg [31:0] projection_mem [0:FIELDS*WIDTH-1];
    reg [31:0] base_mem [0:FIELDS-1];
    reg [31:0] scale_mem [0:2];
    reg [31:0] expected_mem [0:EXPECTED_WORDS-1];
    reg [31:0] rom_config_mem [0:CONFIG_WORDS-1];
    reg [31:0] hbm_config_mem [0:CONFIG_WORDS-1];

    reg [2047:0] meta_path;
    reg [2047:0] fma_path;
    reg [2047:0] hidden_path;
    reg [2047:0] projection_path;
    reg [2047:0] base_path;
    reg [2047:0] scale_path;
    reg [2047:0] expected_path;
    reg [2047:0] rom_config_path;
    reg [2047:0] hbm_config_path;

    integer failures;
    integer checks;
    integer fma_case_count;
    integer fma_successes;
    integer fma_argument_errors;
    integer fma_overflow_errors;
    integer checkpoint_words;
    integer parity_words;
    integer atomic_private_checks;
    integer output_stalls;
    integer active_resets;
    integer descriptor_errors;
    integer arithmetic_errors;
    integer rom_cycles;
    integer hbm_cycles;
    integer coefficient_error_cycles;
    integer case_index;
    integer item;
    integer lane;
    integer address;
    reg [33:0] fma_observed;
    reg [255:0] rom_weight_codes;
    reg [511:0] rom_combination_codes;
    reg [255:0] held_weight_codes;
    reg [511:0] held_combination_codes;
    reg [7:0] held_error;

    ot_a3_hc_pre_t1_descriptor_rne dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .config_words(config_words),
        .base_codes(base_codes),
        .scale_codes(scale_codes),
        .hidden_rd_en(hidden_rd_en),
        .hidden_rd_k(hidden_rd_k),
        .hidden_rd_data(hidden_rd_data),
        .weight_rd_en(weight_rd_en),
        .weight_rd_field_base(weight_rd_field_base),
        .weight_rd_k(weight_rd_k),
        .weight_rd_data(weight_rd_data),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .result_weight_codes(result_weight_codes),
        .result_combination_codes(result_combination_codes),
        .result_error(result_error),
        .scheduler_projection_tiles(scheduler_projection_tiles),
        .scheduler_commit_tiles(scheduler_commit_tiles),
        .scheduler_logical_fmas(scheduler_logical_fmas),
        .scheduler_logical_outputs(scheduler_logical_outputs),
        .arithmetic_square_count(arithmetic_square_count),
        .arithmetic_reduction_add_count(arithmetic_reduction_add_count),
        .arithmetic_fma_count(arithmetic_fma_count)
    );

    always #5 clk = ~clk;

    // Two-cycle synchronous-style memory response.  The engines issue an
    // address, wait one cycle, and consume these registered words next.
    always @(posedge clk) begin
        if (hidden_rd_en)
            hidden_rd_data <= hidden_mem[hidden_rd_k];
        if (weight_rd_en) begin
            for (lane = 0; lane < 8; lane = lane + 1) begin
                address = (weight_rd_field_base + lane) * WIDTH + weight_rd_k;
                weight_rd_data[32*lane +: 32] <= projection_mem[address];
            end
        end
    end

    task automatic tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task automatic expect1;
        input [383:0] label;
        input got;
        input wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 32)
                    $display("FAIL case=%0d %0s got=%b wanted=%b",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect8;
        input [383:0] label;
        input [7:0] got;
        input [7:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 32)
                    $display("FAIL case=%0d %0s got=%0d wanted=%0d",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect32;
        input [383:0] label;
        input [31:0] got;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 32)
                    $display("FAIL case=%0d %0s got=%08h wanted=%08h",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic expect64;
        input [383:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures <= 32)
                    $display("FAIL case=%0d %0s got=%0d wanted=%0d",
                             case_index, label, got, wanted);
            end
        end
    endtask

    task automatic check_private_outputs;
        begin
            atomic_private_checks = atomic_private_checks + 1;
            checks = checks + 1;
            if ({out_valid, result_error, result_weight_codes,
                 result_combination_codes} !== 0) begin
                failures = failures + 1;
                if (failures <= 32)
                    $display(
                        "FAIL case=%0d private output became visible valid=%b error=%0d weights=%h combination=%h",
                        case_index, out_valid, result_error,
                        result_weight_codes, result_combination_codes
                    );
            end
        end
    endtask

    task automatic load_transaction;
        input integer profile;
        input integer poison_base;
        integer word;
        begin
            config_words = 0;
            for (word = 0; word < CONFIG_WORDS; word = word + 1)
                config_words[32*word +: 32] = profile == 0
                    ? rom_config_mem[word] : hbm_config_mem[word];
            base_codes = 0;
            for (word = 0; word < FIELDS; word = word + 1)
                base_codes[32*word +: 32] = base_mem[word];
            if (poison_base != 0)
                base_codes[31:0] = 32'h7fc0_0001;
            scale_codes = 0;
            for (word = 0; word < 3; word = word + 1)
                scale_codes[32*word +: 32] = scale_mem[word];
        end
    endtask

    task automatic poison_live_inputs;
        begin
            config_words = {CONFIG_WORDS{32'hffff_ffff}};
            base_codes = {24{32'h7fc0_0001}};
            scale_codes = {3{32'h7f80_0000}};
        end
    endtask

    task automatic check_projection_witness;
        integer word;
        begin
            expect32("mean square", dut.projection_mean, expected_mem[0]);
            expect32("inverse RMS", dut.projection_inverse, expected_mem[1]);
            checkpoint_words = checkpoint_words + 2;
            for (word = 0; word < FIELDS; word = word + 1) begin
                expect32("raw projection",
                         dut.projection_raw[32*word +: 32],
                         expected_mem[2 + word]);
                expect32("normalized projection",
                         dut.projection_normalized[32*word +: 32],
                         expected_mem[26 + word]);
                checkpoint_words = checkpoint_words + 2;
            end
        end
    endtask

    task automatic check_success_output;
        input integer profile;
        integer word;
        begin
            expect8("successful result error", result_error, 0);
            for (word = 0; word < 8; word = word + 1) begin
                expect32("weight coefficient",
                         result_weight_codes[32*word +: 32],
                         expected_mem[50 + word]);
                checkpoint_words = checkpoint_words + 1;
            end
            for (word = 0; word < 16; word = word + 1) begin
                expect32("combination coefficient",
                         result_combination_codes[32*word +: 32],
                         expected_mem[58 + word]);
                checkpoint_words = checkpoint_words + 1;
            end
            expect32("square work count", arithmetic_square_count, 16384);
            expect32("balanced reduction count",
                     arithmetic_reduction_add_count, 16383);
            expect32("fused accumulation count", arithmetic_fma_count, 393216);
            expect64("scheduler logical FMAs", scheduler_logical_fmas, 393216);
            expect64("scheduler logical outputs", scheduler_logical_outputs, 24);
            if (profile == 0) begin
                //: AM-E9 TILE COUNTS, AND THEY ARE THE SAME ON BOTH STORES.
                //:
                //: These were 16 and 2 on ROM against 49,152 and 3 on HBM -- a
                //: 3,072x difference in what the cycle model charges for
                //: IDENTICAL work, which is the asymmetry AM-E9 exists to remove
                //: (CHIP_ARCHITECTURE_DESIGN section 7.2: one graph lowered
                //: through two private tile policies handed the ROM side a 2x
                //: tensor-lane and 16x column-group advantage).
                //:
                //: Under the shared rule in compiler/backends/schedule_rule.py
                //: both stores now carry tile_cols 4 and tile_depth 1 with
                //: tile_rows equal to the surface, so both walk
                //: ceil(1/tile_rows) * ceil(24/4) * ceil(16384/1) = 98,304
                //: projection tiles and ceil(8/4) + ceil(16/4) = 6 commit tiles.
                //: The engine's walk was already right; these numbers were the
                //: pre-amendment ones.
                //:
                //: The logical work is unchanged and still checked above --
                //: 393,216 FMAs and 24 outputs -- so this is a change in tiling
                //: granularity and not in what the engine computes.
                expect64("ROM projection tiles", scheduler_projection_tiles, 98304);
                expect64("ROM commit tiles", scheduler_commit_tiles, 6);
            end else begin
                expect64("HBM projection tiles", scheduler_projection_tiles, 98304);
                expect64("HBM commit tiles", scheduler_commit_tiles, 6);
                for (word = 0; word < 8; word = word + 1) begin
                    expect32("ROM/HBM weight parity",
                             result_weight_codes[32*word +: 32],
                             rom_weight_codes[32*word +: 32]);
                    parity_words = parity_words + 1;
                end
                for (word = 0; word < 16; word = word + 1) begin
                    expect32("ROM/HBM combination parity",
                             result_combination_codes[32*word +: 32],
                             rom_combination_codes[32*word +: 32]);
                    parity_words = parity_words + 1;
                end
            end
        end
    endtask

    task automatic run_success;
        input integer profile;
        integer cycles;
        integer saw_projection;
        integer stall;
        begin
            case_index = profile;
            while (!in_ready)
                tick();
            load_transaction(profile, 0);
            out_ready = 1'b0;
            in_valid = 1'b1;
            tick();
            expect1("busy refuses replacement", in_ready, 1'b0);
            poison_live_inputs();
            cycles = 1;
            saw_projection = 0;
            while (!out_valid && cycles < TIMEOUT_CYCLES) begin
                expect1("busy refuses poison request", in_ready, 1'b0);
                if (dut.projection_out_valid && !saw_projection) begin
                    expect8("projection stage error",
                            {6'b0, dut.projection_error}, 0);
                    check_projection_witness();
                    saw_projection = 1;
                end
                check_private_outputs();
                tick();
                cycles = cycles + 1;
            end
            in_valid = 1'b0;
            expect1("bounded successful completion", out_valid, 1'b1);
            expect1("projection witness observed", saw_projection != 0, 1'b1);
            check_success_output(profile);
            if (profile == 0) begin
                rom_cycles = cycles;
                rom_weight_codes = result_weight_codes;
                rom_combination_codes = result_combination_codes;
            end else begin
                hbm_cycles = cycles;
            end

            held_weight_codes = result_weight_codes;
            held_combination_codes = result_combination_codes;
            held_error = result_error;
            for (stall = 0; stall < 4; stall = stall + 1) begin
                tick();
                expect1("stalled output remains valid", out_valid, 1'b1);
                expect1("stalled output refuses input", in_ready, 1'b0);
                expect8("stalled output error stable", result_error, held_error);
                for (item = 0; item < 8; item = item + 1)
                    expect32("stalled weight stable",
                             result_weight_codes[32*item +: 32],
                             held_weight_codes[32*item +: 32]);
                for (item = 0; item < 16; item = item + 1)
                    expect32("stalled combination stable",
                             result_combination_codes[32*item +: 32],
                             held_combination_codes[32*item +: 32]);
                output_stalls = output_stalls + 1;
            end
            out_ready = 1'b1;
            tick();
            out_ready = 1'b0;
            expect1("successful output consumed", out_valid, 1'b0);
            expect1("ready after successful output", in_ready, 1'b1);
            expect8("consumed result error clears", result_error, 0);
            for (item = 0; item < 8; item = item + 1)
                expect32("consumed weight clears",
                         result_weight_codes[32*item +: 32], 0);
            for (item = 0; item < 16; item = item + 1)
                expect32("consumed combination clears",
                         result_combination_codes[32*item +: 32], 0);
        end
    endtask

    task automatic consume_error;
        input [7:0] wanted_error;
        integer stall;
        begin
            expect1("error output valid", out_valid, 1'b1);
            expect8("error code", result_error, wanted_error);
            for (item = 0; item < 8; item = item + 1)
                expect32("error weight is zero",
                         result_weight_codes[32*item +: 32], 0);
            for (item = 0; item < 16; item = item + 1)
                expect32("error combination is zero",
                         result_combination_codes[32*item +: 32], 0);
            for (stall = 0; stall < 3; stall = stall + 1) begin
                tick();
                expect1("stalled error remains valid", out_valid, 1'b1);
                expect8("stalled error remains stable", result_error, wanted_error);
                expect1("stalled error refuses input", in_ready, 1'b0);
                output_stalls = output_stalls + 1;
            end
            out_ready = 1'b1;
            tick();
            out_ready = 1'b0;
            expect1("error output consumed once", out_valid, 1'b0);
            expect8("consumed error clears", result_error, 0);
            expect1("ready after error", in_ready, 1'b1);
        end
    endtask

    task automatic run_active_token_error;
        begin
            case_index = 10;
            load_transaction(0, 0);
            config_words[63:32] = 2;
            in_valid = 1'b1;
            tick();
            in_valid = 1'b0;
            consume_error(8'd21);
            descriptor_errors = descriptor_errors + 1;
        end
    endtask

    task automatic run_hidden_error;
        integer cycles;
        begin
            case_index = 11;
            hidden_mem[0] = 16'h7f80;
            load_transaction(0, 0);
            in_valid = 1'b1;
            tick();
            poison_live_inputs();
            cycles = 1;
            while (!out_valid && cycles < TIMEOUT_CYCLES) begin
                expect1("hidden-error busy refusal", in_ready, 1'b0);
                check_private_outputs();
                tick();
                cycles = cycles + 1;
            end
            in_valid = 1'b0;
            consume_error(8'd32);
            hidden_mem[0] = 16'h0000;
            // Restore the authentic first word from disk without rereading the
            // entire memory: all four stream copies are identical.
            hidden_mem[0] = hidden_mem[4096];
            arithmetic_errors = arithmetic_errors + 1;
        end
    endtask

    task automatic run_coefficient_error;
        integer cycles;
        begin
            case_index = 12;
            load_transaction(0, 1);
            in_valid = 1'b1;
            tick();
            poison_live_inputs();
            cycles = 1;
            while (!out_valid && cycles < TIMEOUT_CYCLES) begin
                expect1("coefficient-error busy refusal", in_ready, 1'b0);
                check_private_outputs();
                tick();
                cycles = cycles + 1;
            end
            in_valid = 1'b0;
            coefficient_error_cycles = cycles;
            consume_error(8'd32);
            // A historical wrapper defect emitted this error twice.  Keep an
            // extra idle cycle to prove the single-completion invariant.
            tick();
            expect1("coefficient error has no duplicate", out_valid, 1'b0);
            expect1("coefficient error leaves input ready", in_ready, 1'b1);
            arithmetic_errors = arithmetic_errors + 1;
        end
    endtask

    task automatic run_active_reset;
        integer cycle;
        begin
            case_index = 13;
            load_transaction(0, 0);
            in_valid = 1'b1;
            tick();
            poison_live_inputs();
            for (cycle = 0; cycle < 31; cycle = cycle + 1) begin
                check_private_outputs();
                tick();
            end
            in_valid = 1'b0;
            rst_n = 1'b0;
            #1;
            expect1("active reset clears output valid", out_valid, 1'b0);
            expect8("active reset clears error", result_error, 0);
            expect64("active reset clears scheduler projection count",
                     scheduler_projection_tiles, 0);
            expect32("active reset clears arithmetic square count",
                     arithmetic_square_count, 0);
            repeat (2)
                tick();
            rst_n = 1'b1;
            #1;
            expect1("ready after active reset", in_ready, 1'b1);
            active_resets = active_resets + 1;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        in_valid = 1'b0;
        config_words = 0;
        base_codes = 0;
        scale_codes = 0;
        hidden_rd_data = 0;
        weight_rd_data = 0;
        out_ready = 1'b0;
        failures = 0;
        checks = 0;
        fma_successes = 0;
        fma_argument_errors = 0;
        fma_overflow_errors = 0;
        checkpoint_words = 0;
        parity_words = 0;
        atomic_private_checks = 0;
        output_stalls = 0;
        active_resets = 0;
        descriptor_errors = 0;
        arithmetic_errors = 0;
        rom_cycles = 0;
        hbm_cycles = 0;
        coefficient_error_cycles = 0;
        case_index = -1;
        rom_weight_codes = 0;
        rom_combination_codes = 0;

        if (!$value$plusargs("META=%s", meta_path) ||
            !$value$plusargs("FMA=%s", fma_path) ||
            !$value$plusargs("HIDDEN=%s", hidden_path) ||
            !$value$plusargs("PROJECTION=%s", projection_path) ||
            !$value$plusargs("BASE=%s", base_path) ||
            !$value$plusargs("SCALE=%s", scale_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path) ||
            !$value$plusargs("ROM_CONFIG=%s", rom_config_path) ||
            !$value$plusargs("HBM_CONFIG=%s", hbm_config_path))
            $fatal(1, "missing HC_PRE T=1 vector plusargs");

        $readmemh(meta_path, meta);
        if (meta[0] !== 32'ha3f4_0001 || meta[1] !== 1 ||
            meta[3] !== FMA_CASE_WORDS || meta[4] !== EXPECTED_WORDS ||
            meta[5] !== WIDTH || meta[6] !== FIELDS || meta[7] !== 8)
            $fatal(1, "HC_PRE T=1 vector metadata mismatch");
        fma_case_count = meta[2];
        if (fma_case_count <= 0 || fma_case_count > FMA_CASE_MAX)
            $fatal(1, "HC_PRE T=1 FMA vector count is malformed");
        $readmemh(fma_path, fma_mem, 0,
                  fma_case_count*FMA_CASE_WORDS-1);
        $readmemh(hidden_path, hidden_mem);
        $readmemh(projection_path, projection_mem);
        $readmemh(base_path, base_mem);
        $readmemh(scale_path, scale_mem);
        $readmemh(expected_path, expected_mem);
        $readmemh(rom_config_path, rom_config_mem);
        $readmemh(hbm_config_path, hbm_config_mem);

        // The pure combinational function is checked before any transaction.
        for (case_index = 0; case_index < fma_case_count;
             case_index = case_index + 1) begin
            fma_observed =
                ot_a3_hc_projection_pkg::bf16_fp32_fp32_product_add_rne(
                    fma_mem[case_index*FMA_CASE_WORDS],
                    fma_mem[case_index*FMA_CASE_WORDS + 1][15:0],
                    fma_mem[case_index*FMA_CASE_WORDS + 2]
                );
            expect32("fused product-add result", fma_observed[31:0],
                     fma_mem[case_index*FMA_CASE_WORDS + 3]);
            expect8("fused product-add error", {6'b0, fma_observed[33:32]},
                    fma_mem[case_index*FMA_CASE_WORDS + 4][7:0]);
            if (fma_observed[33:32] == 0)
                fma_successes = fma_successes + 1;
            else if (fma_observed[33:32] == 1)
                fma_argument_errors = fma_argument_errors + 1;
            else if (fma_observed[33:32] == 2)
                fma_overflow_errors = fma_overflow_errors + 1;
        end

        repeat (4)
            tick();
        rst_n = 1'b1;
        repeat (2)
            tick();
        expect1("ready after reset", in_ready, 1'b1);
        check_private_outputs();

        run_active_reset();
        run_success(0);
        run_success(1);
        run_active_token_error();
        run_hidden_error();
        run_coefficient_error();

        $display("HC_PRE_T1_SUMMARY fma_cases=%0d fma_success=%0d fma_argument_errors=%0d fma_overflow_errors=%0d checkpoint_words=%0d parity_words=%0d atomic_private_checks=%0d output_stalls=%0d active_resets=%0d descriptor_errors=%0d arithmetic_errors=%0d rom_cycles=%0d hbm_cycles=%0d coefficient_error_cycles=%0d",
                 fma_case_count, fma_successes, fma_argument_errors,
                 fma_overflow_errors, checkpoint_words, parity_words,
                 atomic_private_checks, output_stalls, active_resets,
                 descriptor_errors, arithmetic_errors, rom_cycles, hbm_cycles,
                 coefficient_error_cycles);
        if (failures != 0) begin
            $display("FAIL a3_hc_pre_t1 failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1);
        end
        $display("PASS a3_hc_pre_t1 checks=%0d", checks);
        $finish;
    end
endmodule
