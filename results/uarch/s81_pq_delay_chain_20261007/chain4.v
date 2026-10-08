module top(input clk,input din,output q);
wire [4:0] w; assign w[0]=din;
HB4xp67_ASAP7_75t_R h0(.A(w[0]),.Y(w[1]));
HB4xp67_ASAP7_75t_R h1(.A(w[1]),.Y(w[2]));
HB4xp67_ASAP7_75t_R h2(.A(w[2]),.Y(w[3]));
HB4xp67_ASAP7_75t_R h3(.A(w[3]),.Y(w[4]));
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(w[4]),.QN(q));
endmodule
