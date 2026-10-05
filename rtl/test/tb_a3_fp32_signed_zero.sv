`timescale 1ns/1ps
// Signed zero through the qualified binary32 MAC, pinned.
//
// ot_fp32_rne_pkg::fp32_add_rne ends with "if (result[30:0] == 0) result = 0",
// so every zero result is canonicalised to +0, and ot_mac_bf16_fp32_pipe --
// qualified against that family -- does the same.  IEEE and numpy do not:
// (-0) + (-0) is -0 there.  runtime.sim.engines.reduction.ordered_sum is numpy,
// so a reduction over negative zeros returns 0x80000000 where this RTL returns
// 0x00000000.  Reachable whenever every contribution to a reduction is a signed
// zero.  This bench asserts the RTL's answer so the difference is a recorded
// fact rather than a surprise during a reduction mismatch hunt.
//
// It also settles a design question: because zero results canonicalise, +0.0
// and -0.0 are EQUALLY valid identities for an inactive lane of a fixed-width
// reduction pipeline in this RTL, and no bypass path is needed for either.
module tb_a3_fp32_signed_zero;
    reg clk=0, rst_n=0, iv=0;
    reg [15:0] a, b;
    reg [31:0] c;
    wire [31:0] y; wire [1:0] err; wire ov;
    ot_mac_bf16_fp32_pipe u(.clk(clk), .rst_n(rst_n), .valid_in(iv),
                            .a(a), .b(b), .c(c), .y(y), .err(err), .valid_out(ov));
    always #1 clk = ~clk;
    integer errors = 0;
    task shot(input [15:0] aa, input [15:0] bb, input [31:0] cc,
              input [31:0] expect_y, input [255:0] label);
        begin
            @(negedge clk); a=aa; b=bb; c=cc; iv=1;
            @(negedge clk); iv=0;
            wait (ov); @(negedge clk);
            if (y !== expect_y) begin
                $display("FAIL %0s: got %08x expected %08x", label, y, expect_y);
                errors = errors + 1;
            end else
                $display("ok   %0s: %08x", label, y);
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n=1; repeat (2) @(negedge clk);
        // a=-0.0 (BF16 0x8000), b=+1.0 (0x3F80): the inactive-lane identity.
        shot(16'h8000, 16'h3F80, 32'h3F800000, 32'h3F800000, "(-0)+1.0 -> 1.0");
        shot(16'h8000, 16'h3F80, 32'hBF800000, 32'hBF800000, "(-0)+(-1.0) -> -1.0");
        shot(16'h8000, 16'h3F80, 32'h00000000, 32'h00000000, "(-0)+(+0) -> +0");
        // THE CASE IN QUESTION: does a -0 accumulator survive?
        // THE DIVERGENCE.  IEEE and numpy give -0 here; this RTL canonicalises
        // every zero result to +0 (fp32_add_rne: "if (result[30:0] == 0)
        // result = 0").  Asserting the RTL's own answer makes the difference a
        // pinned fact instead of a mismatch someone rediscovers while debugging
        // a reduction against runtime.sim.engines.reduction.
        shot(16'h8000, 16'h3F80, 32'h80000000, 32'h00000000, "(-0)+(-0) -> +0 here, -0 in numpy");
        // And what +0.0 as the identity would do to the same accumulator.
        shot(16'h0000, 16'h3F80, 32'h80000000, 32'h00000000, "(+0)+(-0) -> +0, as IEEE also says");
        shot(16'h8000, 16'h3F80, 32'h00000001, 32'h00000001, "(-0)+tiny -> tiny");
        if (errors == 0)
            $display("PASS: signed-zero behaviour of the qualified binary32 MAC is as pinned");
        else
            $display("FAIL: %0d signed-zero expectations differ", errors);
        $finish;
    end
endmodule
