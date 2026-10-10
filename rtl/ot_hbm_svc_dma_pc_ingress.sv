`timescale 1ns/1ps
// CPU/controller vehicle for the fixed, unbackpressured native return ABI.
// Whole-burst bank capacity is reserved before request issue. Payload FIFO
// protection and mapped physical binding remain required before adoption.
module ot_hbm_svc_dma_pc_ingress #(
 parameter integer DEPTH=32,SLOT_BITS=6
)(
 input wire clk,rst,
 output wire reserve_ready,input wire reserve_take,input wire[1:0] reserve_bank,input wire[3:0] reserve_len,
 input wire in_v,input wire[1:0] in_bank,input wire[SLOT_BITS-1:0] in_slot,
 input wire[7:0] in_idx,input wire[255:0] in_data,input wire in_fault,
 input wire[3:0] write_ready,output reg out_v,output reg[1:0] out_bank,
 output reg[SLOT_BITS-1:0] out_slot,output reg[7:0] out_idx,
 output reg[255:0] out_data,output reg out_fault,output reg control_fault
);
 localparam integer PW=$clog2(DEPTH),CW=$clog2(DEPTH+1),MW=SLOT_BITS+9;
 reg[CW-1:0] reserved[0:3],occupied[0:3];
 reg[PW-1:0] head[0:3],tail[0:3];
 reg[255:0] payload[0:3][0:DEPTH-1];
 reg[MW-1:0] metadata[0:3][0:DEPTH-1];
 reg[1:0] turn;
 integer b,j,selected,need[0:3];reg capacity;
 always @* begin
   for(b=0;b<4;b=b+1)need[b]=0;
   for(j=0;j<4;j=j+1)if(j<reserve_len)need[(reserve_bank+j)&3]=need[(reserve_bank+j)&3]+1;
   // All four banks must have one free reservation before a group proposal.
   // This conservative test also admits any partial 1..4-sector group safely.
   capacity=!control_fault;
   for(b=0;b<4;b=b+1)if(reserved[b]>=DEPTH)capacity=0;
   selected=-1;
   for(j=0;j<4;j=j+1)if(selected<0 && occupied[(turn+j)&3]!=0 && write_ready[(turn+j)&3])selected=(turn+j)&3;
   out_v=selected>=0 && !control_fault;out_bank=0;out_slot=0;out_idx=0;out_data=0;out_fault=0;
   if(selected>=0)begin
     out_bank=selected;{out_slot,out_idx,out_fault}=metadata[selected][head[selected]];
     out_data=payload[selected][head[selected]];
   end
 end
 assign reserve_ready=capacity;
 integer k;
 always @(posedge clk)begin
   if(rst)begin
     turn<=0;control_fault<=0;
     for(k=0;k<4;k=k+1)begin reserved[k]<=0;occupied[k]<=0;head[k]<=0;tail[k]<=0;end
   end else begin
     if(reserve_take && (!reserve_ready || reserve_len<1 || reserve_len>4))control_fault<=1;
     if(in_v && (occupied[in_bank]>=DEPTH || occupied[in_bank]>=reserved[in_bank]))control_fault<=1;
     for(k=0;k<4;k=k+1)begin
       reserved[k]<=reserved[k]+(reserve_take?need[k]:0)-(out_v && out_bank==k);
       occupied[k]<=occupied[k]+(in_v && in_bank==k)-(out_v && out_bank==k);
     end
     if(in_v)begin
       payload[in_bank][tail[in_bank]]<=in_data;
       metadata[in_bank][tail[in_bank]]<={in_slot,in_idx,in_fault};tail[in_bank]<=tail[in_bank]+1;
     end
     if(out_v)begin head[out_bank]<=head[out_bank]+1;turn<=out_bank+1;end
`ifndef SYNTHESIS
     if(control_fault)$fatal(1,"DMA native ingress reservation/overflow fault");
`endif
   end
 end
endmodule
