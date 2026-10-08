module top(input clk,input din,output q);
wire [2:0] w; assign w[0]=din;
HB4xp67_ASAP7_75t_R h0(.A(w[0]),.Y(w[1]));
HB4xp67_ASAP7_75t_R h1(.A(w[1]),.Y(w[2]));
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(w[2]),.QN(q));
endmodule
