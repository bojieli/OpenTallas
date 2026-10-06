`timescale 1ps/1fs
`default_nettype none
// Native station release is a pulse. Parent tap_ACK has real backpressure.
// One owed receipt, no new owner authority or payload/memory controller.
// held_frame must be the enclosing parent's actual protected retained frame;
// it cannot retire/rebind while the VM root still awaits this reverse receipt.
// Same actual root clock as the station's input/receipt seats, cold POR only.
module ot_hbm_vm_station_return_bridge #(parameter integer ENABLE=0)(
 input wire clk_sm,por_n,
 input wire station_release,input wire [191:0] station_owner,
 input wire [72:0] held_frame,
 output wire ACK_v,input wire ACK_r,
 output wire [191:0] ACK_owner,output wire [72:0] ACK_frame,
 output wire empty,fault
);
 generate if(!ENABLE)begin:off
  assign ACK_v=0;assign ACK_owner=0;assign ACK_frame=0;
  assign empty=1;assign fault=0;
 end else begin:on
  reg [71:0] code[0:4];
  wire [319:0] raw;wire [4:0] ce,ue;
  for(genvar k=0;k<5;k=k+1)begin:decode
   wire [65:0] d=ot_gpu_w6_secded_pkg::decode64(code[k]);
   assign raw[k*64+:64]=d[63:0];assign ce[k]=d[64];assign ue[k]=d[65];
  end
  wire valid=raw[265];
  wire collision=station_release&&valid;
  assign fault=(|ue)||raw[266]||collision;
  assign ACK_v=valid&&!(|ce)&&!fault;
  assign ACK_owner=raw[191:0];assign ACK_frame=raw[264:192];
  assign empty=!valid&&!(|ce)&&!fault;
  wire [319:0] receipt={53'b0,1'b0,1'b1,held_frame,station_owner};
  wire [319:0] quarantined=raw|(320'd1<<266);
  // A release owed before CE is not backpressurable. Decoded empty-seat CE
  // cannot take priority over that arrival. UE and collisions retain debt.
  always @(posedge clk_sm or negedge por_n)begin
   if(!por_n)for(integer k=0;k<5;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
   else if(!(|ue)&&!raw[266])begin
    if(collision)for(integer k=0;k<5;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(quarantined[k*64+:64]);
    else if(station_release)for(integer k=0;k<5;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(receipt[k*64+:64]);
    else if(|ce)for(integer k=0;k<5;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(raw[k*64+:64]);
    else if(ACK_v&&ACK_r)for(integer k=0;k<5;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
   end
  end
 end endgenerate
endmodule
`default_nettype wire
