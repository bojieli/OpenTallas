module pad #(parameter integer RV=0)(output wire o,input wire pad_i=RV[0]);
assign o=pad_i;
endmodule
module top(input wire i, output wire mismatch);
wire a,b,c;
pad #(.RV(0)) p0(.o(a));
pad #(.RV(1)) p1(.o(b));
`ifdef MUT
pad pe(.o(c));
`else
pad pe(.o(c),.pad_i(i));
`endif
assign mismatch=a | ~b | (c^i);
endmodule
