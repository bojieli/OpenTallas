`timescale 1ns/1ps
`default_nettype none
// 0az: ready is ONLY an off-die link input. No on-die consumer ready exists.
// One complete finite block is admitted before launch. Each fixed slot samples
// the next frame and publishes it exactly three edges later, independent of PHY.
// Native SRAM write capture + macro commit requires two seal edges. No stale
// macro content is readable until every configured block word has committed.
module ot_hgi_coll_offdie_rx_block #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire arm_v,input wire [6:0] block_words,
 input wire phy_v,input wire [611:0] phy_flit,output wire phy_ready,
 output wire block_ready,input wire release_v,
 input wire slot_v,input wire [5:0] slot_index,
 output reg pin_v,output reg [611:0] pin_flit,
 output reg fault,output reg [4:0] fault_cause
);
 localparam [2:0] EMPTY=0,FILL=1,SEAL=2,READY=3,DRAIN=4,FLUSH=5;
 reg [2:0] state;
 reg [6:0] count,words,issued;
 reg seal_age;
 reg [1:0] flush_age;
 reg [5:0] ra;
 reg [2:0] vp;
 wire accept=phy_v && phy_ready;
 wire [611:0] mem_data;
 wire issue=slot_v && state==DRAIN && issued<words && slot_index==issued[5:0];
 assign phy_ready=state==FILL && count<words && !fault;
 assign block_ready=(state==READY) || (MUT==2 && state==FILL && count!=0);
 for(genvar b=0;b<2;b=b+1)begin:g_mem
  ot_qkvd_llr_replay_sram_leaf #(.W(306),.MUT(MUT==1 && b==0)) u_mem(
   .ck(clk),.we(accept),.wa(count[5:0]),.ra(ra),
   .din(phy_flit[b*306+:306]),.dout(mem_data[b*306+:306]));
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=EMPTY;count<=0;words<=0;issued<=0;seal_age<=0;flush_age<=0;
   ra<=0;vp<=0;pin_v<=0;pin_flit<=0;fault<=0;fault_cause<=0;
  end else begin
   vp<={vp[1:0],issue};pin_v<=vp[2];
   if(vp[2])pin_flit<=mem_data;
   if(issue)ra<=slot_index;
   // Violations report faults, never reschedule a reserved on-die slot.
   if(arm_v && (state!=EMPTY || block_words==0 || block_words>64))begin fault<=1;fault_cause[0]<=1;end
   if(release_v && !block_ready)begin fault<=1;fault_cause[1]<=1;end
   if(slot_v && !issue)begin fault<=1;fault_cause[2]<=1;end
   // PHY valid is permitted to wait while ready is low. Its data must be held
   // by the external link until handshake; it does not constitute overflow.
   if(arm_v && state==EMPTY && block_words>=1 && block_words<=64)begin
    state<=FILL;count<=0;words<=block_words;issued<=0;
   end
   if(accept)begin
    count<=count+1'b1;
    if(count+1'b1==words)begin state<=SEAL;seal_age<=0;end
   end
   if(state==SEAL)begin
    seal_age<=1;
    if(seal_age)state<=READY;
   end
   if(release_v && block_ready)begin state<=DRAIN;issued<=0;end
   if(issue)begin
    issued<=issued+1'b1;
    if(issued+1'b1==words)begin state<=FLUSH;flush_age<=0;end
   end
   if(state==FLUSH)begin
    flush_age<=flush_age+1'b1;
    if(flush_age==3)state<=EMPTY;
   end
  end
 end
endmodule
`default_nettype wire
