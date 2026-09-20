`timescale 1ns/1ps
// ot_wide_div_small_seq against the unrolled loop it replaces, bit for bit.
//
// The claim the sequential divider makes is not "close enough" but IDENTICAL:
// same restoring steps, same order, same partial remainders, only fewer of them
// per clock. So the authority here is ot_a3_fp32_exp_pos_cr_rne's own
// ``divide_small`` function, copied verbatim, and the test is equality of both
// outputs -- quotient and the inexact flag -- on every argument.
//
// SIX BITS_PER_STEP VALUES RUN SIDE BY SIDE, because the padding is where a
// chunked restoring divide goes wrong: STEPS*BITS_PER_STEP exceeds WIDTH for
// every one of 2, 4, 8, 16 and 32 at WIDTH = 163, and padding at the wrong end
// computes dividend*2**pad/divisor -- which agrees with the reference for
// divisor 1 and disagrees everywhere else. 1 is included as the degenerate case
// where the chunk is a single bit and the loop is the original.
//
// The corpus targets the remainder rather than the quotient: divisors 1 and 2
// (where the restoring step is trivial), the 56 the exponential actually uses,
// the full 9-bit maximum, dividends that are exact multiples of the divisor (the
// only way inexact goes low), and one below and one above each of those.
module tb_wide_div_small_seq_equiv;
    localparam integer WIDTH = 163;
    localparam integer DBITS = 9;
    localparam integer DUTS = 6;

    reg clk = 0, rst_n = 0;
    reg start = 0;
    reg [WIDTH-1:0] dividend;
    reg [DBITS-1:0] divisor;
    wire [DUTS-1:0] busy, done, inexact;
    wire [WIDTH-1:0] quotient [0:DUTS-1];

    integer errors = 0, checked = 0;

    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(1))
        d1 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
            .divisor(divisor), .busy(busy[0]), .done(done[0]),
            .quotient(quotient[0]), .inexact(inexact[0]));
    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(2))
        d2 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
            .divisor(divisor), .busy(busy[1]), .done(done[1]),
            .quotient(quotient[1]), .inexact(inexact[1]));
    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(4))
        d4 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
            .divisor(divisor), .busy(busy[2]), .done(done[2]),
            .quotient(quotient[2]), .inexact(inexact[2]));
    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(8))
        d8 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
            .divisor(divisor), .busy(busy[3]), .done(done[3]),
            .quotient(quotient[3]), .inexact(inexact[3]));
    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(16))
        d16 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
             .divisor(divisor), .busy(busy[4]), .done(done[4]),
             .quotient(quotient[4]), .inexact(inexact[4]));
    ot_wide_div_small_seq #(.WIDTH(WIDTH), .DIVISOR_BITS(DBITS), .BITS_PER_STEP(32))
        d32 (.clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
             .divisor(divisor), .busy(busy[5]), .done(done[5]),
             .quotient(quotient[5]), .inexact(inexact[5]));

    always #1 clk = ~clk;

    //: ot_a3_fp32_exp_pos_cr_rne's divide_small, verbatim. The only edits are
    //: the parameter names, because this bench does not import FRAC_BITS.
    function automatic [WIDTH:0] divide_small_reference;
        input [WIDTH-1:0] dividend_in;
        input [DBITS-1:0] divisor_in;
        reg [WIDTH-1:0] quotient_r;
        reg [DBITS:0] remainder;
        integer bit_index;
        begin
            quotient_r = 0;
            remainder = 0;
            for (bit_index = WIDTH - 1; bit_index >= 0;
                 bit_index = bit_index - 1) begin
                remainder = {remainder[DBITS-1:0], dividend_in[bit_index]};
                if (remainder >= {1'b0, divisor_in}) begin
                    remainder = remainder - {1'b0, divisor_in};
                    quotient_r[bit_index] = 1'b1;
                end
            end
            divide_small_reference = {quotient_r, |remainder};
        end
    endfunction

    //: ``done`` is a ONE-CYCLE pulse and the six widths finish on six different
    //: cycles -- 6 for the 32-bit chunk, 163 for the 1-bit one -- so waiting on
    //: the conjunction of the live signals never completes. Each is latched, and
    //: the latched quotient is what gets compared.
    reg [DUTS-1:0]   seen;
    reg [WIDTH-1:0]  held_quotient [0:DUTS-1];
    reg [DUTS-1:0]   held_inexact;
    integer h;
    always @(posedge clk) begin
        for (h = 0; h < DUTS; h = h + 1)
            if (done[h]) begin
                seen[h] <= 1'b1;
                held_quotient[h] <= quotient[h];
                held_inexact[h] <= inexact[h];
            end
    end

    reg [WIDTH:0] want;
    integer k;
    task check(input [WIDTH-1:0] a, input [DBITS-1:0] d);
        begin
            @(negedge clk);
            seen = {DUTS{1'b0}};
            dividend = a; divisor = d; start = 1'b1;
            @(negedge clk); start = 1'b0;
            wait (seen == {DUTS{1'b1}});
            want = divide_small_reference(a, d);
            checked = checked + 1;
            for (k = 0; k < DUTS; k = k + 1) begin
                if (held_quotient[k] !== want[WIDTH:1] ||
                    held_inexact[k] !== want[0]) begin
                    errors = errors + 1;
                    $display("FAIL dut %0d divisor %0d: quotient %h/%h inexact %b/%b",
                             k, d, held_quotient[k], want[WIDTH:1],
                             held_inexact[k], want[0]);
                end
            end
            @(negedge clk);
        end
    endtask

    //: All six run in lockstep only because ``start`` is broadcast and each
    //: raises ``done`` on its own cycle; ``wait`` on the conjunction is what
    //: lets the slowest set the pace.
    reg [WIDTH-1:0] value;
    integer trial, w;
    initial begin
        seen = {DUTS{1'b0}};
        rst_n = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        //: Exact multiples, and their neighbours: the only inputs where inexact
        //: is low, and the ones a wrongly-padded chunk gets right by accident.
        for (trial = 1; trial <= 56; trial = trial + 1) begin
            value = {{(WIDTH-40){1'b0}}, 40'h9e3779b97f} * trial;
            check(value, trial[DBITS-1:0]);
            check(value + 1, trial[DBITS-1:0]);
            check(value - 1, trial[DBITS-1:0]);
        end

        //: The degenerate divisors and the widest one.
        check({WIDTH{1'b1}}, 9'd1);
        check({WIDTH{1'b1}}, 9'd2);
        check({WIDTH{1'b1}}, 9'd511);
        check({WIDTH{1'b0}}, 9'd7);
        check({1'b1, {(WIDTH-1){1'b0}}}, 9'd3);
        check({{(WIDTH-1){1'b0}}, 1'b1}, 9'd511);

        //: Random, over the divisors the series uses and the full 9-bit range.
        for (trial = 0; trial < 180; trial = trial + 1) begin
            value = {WIDTH{1'b0}};
            for (w = 0; w < WIDTH; w = w + 32)
                value = (value << 32) | {{(WIDTH-32){1'b0}}, $random};
            check(value, (trial % 2 == 0) ? ((trial % 56) + 1) : ($random % 511 + 1));
        end

        if (errors == 0)
            $display("PASS tb_wide_div_small_seq_equiv %0d arguments x %0d widths",
                     checked, DUTS);
        else
            $display("FAIL tb_wide_div_small_seq_equiv %0d mismatches", errors);
        $finish;
    end
endmodule
