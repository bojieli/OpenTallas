`timescale 1ns/1ps
`default_nettype none
// Physical native compaction, not a compiler alias: four padded16word TP4
// records become24 contiguous FP32 words in two full512bit nativeVM rows.
// Clock: actual fast1.2GHz collective/VM port. The projection-to-fast bridge
// precedes this leaf. All inputs, output writes and completion have fixed slots.
// R_CYC counts edges after start; values include this leaf's input-pin register.
module ot_s81_hcx_gatherpack #(
 parameter integer WL=4,
 parameter[63:0]R_CYC={16'd14,16'd10,16'd6,16'd2}
)(
 input wire clk,rst_n,start,
 input wire[13:0]raw_base_row,
 input wire i_v,
 input wire[1:0]i_rank,
 input wire[511:0]i_d,
 output reg wq_v,
 output reg[13:0]wq_row,
 output wire[15:0]wq_mask,
 output reg[511:0]wq_d,
 input wire wq_commit,
 output reg done,fault
);
 function automatic integer max_return(input[63:0]r);
  max_return=0;for(integer j=0;j<4;j=j+1)if(r[16*j+:16]>max_return)max_return=r[16*j+:16];
 endfunction
 localparam integer LAST=max_return(R_CYC), W0=LAST+1,W1=LAST+2,END_CYC=LAST+WL+4;
 reg busy;reg[15:0]age;reg[13:0]base;
 reg vq;reg[1:0]rankq;reg[511:0]dq;
 reg[191:0]words[0:3];
 reg[WL-1:0]commit_due;
 wire[3:0]due;
 generate for(genvar j=0;j<4;j=j+1)begin:g_due
  assign due[j]=busy && age+1'b1==R_CYC[16*j+:16];
 end endgenerate
 assign wq_mask=16'hffff;
 always @(posedge clk)begin dq<=i_d;rankq<=i_rank;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;age<=0;vq<=0;wq_v<=0;done<=0;fault<=0;commit_due<=0;end
  else begin
   vq<=i_v;wq_v<=0;done<=0;
   commit_due[0]<=wq_v;
   for(integer p=1;p<WL;p=p+1)commit_due[p]<=commit_due[p-1];
   if(wq_commit!=commit_due[WL-1])fault<=1;
   if(start)begin
    if(busy||raw_base_row[3:0]!=0||(|commit_due))fault<=1;
    busy<=1;age<=0;base<=raw_base_row;
   end
   if(vq!=(|due))fault<=1;
   for(integer j=0;j<4;j=j+1)if(due[j])begin
    // Capture on the compiled edge even when the observed record is wrong.
    // A late valid never repairs or moves the write calendar.
    words[j]<=dq[191:0];if(rankq!=j)fault<=1;
   end
   if(busy)begin
    age<=age+1'b1;
    if(age+1'b1==W0)begin
     wq_v<=1;wq_row<=base;wq_d<={words[2][127:0],words[1],words[0]};
    end
    if(age+1'b1==W1)begin
     wq_v<=1;wq_row<=base+1'b1;wq_d<={256'd0,words[3],words[2][191:128]};
    end
    if(age+1'b1==END_CYC)begin done<=1;busy<=0;end
   end
  end
 end
endmodule
`default_nettype wire
