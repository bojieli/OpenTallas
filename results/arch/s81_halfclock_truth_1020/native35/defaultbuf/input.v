module fc_coupon(input clk_in,input d,output clk_out,output q); wire a,b; BUFx4_ASAP7_75t_R b0(.A(clk_in),.Y(clk_out)); DFFHQNx1_ASAP7_75t_R ff(.CLK(clk_in),.D(d),.QN(q)); endmodule
