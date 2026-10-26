module amax_al(input v, input [23:0] r_addr, input [31:0] q, input [31:0] d, output [56:0] y);
 
 assign y = {v, r_addr + q[23:0], d};
endmodule
