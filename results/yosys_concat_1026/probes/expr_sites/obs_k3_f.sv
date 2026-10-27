module obs_k3(input [6:0] k3, input [7:0] pe, pc, output [23:0] y);
 wire[6:0] k3_rel=k3-7'(77);
 assign y = {1'b1,1'b1,(k3==7'd64)?6'd0:((k3>7'd64)?k3_rel[5:0]:k3[5:0]),(k3==7'd64)?pe:pc};
endmodule
