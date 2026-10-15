`timescale 1ns/1ps
`default_nettype none
// HLAYOUT=1 staging transpose: HC H rows (hc_gate h_rows, the layout the H landing producer, the HC slab NORM/POST
// and H_STORE use) -> the canonical copy-major FP32-sector order the projection leaves' x SRAM and the HCP chunk8
// reduction consume.  Interleaved VM row q holds elements 8q..8q+7 of all four HC copies (copy k of element e at
// 16-bit slot 4*(e%8)+k).  Canonical stage word w = copy k=w/20, elements 256*(w%20)..+255 (lane l, bank b ->
// element 256*(w%20)+8l+b), i.e. rows 32g..32g+31 (g=w%20) = four consecutive prefetch beats 4g..4g+3.
// Fixed wires + one 16-cell (4 beats x 4 copies x 1024 b) buffer written in alternating orientation per group, so a
// group's four canonical words leave on the four edges while the next group's four beats land (no double buffer).
// Emission order: canonical word 20k+g for the k-th edge after beat 4g+3 (leaf expects (n%4)*20+n/4).  No request,
// ready, wait or arithmetic; +4 stage edges (prefetch settle absorbs them).  Data/order checks fault only.
module ot_s81_hcx_hrow_transpose (
 input wire clk,rst_n,
 input wire in_begin,in_v,
 input wire[6:0]in_word,
 input wire[4095:0]in_d,
 output reg out_v,
 output reg[6:0]out_word,
 output reg[4095:0]out_d,
 output reg fault
);
 reg[1023:0]cell[0:3][0:3];
 reg[6:0]nw;               // next expected raw beat
 reg e_act,e_par;reg[1:0]e_k;reg[4:0]e_g;
 function automatic [1023:0] extract(input[4095:0]d,input integer k);
  for(integer p=0;p<8;p=p+1)for(integer b=0;b<8;b=b+1)extract[16*(8*p+b)+:16]=d[512*p+16*(4*b+k)+:16];
 endfunction
 wire[1:0]j=nw[1:0];wire[4:0]gw=nw[6:2];
 always @(posedge clk)begin
  if(in_v)for(integer k=0;k<4;k=k+1)begin
   if(!gw[0])cell[j][k]<=extract(in_d,k);else cell[k][j]<=extract(in_d,k);
  end
  if(e_act)for(integer q=0;q<4;q=q+1)out_d[1024*q+:1024]<=e_par?cell[e_k][q]:cell[q][e_k];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin nw<=0;e_act<=0;e_par<=0;e_k<=0;e_g<=0;out_v<=0;out_word<=0;fault<=0;end
  else begin
   out_v<=e_act;
   if(e_act)begin out_word<=7'(20*e_k+e_g);e_k<=e_k+1'b1;if(e_k==3)e_act<=0;end
   if(in_begin)begin if(e_act||nw!=0&&nw!=80)fault<=1;nw<=0;end
   if(in_v)begin
    if(in_word!=nw||nw>=80||in_begin)fault<=1;
    nw<=nw+1'b1;
    if(j==3)begin e_act<=1;e_k<=0;e_g<=gw;e_par<=gw[0];if(e_act&&e_k!=3)fault<=1;end
   end
  end
 end
endmodule
`default_nettype wire
