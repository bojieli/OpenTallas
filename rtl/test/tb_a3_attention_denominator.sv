`timescale 1ns/1ps
// ATTENTION.SPARSE's across-block online denominator, against the reference loop.
//
// Expectations come from tools/build_a3_attention_denominator_vectors.py, which
// walks the reference's own per-block loop with ITS exp_cr32 and ITS
// _balanced_sum, and records the running maximum, the rescale and the denominator
// after EVERY block. Checking only the final value would miss a carried-state
// defect that happens to cancel.
//
// THE RESCALE ONLY DOES WORK WHEN THE MAXIMUM MOVES. A descending sequence leaves
// every later rescale at exactly 1.0, so a block that never applied it would
// still pass -- case rising_maxima (3 of 4 blocks) and long_sequence (7 of 8) are
// the ones that catch it, and falling_maxima is kept beside them to show the
// contrast. The generator refuses to build a set where no case moves the maximum.
module tb_a3_attention_denominator;
    localparam integer LANES = 64;

    reg clk = 0, rst_n = 0;
    reg block_valid = 0, block_first = 0;
    reg [LANES-1:0] lane_valid;
    reg [LANES*32-1:0] scores;
    wire block_ready, block_done, busy;
    wire [31:0] running_max, running_sums, block_rescale;
    wire [LANES*32-1:0] block_probabilities;
    wire [7:0] error_code;
    wire [31:0] blocks_retired;

    reg [31:0] smem [0:LANES-1];
    integer j, errors = 0;
    integer ncases, c, nblocks, b;
    integer fh, code;
    reg [1023:0] name, path;
    reg [LANES-1:0] mask;
    reg [31:0] max_exp, res_exp, sums_exp;

    ot_a3_attention_denominator #(.LANES(LANES)) dut (
        .clk(clk), .rst_n(rst_n),
        .block_valid(block_valid), .block_first(block_first),
        .lane_valid(lane_valid), .scores(scores), .block_ready(block_ready),
        .running_max(running_max), .running_sums(running_sums),
        .block_rescale(block_rescale),
        .block_probabilities(block_probabilities),
        .block_done(block_done),
        .busy(busy), .error_code(error_code), .blocks_retired(blocks_retired)
    );

    always #1 clk = ~clk;

    task feed; begin
        wait (block_ready);
        @(negedge clk); block_valid = 1;
        @(negedge clk); block_valid = 0;
        wait (block_done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d\n", name, nblocks);
            for (b = 0; b < nblocks; b = b + 1) begin
                code = $fscanf(fh, " %b %h %h %h\n", mask, max_exp, res_exp, sums_exp);
                for (j = 0; j < LANES; j = j + 1) smem[j] = 32'd0;
                $sformat(path, "scores_%0d_%0d.hex", c, b); $readmemh(path, smem);
                for (j = 0; j < LANES; j = j + 1) scores[j*32 +: 32] = smem[j];
                lane_valid = mask;
                block_first = (b == 0);
                feed;

                if (error_code !== 8'h00) begin
                    $display("FAIL %0s block %0d error_code=%0h", name, b, error_code);
                    errors = errors + 1;
                end
                if (running_max !== max_exp) begin
                    $display("FAIL %0s block %0d max got %08h expected %08h",
                             name, b, running_max, max_exp);
                    errors = errors + 1;
                end
                if (block_rescale !== res_exp) begin
                    $display("FAIL %0s block %0d rescale got %08h expected %08h",
                             name, b, block_rescale, res_exp);
                    errors = errors + 1;
                end
                if (running_sums !== sums_exp) begin
                    $display("FAIL %0s block %0d sums got %08h expected %08h",
                             name, b, running_sums, sums_exp);
                    errors = errors + 1;
                end
            end
            if (blocks_retired !== nblocks) begin
                $display("FAIL %0s retired %0d blocks, expected %0d",
                         name, blocks_retired, nblocks);
                errors = errors + 1;
            end
            $display("  %0s: %0d blocks, final max=%08h sums=%08h",
                     name, nblocks, running_max, running_sums);
        end
        $fclose(fh);

        if (errors == 0)
            $display("PASS a3_attention_denominator: %0d block sequences match the reference loop on the maximum, the rescale and the denominator after every block", ncases);
        else
            $display("FAIL a3_attention_denominator: %0d errors", errors);
        $finish;
    end
endmodule
