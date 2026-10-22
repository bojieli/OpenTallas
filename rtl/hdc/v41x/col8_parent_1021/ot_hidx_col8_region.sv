`timescale 1ns/1ps
module ot_hidx_col8_region(input wire clk,rst_n,qv_b,input wire[567:0]q_b,input wire[543:0]key,input wire[63:0]hid,output wire[31:0]cs_out,output wire cf_out,output wire prdy0,prdy1,prdy2,prdy3);
wire[31:0]cs1,cs2,cs3,cs4;wire cf1,cf2,cf3,cf4;wire p0,p1,p2,p3;
ot_hidx_score_pair8_r0 u_pair0(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid[0+:16]),.cs_out(cs1),.cf_out(cf1),.prdy(p0));
ot_hidx_score_pair8_r1 u_pair1(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid[16+:16]),.cs_in(cs1),.cf_in(cf1),.cs_out(cs2),.cf_out(cf2),.prdy(p1));
ot_hidx_score_pair8_r2 u_pair2(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid[32+:16]),.cs_in(cs2),.cf_in(cf2),.cs_out(cs3),.cf_out(cf3),.prdy(p2));
ot_hidx_score_pair8_r3 u_pair3(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid[48+:16]),.cs_in(cs3),.cf_in(cf3),.cs_out(cs4),.cf_out(cf4),.prdy(p3));
ot_hidx_col8_join u_join(.clk(clk),.rst_n(rst_n),.s(cs4),.f(cf4),.p0(p0),.p1(p1),.p2(p2),.p3(p3),.score(cs_out),.fault(cf_out),.o0(prdy0),.o1(prdy1),.o2(prdy2),.o3(prdy3));
endmodule
