`timescale 1ns/1ps
// ot_wide_div_seq against ot_a3_fp32_transcendental_cr_rne's divide_fixed_ratio.
//
// The claim is identity, not approximation: the same restoring steps over the
// same numerator bits, only fewer per clock. So the reference is that function
// copied verbatim, and both outputs are compared -- the windowed quotient and
// the remainder-nonzero flag that rounds the upper endpoint away from zero.
//
// THE CORPUS IS THE SIGMOID TRANSFORM'S OWN SHAPE. Its numerators are never
// arbitrary: either an interval endpoint shifted up by FRAC_BITS bits (so the low
// 160 bits are zero) or a single set bit at 2*FRAC_BITS, and its denominators are
// one plus an endpoint. Those are the cases that matter, so they are here
// explicitly alongside random ones; a divisor of one, a numerator of zero and a
// numerator just below and just above the denominator cover the degenerate ends.
module tb_wide_div_seq_equiv;
    localparam integer FRAC_BITS = 160;
    localparam integer NUM_BITS = 2*FRAC_BITS + 8;   // 328
    localparam integer DEN_BITS = FRAC_BITS + 4;     // 164
    localparam integer QUOT_BITS = FRAC_BITS + 3;    // 163

    reg clk = 0, rst_n = 0, start = 0;
    reg [NUM_BITS-1:0] numerator;
    reg [DEN_BITS-1:0] denominator;
    wire busy, done, inexact;
    wire [QUOT_BITS-1:0] quotient;

    integer errors = 0, checked = 0;

    ot_wide_div_seq #(.NUM_BITS(NUM_BITS), .DEN_BITS(DEN_BITS),
                      .QUOT_BITS(QUOT_BITS), .BITS_PER_STEP(1))
        dut (.clk(clk), .rst_n(rst_n), .start(start), .numerator(numerator),
             .denominator(denominator), .busy(busy), .done(done),
             .quotient(quotient), .inexact(inexact));

    always #1 clk = ~clk;

    //: divide_fixed_ratio, verbatim.
    function automatic [FRAC_BITS+3:0] divide_fixed_ratio;
        input [2*FRAC_BITS+7:0] numerator_in;
        input [FRAC_BITS+3:0] denominator_in;
        reg [FRAC_BITS+2:0] quotient_r;
        reg [FRAC_BITS+3:0] remainder;
        reg [FRAC_BITS+4:0] shifted_remainder;
        reg [FRAC_BITS+4:0] remainder_difference;
        integer divide_bit;
        begin
            quotient_r = 0;
            remainder = 0;
            shifted_remainder = 0;
            remainder_difference = 0;
            for (divide_bit = 2*FRAC_BITS + 7; divide_bit >= 0;
                 divide_bit = divide_bit - 1) begin
                shifted_remainder = {remainder, numerator_in[divide_bit]};
                if (shifted_remainder >= {1'b0, denominator_in}) begin
                    remainder_difference =
                        shifted_remainder - {1'b0, denominator_in};
                    remainder = remainder_difference[FRAC_BITS+3:0];
                    if (divide_bit <= FRAC_BITS + 2)
                        quotient_r[divide_bit] = 1'b1;
                end else begin
                    remainder = shifted_remainder[FRAC_BITS+3:0];
                end
            end
            divide_fixed_ratio = {quotient_r, remainder != 0};
        end
    endfunction

    reg [FRAC_BITS+3:0] want;
    task check(input [NUM_BITS-1:0] n, input [DEN_BITS-1:0] d);
        begin
            @(negedge clk);
            numerator = n; denominator = d; start = 1'b1;
            @(negedge clk); start = 1'b0;
            wait (done);
            want = divide_fixed_ratio(n, d);
            checked = checked + 1;
            if (quotient !== want[FRAC_BITS+3:1] || inexact !== want[0]) begin
                errors = errors + 1;
                $display("FAIL quotient %h/%h inexact %b/%b",
                         quotient, want[FRAC_BITS+3:1], inexact, want[0]);
            end
            @(negedge clk);
        end
    endtask

    localparam [FRAC_BITS+2:0] FIXED_ONE = {2'b0, 1'b1, {FRAC_BITS{1'b0}}};
    reg [FRAC_BITS+2:0] endpoint;
    reg [NUM_BITS-1:0] num;
    reg [DEN_BITS-1:0] den;
    integer trial, w;
    initial begin
        rst_n = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        //: Degenerate ends.
        check({NUM_BITS{1'b0}}, {{(DEN_BITS-1){1'b0}}, 1'b1});
        check({NUM_BITS{1'b1}}, {{(DEN_BITS-1){1'b0}}, 1'b1});
        check({NUM_BITS{1'b1}}, {DEN_BITS{1'b1}});
        check({{(NUM_BITS-1){1'b0}}, 1'b1}, {DEN_BITS{1'b1}});

        //: e/(1+e): the endpoint shifted up by FRAC_BITS over one plus itself.
        for (trial = 0; trial < 10; trial = trial + 1) begin
            endpoint = ({{(FRAC_BITS+2){1'b0}}, 1'b1} << (FRAC_BITS - trial*16)) - 1'b1;
            num = {5'b0, endpoint, {FRAC_BITS{1'b0}}};
            den = {1'b0, FIXED_ONE} + {1'b0, endpoint};
            check(num, den);
            //: 1/(1+e): a single set bit at 2*FRAC_BITS.
            num = {NUM_BITS{1'b0}};
            num[2*FRAC_BITS] = 1'b1;
            check(num, den);
        end

        //: The numerator just below, at, and just above the denominator, where the
        //: first quotient bit lands and the window matters.
        den = {1'b0, FIXED_ONE};
        check({{(NUM_BITS-DEN_BITS){1'b0}}, den} - 1'b1, den);
        check({{(NUM_BITS-DEN_BITS){1'b0}}, den}, den);
        check({{(NUM_BITS-DEN_BITS){1'b0}}, den} + 1'b1, den);

        for (trial = 0; trial < 24; trial = trial + 1) begin
            num = {NUM_BITS{1'b0}};
            for (w = 0; w < NUM_BITS; w = w + 32)
                num = (num << 32) | {{(NUM_BITS-32){1'b0}}, $random};
            den = {DEN_BITS{1'b0}};
            for (w = 0; w < DEN_BITS; w = w + 32)
                den = (den << 32) | {{(DEN_BITS-32){1'b0}}, $random};
            if (den == 0) den = {{(DEN_BITS-1){1'b0}}, 1'b1};
            check(num, den);
        end

        if (errors == 0)
            $display("PASS tb_wide_div_seq_equiv %0d divisions", checked);
        else
            $display("FAIL tb_wide_div_seq_equiv %0d mismatches", errors);
        $finish;
    end
endmodule
