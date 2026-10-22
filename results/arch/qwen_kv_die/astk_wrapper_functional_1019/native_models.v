module INVx3_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = !A;
endmodule
module BUFx16f_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = A;
endmodule
module BUFx24_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = A;
endmodule
module INVx4_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = !A;
endmodule
module INVx2_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = !A;
endmodule
module BUFx8_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = A;
endmodule
module INVx5_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = !A;
endmodule
module TIEHIx1_ASAP7_75t_R(H);
output H;
assign H = 1'b1;
endmodule
module BUFx2_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = A;
endmodule
module BUFx3_ASAP7_75t_R(A,Y);
input A;
output Y;
assign Y = A;
endmodule
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
always @(posedge CLK or negedge RESETN or negedge SETN) if (!SETN) QN<=0; else if (!RESETN) QN<=1; else QN<=!D;
endmodule
