`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Independent ready/valid scoreboard for the exact ABI 3.0 DeepSeek HC_PRE
// tile scheduler.  This testbench verifies work-coordinate coverage only.  It
// neither supplies nor accepts precomputed HC_PRE arithmetic results and makes
// no model-token, EOS, architectural-latency, or TPOT claim.
// ---------------------------------------------------------------------------
module tb_a3_mhc_pre_tile_scheduler;
    parameter integer CASES = 22;
    parameter integer CONFIG_WORDS = 128;
    parameter integer CASE_WORDS = 144;
    parameter integer TIMEOUT_CYCLES = 1200000;

    reg [31:0] case_mem [0:CASES*CASE_WORDS-1];
    reg [1023:0] cases_path;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg start = 1'b0;
    reg tile_ready = 1'b0;
    reg [CONFIG_WORDS*32-1:0] config_words = 0;

    wire tile_valid;
    wire [1:0] tile_kind;
    wire [31:0] tile_token_base;
    wire [31:0] tile_field_base;
    wire [31:0] tile_k_base;
    wire [31:0] tile_active_tokens;
    wire [31:0] tile_active_fields;
    wire [31:0] tile_active_k;
    wire [63:0] tile_logical_work;
    wire [63:0] tile_output_base;
    wire [31:0] tile_output_row_stride;
    wire tile_last;
    wire busy;
    wire done;
    wire [7:0] error_code;
    wire [63:0] projection_tile_count;
    wire [63:0] commit_tile_count;
    wire [63:0] logical_fma_count;
    wire [63:0] logical_output_count;

    ot_a3_vector_mhc_pre_tile_scheduler dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .config_words(config_words),
        .tile_valid(tile_valid),
        .tile_ready(tile_ready),
        .tile_kind(tile_kind),
        .tile_token_base(tile_token_base),
        .tile_field_base(tile_field_base),
        .tile_k_base(tile_k_base),
        .tile_active_tokens(tile_active_tokens),
        .tile_active_fields(tile_active_fields),
        .tile_active_k(tile_active_k),
        .tile_logical_work(tile_logical_work),
        .tile_output_base(tile_output_base),
        .tile_output_row_stride(tile_output_row_stride),
        .tile_last(tile_last),
        .busy(busy),
        .done(done),
        .error_code(error_code),
        .projection_tile_count(projection_tile_count),
        .commit_tile_count(commit_tile_count),
        .logical_fma_count(logical_fma_count),
        .logical_output_count(logical_output_count)
    );

    integer failures;
    integer checks;
    integer ci;
    integer wi;
    integer guard;
    integer ready_choice;
    integer stall_held;
    integer expected_admitted;
    integer expected_error;
    integer expected_finished;
    integer expected_kind;
    integer case_stalls;
    integer case_cycles;

    reg [31:0] tokens_total;
    reg [31:0] tile_rows;
    reg [31:0] tile_cols;
    reg [31:0] tile_depth;
    reg [31:0] expected_token_base;
    reg [31:0] expected_field_base;
    reg [31:0] expected_k_base;
    reg [31:0] expected_fields_total;
    reg [31:0] expected_k_total;
    reg [31:0] expected_active_tokens;
    reg [31:0] expected_active_fields;
    reg [31:0] expected_active_k;
    reg [31:0] expected_stride;
    reg [63:0] expected_tile_work;
    reg [63:0] expected_output_base;
    reg expected_last;

    reg [63:0] expected_projection_tiles;
    reg [63:0] expected_commit_tiles;
    reg [63:0] expected_total_tiles;
    reg [63:0] expected_fmas;
    reg [63:0] expected_outputs;
    reg [63:0] observed_projection_tiles;
    reg [63:0] observed_commit_tiles;
    reg [63:0] observed_total_tiles;
    reg [63:0] observed_fmas;
    reg [63:0] observed_outputs;

    reg [1:0] held_kind;
    reg [31:0] held_token_base;
    reg [31:0] held_field_base;
    reg [31:0] held_k_base;
    reg [31:0] held_active_tokens;
    reg [31:0] held_active_fields;
    reg [31:0] held_active_k;
    reg [63:0] held_logical_work;
    reg [63:0] held_output_base;
    reg [31:0] held_output_stride;
    reg held_last;
    reg [63:0] held_projection_count;
    reg [63:0] held_commit_count;
    reg [63:0] held_fma_count;
    reg [63:0] held_output_count;

    task expect32;
        input [255:0] label;
        input [31:0] got;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d %0s: got %0d (%h), wanted %0d (%h)",
                             ci, label, got, got, wanted, wanted);
            end
        end
    endtask

    task expect64;
        input [255:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d %0s: got %0d, wanted %0d",
                             ci, label, got, wanted);
            end
        end
    endtask

    task expect1;
        input [255:0] label;
        input got;
        input wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d %0s: got %b, wanted %b",
                             ci, label, got, wanted);
            end
        end
    endtask

    task load_case;
        input integer case_index;
        integer base;
        begin
            base = case_index * CASE_WORDS;
            for (wi = 0; wi < CONFIG_WORDS; wi = wi + 1)
                config_words[wi*32 +: 32] = case_mem[base + wi];
            expected_admitted = case_mem[base + 128];
            expected_error = case_mem[base + 129];
            expected_projection_tiles = {
                case_mem[base + 131], case_mem[base + 130]
            };
            expected_commit_tiles = {
                case_mem[base + 133], case_mem[base + 132]
            };
            expected_total_tiles = {
                case_mem[base + 135], case_mem[base + 134]
            };
            expected_fmas = {
                case_mem[base + 137], case_mem[base + 136]
            };
            expected_outputs = {
                case_mem[base + 139], case_mem[base + 138]
            };
            tokens_total = case_mem[base + 1];
            tile_rows = case_mem[base + 55];
            tile_cols = case_mem[base + 56];
            tile_depth = case_mem[base + 57];
        end
    endtask

    task initialize_scoreboard;
        begin
            expected_kind = 0;
            expected_token_base = 0;
            expected_field_base = 0;
            expected_k_base = 0;
            expected_finished = 0;
            observed_projection_tiles = 0;
            observed_commit_tiles = 0;
            observed_total_tiles = 0;
            observed_fmas = 0;
            observed_outputs = 0;
        end
    endtask

    task calculate_expected_tile;
        begin
            if (expected_kind == 0) begin
                expected_fields_total = 24;
                expected_k_total = 16384;
            end else if (expected_kind == 1) begin
                expected_fields_total = 8;
                expected_k_total = 1;
            end else begin
                expected_fields_total = 16;
                expected_k_total = 1;
            end

            if (tokens_total - expected_token_base > tile_rows)
                expected_active_tokens = tile_rows;
            else
                expected_active_tokens = tokens_total - expected_token_base;
            if (expected_fields_total - expected_field_base > tile_cols)
                expected_active_fields = tile_cols;
            else
                expected_active_fields =
                    expected_fields_total - expected_field_base;
            if (expected_k_total - expected_k_base > tile_depth)
                expected_active_k = tile_depth;
            else
                expected_active_k = expected_k_total - expected_k_base;

            if (expected_kind == 0) begin
                expected_tile_work =
                    {32'd0, expected_active_tokens} *
                    {32'd0, expected_active_fields};
                expected_tile_work = expected_tile_work *
                    {32'd0, expected_active_k};
                expected_stride = 0;
                expected_output_base = 0;
            end else begin
                expected_tile_work = 0;
                expected_stride = (expected_kind == 1) ? 8 : 16;
                expected_output_base =
                    ({32'd0, expected_token_base} *
                     {32'd0, expected_stride}) +
                    {32'd0, expected_field_base};
            end
            expected_last =
                (expected_kind == 2) &&
                (expected_token_base + expected_active_tokens == tokens_total) &&
                (expected_field_base + expected_active_fields ==
                 expected_fields_total);
        end
    endtask

    task advance_expected_tile;
        begin
            if (expected_k_base + expected_active_k < expected_k_total) begin
                expected_k_base = expected_k_base + expected_active_k;
            end else if (expected_field_base + expected_active_fields <
                         expected_fields_total) begin
                expected_k_base = 0;
                expected_field_base =
                    expected_field_base + expected_active_fields;
            end else if (expected_token_base + expected_active_tokens <
                         tokens_total) begin
                expected_k_base = 0;
                expected_field_base = 0;
                expected_token_base =
                    expected_token_base + expected_active_tokens;
            end else if (expected_kind < 2) begin
                expected_kind = expected_kind + 1;
                expected_k_base = 0;
                expected_field_base = 0;
                expected_token_base = 0;
            end else begin
                expected_finished = 1;
            end
        end
    endtask

    task check_accepted_tile;
        begin
            calculate_expected_tile;
            expect32("tile kind", {30'd0, tile_kind}, expected_kind);
            expect32("token origin", tile_token_base, expected_token_base);
            expect32("field origin", tile_field_base, expected_field_base);
            expect32("K origin", tile_k_base, expected_k_base);
            expect32("active tokens", tile_active_tokens,
                     expected_active_tokens);
            expect32("active fields", tile_active_fields,
                     expected_active_fields);
            expect32("active K", tile_active_k, expected_active_k);
            expect64("logical work", tile_logical_work,
                     expected_tile_work);
            expect64("output base", tile_output_base,
                     expected_output_base);
            expect32("output row stride", tile_output_row_stride,
                     expected_stride);
            expect1("last marker", tile_last, expected_last);

            observed_total_tiles = observed_total_tiles + 1;
            if (expected_kind == 0) begin
                observed_projection_tiles = observed_projection_tiles + 1;
                observed_fmas = observed_fmas + expected_tile_work;
            end else begin
                observed_commit_tiles = observed_commit_tiles + 1;
                observed_outputs = observed_outputs +
                    ({32'd0, expected_active_tokens} *
                     {32'd0, expected_active_fields});
            end
            advance_expected_tile;
        end
    endtask

    task capture_stalled_tile;
        begin
            held_kind = tile_kind;
            held_token_base = tile_token_base;
            held_field_base = tile_field_base;
            held_k_base = tile_k_base;
            held_active_tokens = tile_active_tokens;
            held_active_fields = tile_active_fields;
            held_active_k = tile_active_k;
            held_logical_work = tile_logical_work;
            held_output_base = tile_output_base;
            held_output_stride = tile_output_row_stride;
            held_last = tile_last;
            held_projection_count = projection_tile_count;
            held_commit_count = commit_tile_count;
            held_fma_count = logical_fma_count;
            held_output_count = logical_output_count;
        end
    endtask

    task check_stalled_tile;
        begin
            expect1("stalled valid", tile_valid, 1'b1);
            expect32("stalled kind", {30'd0, tile_kind},
                     {30'd0, held_kind});
            expect32("stalled token origin", tile_token_base,
                     held_token_base);
            expect32("stalled field origin", tile_field_base,
                     held_field_base);
            expect32("stalled K origin", tile_k_base, held_k_base);
            expect32("stalled active tokens", tile_active_tokens,
                     held_active_tokens);
            expect32("stalled active fields", tile_active_fields,
                     held_active_fields);
            expect32("stalled active K", tile_active_k, held_active_k);
            expect64("stalled logical work", tile_logical_work,
                     held_logical_work);
            expect64("stalled output base", tile_output_base,
                     held_output_base);
            expect32("stalled output stride", tile_output_row_stride,
                     held_output_stride);
            expect1("stalled last marker", tile_last, held_last);
            expect64("stalled projection counter", projection_tile_count,
                     held_projection_count);
            expect64("stalled commit counter", commit_tile_count,
                     held_commit_count);
            expect64("stalled FMA counter", logical_fma_count,
                     held_fma_count);
            expect64("stalled output counter", logical_output_count,
                     held_output_count);
        end
    endtask

    task run_case;
        input integer case_index;
        begin
            ci = case_index;
            load_case(case_index);
            initialize_scoreboard;
            case_stalls = 0;
            case_cycles = 0;
            stall_held = 0;
            tile_ready = 0;

            @(negedge clk);
            start = 1;
            @(posedge clk);
            @(negedge clk);
            start = 0;

            guard = 0;
            while (!done && guard < TIMEOUT_CYCLES) begin
                if (stall_held)
                    check_stalled_tile;

                ready_choice = ((guard % 7) != 2) &&
                               ((guard % 13) != 5);
                if (tile_valid) begin
                    expect1("tile from admitted case", expected_admitted, 1'b1);
                    if (ready_choice) begin
                        tile_ready = 1;
                        check_accepted_tile;
                        stall_held = 0;
                    end else begin
                        tile_ready = 0;
                        capture_stalled_tile;
                        stall_held = 1;
                        case_stalls = case_stalls + 1;
                    end
                end else begin
                    tile_ready = 0;
                    stall_held = 0;
                end
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
                case_cycles = case_cycles + 1;
            end
            tile_ready = 0;

            if (guard >= TIMEOUT_CYCLES) begin
                failures = failures + 1;
                $display("FAIL case %0d timed out after %0d cycles",
                         ci, guard);
            end
            expect1("terminal done", done, 1'b1);
            expect1("terminal busy", busy, 1'b0);
            expect1("terminal tile valid", tile_valid, 1'b0);
            expect32("terminal error", {24'd0, error_code}, expected_error);
            expect64("projection counter", projection_tile_count,
                     expected_projection_tiles);
            expect64("commit counter", commit_tile_count,
                     expected_commit_tiles);
            expect64("FMA counter", logical_fma_count, expected_fmas);
            expect64("output counter", logical_output_count, expected_outputs);
            expect64("scoreboard projection tiles",
                     observed_projection_tiles, expected_projection_tiles);
            expect64("scoreboard commit tiles", observed_commit_tiles,
                     expected_commit_tiles);
            expect64("scoreboard total tiles", observed_total_tiles,
                     expected_total_tiles);
            expect64("scoreboard FMAs", observed_fmas, expected_fmas);
            expect64("scoreboard outputs", observed_outputs,
                     expected_outputs);
            expect1("scoreboard final coordinate", expected_finished,
                    expected_admitted);

            $display("CASE_SUMMARY index=%0d admitted=%0d error=%0d tiles=%0d projection=%0d commit=%0d fmas=%0d outputs=%0d stalls=%0d cycles=%0d",
                     ci, expected_admitted, error_code,
                     observed_total_tiles, observed_projection_tiles,
                     observed_commit_tiles, observed_fmas, observed_outputs,
                     case_stalls, case_cycles);

            @(posedge clk);
            @(negedge clk);
            expect1("done pulse width", done, 1'b0);
        end
    endtask

    task run_active_reset;
        integer accepted_before_reset;
        integer reset_stalls;
        begin
            ci = 3;
            load_case(3);
            initialize_scoreboard;
            accepted_before_reset = 0;
            reset_stalls = 0;
            guard = 0;
            stall_held = 0;
            tile_ready = 0;

            @(negedge clk);
            start = 1;
            @(posedge clk);
            @(negedge clk);
            start = 0;
            while (accepted_before_reset < 37 && guard < 200) begin
                if (stall_held)
                    check_stalled_tile;
                ready_choice = (guard % 5) != 1;
                if (!tile_valid) begin
                    failures = failures + 1;
                    if (failures < 40)
                        $display("FAIL active reset lost tile_valid at %0d",
                                 accepted_before_reset);
                    tile_ready = 0;
                    stall_held = 0;
                end else if (ready_choice) begin
                    tile_ready = 1;
                    check_accepted_tile;
                    accepted_before_reset = accepted_before_reset + 1;
                    stall_held = 0;
                end else begin
                    tile_ready = 0;
                    capture_stalled_tile;
                    stall_held = 1;
                    reset_stalls = reset_stalls + 1;
                end
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            tile_ready = 0;
            expect32("reset accepted prefix", accepted_before_reset, 37);
            expect1("busy before active reset", busy, 1'b1);
            expect64("projection prefix before reset", projection_tile_count,
                     37);
            expect64("commit prefix before reset", commit_tile_count, 0);

            rst_n = 0;
            #1;
            expect1("busy cleared by active reset", busy, 1'b0);
            expect1("valid cleared by active reset", tile_valid, 1'b0);
            expect1("done cleared by active reset", done, 1'b0);
            expect32("error cleared by active reset", {24'd0, error_code}, 0);
            expect64("projection cleared by active reset",
                     projection_tile_count, 0);
            expect64("commit cleared by active reset", commit_tile_count, 0);
            expect64("FMAs cleared by active reset", logical_fma_count, 0);
            expect64("outputs cleared by active reset", logical_output_count, 0);
            repeat (2) @(posedge clk);
            @(negedge clk);
            rst_n = 1;
            $display("RESET_SUMMARY accepted=%0d stalls=%0d",
                     accepted_before_reset, reset_stalls);
        end
    endtask

    initial begin
        failures = 0;
        checks = 0;
        if (!$value$plusargs("CASES=%s", cases_path))
            cases_path = "testdata/rtl/a3_mhc_pre_tiles/cases.hex";
        $readmemh(cases_path, case_mem);

        repeat (4) @(posedge clk);
        @(negedge clk);
        rst_n = 1;

        run_active_reset;
        for (ci = 0; ci < CASES; ci = ci + 1)
            run_case(ci);

        if (failures != 0) begin
            $display("FAIL a3_mhc_pre_tile failures=%0d checks=%0d",
                     failures, checks);
            $fatal(1);
        end
        $display("PASS a3_mhc_pre_tile checks=%0d", checks);
        $finish;
    end
endmodule
