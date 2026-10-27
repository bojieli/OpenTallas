module rg_ipd(input [3:0] wc, input [15:0] gk_wb, input wr, output [24:0] y);
 assign y = {wr, wc, gk_wb + 16'(wc), wc};
endmodule
