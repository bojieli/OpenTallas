`timescale 1ns/1ps
// 64 edges: identical shift/assert/deassert semantics to the existing reset tree.
module qfd_rst_rep_p62 (input wire clk, input wire d, output wire q0, output wire q1);
    ot_qwen_rst_rep #(.PAD(62)) u_rep (.clk(clk), .d(d), .q0(q0), .q1(q1));
endmodule
