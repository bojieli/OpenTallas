module inv(input a, output y);
INVx1_ASAP7_75t_R u_inv (.A(a),.Y(y));
endmodule
module top(input clk, input d, output q, output gclk);
wire nclk,pclk;
inv \g_half.g_root.u_inv0 (.a(clk),.y(nclk));
inv \wrong_clock_root (.a(nclk),.y(pclk));
DFFHQNx1_ASAP7_75t_R \g_half.ph (.CLK(pclk),.D(d),.QN(q));
ICGx1_ASAP7_75t_R \g_half.u_hcg.u_icg (.CLK(clk),.ENA(q),.SE(1'b0),.GCLK(gclk));
endmodule
