`timescale 1ns/1ps
// Independently clocked8-bank native FSR leaf. Original E0 request header / E1 bank pin age; II1.
// Four leaves cover32banks. Slot legal/duplicate checks are real RTL in every leaf; no free parent logic.
// Native ports0..15=SU,16..17=HC; auxiliary ports map return slots20..31.
// Compiler supplies native return slots every issue edge. Restricted choices
// keep14wide SU lanes wired, sparseSU0/1 and HC allow per-beat permutation.
// Replaces the old generic rscatter's pin stage, so E0pins->E1bank outputs.
module dsfd_vm_static_fsr_bank8 #(parameter integer BASE=0)(
 input wire ck,rst_n,input wire [17:0] i_v,input wire [251:0] i_row,
 input wire [89:0] i_slot,input wire [2:0] i_group,
 input wire [11:0] i_aux_v,input wire [167:0] i_aux_row,
 output reg [7:0] o_v,output reg [71:0] o_addr,output reg [63:0] o_tag,
 output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [29:0] v;reg [419:0] row;reg [89:0] slots;reg [2:0] group;
 always @(posedge ck or negedge rn)if(!rn)v<=0;else v<={i_aux_v,i_v};
 always @(posedge ck)begin row<={i_aux_row,i_row};slots<=i_slot;group<=i_group;end
 reg bad;integer p,q,s,t;reg [4:0] bank;reg legal;
 always @*begin
  bad=0;bank=0;legal=1;s=0;t=0;
  for(p=0;p<30;p=p+1)if(v[p])begin
   s=p<18?slots[5*p+:5]:p+2;legal=1;
   if(p==0)legal=s<4;else if(p==1)legal=s<8;
   else if(p<16)legal=s==p;else if(p<18)legal=s>=16 &&s<20;
   if(!legal || (s%4)!=row[14*p+:2])bad=1;
   for(q=p+1;q<30;q=q+1)if(v[q])begin
    t=q<18?slots[5*q+:5]:q+2;
    if(t==s)bad=1;
   end
  end
 end
 wire [7:0] bv,dup;
 genvar g;generate for(g=0;g<8;g=g+1)begin:bank_route
  reg hit,d;reg [8:0] a;reg [7:0] tag;integer j,slot;reg [4:0] b;
  always @*begin
   hit=0;d=0;a=0;tag=0;slot=0;b=0;
   for(j=0;j<30;j=j+1)begin
    slot=j<18?slots[5*j+:5]:j+2;
    b=row[14*j+:5]^{row[14*j+5+:3],2'b00};
    if(v[j] && b==(g+BASE))begin
     if(hit)d=1;hit=1;a=a|row[14*j+5+:9];tag=tag|{group,5'(slot)};
    end
   end
  end
  assign bv[g]=hit&&!d;assign dup[g]=d;
  always @(posedge ck)begin o_addr[9*g+:9]<=a;
`ifdef OT_VM_FSR8_MUT_TAG
   o_tag[8*g+:8]<=tag^8'h1;
`else
   o_tag[8*g+:8]<=tag;
`endif
  end
 end endgenerate
 always @(posedge ck or negedge rn)
  if(!rn)begin o_v<=0;fault<=0;end else begin o_v<=bv;fault<=fault|bad|(|dup);end
endmodule
