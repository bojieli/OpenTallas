`timescale 1ns/1ps
`default_nettype none
// Actual mapped-memory consumer for a compiler-owned20-row HC operand window.
// Start fixes BOTH producer capture and consumer read cycles. Actual producer
// valid/tag are checked; they cannot stall, retry or move either calendar.
module ot_s81_hc_y_calendar #(
 parameter integer W=8192,ROWS=20,WRITE_FIRST=4,READ_FIRST=8
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
 wire write_cycle=run && age>=WRITE_FIRST && age<WRITE_FIRST+ROWS;
 wire read_cycle=run && age>=READ_FIRST && age<READ_FIRST+ROWS;
 wire mem_fault;
 ot_s81_hc_rows_static #(.W(W),.ROWS(ROWS)) rows(
  .clk(clk),.rst_n(rst_n),.reserve_v(start_q),.reserve_slot(slot_q),.reserve_tag(tag_q),
  .wr_v(write_cycle),.wr_slot(owner_slot),.wr_row(5'(age-WRITE_FIRST)),.wr_tag(owner_tag),.wr_data(pd),
  .rd_v(read_cycle),.rd_slot(owner_slot),.rd_row(5'(age-READ_FIRST)),.rd_tag(owner_tag),
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
   if(run&&age==READ_FIRST+ROWS+3)begin run<=0;done<=1;end
  end
 end
`ifndef SYNTHESIS
 initial if(READ_FIRST<WRITE_FIRST+2||ROWS>32)$fatal(1,"HC static calendar visibility");
`endif
endmodule
`default_nettype wire
