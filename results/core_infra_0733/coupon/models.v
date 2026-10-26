module BUFx16f_ASAP7_75t_R(input A, output Y); assign Y=A; endmodule
module BUFx8_ASAP7_75t_R(input A, output Y); assign Y=A; endmodule
module BUFx4_ASAP7_75t_R(input A, output Y);
`ifdef MUTANT
assign Y=~A;
`else
assign Y=A;
`endif
endmodule
module DFFHQNx1_ASAP7_75t_R(input CLK,D,output reg QN); always @(posedge CLK) QN <= ~D; endmodule
module coupon_gold(input ck, input rst_n, input [3:0] d, output [3:0] q);
DFFHQNx1_ASAP7_75t_R f0(.CLK(ck),.D(d[0]),.QN(q[0]));
DFFHQNx1_ASAP7_75t_R f1(.CLK(ck),.D(d[1]),.QN(q[1]));
DFFHQNx1_ASAP7_75t_R f2(.CLK(ck),.D(d[2]),.QN(q[2]));
DFFHQNx1_ASAP7_75t_R f3(.CLK(ck),.D(d[3]),.QN(q[3]));
endmodule
module miter(input ck,rst_n,fi,ri,input [3:0] d);
wire [3:0] qg,qc;wire fo,ro;
coupon_gold g(.ck(ck),.rst_n(rst_n),.d(d),.q(qg));
coupon c(.ck(ck),.rst_n(rst_n),.d(d),.q(qc),.mp_isl0_ck_i(fi),.mp_isl0_ck_o(fo),.mp_isl0_rst_i(ri),.mp_isl0_rst_o(ro));
always @* begin assert(qg==qc); assert(fi==fo); assert(ri==ro);end
endmodule
