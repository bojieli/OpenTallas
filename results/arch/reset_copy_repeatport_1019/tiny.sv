module buf2(input [1:0] A,output [1:0] Y);assign Y=A;endmodule
module top(input clk,rst_n,output [5:0] y);
(*keep*)reg[2:0] rr__ot_rlv;
always@(posedge clk or negedge rst_n)if(!rst_n)rr__ot_rlv<=0;else rr__ot_rlv<=3'b111;
buf2 u0(.A({rr__ot_rlv[0],rr__ot_rlv[0]}),.Y(y[1:0]));
buf2 u1(.A({rr__ot_rlv[0],rr__ot_rlv[0]}),.Y(y[3:2]));
buf2 u2(.A({rr__ot_rlv[0],rr__ot_rlv[0]}),.Y(y[5:4]));
endmodule
