`timescale 1ns/1ps
`default_nettype none
// Column entry identical to ot_s81_static_column_ingress (pin register on f_ck, two-flop epoch reset on ck,
// EPOCH_SHIFT 1) but with the half-cycle-read crossing ot_s81_static_lane_cross_hr: the delivered word o is
// registered on o_ck (the consumer root, same PLL phase 0 as ck) instead of ck. Same words, same edges.
module ot_s81_static_column_ingress_hr #(parameter integer W=1101)(
 input wire f_ck,input wire [W:0] i,
 input wire ck,rst_n,o_ck,
 output wire [W-1:0] o,output wire fault
);
 reg [W:0] pin;
 always @(posedge f_ck)pin<=i;
 (* async_reg="true" *)reg [1:0] epoch_reset;
 always @(posedge ck or negedge rst_n)
   if(!rst_n)epoch_reset<=0;
   else epoch_reset<={epoch_reset[0],pin[0]};
 ot_s81_static_lane_cross_hr #(.W(W),.EPOCH_SHIFT(1))u_cross(
   .w_ck(f_ck),.w_rst_n(pin[0]),.i(pin[W:1]),
   .r_ck(ck),.r_rst_n(epoch_reset[1]),.o_ck(o_ck),.o(o),.fault(fault));
endmodule
`default_nettype wire
