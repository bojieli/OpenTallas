module attr_probe(input clk,input a,output reg f,output q);
(* keep=1 *)reg sticky;
always @(posedge clk)sticky<=sticky|a;
(* keep=1,dont_touch=1 *)always @(posedge clk)f<=sticky|a;
assign q=sticky;
endmodule
