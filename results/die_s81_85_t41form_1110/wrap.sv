module gold_dsel (input logic clk, align, on, input logic [1:0] place, input logic [255:0] sd, output logic [63:0] y);
  ot_meso_dsel #(.W(64), .DEPTH(4), .REG(1), .SPLIT(0), .SREP(1)) u (.clk(clk), .align(align), .on(on), .place(place), .sd(sd), .y(y));
endmodule
module gate_dsel (input logic clk, align, on, input logic [1:0] place, input logic [255:0] sd, output logic [63:0] y);
  ot_meso_dsel #(.W(64), .DEPTH(4), .REG(1), .SPLIT(0), .SREP(8)) u (.clk(clk), .align(align), .on(on), .place(place), .sd(sd), .y(y));
endmodule
