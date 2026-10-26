`timescale 1ns/1ps
// Diagnostic convergence is a real leaf. Raw reset reaches only a plain D pin.
module s81_area_id_fault_join(
 input wire ck,rst_n,input wire [9:0] i_fault,output reg fault
);
 reg rst_pin_q;reg [1:0] rr;reg [9:0] pin_fault;
 always @(posedge ck)begin
  rst_pin_q<=rst_n;
  if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
  pin_fault<=i_fault;
  if(!rr[1])fault<=0;else fault<=|pin_fault;
 end
endmodule

// Native-shaped parent: only hardleaf instances and static wires. No parent
// flops, soft diagnostic OR, shared clock tie, or hidden global reset adapter.
module s81_area_id_native_quarter #(parameter NSRC=53,BASE=0)(
 input wire ck_sel,ck_meta,input wire [7:0] ck_data,input wire ck_fault,
 input wire rst_sel_n,rst_meta_n,input wire [7:0] rst_data_n,input wire rst_fault_n,
 input wire [NSRC-1:0] i_v,input wire [14*NSRC-1:0] i_row,
 input wire [2*NSRC-1:0] i_lane,input wire [4*NSRC-1:0] i_mask,
 input wire [8*NSRC-1:0] i_tag,input wire [128*NSRC-1:0] i_data,
 input wire [7:0] i_drain_v,input wire [15:0] i_drain_slot,
 output wire [7:0] o_v,output wire [111:0] o_row,output wire [31:0] o_mask,
 output wire [63:0] o_tag,output wire [1023:0] o_data,output wire fault
);
 wire [167:0] sel;wire fs,fm;wire [7:0] fd;
 wire [26*NSRC-1:0] mi;wire [207:0] mo;
 s81_area_selector #(.NSRC(NSRC),.BASE(BASE)) u_sel(
  ck_sel,rst_sel_n,i_v,i_row,i_lane,sel,fs);
 genvar s,k;
 generate for(s=0;s<NSRC;s=s+1)begin
  assign mi[26*s+:26]={i_tag[8*s+:8],i_mask[4*s+:4],i_row[14*s+:14]};
 end
 for(k=0;k<8;k=k+1)begin
  assign {o_tag[8*k+:8],o_mask[4*k+:4],o_row[14*k+:14]}=mo[26*k+:26];
  wire [16*NSRC-1:0] di;wire [127:0] dout;wire [7:0] unused_v;
  for(s=0;s<NSRC;s=s+1)begin assign di[16*s+:16]=i_data[128*s+16*k+:16];end
  s81_area_stripe #(.NSRC(NSRC),.W(16)) u_data(
   ck_data[k],rst_data_n[k],di,sel,i_drain_v,i_drain_slot,unused_v,dout,fd[k]);
  for(s=0;s<8;s=s+1)begin assign o_data[128*s+16*k+:16]=dout[16*s+:16];end
 end endgenerate
 s81_area_stripe #(.NSRC(NSRC),.W(26)) u_meta(
  ck_meta,rst_meta_n,mi,sel,i_drain_v,i_drain_slot,o_v,mo,fm);
 s81_area_id_fault_join u_fault(ck_fault,rst_fault_n,{fd,fm,fs},fault);
endmodule
