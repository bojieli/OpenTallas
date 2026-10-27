module cal_gen(input [11:0] po0_8, po1_8, input [15:0] pv8, k_rl, input st, output [63:0] y);
 assign y = {st?k_rl-16'd1-pv8:16'(po0_8),16'(po1_8),16'(po0_8),pv8};
endmodule
