`timescale 1ns/1ps
// Opt-in source for bounded mapped graph; default production RTL unchanged.
module ot_s81svc7_bmul_graph_input (
 input wire clk, rst_n, input wire [15:0] a,b, input wire pad,
 output wire [31:0] y, output wire flt
);
 (* keep *) reg rst0, rst1;
 (* keep *) reg [32:0] pins;
 always @(posedge clk) begin
   rst0 <= rst_n; rst1 <= rst0;
   pins <= {a,b,pad};
 end
 // Reset becomes a padded zero before the original operand register only.
 ot_hdc_v41x_attn_bmul_s #(.ML(6)) u_mul (.clk(clk),
   .a(pins[32:17]),.b(pins[16:1]),.pad(pins[0] | !rst1),.y(y),.flt(flt));
endmodule
