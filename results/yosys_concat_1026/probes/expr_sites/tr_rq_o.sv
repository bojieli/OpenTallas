module tr_rq(input cv, input [15:0] cs, input [2:0] lo, input [2:0] kr, output [16:0] y);
 assign y = {cv,{cs[15:3],lo}+16'(kr)};
endmodule
