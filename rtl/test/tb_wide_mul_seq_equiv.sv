`timescale 1ns/1ps
// ot_wide_mul_seq against the ``*`` operator it replaces.
//
// The carry-save accumulator is where this can go silently wrong: a level pushes
// a set bit one position up, so a chain of them can creep above the true
// magnitude, and a product whose top bit fell off the accumulator is simply a
// wrong number -- no flag, no refusal. So the authority is ``a * b`` itself at
// full width, and the comparison is on both outputs: the kept high bits and the
// OR of the discarded low ones.
//
// FOUR CHUNK WIDTHS SIDE BY SIDE at the widths ot_a3_fp32_exp_pos_cr_rne
// actually instantiates -- 163 by 161 split at 160, which is
// ``term * reduced`` -- because the emission split and the accumulator headroom
// both depend on BITS_PER_STEP and a value that fits at 4 can overflow at 32.
//
// THE CORPUS IS ADVERSARIAL ABOUT THE TOP BIT. All-ones times all-ones is the
// largest product the widths admit and the one that stresses the headroom;
// powers of two isolate the shift; and the low-half OR is checked both ways by
// multiplying values whose product has exactly zero low bits (a power of two
// times a power of two) and values one away from those.
module tb_wide_mul_seq_equiv;
    localparam integer WA = 163;
    localparam integer WB = 161;
    localparam integer LOW = 160;
    localparam integer HIGH_W = WA + WB - LOW;
    localparam integer DUTS = 4;

    reg clk = 0, rst_n = 0, start = 0;
    reg [WA-1:0] a;
    reg [WB-1:0] b;
    wire [DUTS-1:0] busy, done, low_nonzero;
    wire [HIGH_W-1:0] product_high [0:DUTS-1];

    integer errors = 0, checked = 0;

    ot_wide_mul_seq #(.WA(WA), .WB(WB), .BITS_PER_STEP(2), .LOW_BITS(LOW))
        m2 (.clk(clk), .rst_n(rst_n), .start(start), .a(a), .b(b),
            .busy(busy[0]), .done(done[0]), .product_high(product_high[0]),
            .low_nonzero(low_nonzero[0]));
    ot_wide_mul_seq #(.WA(WA), .WB(WB), .BITS_PER_STEP(4), .LOW_BITS(LOW))
        m4 (.clk(clk), .rst_n(rst_n), .start(start), .a(a), .b(b),
            .busy(busy[1]), .done(done[1]), .product_high(product_high[1]),
            .low_nonzero(low_nonzero[1]));
    ot_wide_mul_seq #(.WA(WA), .WB(WB), .BITS_PER_STEP(8), .LOW_BITS(LOW))
        m8 (.clk(clk), .rst_n(rst_n), .start(start), .a(a), .b(b),
            .busy(busy[2]), .done(done[2]), .product_high(product_high[2]),
            .low_nonzero(low_nonzero[2]));
    ot_wide_mul_seq #(.WA(WA), .WB(WB), .BITS_PER_STEP(16), .LOW_BITS(LOW))
        m16 (.clk(clk), .rst_n(rst_n), .start(start), .a(a), .b(b),
             .busy(busy[3]), .done(done[3]), .product_high(product_high[3]),
             .low_nonzero(low_nonzero[3]));

    always #1 clk = ~clk;

    //: ``done`` is a one-cycle pulse and the four widths land on four different
    //: cycles, so each is latched before anything is compared.
    reg [DUTS-1:0]    seen;
    reg [HIGH_W-1:0]  held_high [0:DUTS-1];
    reg [DUTS-1:0]    held_low;
    integer h;
    always @(posedge clk) begin
        for (h = 0; h < DUTS; h = h + 1)
            if (done[h]) begin
                seen[h] <= 1'b1;
                held_high[h] <= product_high[h];
                held_low[h] <= low_nonzero[h];
            end
    end

    reg [WA+WB-1:0] want;
    reg [HIGH_W-1:0] want_high;
    reg want_low;
    integer k;
    task check(input [WA-1:0] av, input [WB-1:0] bv);
        begin
            @(negedge clk);
            seen = {DUTS{1'b0}};
            a = av; b = bv; start = 1'b1;
            @(negedge clk); start = 1'b0;
            wait (seen == {DUTS{1'b1}});
            want = {{(WB){1'b0}}, av} * {{(WA){1'b0}}, bv};
            want_high = want[WA+WB-1:LOW];
            want_low = |want[LOW-1:0];
            checked = checked + 1;
            for (k = 0; k < DUTS; k = k + 1) begin
                if (held_high[k] !== want_high || held_low[k] !== want_low) begin
                    errors = errors + 1;
                    $display("FAIL dut %0d: high %h/%h low %b/%b",
                             k, held_high[k], want_high, held_low[k], want_low);
                end
            end
            @(negedge clk);
        end
    endtask

    reg [WA-1:0] av;
    reg [WB-1:0] bv;
    integer trial, w;
    initial begin
        seen = {DUTS{1'b0}};
        rst_n = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        //: The largest product the widths admit, and the headroom case.
        check({WA{1'b1}}, {WB{1'b1}});
        check({WA{1'b0}}, {WB{1'b1}});
        check({WA{1'b1}}, {WB{1'b0}});
        check({{(WA-1){1'b0}}, 1'b1}, {WB{1'b1}});
        check({WA{1'b1}}, {{(WB-1){1'b0}}, 1'b1});

        //: Isolated powers of two: the product has a single set bit, so the
        //: low-half OR is low exactly when that bit lands at or above LOW.
        for (trial = 0; trial < WB; trial = trial + 8) begin
            check({{(WA-1){1'b0}}, 1'b1} << (WA - 1 - trial),
                  {{(WB-1){1'b0}}, 1'b1} << trial);
            check(({{(WA-1){1'b0}}, 1'b1} << (WA - 1 - trial)) + 1'b1,
                  {{(WB-1){1'b0}}, 1'b1} << trial);
        end

        //: The exponential's own shape: a term just below one in Q0.160 times a
        //: reduced argument just below ln2.
        check({3'b000, 1'b1, {(WA-4){1'b0}}},
              161'h0b17217f7d1cf79abc9e3b39803f2f6af40f34325);
        check({3'b000, {(WA-3){1'b1}}},
              161'h0b17217f7d1cf79abc9e3b39803f2f6af40f34326);

        for (trial = 0; trial < 120; trial = trial + 1) begin
            av = {WA{1'b0}};
            for (w = 0; w < WA; w = w + 32)
                av = (av << 32) | {{(WA-32){1'b0}}, $random};
            bv = {WB{1'b0}};
            for (w = 0; w < WB; w = w + 32)
                bv = (bv << 32) | {{(WB-32){1'b0}}, $random};
            check(av, bv);
        end

        if (errors == 0)
            $display("PASS tb_wide_mul_seq_equiv %0d products x %0d chunk widths",
                     checked, DUTS);
        else
            $display("FAIL tb_wide_mul_seq_equiv %0d mismatches", errors);
        $finish;
    end
endmodule
