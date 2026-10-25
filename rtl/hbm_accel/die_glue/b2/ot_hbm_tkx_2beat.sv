`timescale 1ns/1ps
`default_nettype none
// Selected TKM-only hardware endpoint profiles: no correlated SIDE port.
// Raw2341 → two1171-bit beats, one fault bit, no constant padding pins.
module ot_hbm_tkx_2beat_tx(
 input wire clk,rst_n,boot_start,input wire[2340:0]raw,
 output wire[1170:0]beat,output wire fault,slot0
);
 wire unused_side;
 ot_hbm_static_2beat_tx #(.W(2341),.B(1171),.S(1),
 .CONTROL_MASK({9'h1ff,{2332{1'b0}}}),.HOLD_MASK(2341'd0),.SIDE_CONTROL_MASK(1'b0),.SIDE_HOLD_MASK(1'b0))
 u(.clk(clk),.rst_n(rst_n),.start(boot_start),.d(raw),.side_d(1'b0),.beat(beat),.side_beat(unused_side),.fault(fault),.slot0(slot0));
endmodule
module ot_hbm_tkx_2beat_rx #(parameter integer LINK_STAGES=2)(
 input wire clk,rst_n,boot_start,input wire[1170:0]beat,
 output wire[2340:0]raw,output wire fault
);
 wire unused_side;
 ot_hbm_static_2beat_rx #(.W(2341),.B(1171),.S(1),.LINK_STAGES(LINK_STAGES),
 .CONTROL_MASK({9'h1ff,{2332{1'b0}}}),.HOLD_MASK(2341'd0),.SIDE_CONTROL_MASK(1'b0),.SIDE_HOLD_MASK(1'b0))
 u(.clk(clk),.rst_n(rst_n),.start(boot_start),.beat(beat),.side_beat(1'b0),.q(raw),.side_q(unused_side),.fault(fault));
endmodule
`default_nettype wire
