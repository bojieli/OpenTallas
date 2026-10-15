`timescale 1ns/1ps
`default_nettype none
// Five real W0 leaves replace the scalar 29,203-sink source register.
// All roots reserve the same compiler edge; no data stage or scheduling age is
// added. Each leaf has its own clock pin and local reset release. Epoch outputs
// are observation only: mismatches fault in the control leaf and never gate data.
module dsfd_vm_static_w0_payload #(parameter integer NSRC=53)(
 input wire ck,rst_n,
 input wire [4*NSRC-1:0] i_mask,input wire [128*NSRC-1:0] i_data,
 output reg [4*NSRC-1:0] o_mask,output reg [128*NSRC-1:0] o_data,
 output reg [2:0] o_epoch
);
 reg [1:0] rr;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ck)begin
  o_mask<=i_mask;
`ifdef OT_VM_W0_MUT_SLICE
  o_data<=i_data^{{(128*NSRC-1){1'b0}},1'b1};
`else
  o_data<=i_data;
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
 always @(posedge ck)begin
  if(!rr[1])o_v<=0;else o_v<=i_v;
  o_row<=i_row;o_tag<=i_tag;
  if(!rr[1])o_epoch<=0;else o_epoch<=o_epoch+3'd1;
 end
endmodule
`default_nettype wire
