module top(input clk,input din,output q);
wire [3:0] w;
BUFx2_ASAP7_75t_R original_input(.A(din),.Y(w[0]));
HB4xp67_ASAP7_75t_R h0(.A(w[0]),.Y(w[1]));
HB4xp67_ASAP7_75t_R h1(.A(w[1]),.Y(w[2]));
HB4xp67_ASAP7_75t_R h2(.A(w[2]),.Y(w[3]));
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(w[3]),.QN(q));
endmodule
