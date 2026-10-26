`timescale 1ns/1ps
`default_nettype none
// Strict partition-pin successors. Each signal input has its own direct-D
// boundary register and each output has an exclusive boundary register.
// Relative to native endpoints: TX +2 edges, RX +2 edges, II remains2.
// All taps are one833ps domain. Hold reset and boot_start=0 long enough to
// flush both face cohorts; assert boot only after published reset release.
module ot_hbm_tkx_2beat_tx_pr(
 input wire clk,rst_n,boot_start,input wire[2340:0]raw,
 output wire[1170:0]beat,output wire fault,slot0
);
 wire[2340:0]raw_pin;wire boot_pin;
 wire[1170:0]beat_native;wire fault_native,slot0_native;
 (* keep *) ot_hbm_face_reg #(.W(2341)) u_in_raw(.clk(clk),.d(raw),.q(raw_pin));
 (* keep *) ot_hbm_face_reg #(.W(1)) u_in_boot(.clk(clk),.d(boot_start),.q(boot_pin));
 ot_hbm_tkx_2beat_tx #(.BANK_BITS(32)) u(.clk(clk),.rst_n(rst_n),.boot_start(boot_pin),.raw(raw_pin),.beat(beat_native),.fault(fault_native),.slot0(slot0_native));
 (* keep *) ot_hbm_face_reg #(.W(1171)) u_out_beat(.clk(clk),.d(beat_native),.q(beat));
 (* keep *) ot_hbm_face_reg #(.W(1)) u_out_fault(.clk(clk),.d(fault_native),.q(fault));
 (* keep *) ot_hbm_face_reg #(.W(1)) u_out_slot(.clk(clk),.d(slot0_native),.q(slot0));
endmodule
module ot_hbm_tkx_2beat_rx_pr #(parameter integer LINK_STAGES=2)(
 input wire clk,rst_n,boot_start,input wire[1170:0]beat,
 output wire[2340:0]raw,output wire fault
);
 wire[1170:0]beat_pin;wire boot_pin;
 wire[2340:0]raw_native;wire fault_native;
 (* keep *) ot_hbm_face_reg #(.W(1171)) u_in_beat(.clk(clk),.d(beat),.q(beat_pin));
 (* keep *) ot_hbm_face_reg #(.W(1)) u_in_boot(.clk(clk),.d(boot_start),.q(boot_pin));
 // TX output face and RX input face are two additional beat-channel edges.
 // Both boot inputs have the same one-edge capture, so phase/warmup uses N+2.
 ot_hbm_tkx_2beat_rx #(.LINK_STAGES(LINK_STAGES+2),.BANK_BITS(32)) u(.clk(clk),.rst_n(rst_n),.boot_start(boot_pin),.beat(beat_pin),.raw(raw_native),.fault(fault_native));
 (* keep *) ot_hbm_face_reg #(.W(2341)) u_out_raw(.clk(clk),.d(raw_native),.q(raw));
 (* keep *) ot_hbm_face_reg #(.W(1)) u_out_fault(.clk(clk),.d(fault_native),.q(fault));
endmodule
`default_nettype wire
