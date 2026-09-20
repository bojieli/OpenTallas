`timescale 1ns/1ps
// ot_fp32_rsqrt_rne's two-cycle comparison against the single-cycle form it
// replaces, result bit for result bit.
//
// WHY. The single-cycle form computed the comparison TWICE in one combinational
// block -- once for the search's candidate, once for the midpoint -- and each copy
// chained a 25-by-25 multiply into a 50-by-24 multiply, a 74-bit priority scan and a
// 74-bit OR. Four wide multiplies and two 74-iteration loops in every cycle of a
// 31-step binary search, and yosys could not finish it: ot_a3_vector_rms_norm's route
// timed out after four hours in 1_2_yosys and this module alone produces no netlist in
// ten minutes.
//
// The rewrite has ONE comparison datapath with multiplexed operands over two cycles.
// The claim is that the arithmetic is untouched and only the schedule moved, so the
// test is EQUALITY of the published result code and error on the same arguments -- not
// a tolerance, and not a re-derivation from a model, because the reference here is the
// code that shipped.
//
// THE CORPUS IS THE AWKWARD END OF THE DOMAIN. The refusals (negative, zero,
// infinity, NaN), the subnormal edge, one and its neighbours, the largest finite, and
// powers of two where the exact reciprocal square root is representable -- plus random
// positive codes, because a binary search's decisions are what this changes and they
// are argument-dependent.
module tb_fp32_rsqrt_split_equiv;
    reg clk = 0, rst_n = 0;
    reg [31:0] argument_code;
    reg  a_in_valid = 0, b_in_valid = 0;
    wire a_in_ready, b_in_ready, a_out_valid, b_out_valid;
    reg  a_out_ready = 1, b_out_ready = 1;
    wire [31:0] a_result, b_result;
    wire [1:0]  a_error, b_error;

    ot_fp32_rsqrt_rne split (
        .clk(clk), .rst_n(rst_n), .in_valid(a_in_valid), .in_ready(a_in_ready),
        .argument_code(argument_code), .out_valid(a_out_valid),
        .out_ready(a_out_ready), .result_code(a_result), .result_error(a_error)
    );
    ot_fp32_rsqrt_rne_reference reference (
        .clk(clk), .rst_n(rst_n), .in_valid(b_in_valid), .in_ready(b_in_ready),
        .argument_code(argument_code), .out_valid(b_out_valid),
        .out_ready(b_out_ready), .result_code(b_result), .result_error(b_error)
    );

    always #1 clk = ~clk;

    //: The two publish on different cycles -- the rewrite takes about 64 where the
    //: reference takes 31 -- so each is latched and the comparison waits for both.
    reg seen_a, seen_b;
    reg [31:0] held_a, held_b;
    reg [1:0]  held_ea, held_eb;
    always @(posedge clk) begin
        if (a_out_valid) begin seen_a <= 1'b1; held_a <= a_result; held_ea <= a_error; end
        if (b_out_valid) begin seen_b <= 1'b1; held_b <= b_result; held_eb <= b_error; end
    end

    integer errors = 0, checked = 0;
    task check(input [31:0] code);
        begin
            @(negedge clk);
            seen_a = 1'b0; seen_b = 1'b0;
            argument_code = code;
            wait (a_in_ready && b_in_ready);
            @(negedge clk); a_in_valid = 1'b1; b_in_valid = 1'b1;
            @(negedge clk); a_in_valid = 1'b0; b_in_valid = 1'b0;
            wait (seen_a && seen_b);
            checked = checked + 1;
            if (held_a !== held_b || held_ea !== held_eb) begin
                errors = errors + 1;
                if (errors < 12)
                    $display("FAIL arg %h: split %h/%0d reference %h/%0d",
                             code, held_a, held_ea, held_b, held_eb);
            end
            @(negedge clk);
        end
    endtask

    integer trial;
    initial begin
        seen_a = 0; seen_b = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        //: refusals
        check(32'h8000_0000); check(32'h0000_0000); check(32'h7f80_0000);
        check(32'hff80_0000); check(32'h7fc0_0001); check(32'hbf80_0000);
        //: the domain's edges
        check(32'h0000_0001); check(32'h007f_ffff); check(32'h0080_0000);
        check(32'h3f80_0000); check(32'h3f80_0001); check(32'h3f7f_ffff);
        check(32'h7f7f_ffff); check(32'h0000_0002);
        //: powers of two, where the exact answer is representable
        for (trial = 0; trial < 64; trial = trial + 1)
            check({1'b0, (8'd127 - 8'd32 + trial[7:0]), 23'd0});
        //: random positive codes
        for (trial = 0; trial < 220; trial = trial + 1)
            check({1'b0, $random} & 32'h7fff_ffff);

        if (errors == 0)
            $display("PASS tb_fp32_rsqrt_split_equiv %0d arguments identical", checked);
        else
            $display("FAIL tb_fp32_rsqrt_split_equiv %0d of %0d differ", errors, checked);
        $finish;
    end
endmodule
