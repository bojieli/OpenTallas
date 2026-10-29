(* blackbox *)
module bbx #(parameter integer W = 4) (input clk, input [W-1:0] d, output [W-1:0] q);
endmodule
module top(input clk, input [521:0] d, output [521:0] q);
  bbx #(.W(522)) u_core (.clk(clk), .d(d), .q(q));
endmodule
