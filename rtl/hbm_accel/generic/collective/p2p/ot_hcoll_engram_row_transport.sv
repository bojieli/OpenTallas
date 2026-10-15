`timescale 1ns/1ps
`default_nettype none
// Complete288-byte Engram row transport, source-pinned native545 header.
// Raw input sample C -> registered packet output C+1 -> qslots capture C+2.
// All issue controls are compiler slots. Faults do not defer valid publication.
module ot_hcoll_engram_row_packetizer #(
 parameter integer HOME=0,DEST=8
)(
 input wire clk,rst_n,epoch_begin,
 input wire raw_v,input wire [4:0] raw_row,input wire [3:0] raw_sector,
 input wire [255:0] raw_data,
 input wire expect_raw_v,capture_low,publish_v,
 input wire [4:0] publish_row,input wire [2:0] publish_pair,
 output reg out_v,output reg [544:0] out_flit,output reg fault
);
 reg epoch_p,v_p,expect_p,low_p,pub_p;
 reg [4:0] row_p,pr_p;reg [3:0] sector_p;reg [2:0] pair_p;
 reg [255:0] data_p,low_data;reg [4:0] low_row;reg [3:0] low_sector;
 reg low_valid;reg [215:0] seen;
 wire [15:0] pub_index=16'(pr_p*5+pair_p);
 always @(posedge clk)begin
  data_p<=raw_data;row_p<=raw_row;sector_p<=raw_sector;
  pr_p<=publish_row;pair_p<=publish_pair;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin epoch_p<=0;v_p<=0;expect_p<=0;low_p<=0;pub_p<=0;end
  else begin epoch_p<=epoch_begin;v_p<=raw_v;expect_p<=expect_raw_v;low_p<=capture_low;pub_p<=publish_v;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin out_v<=0;fault<=0;low_valid<=0;seen<=0;end
  else if(epoch_p)begin out_v<=0;fault<=0;low_valid<=0;seen<=0;end
  else begin
   out_v<=pub_p;
   if(v_p!==expect_p)fault<=1;
   if((low_p||pub_p)&&!expect_p)fault<=1;
   if(low_p&&pub_p)fault<=1;
   if(expect_p)begin
    if(row_p>=24||sector_p>=9)fault<=1;
    else begin
     if(seen[row_p*9+sector_p])fault<=1;
     seen[row_p*9+sector_p]<=1;
    end
   end
   if(low_p)begin
    if(low_valid||sector_p[0]||sector_p>=8)fault<=1;
    low_valid<=1;low_row<=row_p;low_sector<=sector_p;
   end
   if(pub_p)begin
    if(pr_p>=24||pair_p>4||row_p!=pr_p)fault<=1;
    if(pair_p==4)begin
     if(sector_p!=8||low_valid)fault<=1;
    end else begin
     if(!low_valid||low_row!=pr_p||low_sector!=4'(pair_p*2)||sector_p!=4'(pair_p*2+1))fault<=1;
     low_valid<=0;
    end
   end
  end
 end
 always @(posedge clk)begin
  if(low_p)low_data<=data_p;
  if(pub_p)out_flit<={1'b1,8'(DEST),8'(HOME),pub_index,pair_p==4?{256'b0,data_p}:{data_p,low_data}};
 end
endmodule

// Packet sample C -> lower write output C+1, upper C+2 (when present).
// Real row-store samples these at C+2/C+3. Compiler arrival spacing>=2.
module ot_hcoll_engram_row_assembler #(parameter integer DEST=8)(
 input wire clk,rst_n,epoch_begin,
 input wire in_v,input wire [544:0] in_flit,
 input wire expect_v,input wire [4:0] expect_row,input wire [2:0] expect_pair,
 input wire [7:0] expect_home,
 output reg write_v,output reg [4:0] write_row,output reg [3:0] write_sector,
 output reg [255:0] write_data,output reg fault
);
 reg epoch_p,v_p,expect_p;reg [544:0] flit_p;
 reg [4:0] row_p;reg [2:0] pair_p;reg [7:0] home_p;
 reg pending;reg [255:0] high_data;reg [4:0] high_row;reg [3:0] high_sector;
 reg [119:0] seen;
 wire [15:0] want_index=16'(row_p*5+pair_p);
 always @(posedge clk)begin flit_p<=in_flit;row_p<=expect_row;pair_p<=expect_pair;home_p<=expect_home;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin epoch_p<=0;v_p<=0;expect_p<=0;end
  else begin epoch_p<=epoch_begin;v_p<=in_v;expect_p<=expect_v;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin write_v<=0;fault<=0;pending<=0;seen<=0;end
  else if(epoch_p)begin write_v<=0;fault<=0;pending<=0;seen<=0;end
  else begin
   write_v<=pending||expect_p;pending<=0;
   if(v_p!==expect_p)fault<=1;
   if(pending&&expect_p)fault<=1;
   if(expect_p)begin
    if(row_p>=24||pair_p>4)fault<=1;
    else begin if(seen[want_index])fault<=1;seen[want_index]<=1;end
    if(flit_p[544]!==1'b1||flit_p[543:536]!==8'(DEST)||flit_p[535:528]!==home_p||flit_p[527:512]!==want_index)fault<=1;
    if(pair_p==4&&flit_p[511:256]!==256'b0)fault<=1;
    pending<=pair_p<4;
   end
  end
 end
 always @(posedge clk)begin
  if(pending)begin write_row<=high_row;write_sector<=high_sector;write_data<=high_data;end
  if(expect_p)begin
   write_row<=row_p;write_sector<=4'(pair_p*2);write_data<=flit_p[255:0];
   high_row<=row_p;high_sector<=4'(pair_p*2+1);high_data<=flit_p[511:256];
  end
 end
endmodule
`default_nettype wire
