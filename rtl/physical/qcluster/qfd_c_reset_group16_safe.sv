`timescale 1ns/1ps
`default_nettype none
// Diagnostic hard reset-relay payload: sixteen independent two-capture paths.
// No counter substitution, shared enable, asynchronous clear, or latency change.
// Parent grouping/locations/clock phase and release epochs remain UNBOUND.
module qfd_c_reset_group16_safe(input wire ck,input wire[15:0] d,output wire[15:0] q);
 (* keep=1, async_reg="true" *) reg[15:0] first,second;
 always@(posedge ck)begin first<=d;second<=first;end
 assign q=second;
endmodule
`default_nettype wire
