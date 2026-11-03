module ot_s81c_attn_hcore #(parameter integer WPRE=2,BZ0=1,WSEG=0)(input wire clk,rst_n,input wire[7:0]i,output reg[7:0] q);
 always@(posedge clk)if(!rst_n)q<=0;else q<=q+8'(WPRE+BZ0+WSEG)+i;
endmodule
