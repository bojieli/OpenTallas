// SPDX-License-Identifier: Apache-2.0
//
// Bit-exact equivalence of ot_a3_fp32_div_rne_pipe against ot_a3_fp32_div_rne.
//
// The reference is the golden side: it is the module seven token-path parents
// instantiate today, and it closes on ASAP7 at 283.5 MHz.  The pipelined twin
// exists to shorten that block's critical path, so the only interesting question
// is whether it computes the SAME thing -- ``result_code`` and ``result_error``,
// bit for bit, on every case.
//
// Both are driven from one stimulus stream through their own handshakes and each
// is allowed to take as many cycles as it wants; the comparison is made when both
// have produced a result for the same input.  That is the shape the earlier
// VECTOR.SCALE equivalence bench needed too: ``done`` is not a shared clock edge,
// and a bench that waits for one side's pulse while the other has already
// finished hangs rather than fails.
//
// Coverage is deliberate, not only random.  Division is where the edges live:
// zero and subnormal numerators, a zero denominator, infinity and NaN arguments,
// MAX_FINITE and the codes either side of it (the overflow boundary is the
// midpoint between max finite and 2**128), exact powers of two, and equal
// operands.
`timescale 1ns / 1ps
`default_nettype none

module tb_a3_fp32_div_pipe_equiv;
    localparam integer TIMEOUT_CYCLES = 20000;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #0.5 clk = ~clk;

    reg  [31:0] numerator;
    reg  [31:0] denominator;
    reg         start;

    wire        ref_ready, pipe_ready;
    wire        ref_valid, pipe_valid;
    wire [31:0] ref_code,  pipe_code;
    wire [1:0]  ref_error, pipe_error;

    ot_a3_fp32_div_rne reference (
        .clk(clk), .rst_n(rst_n),
        .in_valid(start && ref_ready), .in_ready(ref_ready),
        .numerator_code(numerator), .denominator_code(denominator),
        .out_valid(ref_valid), .out_ready(1'b1),
        .result_code(ref_code), .result_error(ref_error)
    );

    ot_a3_fp32_div_rne_pipe pipelined (
        .clk(clk), .rst_n(rst_n),
        .in_valid(start && pipe_ready), .in_ready(pipe_ready),
        .numerator_code(numerator), .denominator_code(denominator),
        .out_valid(pipe_valid), .out_ready(1'b1),
        .result_code(pipe_code), .result_error(pipe_error)
    );

    integer cases = 0;
    integer failures = 0;
    integer ref_cycles = 0;
    integer pipe_cycles = 0;

    // Latched, because the two sides finish on different cycles and out_valid is
    // a one-cycle pulse.
    reg        got_ref, got_pipe;
    reg [31:0] saw_ref_code, saw_pipe_code;
    reg [1:0]  saw_ref_error, saw_pipe_error;
    integer    ref_took, pipe_took, elapsed;

    task automatic check;
        input [31:0] a;
        input [31:0] b;
        input [255:0] label;
        begin
            numerator = a;
            denominator = b;
            // Both must be able to accept before the shared pulse is raised.
            while (!(ref_ready && pipe_ready)) @(posedge clk);
            got_ref = 1'b0; got_pipe = 1'b0;
            ref_took = 0; pipe_took = 0; elapsed = 0;
            start = 1'b1;
            @(posedge clk);
            start = 1'b0;
            while (!(got_ref && got_pipe) && elapsed < TIMEOUT_CYCLES) begin
                if (ref_valid && !got_ref) begin
                    got_ref = 1'b1;
                    saw_ref_code = ref_code;
                    saw_ref_error = ref_error;
                    ref_took = elapsed;
                end
                if (pipe_valid && !got_pipe) begin
                    got_pipe = 1'b1;
                    saw_pipe_code = pipe_code;
                    saw_pipe_error = pipe_error;
                    pipe_took = elapsed;
                end
                @(posedge clk);
                elapsed = elapsed + 1;
            end
            cases = cases + 1;
            if (!got_ref || !got_pipe) begin
                failures = failures + 1;
                $display("FAIL %0s: timeout after %0d cycles (ref %0b pipe %0b) n=%08x d=%08x",
                         label, elapsed, got_ref, got_pipe, a, b);
            end else begin
                ref_cycles = ref_cycles + ref_took;
                pipe_cycles = pipe_cycles + pipe_took;
                if (saw_ref_code !== saw_pipe_code ||
                    saw_ref_error !== saw_pipe_error) begin
                    failures = failures + 1;
                    $display("FAIL %0s: n=%08x d=%08x ref=%08x/%0d pipe=%08x/%0d",
                             label, a, b, saw_ref_code, saw_ref_error,
                             saw_pipe_code, saw_pipe_error);
                end
            end
            // Let both drain their out_valid before the next case.
            @(posedge clk);
        end
    endtask

    integer i;
    reg [31:0] a;
    reg [31:0] b;
    integer seed;

    // Codes worth naming.  MAX_FINITE and its neighbours bracket the RNE
    // overflow boundary; 8'h00 exponents are subnormal; 8'hff is inf/NaN.
    localparam [31:0] MAXF   = 32'h7f7f_ffff;
    localparam [31:0] ONE    = 32'h3f80_0000;
    localparam [31:0] TWO    = 32'h4000_0000;
    localparam [31:0] HALF   = 32'h3f00_0000;
    localparam [31:0] THREE  = 32'h4040_0000;
    localparam [31:0] TINY   = 32'h0000_0001;   // smallest subnormal
    localparam [31:0] SUBN   = 32'h007f_ffff;   // largest subnormal
    localparam [31:0] MINN   = 32'h0080_0000;   // smallest normal
    localparam [31:0] INF    = 32'h7f80_0000;
    localparam [31:0] NAN    = 32'h7fc0_0000;

    initial begin
        start = 1'b0;
        numerator = 0;
        denominator = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        // -- named edges ---------------------------------------------------
        check(ONE,   ONE,   "1/1");
        check(ONE,   TWO,   "1/2");
        check(TWO,   ONE,   "2/1");
        check(ONE,   THREE, "1/3");
        check(THREE, ONE,   "3/1");
        check(MAXF,  HALF,  "maxfinite/0.5 overflows");
        check(MAXF,  ONE,   "maxfinite/1");
        check(MAXF,  MAXF,  "maxfinite/maxfinite");
        check(MAXF,  TWO,   "maxfinite/2");
        check(ONE,   MAXF,  "1/maxfinite");
        check(TINY,  ONE,   "min subnormal/1");
        check(TINY,  TWO,   "min subnormal/2 underflows");
        check(ONE,   TINY,  "1/min subnormal overflows");
        check(SUBN,  MINN,  "max subnormal/min normal");
        check(MINN,  SUBN,  "min normal/max subnormal");
        check(32'h0, ONE,   "zero numerator");
        check(ONE,   32'h0, "zero denominator refuses");
        check(INF,   ONE,   "inf numerator refuses");
        check(ONE,   INF,   "inf denominator refuses");
        check(NAN,   ONE,   "nan numerator refuses");
        check(ONE,   NAN,   "nan denominator refuses");
        check(32'hbf80_0000, TWO, "-1/2 sign");
        check(ONE, 32'hc000_0000, "1/-2 sign");
        check(32'hbf80_0000, 32'hc000_0000, "-1/-2 sign");
        check(32'h8000_0000, ONE, "negative zero numerator");

        // -- exact powers of two, where the quotient is representable -------
        for (i = 0; i < 24; i = i + 1) begin
            a = {1'b0, 8'd127 + i[7:0], 23'b0};
            b = {1'b0, 8'd127, 23'b0};
            check(a, b, "2^k / 1");
            check(b, a, "1 / 2^k");
        end

        // -- random finite pairs -------------------------------------------
        seed = 32'h0bad_c0de;
        for (i = 0; i < 400; i = i + 1) begin
            a = {$random(seed)} & 32'h7fff_ffff;
            b = {$random(seed)} & 32'h7fff_ffff;
            if (a[30:23] == 8'hff) a[30:23] = 8'hfe;
            if (b[30:23] == 8'hff) b[30:23] = 8'hfe;
            if (b[30:0] == 0) b[23] = 1'b1;
            check(a, b, "random finite");
        end

        // -- random pairs with narrow exponents, where ties are common ------
        for (i = 0; i < 200; i = i + 1) begin
            a = {1'b0, 8'd127, {$random(seed)} & 23'h7fffff};
            b = {1'b0, 8'd127, {$random(seed)} & 23'h7fffff};
            check(a, b, "random near one");
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
