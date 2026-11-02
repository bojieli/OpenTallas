`timescale 1ps/1fs
`default_nettype none
module su31_ft_7(input wire clk,rst_n,input wire[2724:0]d,input wire ea,output wire[2724:0]q,output wire eq);
wire[2724:0] data[0:7];wire epoch[0:7];assign data[0]=d;assign epoch[0]=ea;assign q=data[7];assign eq=epoch[7];
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s0(.clk(clk),.rst_n(rst_n),.d(data[0]),.ea(epoch[0]),.q(data[1]),.eq(epoch[1]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s1(.clk(clk),.rst_n(rst_n),.d(data[1]),.ea(epoch[1]),.q(data[2]),.eq(epoch[2]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s2(.clk(clk),.rst_n(rst_n),.d(data[2]),.ea(epoch[2]),.q(data[3]),.eq(epoch[3]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s3(.clk(clk),.rst_n(rst_n),.d(data[3]),.ea(epoch[3]),.q(data[4]),.eq(epoch[4]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s4(.clk(clk),.rst_n(rst_n),.d(data[4]),.ea(epoch[4]),.q(data[5]),.eq(epoch[5]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s5(.clk(clk),.rst_n(rst_n),.d(data[5]),.ea(epoch[5]),.q(data[6]),.eq(epoch[6]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s6(.clk(clk),.rst_n(rst_n),.d(data[6]),.ea(epoch[6]),.q(data[7]),.eq(epoch[7]));
endmodule
module su31_ft_8(input wire clk,rst_n,input wire[2724:0]d,input wire ea,output wire[2724:0]q,output wire eq);
wire[2724:0] data[0:8];wire epoch[0:8];assign data[0]=d;assign epoch[0]=ea;assign q=data[8];assign eq=epoch[8];
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s0(.clk(clk),.rst_n(rst_n),.d(data[0]),.ea(epoch[0]),.q(data[1]),.eq(epoch[1]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s1(.clk(clk),.rst_n(rst_n),.d(data[1]),.ea(epoch[1]),.q(data[2]),.eq(epoch[2]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s2(.clk(clk),.rst_n(rst_n),.d(data[2]),.ea(epoch[2]),.q(data[3]),.eq(epoch[3]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s3(.clk(clk),.rst_n(rst_n),.d(data[3]),.ea(epoch[3]),.q(data[4]),.eq(epoch[4]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s4(.clk(clk),.rst_n(rst_n),.d(data[4]),.ea(epoch[4]),.q(data[5]),.eq(epoch[5]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s5(.clk(clk),.rst_n(rst_n),.d(data[5]),.ea(epoch[5]),.q(data[6]),.eq(epoch[6]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s6(.clk(clk),.rst_n(rst_n),.d(data[6]),.ea(epoch[6]),.q(data[7]),.eq(epoch[7]));
ot_dp_st #(.W(2725)) u_ft_L5r0_1_s7(.clk(clk),.rst_n(rst_n),.d(data[7]),.ea(epoch[7]),.q(data[8]),.eq(epoch[8]));
endmodule
`default_nettype wire
