`timescale 1ns/1ps
`default_nettype none
// Compiler reserves the scalar result slot. The real reducer result becomes a
// masked VM write, preserving the other seven FP32 words in its sector.
// A missing/mistagged scalar faults instead of rescheduling the write.
module ot_hbm_p_scalar_publish_static(
 input wire clk,rst_n,
 input wire publish_slot,
 input wire [31:0] expected_tag,
 input wire [15:0] publish_sector,
 input wire [2:0] publish_word,
 input wire scalar_valid,
 input wire [31:0] scalar_tag,scalar_fp32,
 output reg [2247:0] vm_wq,
 output reg fault
);
 always @(posedge clk)begin
  if(!rst_n)begin vm_wq<=0;fault<=0;end
  else begin
   vm_wq<=0;
   if(scalar_valid!=publish_slot ||
      (publish_slot&&scalar_tag!=expected_tag))fault<=1;
   if(publish_slot)
    vm_wq[281*publish_sector[2:0]+:281]<=
      {1'b1,publish_sector,{8{scalar_fp32}},8'b1<<publish_word};
  end
 end
endmodule
`default_nettype wire
