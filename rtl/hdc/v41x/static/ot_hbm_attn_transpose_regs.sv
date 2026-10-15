`timescale 1ns/1ps
`default_nettype none
// Literal fixed-profile transpose state. Every18-bit value is an explicit
// clocked cell, not an inferred multiport payload RAM. Data is split into two
// 9216sink half-buffer clock clusters in the physical contract; placement,
// clockdelivery and mappedarea remain unqualified.
module ot_hbm_attn_transpose_regs #(
 parameter integer XOFF=0
)(
 input wire clk,rst_n,w_en_i,w_half_i,input wire[7:0]w_cnt_i,
 input wire[1:0]w_pad_i,input wire[529:0]w_g,
 input wire r_half_i,input wire[7:0]r_c_i,
 input wire sel_i,input wire[575:0]qk_ib,
 output wire[575:0]col,eib,output reg fault
);
 function automatic[17:0]elem(input[264:0]gw,input integer x,input pad);
  if(gw[264])elem={pad,1'b1,4'd0,gw[4*x+:4],gw[128+8*(x/16)+:8]};
  else elem={pad,1'b0,gw[8*x+:8],gw[263:256]};
 endfunction
 initial if(!(XOFF==0||XOFF==16))$fatal(1,"exactTD32/DPT16 transposeXOFF");
 genvar r,h,x;
 generate for(r=0;r<32;r=r+1)begin:g_row
  wire[575:0]choices;
  for(h=0;h<2;h=h+1)begin:g_half
   for(x=0;x<16;x=x+1)begin:g_dim
    reg[17:0]value;
    always @(posedge clk)if(w_en_i&&w_half_i==1'(h)&&w_cnt_i==8'(r/2))
     value<=elem(w_g[(r%2)*265+:265],XOFF+x,w_pad_i[r%2]);
    assign choices[(h*16+x)*18+:18]=value;
   end
  end
  assign col[r*18+:18]=choices[(int'(r_half_i)*16+int'(r_c_i))*18+:18];
 end endgenerate
 assign eib=576'd0; // exactsource REPL0 behavior; issueoperand E-register isexternal.
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;
 else if((w_en_i&&w_cnt_i>=16)||r_c_i>=16)fault<=1;
endmodule
`default_nettype wire
