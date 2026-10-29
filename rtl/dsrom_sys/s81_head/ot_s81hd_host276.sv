`timescale 1ns/1ps
`default_nettype none
// Full HSF0 frame over the current 276-wire host lane. With 273 payload
// bits, valid and a two-bit beat index, two beats carry only 546 of553
// source bits: N=3 is mandatory at this unchanged width. Reuses the existing
// fixed-date, sticky-fault beat protocol; all553 bits are preserved.
// Presentation rate <=1frame/3cycles; sampled TX->RX visibility is3edges
// plus relay count (N+1+S under beat_link's cycle-label convention).
// This transport is independent of HBC schedule/context/job-active authority.
// No canonical plan or compiled host dates are changed by these new modules.
module ot_s81hd_host276_tx #(parameter integer MUT_HIGH=0,parameter integer IDLE_ZERO=0)(
 input wire ck,rn,v,input wire[552:0] frame,
 output wire[275:0] lane,output wire fault
);
 wire[552:0] body=frame ^ (MUT_HIGH ? (553'd1<<552) : 553'd0);
 ot_s81hd_beat_tx #(.W(553),.N(3),.P(273),.IDLE_ZERO(IDLE_ZERO)) u_tx(
  .ck(ck),.rn(rn),.v(v),.d(body),.o(lane),.fault(fault));
endmodule
module ot_s81hd_host276_rx(
 input wire ck,rn,input wire[275:0] lane,
 output wire v,output wire[552:0] frame,output wire fault
);
 ot_s81hd_beat_rx #(.W(553),.N(3),.P(273)) u_rx(
  .ck(ck),.rn(rn),.i(lane),.v(v),.d(frame),.fault(fault));
endmodule
`default_nettype wire
