`timescale 1ns/1ps
// Two statically reserved real VM returns supply one arbitrary {last,payload552}.
// Parent owns registered t_crq and compiler return ownership: read control+14
// edges = request register1 + actualVM12 + consumer capture1. f_crs data is the
// actual shared VM response; parent demuxes only its valid by raw capture slots
// and separately faults unsolicited/overlapping global response ownership.
// Two fixed capture registers, not queues. Output is combinational from those
// registers, then the channel adapter supplies its own registered pin stage.
// Missing loads suppress only this slot's valid and fault; no retry or sliding.
// RX produces real source44/45 VM tuples one edge later. Parent checks overlap
// with gather/reduce writers. Metadata low41 retains independent outer last.
module s81_static_raw_vm_rows #(parameter integer MUT=0, parameter integer REGISTER_VM_WRITES=1)(
 input wire clk,rst_n,
 input wire capture_payload_slot,capture_meta_slot,input wire[512:0]f_crs,
 input wire send_slot,send_last,input wire[2:0]send_channel,
 output wire vm_tx_valid,output wire vm_tx_last,output wire[2:0]vm_tx_channel,
 output wire[551:0]vm_tx_payload,
 input wire rx_slot,rx_valid,rx_last,input wire[551:0]rx_payload,
 input wire[13:0]rx_payload_row,rx_meta_row,input wire[7:0]rx_tag,
 output wire[1101:0]vm_write_sources,output reg fault
);
 reg[511:0]payload_q;reg[40:0]meta_q;reg payload_loaded,meta_loaded;
 assign vm_tx_valid=send_slot && payload_loaded && meta_loaded;
 assign vm_tx_last=meta_q[40];
 assign vm_tx_channel=send_channel;
 assign vm_tx_payload={meta_q[39:0],payload_q} ^ ((MUT==1)?552'b1:552'b0);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin payload_q<=0;meta_q<=0;payload_loaded<=0;meta_loaded<=0;fault<=0;end
  else begin
   if(f_crs[0]!=(capture_payload_slot||capture_meta_slot))fault<=1;
   if(capture_payload_slot && capture_meta_slot)fault<=1;
   if(send_slot && (capture_payload_slot || capture_meta_slot))fault<=1;
   if(capture_payload_slot)begin
    if(payload_loaded)fault<=1;
    if(f_crs[0])begin payload_q<=f_crs[512:1];payload_loaded<=1;end
   end
   if(capture_meta_slot)begin
    if(meta_loaded)fault<=1;
    if(f_crs[0])begin meta_q<=f_crs[41:1];meta_loaded<=1;end
   end
   if(send_slot)begin
    if(!payload_loaded || !meta_loaded || send_last!=meta_q[40] || send_channel>4)fault<=1;
    payload_loaded<=0;meta_loaded<=0;
   end
   if(rx_valid!=rx_slot || (rx_slot && rx_payload_row==rx_meta_row))fault<=1;
  end
 end
 wire[1101:0]write_comb={
  rx_tag,471'b0,rx_last,rx_payload[551:512],16'h0003,rx_meta_row,rx_slot&&rx_valid,
  rx_tag,rx_payload[511:0],16'hffff,rx_payload_row,rx_slot&&rx_valid};
 // Native parent chooses0, combines all producers before its final pin flop.
 // Default1 is the standalone registered-source boundary qualified below.
 generate if(REGISTER_VM_WRITES!=0)begin:g_reg
  reg[1101:0]writes_q;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)writes_q<=0;else writes_q<=write_comb;
  assign vm_write_sources=writes_q;
 end else begin:g_comb
  assign vm_write_sources=write_comb;
 end endgenerate
endmodule
