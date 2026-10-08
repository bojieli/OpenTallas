module top(input clk,input din,output q);
wire [0:0] w;
BUFx2_ASAP7_75t_R original_input(.A(din),.Y(w[0]));
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(w[0]),.QN(q));
endmodule
