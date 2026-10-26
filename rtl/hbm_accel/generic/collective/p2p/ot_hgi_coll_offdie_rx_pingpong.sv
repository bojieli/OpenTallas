`timescale 1ns/1ps
`default_nettype none
// Two complete blocks: off-die fill overlaps deterministic drain of other bank.
// Explicit bank commands are checked. No on-die backpressure is introduced.
module ot_hgi_coll_offdie_rx_pingpong #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire arm_v,arm_bank,input wire [6:0] block_words,
 input wire phy_v,input wire [611:0] phy_flit,output wire phy_ready,
 output wire [1:0] block_ready,
 input wire release_v,release_bank,
 input wire slot_v,slot_bank,input wire [5:0] slot_index,
 output reg pin_v,output reg [611:0] pin_flit,
 output wire fault,output wire [6:0] fault_cause
);
 reg fill_bank,drain_bank,drain_active,flushing;
 reg [6:0] words[0:1];
 reg [6:0] drain_words;
 reg [2:0] flush_age;
 reg [1:0] ctl_fault;
 wire [1:0] ready,pv,bfault;
 wire [9:0] bcause;
 wire [1223:0] pd;
 wire arm_ok=arm_v && !phy_ready;
 wire release_ok=release_v && !drain_active && block_ready[release_bank];
 wire slot_ok=slot_v && drain_active && !flushing && slot_bank==drain_bank;
 assign phy_ready=ready[fill_bank] && !fault;
 assign fault=(|bfault)||(|ctl_fault);
 assign fault_cause={ctl_fault,bcause[4:0]|bcause[9:5]};
 for(genvar b=0;b<2;b=b+1)begin:g_block
  ot_hgi_coll_offdie_rx_block #(.MUT(MUT==1 && b==0?1:0)) u_block(
   .clk(clk),.rst_n(rst_n),.arm_v(arm_ok && arm_bank==b),.block_words(block_words),
   .phy_v(phy_v && (MUT==3 && drain_active ? !fill_bank:fill_bank)==b && !fault),.phy_flit(phy_flit),.phy_ready(ready[b]),
   .block_ready(block_ready[b]),.release_v(release_ok && release_bank==b),
   .slot_v(slot_ok && ((MUT==2?!drain_bank:drain_bank)==b)),.slot_index(slot_index),
   .pin_v(pv[b]),.pin_flit(pd[b*612+:612]),.fault(bfault[b]),.fault_cause(bcause[b*5+:5]));
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fill_bank<=0;drain_bank<=0;drain_active<=0;flushing<=0;
   words[0]<=0;words[1]<=0;drain_words<=0;flush_age<=0;ctl_fault<=0;
   pin_v<=0;pin_flit<=0;
  end else begin
   // Final registered merge: slot -> bank pin+3 -> merged pin+4.
   pin_v<=|pv;
   if(|pv)pin_flit<=({612{pv[0]}}&pd[0+:612])|({612{pv[1]}}&pd[612+:612]);
   if(arm_v && !arm_ok)ctl_fault[0]<=1;
   if(release_v && !release_ok)ctl_fault[1]<=1;
   if(slot_v && !slot_ok)ctl_fault[1]<=1;
   if(arm_ok)begin fill_bank<=arm_bank;words[arm_bank]<=block_words;end
   if(release_ok)begin
    drain_bank<=release_bank;drain_active<=1;flushing<=0;drain_words<=words[release_bank];
   end
   if(slot_ok && {1'b0,slot_index}+1'b1==drain_words)begin flushing<=1;flush_age<=0;end
   if(flushing)begin
    flush_age<=flush_age+1'b1;
    if(flush_age==4)begin drain_active<=0;flushing<=0;end
   end
  end
 end
endmodule
`default_nettype wire
