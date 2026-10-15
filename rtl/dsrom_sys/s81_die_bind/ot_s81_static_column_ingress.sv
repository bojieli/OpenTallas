`timescale 1ns/1ps
`default_nettype none
// Source-synchronous column entry. i = {packed1101, reset_n}. The marker
// arrives on the same forwarded path as every payload bit; it is not a ready.
// A source pin register captures the complete record. Two destination reset
// flops establish a predetermined epoch shift +1: source edge zero is the first
// edge after the captured marker rises; destination edge zero follows source
// edge one. This removes dependence on how many forwarded trunk stages exist.
// The root reset MUST release before the forwarded marker; clocks are running,
// equal frequency, fixed phase, with the ordinary related-clock setup/hold guard.
// All words, including bubbles, traverse exactly the same slots. No alignment
// training, occupancy state, credits, queue grants or traffic-dependent latency.
module ot_s81_static_column_ingress(
 input wire f_ck,input wire [1101:0] i,
 input wire ck,rst_n,
 output wire [1100:0] o,output wire fault
);
 reg [1101:0] pin;
 always @(posedge f_ck)pin<=i;
 (* async_reg="true" *)reg [1:0] epoch_reset;
 always @(posedge ck or negedge rst_n)
   if(!rst_n)epoch_reset<=0;
   else epoch_reset<={epoch_reset[0],pin[0]};
 ot_s81_static_lane_cross #(.W(1101),.EPOCH_SHIFT(1))u_cross(
   .w_ck(f_ck),.w_rst_n(pin[0]),.i(pin[1101:1]),
   .r_ck(ck),.r_rst_n(epoch_reset[1]),.o(o),.fault(fault));
endmodule
`default_nettype wire
