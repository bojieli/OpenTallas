module miter(input clk,rst_n,output trigger);
wire[5:0]g,t;gold a(clk,rst_n,g);gate b(clk,rst_n,t);
assign trigger=(g!=t);
endmodule
