`timescale 1ns/1ps
`default_nettype none
// Captured serial-only summary: no stream-domain signals cross into this leaf.
// Normal capture data is unchanged; fault reporting takes two serial edges.
module dsfd_vm_capture_fault_serial (
 input wire ck, rst_n,
 input wire [39:0] i_lo, i_hi,
 input wire i_status,
 output reg fault
);
 reg [80:0] fault_q;
 always @(posedge ck) begin
  fault_q <= {i_status,i_hi,i_lo};
  if (!rst_n) fault <= 1'b0;
  else fault <= fault | (|fault_q);
 end
endmodule
`default_nettype wire
