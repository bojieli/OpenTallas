`timescale 1ns/1ps
// KV-PVFIN output PIN form: +1 output cycle beyond the existing IN_STAGE contract.
// Control PIN flops preserve immediate asynchronous reset; payload stays resetless.
// Between reset edges, every output is exactly the prior core output (including invalid payload). Two slices concurrently add one cycle.
module qkd_pv_fin_s8_pin #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0,
 parameter integer NL=8,
 parameter integer IN_STAGE=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [32*NL-1:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [32*NL-1:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output wire out_valid,output wire [4:0] out_beat,output wire [15:0] out_epoch,output wire [32*NL-1:0] out_data,
 output wire fault
);
 wire  c_out_valid;
 (* keep = 1 *) reg  pin_out_valid;
 assign out_valid=pin_out_valid;
 wire [4:0] c_out_beat;
 (* keep = 1 *) reg [4:0] pin_out_beat;
 assign out_beat=pin_out_beat;
 wire [15:0] c_out_epoch;
 (* keep = 1 *) reg [15:0] pin_out_epoch;
 assign out_epoch=pin_out_epoch;
 wire [32*NL-1:0] c_out_data;
 (* keep = 1 *) reg [32*NL-1:0] pin_out_data;
 assign out_data=pin_out_data;
 wire  c_fault;
 (* keep = 1 *) reg  pin_fault;
 assign fault=pin_fault;
 qkd_pv_fin_s8 #(.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT),.SKEW(SKEW),.MUT(MUT),.NL(NL),.IN_STAGE(IN_STAGE)) u_core (
  .ck(ck),
  .rst_n(rst_n),
  .start(start),
  .epoch(epoch),
  .cal(cal),
  .p0_valid(p0_valid),
  .p0_beat(p0_beat),
  .p0_epoch(p0_epoch),
  .p0_data(p0_data),
  .p1_valid(p1_valid),
  .p1_beat(p1_beat),
  .p1_epoch(p1_epoch),
  .p1_data(p1_data),
  .rz_valid(rz_valid),
  .rz_epoch(rz_epoch),
  .rz(rz),
  .out_valid(c_out_valid),
  .out_beat(c_out_beat),
  .out_epoch(c_out_epoch),
  .out_data(c_out_data),
  .fault(c_fault));
 // Unconditional PIN flops: no external Q feeds an enable mux or other internal load.
 always @(posedge ck) pin_out_data <= c_out_data;
 always @(posedge ck or negedge rst_n) begin
  if(!rst_n) begin pin_out_valid<=0;pin_out_beat<=0;pin_out_epoch<=0;pin_fault<=0;end
  else begin pin_out_valid<=c_out_valid;pin_out_beat<=c_out_beat;pin_out_epoch<=c_out_epoch;pin_fault<=c_fault;end
 end
endmodule
module qkd_pv_fin_s2x8_pin #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0,
 parameter integer IN_STAGE=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [511:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [511:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output wire out_valid,output wire [4:0] out_beat,output wire [15:0] out_epoch,output wire [511:0] out_data,
 output wire fault
);
 wire [1:0] ov,fl;wire [4:0] ob[0:1];wire [15:0] oe[0:1];wire [255:0] od[0:1];
 genvar s;
 generate for(s=0;s<2;s=s+1)begin:g_sl
`ifdef OT_PVFIN_S2X8_MUTANT_LANESWAP
  localparam integer LO=256*(1-s);                                // MUTANT: the slices take each other's lanes
`else
  localparam integer LO=256*s;
`endif
  qkd_pv_fin_s8_pin #(.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT),.SKEW(SKEW),.MUT(MUT),.NL(8),.IN_STAGE(IN_STAGE)) u_sl(.ck(ck),.rst_n(rst_n),
   .start(start),.epoch(epoch),.cal(cal),
   .p0_valid(p0_valid),.p0_beat(p0_beat),.p0_epoch(p0_epoch),.p0_data(p0_data[LO+:256]),
   .p1_valid(p1_valid),.p1_beat(p1_beat),.p1_epoch(p1_epoch),.p1_data(p1_data[LO+:256]),
   .rz_valid(rz_valid),.rz_epoch(rz_epoch),.rz(rz),
   .out_valid(ov[s]),.out_beat(ob[s]),.out_epoch(oe[s]),.out_data(od[s]),.fault(fl[s]));
 end endgenerate
 assign out_valid=&ov,fault=|fl,out_beat=ob[0],out_epoch=oe[0],out_data={od[1],od[0]};
endmodule
