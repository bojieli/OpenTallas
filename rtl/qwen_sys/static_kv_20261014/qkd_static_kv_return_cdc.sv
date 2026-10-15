`timescale 1ns/1ps
// Corrected native controller return -> fixed core landing slot. Scheduler
// status never changes a slot. Missing/late/tag mismatches latch fault; the
// consumer timeline continues. Clocks/resets need the actual die phase receipt.
module qkd_static_kv_return_cdc #(
 parameter integer DEPTH=8
)(
 input wire pll_hbm,hrst,ck,rsi,
 input wire [293:0] controller_co,input wire [15:0] controller_epoch,
 input wire expected_put,input wire [9:0] expected_sector,
 input wire [15:0] expected_epoch,input wire [5:0] expected_layer,
 output reg actual_valid,output reg [9:0] actual_sector,
 output reg [15:0] actual_epoch,output reg [5:0] actual_layer,
 output reg [255:0] actual_data,output reg fault_hbm,output reg fault_core
);
 (* keep *) reg hr,rs;
 always @(posedge pll_hbm)hr<=hrst;
 always @(posedge ck)rs<=rsi;
 (* keep *) reg hv;
 (* keep *) reg [287:0] hd;
 always @(posedge pll_hbm)hd<={controller_epoch,controller_co[17:12],controller_co[11:9],controller_co[7:1],controller_co[281:26]};
 always @(posedge pll_hbm or negedge hr)if(!hr)hv<=0;else hv<=controller_co[0];
 (* keep *) reg slot;
 (* keep *) reg [31:0] meta;
 always @(posedge ck)meta<={expected_epoch,expected_layer,expected_sector};
 always @(posedge ck or negedge rs)if(!rs)slot<=0;else slot<=expected_put;
 wire ready,valid,overflow,underflow;wire [287:0] data;
 ot_async_fifo #(.WIDTH(288),.DEPTH(DEPTH),.EXT_RST(1))u_return(
  .wr_clk(pll_hbm),.wr_rst_n(hr),.wr_valid(hv),.wr_ready(ready),.wr_data(hd),.wr_overflow(overflow),
  .rd_clk(ck),.rd_rst_n(rs),.rd_valid(valid),.rd_ready(slot),.rd_data(data),.rd_underflow(underflow));
 always @(posedge pll_hbm or negedge hr)
  if(!hr)fault_hbm<=0;else if(overflow||(hv&&!ready))fault_hbm<=1;
 always @(posedge ck)begin actual_data<=data[255:0];actual_sector<=data[265:256];actual_layer<=data[271:266];actual_epoch<=data[287:272];end
 always @(posedge ck or negedge rs)
  if(!rs)begin actual_valid<=0;fault_core<=0;end
  else begin actual_valid<=slot&&valid;if(underflow||(slot&&(!valid||data[287:256]!=meta)))fault_core<=1;end
endmodule
