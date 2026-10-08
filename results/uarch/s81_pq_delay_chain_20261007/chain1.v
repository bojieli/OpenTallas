module top(input clk,input din,output q);
wire [1:0] w; assign w[0]=din;
HB4xp67_ASAP7_75t_R h0(.A(w[0]),.Y(w[1]));
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(w[1]),.QN(q));
endmodule
