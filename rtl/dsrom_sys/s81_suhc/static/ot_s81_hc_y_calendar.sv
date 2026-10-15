`timescale 1ns/1ps
`default_nettype none
// Actual mapped-memory consumer for a compiler-owned20-row HC operand window.
// Start fixes BOTH producer capture and consumer read cycles. Actual producer
// valid/tag are checked; they cannot stall, retry or move either calendar.
module ot_s81_hc_y_calendar #(
 parameter integer W=8192,ROWS=20,WRITE_FIRST=4,READ_FIRST=8,WRITE_STRIDE=1,READ_STRIDE=1,
 parameter integer EXPLICIT_AGES=0,
 parameter [ROWS*32-1:0] WRITE_AGES=0,READ_AGES=0
)(
 input wire clk,rst_n,start,slot,
 input wire [31:0] job_tag,
 input wire producer_v,
 input wire [31:0] producer_tag,
 input wire [W-1:0] producer_data,
 output wire out_v,
 output wire [W-1:0] out_data,
 output wire [31:0] out_tag,
 output wire [4:0] out_row,
 output wire out_slot,
 output reg done,
 output reg fault
);
 reg start_q,slot_q,pv;
 reg [31:0]tag_q,pt;
 reg [W-1:0]pd;
 always @(posedge clk)begin slot_q<=slot;tag_q<=job_tag;pt<=producer_tag;pd<=producer_data;end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin start_q<=0;pv<=0;end else begin start_q<=start;pv<=producer_v;end
 reg run,owner_slot;
 reg [31:0]owner_tag;
 reg [15:0]age;
 reg write_cycle,read_cycle;
 reg [4:0] write_ordinal,read_ordinal;
 always @(*)begin
  write_cycle=0;read_cycle=0;write_ordinal=0;read_ordinal=0;
  for(integer row=0;row<ROWS;row=row+1)begin
   if(run&&age==(EXPLICIT_AGES?WRITE_AGES[row*32+:32]:WRITE_FIRST+row*WRITE_STRIDE))begin write_cycle=1;write_ordinal=5'(row);end
   if(run&&age==(EXPLICIT_AGES?READ_AGES[row*32+:32]:READ_FIRST+row*READ_STRIDE))begin read_cycle=1;read_ordinal=5'(row);end
  end
 end
 localparam integer LAST_READ=EXPLICIT_AGES?READ_AGES[(ROWS-1)*32+:32]:READ_FIRST+(ROWS-1)*READ_STRIDE;
 wire mem_fault;
 ot_s81_hc_rows_static #(.W(W),.ROWS(ROWS)) rows(
  .clk(clk),.rst_n(rst_n),.reserve_v(start_q),.reserve_slot(slot_q),.reserve_tag(tag_q),
  .wr_v(write_cycle),.wr_slot(owner_slot),.wr_row(write_ordinal),.wr_tag(owner_tag),.wr_data(pd),
  .rd_v(read_cycle),.rd_slot(owner_slot),.rd_row(read_ordinal),.rd_tag(owner_tag),
  .out_v(out_v),.out_data(out_data),.out_tag(out_tag),.out_row(out_row),.out_slot(out_slot),.fault(mem_fault));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin run<=0;age<=0;owner_slot<=0;owner_tag<=0;done<=0;fault<=0;end
  else begin
   done<=0;
   if(start_q)begin
    if(run)fault<=1;
    run<=1;age<=0;owner_slot<=slot_q;owner_tag<=tag_q;
   end else if(run)age<=age+1;
   if(pv!=write_cycle || (write_cycle&&pt!=owner_tag))fault<=1;
   if(mem_fault)fault<=1;
   // Memory rowstore adds3sampleedges, including its own PINcapture.
   if(run&&age==LAST_READ+4)begin run<=0;done<=1;end
  end
 end
`ifndef SYNTHESIS
 initial if((!EXPLICIT_AGES && (READ_FIRST<WRITE_FIRST+2||WRITE_STRIDE<1||READ_STRIDE<WRITE_STRIDE))||ROWS>32)$fatal(1,"HC static calendar visibility");
`endif
endmodule
`default_nettype wire
