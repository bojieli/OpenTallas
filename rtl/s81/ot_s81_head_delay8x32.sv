`timescale 1ns/1ps
// One native paired-lane skew element: exactly eight cycles, 256 state bits.
// Harden this element once; compose the original head skew with j%8 copies.
module ot_s81_head_delay8x32(input wire clk, input wire [31:0] d, output wire [31:0] q);
    reg [255:0] line;
    always @(posedge clk) line <= {line[223:0],d};
    assign q=line[255:224];
endmodule
