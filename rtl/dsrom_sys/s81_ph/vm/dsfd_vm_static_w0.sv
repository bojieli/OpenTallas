`timescale 1ns/1ps
`default_nettype none
// Five real W0 leaves replace the scalar 29,203-sink source register.
// All roots reserve the same compiler edges. Each leaf has its own clock pin and local reset release. Epoch outputs
// are observation only: mismatches fault in the control leaf and never gate data.
// TWO STAGES (claude S81 VM F1, 2026-10-15, structural, +1 write cycle): source pins registered at P, outputs at P+1,
// so the control leaf's lane function runs register-to-register (P -> P+1) and every dispatch input is a pin register
// at P+2 (native pin rule: no combinational lane path between leaves).
module dsfd_vm_static_w0_payload #(parameter integer NSRC=53)(
 input wire ck,rst_n,
 input wire [4*NSRC-1:0] i_mask,input wire [128*NSRC-1:0] i_data,
 output reg [4*NSRC-1:0] o_mask,output reg [128*NSRC-1:0] o_data,
 output reg [2:0] o_epoch
);
 reg [1:0] rr;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 reg [4*NSRC-1:0] s_mask;reg [128*NSRC-1:0] s_data;
 always @(posedge ck)begin
  s_mask<=i_mask;s_data<=i_data;
  o_mask<=s_mask;
`ifdef OT_VM_W0_MUT_SLICE
  o_data<=s_data^{{(128*NSRC-1){1'b0}},1'b1};
`else
  o_data<=s_data;
`endif
  if(!rr[1])o_epoch<=0;else o_epoch<=o_epoch+3'd1;
 end
endmodule
module dsfd_vm_static_w0_header #(parameter integer NSRC=53)(
 input wire ck,rst_n,
 input wire [NSRC-1:0] i_v,input wire [14*NSRC-1:0] i_row,input wire [8*NSRC-1:0] i_tag,
 output reg [NSRC-1:0] o_v,output reg [14*NSRC-1:0] o_row,output reg [8*NSRC-1:0] o_tag,
 output reg [2:0] o_epoch
);
 reg [1:0] rr;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 reg [NSRC-1:0] s_v;reg [14*NSRC-1:0] s_row;reg [8*NSRC-1:0] s_tag;
 always @(posedge ck)begin
  if(!rr[1])begin s_v<=0;o_v<=0;end else begin s_v<=i_v;o_v<=s_v;end
  s_row<=i_row;s_tag<=i_tag;o_row<=s_row;o_tag<=s_tag;
  if(!rr[1])o_epoch<=0;else o_epoch<=o_epoch+3'd1;
 end
endmodule
`default_nettype wire
