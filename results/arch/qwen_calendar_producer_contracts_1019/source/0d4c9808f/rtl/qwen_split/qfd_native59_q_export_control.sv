`timescale 1ns/1ps
// Named physical producer for VM's epoch reset and Q-export start. Both events
// are fixed one-register descendants of actual accepted source events. Missing
// Q commits faults at the reserved start edge; it never holds/reissues start.
module qfd_native59_q_export_control(
 input wire ck,rst_n,
 input wire begin_slot,request_slot,q_committed,
 output reg vm_q_epoch,vm_q_start,
 output reg fault
);
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin vm_q_epoch<=0;vm_q_start<=0;fault<=0;end
  else begin
   vm_q_epoch<=begin_slot;
   vm_q_start<=request_slot;
   if(vm_q_start&&!q_committed)fault<=1;
  end
endmodule
