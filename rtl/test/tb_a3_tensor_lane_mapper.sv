`timescale 1ns/1ps
// Source-bound dual-simulator testbench for the ABI 3.0 lane mapper.
// Every accepted logical coordinate is checked exactly once at handshake.
module tb_a3_tensor_lane_mapper;
    parameter integer MAX_CASES = 64;
    parameter integer CASE_WORDS = 12;
    parameter integer MAX_WAVES = 4096;
    parameter integer WAVE_WORDS = 8;
    parameter integer MAX_LOGICAL_OUTPUTS = 300000;
    parameter integer TIMEOUT_CYCLES = 200000;

    reg [63:0] case_mem [0:MAX_CASES*CASE_WORDS-1];
    reg [63:0] wave_mem [0:MAX_WAVES*WAVE_WORDS-1];
    reg [255:0] mask_mem [0:MAX_WAVES-1];
    reg seen [0:MAX_LOGICAL_OUTPUTS-1];

    reg [2047:0] case_path;
    reg [2047:0] wave_path;
    reg [2047:0] mask_path;
    integer case_count;
    integer expected_total_waves;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg start = 1'b0;
    reg [31:0] cfg_rows = 32'd0;
    reg [31:0] cfg_cols = 32'd0;
    reg [31:0] cfg_tile_rows = 32'd0;
    reg [31:0] cfg_tile_cols = 32'd0;
    reg [31:0] cfg_issue_window = 32'd0;
    wire wave_valid;
    reg wave_ready = 1'b0;
    wire [31:0] wave_row_base;
    wire [31:0] wave_col_base;
    wire [8:0] wave_rows;
    wire [8:0] wave_cols_per_row;
    wire [8:0] wave_active_lanes;
    wire [255:0] lane_valid;
    wire [27:0] issue_group_active_counts;
    wire wave_last;
    wire busy;
    wire done;
    wire [7:0] error_code;
    wire [63:0] wave_count;
    wire [63:0] logical_output_count;
    wire [63:0] active_lane_slots;
    wire [63:0] masked_lane_slots;
    wire [63:0] row_folded_output_count;

    ot_a3_tensor_lane_mapper dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_rows(cfg_rows),
        .cfg_cols(cfg_cols),
        .cfg_tile_rows(cfg_tile_rows),
        .cfg_tile_cols(cfg_tile_cols),
        .cfg_issue_window(cfg_issue_window),
        .wave_valid(wave_valid),
        .wave_ready(wave_ready),
        .wave_row_base(wave_row_base),
        .wave_col_base(wave_col_base),
        .wave_rows(wave_rows),
        .wave_cols_per_row(wave_cols_per_row),
        .wave_active_lanes(wave_active_lanes),
        .lane_valid(lane_valid),
        .issue_group_active_counts(issue_group_active_counts),
        .wave_last(wave_last),
        .busy(busy),
        .done(done),
        .error_code(error_code),
        .wave_count(wave_count),
        .logical_output_count(logical_output_count),
        .active_lane_slots(active_lane_slots),
        .masked_lane_slots(masked_lane_slots),
        .row_folded_output_count(row_folded_output_count)
    );

    integer failures;
    integer checks;
    integer ci;
    integer j;
    integer guard;
    integer local_wave;
    integer global_wave;
    integer total_observed_waves;
    integer total_observed_outputs;
    integer logical_index;
    integer local_row;
    integer local_col;
    integer lane_index;
    integer case_base;
    integer expected_wave_start;
    integer expected_case_waves;
    integer expected_case_outputs;
    reg case_had_stall;
    reg stall_previous;
    reg [31:0] stalled_row_base;
    reg [31:0] stalled_col_base;
    reg [8:0] stalled_rows;
    reg [8:0] stalled_cols;
    reg [8:0] stalled_active;
    reg [255:0] stalled_mask;
    reg [27:0] stalled_groups;
    reg stalled_last;

    task expect64;
        input [383:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                $display(
                    "FAIL case=%0d wave=%0d %0s got=%h wanted=%h",
                    ci, local_wave, label, got, wanted
                );
            end
        end
    endtask

    task expect256;
        input [383:0] label;
        input [255:0] got;
        input [255:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                $display(
                    "FAIL case=%0d wave=%0d %0s got=%h wanted=%h",
                    ci, local_wave, label, got, wanted
                );
            end
        end
    endtask

    task check_wave_metadata;
        input integer wave_index;
        integer base;
        begin
            base = wave_index * WAVE_WORDS;
            expect64("source case", ci, wave_mem[base]);
            expect64("row base", wave_row_base, wave_mem[base + 1]);
            expect64("column base", wave_col_base, wave_mem[base + 2]);
            expect64("row count", wave_rows, wave_mem[base + 3]);
            expect64("columns per row", wave_cols_per_row,
                     wave_mem[base + 4]);
            expect64("active lanes", wave_active_lanes, wave_mem[base + 5]);
            expect64("group active counts", issue_group_active_counts,
                     wave_mem[base + 6]);
            expect64("last", wave_last, wave_mem[base + 7]);
            expect256("lane-valid mask", lane_valid, mask_mem[wave_index]);
            for (lane_index = 0; lane_index < 256;
                 lane_index = lane_index + 1) begin
                checks = checks + 1;
                if (lane_valid[lane_index] !==
                    (lane_index < wave_active_lanes)) begin
                    failures = failures + 1;
                    $display(
                        "FAIL case=%0d wave=%0d lane=%0d validity",
                        ci, local_wave, lane_index
                    );
                end
            end
        end
    endtask

    task record_wave_coordinates;
        begin
            for (local_row = 0; local_row < wave_rows;
                 local_row = local_row + 1) begin
                for (local_col = 0; local_col < wave_cols_per_row;
                     local_col = local_col + 1) begin
                    logical_index =
                        (wave_row_base + local_row) * cfg_cols +
                        wave_col_base + local_col;
                    checks = checks + 1;
                    if ((logical_index < 0) ||
                        (logical_index >= expected_case_outputs) ||
                        (logical_index >= MAX_LOGICAL_OUTPUTS)) begin
                        failures = failures + 1;
                        $display(
                            "FAIL case=%0d wave=%0d coordinate index=%0d",
                            ci, local_wave, logical_index
                        );
                    end else if (seen[logical_index]) begin
                        failures = failures + 1;
                        $display(
                            "FAIL case=%0d wave=%0d duplicate index=%0d",
                            ci, local_wave, logical_index
                        );
                    end else begin
                        seen[logical_index] = 1'b1;
                        total_observed_outputs = total_observed_outputs + 1;
                    end
                end
            end
        end
    endtask

    task capture_stalled_wave;
        begin
            stalled_row_base = wave_row_base;
            stalled_col_base = wave_col_base;
            stalled_rows = wave_rows;
            stalled_cols = wave_cols_per_row;
            stalled_active = wave_active_lanes;
            stalled_mask = lane_valid;
            stalled_groups = issue_group_active_counts;
            stalled_last = wave_last;
        end
    endtask

    task check_stalled_wave;
        begin
            expect64("stalled valid", wave_valid, 64'd1);
            expect64("stalled row base", wave_row_base, stalled_row_base);
            expect64("stalled column base", wave_col_base, stalled_col_base);
            expect64("stalled rows", wave_rows, stalled_rows);
            expect64("stalled columns", wave_cols_per_row, stalled_cols);
            expect64("stalled active", wave_active_lanes, stalled_active);
            expect256("stalled mask", lane_valid, stalled_mask);
            expect64("stalled groups", issue_group_active_counts,
                     stalled_groups);
            expect64("stalled last", wave_last, stalled_last);
        end
    endtask

    initial begin
        failures = 0;
        checks = 0;
        total_observed_waves = 0;
        total_observed_outputs = 0;
        if (!$value$plusargs("case_path=%s", case_path) ||
            !$value$plusargs("wave_path=%s", wave_path) ||
            !$value$plusargs("mask_path=%s", mask_path) ||
            !$value$plusargs("case_count=%d", case_count) ||
            !$value$plusargs("wave_count=%d", expected_total_waves)) begin
            $fatal(1, "missing lane-mapper vector plusargs");
        end
        if ((case_count <= 0) || (case_count > MAX_CASES) ||
            (expected_total_waves <= 0) ||
            (expected_total_waves > MAX_WAVES)) begin
            $fatal(1, "lane-mapper vector bounds are invalid");
        end
        $readmemh(
            case_path, case_mem, 0, case_count * CASE_WORDS - 1
        );
        $readmemh(
            wave_path, wave_mem, 0,
            expected_total_waves * WAVE_WORDS - 1
        );
        $readmemh(
            mask_path, mask_mem, 0, expected_total_waves - 1
        );

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (ci = 0; ci < case_count; ci = ci + 1) begin
            case_base = ci * CASE_WORDS;
            cfg_rows = case_mem[case_base][31:0];
            cfg_cols = case_mem[case_base + 1][31:0];
            cfg_tile_rows = case_mem[case_base + 2][31:0];
            cfg_tile_cols = case_mem[case_base + 3][31:0];
            cfg_issue_window = case_mem[case_base + 4][31:0];
            expected_wave_start = case_mem[case_base + 6];
            expected_case_waves = case_mem[case_base + 7];
            expected_case_outputs = case_mem[case_base + 8];
            if (expected_case_outputs > MAX_LOGICAL_OUTPUTS)
                $fatal(1, "case logical-output bound exceeds testbench");
            for (j = 0; j < expected_case_outputs; j = j + 1)
                seen[j] = 1'b0;

            wave_ready = 1'b0;
            local_wave = 0;
            guard = 0;
            case_had_stall = 1'b0;
            stall_previous = 1'b0;
            @(negedge clk);
            start = 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            start = 1'b0;

            while (!done && guard < TIMEOUT_CYCLES) begin
                @(negedge clk);
                if (!done && wave_valid) begin
                    if (local_wave >= expected_case_waves) begin
                        failures = failures + 1;
                        $display("FAIL case=%0d unexpected wave", ci);
                    end else begin
                        global_wave = expected_wave_start + local_wave;
                        check_wave_metadata(global_wave);
                    end

                    // Every accepted case is stalled at least once, then a
                    // deterministic periodic stall exercises later waves.
                    if ((!case_had_stall && !stall_previous) ||
                        (((guard + ci * 3) % 11) == 3)) begin
                        wave_ready = 1'b0;
                        case_had_stall = 1'b1;
                        if (stall_previous)
                            check_stalled_wave();
                        else
                            capture_stalled_wave();
                        stall_previous = 1'b1;
                    end else begin
                        wave_ready = 1'b1;
                        if (stall_previous)
                            check_stalled_wave();
                        stall_previous = 1'b0;
                        if (local_wave < expected_case_waves)
                            record_wave_coordinates();
                        local_wave = local_wave + 1;
                        total_observed_waves = total_observed_waves + 1;
                    end
                end else begin
                    wave_ready = 1'b1;
                    if (stall_previous) begin
                        failures = failures + 1;
                        $display("FAIL case=%0d stalled wave disappeared", ci);
                        stall_previous = 1'b0;
                    end
                end
                @(posedge clk);
                #1;
                guard = guard + 1;
            end

            if (!done) begin
                failures = failures + 1;
                $display("FAIL case=%0d timeout", ci);
            end
            expect64("error code", error_code, case_mem[case_base + 5]);
            expect64("wave counter", wave_count, case_mem[case_base + 7]);
            expect64("logical outputs", logical_output_count,
                     case_mem[case_base + 8]);
            expect64("active slots", active_lane_slots,
                     case_mem[case_base + 9]);
            expect64("masked slots", masked_lane_slots,
                     case_mem[case_base + 10]);
            expect64("folded outputs", row_folded_output_count,
                     case_mem[case_base + 11]);
            expect64("busy clear", busy, 64'd0);
            expect64("observed wave count", local_wave,
                     case_mem[case_base + 7]);
            if (expected_case_waves != 0)
                expect64("backpressure exercised", case_had_stall, 64'd1);
            for (j = 0; j < expected_case_outputs; j = j + 1) begin
                checks = checks + 1;
                if (!seen[j]) begin
                    failures = failures + 1;
                    $display("FAIL case=%0d missing coordinate=%0d", ci, j);
                end
            end

            // done is a pulse; retire it before issuing the next case.
            start = 1'b0;
            wave_ready = 1'b0;
            @(posedge clk);
            #1;
        end

        expect64("campaign wave count", total_observed_waves,
                 expected_total_waves);
        if (failures != 0)
            $fatal(
                1, "ABI3 lane mapper failures=%0d checks=%0d",
                failures, checks
            );
        $display(
            "PASS: ABI3 tensor lane mapper cases=%0d waves=%0d logical_outputs=%0d checks=%0d",
            case_count, total_observed_waves,
            total_observed_outputs, checks
        );
        $finish;
    end
endmodule
