`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_xio_fault_join(
 input wire ck,rst_n,request_fault,return_fault,serial_valid,serial_level,transport_fault,output reg fault
);
 // Fixed exceptional initialization guard: old no-reset transport data must not
 // re-latch a prior epoch's diagnostic during common-epoch warm reset. Sticky
 // producers retain any new fault until this six-core-edge flush completes.
 reg[5:0] warm;
 always @(posedge ck or negedge rst_n)if(!rst_n)warm<=0;else warm<={warm[4:0],1'b1};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)fault<=0;
`ifndef OT_VM_XIO_MUT_WARM
  else if(!warm[5])fault<=0;
`endif
`ifdef OT_VM_XIO_MUT_FAULT
  else fault<=fault|request_fault|return_fault;
`else
  else fault<=fault|request_fault|return_fault|(serial_valid&&serial_level)|transport_fault;
`endif
 end
endmodule
`default_nettype wire
