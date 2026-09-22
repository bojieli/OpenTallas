// SPDX-License-Identifier: Apache-2.0
//
// Bit-exact equivalence of ot_a3_hc_sinkhorn20_rne_pipe against
// ot_a3_hc_sinkhorn20_rne.
//
// The reference is the golden side: it is the certifying block the HC_PRE path
// ships, and the twin exists only to shorten its critical path -- 196.6 MHz
// routed, which made it the datapath's clock limiter.  So the only question is
// whether the twin computes the same 4x4 matrix, bit for bit, and returns the
// same error code.
//
// Both sides are driven from one stimulus through their own handshakes and each
// takes as many cycles as it wants; the comparison happens once both have
// produced a result for the same input.  ``out_valid`` is held until
// ``out_ready``, but the two sides finish on different cycles, so each result is
// latched rather than sampled on a shared edge.
//
// Coverage is deliberate.  A Sinkhorn input is the stable-softmax matrix AFTER
// the contract's epsilon addition, so every element is finite, positive and
// nonzero -- the block refuses anything else, and that refusal is itself a case.
// The named inputs cover the uniform matrix (where every division is exactly
// 0.25), a matrix already doubly stochastic, one with a 2^-20 dynamic range
// across its rows, the smallest normal, the largest finite, and each of the
// three malformed classes the loader rejects: a zero element, a negative one
// and a non-finite one.
`timescale 1ns / 1ps
`default_nettype none

module tb_a3_hc_sinkhorn20_pipe_equiv #(
    //: passed through to the twin so BOTH divider configurations can be
    //: proven bit-exact against the reference and their cycle costs read
    //: off the same stimulus; the header's 1.55x figure was measured here
    parameter integer PIPELINED_DIVIDER = 0
);
    localparam integer TIMEOUT_CYCLES = 2000000;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #0.5 clk = ~clk;

    reg  [511:0] matrix;
    reg          start;

    wire         ref_ready, pipe_ready;
    wire         ref_valid, pipe_valid;
    wire [511:0] ref_codes,  pipe_codes;
    wire [1:0]   ref_error,  pipe_error;

    ot_a3_hc_sinkhorn20_rne reference (
        .clk(clk), .rst_n(rst_n),
        .in_valid(start && ref_ready), .in_ready(ref_ready),
        .matrix_codes(matrix),
        .out_valid(ref_valid), .out_ready(1'b1),
        .result_codes(ref_codes), .result_error(ref_error)
    );

    ot_a3_hc_sinkhorn20_rne_pipe #(
        .PIPELINED_DIVIDER(PIPELINED_DIVIDER)
    ) pipelined (
        .clk(clk), .rst_n(rst_n),
        .in_valid(start && pipe_ready), .in_ready(pipe_ready),
        .matrix_codes(matrix),
        .out_valid(pipe_valid), .out_ready(1'b1),
        .result_codes(pipe_codes), .result_error(pipe_error)
    );

    integer cases = 0;
    integer failures = 0;
    integer ref_cycles = 0;
    integer pipe_cycles = 0;

    reg          got_ref, got_pipe;
    reg  [511:0] saw_ref_codes, saw_pipe_codes;
    reg  [1:0]   saw_ref_error, saw_pipe_error;
    integer      ref_took, pipe_took, elapsed, word;

    task automatic check;
        input [511:0] m;
        input [255:0] label;
        begin
            matrix = m;
            while (!(ref_ready && pipe_ready)) @(posedge clk);
            got_ref = 1'b0; got_pipe = 1'b0;
            ref_took = 0; pipe_took = 0; elapsed = 0;
            start = 1'b1;
            @(posedge clk);
            start = 1'b0;
            while (!(got_ref && got_pipe) && elapsed < TIMEOUT_CYCLES) begin
                if (ref_valid && !got_ref) begin
                    got_ref = 1'b1;
                    saw_ref_codes = ref_codes;
                    saw_ref_error = ref_error;
                    ref_took = elapsed;
                end
                if (pipe_valid && !got_pipe) begin
                    got_pipe = 1'b1;
                    saw_pipe_codes = pipe_codes;
                    saw_pipe_error = pipe_error;
                    pipe_took = elapsed;
                end
                @(posedge clk);
                elapsed = elapsed + 1;
            end
            cases = cases + 1;
            if (!got_ref || !got_pipe) begin
                failures = failures + 1;
                $display("FAIL %0s: timeout after %0d cycles (ref %0b pipe %0b)",
                         label, elapsed, got_ref, got_pipe);
            end else begin
                ref_cycles = ref_cycles + ref_took;
                pipe_cycles = pipe_cycles + pipe_took;
                if (saw_ref_codes !== saw_pipe_codes ||
                    saw_ref_error !== saw_pipe_error) begin
                    failures = failures + 1;
                    $display("FAIL %0s: error ref=%0d pipe=%0d", label,
                             saw_ref_error, saw_pipe_error);
                    for (word = 0; word < 16; word = word + 1)
                        if (saw_ref_codes[32*word +: 32] !==
                            saw_pipe_codes[32*word +: 32])
                            $display("     [%0d] ref=%08x pipe=%08x", word,
                                     saw_ref_codes[32*word +: 32],
                                     saw_pipe_codes[32*word +: 32]);
                end
            end
            @(posedge clk);
        end
    endtask

    // Build a 512-bit matrix from one repeated code, then override elements.
    function automatic [511:0] uniform;
        input [31:0] code;
        integer k;
        begin
            uniform = 0;
            for (k = 0; k < 16; k = k + 1)
                uniform[32*k +: 32] = code;
        end
    endfunction

    localparam [31:0] ONE     = 32'h3f80_0000;
    localparam [31:0] QUARTER = 32'h3e80_0000;
    localparam [31:0] TINY    = 32'h0080_0000;  // smallest normal
    localparam [31:0] MAXF    = 32'h7f7f_ffff;
    localparam [31:0] SMALL   = 32'h3580_0000;  // 2^-20

    reg [511:0] m;
    integer i, j;
    integer seed;

    initial begin
        start = 1'b0;
        matrix = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        // -- named inputs --------------------------------------------------
        check(uniform(ONE),     "uniform one");
        check(uniform(QUARTER), "uniform quarter");
        check(uniform(TINY),    "uniform smallest normal");
        check(uniform(MAXF),    "uniform largest finite");

        // A row-graded matrix: 2^-20 across the rows.
        m = uniform(ONE);
        for (i = 0; i < 4; i = i + 1)
            for (j = 0; j < 4; j = j + 1)
                m[32*(4*i + j) +: 32] = (i == 0) ? SMALL : ONE;
        check(m, "one row at 2^-20");

        // A column-graded matrix.
        m = uniform(ONE);
        for (i = 0; i < 4; i = i + 1)
            m[32*(4*i) +: 32] = SMALL;
        check(m, "one column at 2^-20");

        // Mixed magnitudes, largest finite beside smallest normal.
        m = uniform(ONE);
        m[32*0  +: 32] = MAXF;
        m[32*5  +: 32] = TINY;
        m[32*10 +: 32] = MAXF;
        m[32*15 +: 32] = TINY;
        check(m, "maxfinite beside smallest normal");

        // -- the three malformed classes the loader refuses -----------------
        m = uniform(ONE); m[32*7 +: 32] = 32'h0000_0000;
        check(m, "a zero element refuses");
        m = uniform(ONE); m[32*7 +: 32] = 32'hbf80_0000;
        check(m, "a negative element refuses");
        m = uniform(ONE); m[32*7 +: 32] = 32'h7f80_0000;
        check(m, "an infinite element refuses");
        m = uniform(ONE); m[32*7 +: 32] = 32'h7fc0_0000;
        check(m, "a NaN element refuses");

        // -- random positive finite matrices -------------------------------
        seed = 32'h51_9ec0de;
        for (i = 0; i < 24; i = i + 1) begin
            for (j = 0; j < 16; j = j + 1) begin
                // exponent in [110, 140] keeps every element finite, normal
                // and within a range the reduction cannot overflow.
                m[32*j +: 32] = {1'b0,
                                 8'd110 + ({$random(seed)} % 31),
                                 {$random(seed)} & 23'h7fffff};
            end
            check(m, "random positive finite");
        end

        $display("CASES %0d", cases);
        $display("FAILURES %0d", failures);
        $display("REF_CYCLES %0d", ref_cycles);
        $display("PIPE_CYCLES %0d", pipe_cycles);
        if (cases > 0 && ref_cycles > 0)
            $display("CYCLE_RATIO_PIPE_OVER_REF %0d.%02d",
                     (pipe_cycles * 100 / ref_cycles) / 100,
                     (pipe_cycles * 100 / ref_cycles) % 100);
        if (failures == 0)
            $display("EQUIVALENT");
        else
            $display("NOT_EQUIVALENT");
        $finish;
    end
endmodule

`default_nettype wire
