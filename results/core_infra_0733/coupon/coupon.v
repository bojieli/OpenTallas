module coupon(input ck, input rst_n, input [3:0] d, output [3:0] q);
DFFHQNx1_ASAP7_75t_R f0(.CLK(ck),.D(d[0]),.QN(q[0]));
DFFHQNx1_ASAP7_75t_R f1(.CLK(ck),.D(d[1]),.QN(q[1]));
DFFHQNx1_ASAP7_75t_R f2(.CLK(ck),.D(d[2]),.QN(q[2]));
DFFHQNx1_ASAP7_75t_R f3(.CLK(ck),.D(d[3]),.QN(q[3]));
endmodule
