module gate(input clk,en,output q);ICGx1_ASAP7_75t_R u_icg(.CLK(clk),.ENA(en),.SE(1'b0),.GCLK(q));endmodule
module pair(input clk,en,output a,b);gate ga(clk,en,a);gate gb(clk,en,b);endmodule
module top(input clk,en,output [3:0] q);pair d1(clk,en,q[0],q[1]);pair d2(clk,en,q[2],q[3]);endmodule
