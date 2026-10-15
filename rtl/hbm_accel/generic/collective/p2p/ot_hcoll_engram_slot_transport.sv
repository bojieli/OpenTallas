`timescale 1ns/1ps
`default_nettype none
// Explicit160-reservation typed successor. Outer endpoint valid is independent
// of inner application-present: absent slots publish a sequenced application
// NOP. Source metadata comes from actual hash descriptor flops, not a row LUT.
// All input faces sampled C; packet FF changes C+1; qslots samples C+2.
module ot_hcoll_engram_slot_packetizer #(parameter integer HOME=0,DEST=8)(
 input wire clk,rst_n,epoch_begin,
 input wire [3:0] owned_slot_valid,input wire [19:0] owned_slot_global_row,
 input wire response_v,response_present,input wire [4:0] response_row,input wire [3:0] response_sector,
 input wire raw_v,input wire [4:0] raw_row,input wire [3:0] raw_sector,input wire [255:0] raw_data,
 input wire expect_response_v,capture_low,publish_v,input wire [1:0] publish_slot,input wire [2:0] publish_pair,
 output reg out_v,output reg [544:0] out_flit,output reg fault
);
 reg ep,v,p,rv,x,low,pub;reg [4:0] row,rr;reg [3:0] sector,rs,owned_v;
 reg [19:0] owned_rows;reg [1:0] slot;reg [2:0] pair;
 reg [255:0] data,low_data;reg low_valid,low_present;reg [4:0] low_row;reg [3:0] low_sector;
 reg [19:0] seen;
 wire want_present=owned_v[slot];wire [4:0] want_row=owned_rows[slot*5+:5];
 wire [15:0] index=want_present?16'(want_row*5+pair):16'(pair);
 always @(posedge clk)begin
  row<=response_row;sector<=response_sector;rr<=raw_row;rs<=raw_sector;data<=raw_data;
  owned_v<=owned_slot_valid;owned_rows<=owned_slot_global_row;slot<=publish_slot;pair<=publish_pair;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ep<=0;v<=0;p<=0;rv<=0;x<=0;low<=0;pub<=0;end
  else begin ep<=epoch_begin;v<=response_v;p<=response_present;rv<=raw_v;x<=expect_response_v;low<=capture_low;pub<=publish_v;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin out_v<=0;fault<=0;low_valid<=0;seen<=0;end
  else if(ep)begin out_v<=0;fault<=0;low_valid<=0;seen<=0;end
  else begin
   out_v<=pub;
   if(v!==x || rv!==(v&&p))fault<=1;
   if((low||pub)&&!x || (low&&pub))fault<=1;
   if(x)begin
    if(sector>=9 || (p&&(row>=24 || rr!=row || rs!=sector)))fault<=1;
    if(!p && row!=0)fault<=1;
   end
   if(low)begin
    if(low_valid || sector>=8 || sector[0])fault<=1;
    low_valid<=1;low_present<=p;low_row<=row;low_sector<=sector;
   end
   if(pub)begin
    if(pair>4 || p!==want_present || (p && (want_row>=24 || row!=want_row)))fault<=1;
    if(pair<=4)begin if(seen[slot*5+pair])fault<=1;seen[slot*5+pair]<=1;end
    if(pair==4)begin if(sector!=8 || low_valid)fault<=1;end
    else begin
     if(!low_valid || low_present!==p || low_row!=row || low_sector!=4'(pair*2) || sector!=4'(pair*2+1))fault<=1;
     low_valid<=0;
    end
   end
  end
 end
 always @(posedge clk)begin
  if(low)low_data<=data;
  if(pub)out_flit<={want_present,8'(DEST),8'(HOME),index,
   !want_present?512'b0:(pair==4?{256'b0,data}:{data,low_data})};
 end
endmodule

// Exactly160 physical publications,120 actual indexed payloads. Row address
// comes from the registered native header; source verified it against actual
// owned-slot metadata. Original column order is restored in actual SRAM.
// C input capture -> lower write FF C+1 / upper C+2; no ready or data wait.
module ot_hcoll_engram_slot_assembler #(parameter integer DEST=8,HOME_BASE=0)(
 input wire clk,rst_n,epoch_begin,
 input wire in_v,input wire [544:0] in_flit,
 input wire expect_v,input wire [1:0] expect_local_slot,input wire [2:0] expect_pair,input wire [7:0] expect_home,
 output reg write_v,output reg [4:0] write_row,output reg [3:0] write_sector,output reg [255:0] write_data,
 output reg fault,output reg complete
);
 reg ep,v,x;reg [544:0] f;reg [1:0] slot;reg [2:0] pair;reg [7:0] home;
 reg pending;reg [255:0] high;reg [4:0] high_row;reg [3:0] high_sector;
 reg [159:0] physical_seen;reg [119:0] logical_seen;
 wire present=f[544];wire [6:0] idx=f[518:512];wire [4:0] row=5'(idx/7'd5);
 wire [7:0] physical_index=8'((home-HOME_BASE)*20+slot*5+pair);
 always @(posedge clk)begin f<=in_flit;slot<=expect_local_slot;pair<=expect_pair;home<=expect_home;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ep<=0;v<=0;x<=0;end
  else begin ep<=epoch_begin;v<=in_v;x<=expect_v;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin write_v<=0;pending<=0;fault<=0;physical_seen<=0;logical_seen<=0;complete<=0;end
  else if(ep)begin write_v<=0;pending<=0;fault<=0;physical_seen<=0;logical_seen<=0;complete<=0;end
  else begin
   write_v<=pending || (x&&present);pending<=0;complete<=(&physical_seen)&&(&logical_seen);
   if(v!==x || (pending&&x))fault<=1;
   if(x)begin
    if(home<HOME_BASE || home>=HOME_BASE+8 || pair>4)fault<=1;
    else begin if(physical_seen[physical_index])fault<=1;physical_seen[physical_index]<=1;end
    if(f[543:536]!==8'(DEST) || f[535:528]!==home || (|f[527:519]) || idx%7'd5!=pair)fault<=1;
    if(present)begin
     if(idx>=120)fault<=1;
     else begin if(logical_seen[idx])fault<=1;logical_seen[idx]<=1;end
     if(pair==4 && f[511:256]!==256'b0)fault<=1;
     pending<=pair<4;
    end else if(f[511:0]!==512'b0 || row!=0)fault<=1;
   end
  end
 end
 always @(posedge clk)begin
  if(pending)begin write_row<=high_row;write_sector<=high_sector;write_data<=high;end
  if(x&&present)begin
   write_row<=row;write_sector<=4'(pair*2);write_data<=f[255:0];
   high_row<=row;high_sector<=4'(pair*2+1);high<=f[511:256];
  end
 end
endmodule
`default_nettype wire
