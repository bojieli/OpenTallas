`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice ring RELAY STAGE (el1011-hbm-b2-vm, 2026-10-12): one <= 500 um wire stage of a credit link -- the
// flit forward through one flop, the credit pulses back through one flop.  No logic: the receiver's buffer depth
// covers the loop (each stage adds 2 cycles to the credit round trip).  W = 2223 for the CW link, 292 (C = 2) for CCW.
module ot_vms_relay #(parameter integer W = 2223, parameter integer C = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] f_in,
    output wire [W-1:0] f_out,
    input  wire [C-1:0] cr_in,       // from downstream
    output reg  [C-1:0] cr_out       // to upstream
);
    // reset only on control (the flit valid, the credits); the flit payload is a plain flop (no reset load)
    reg v; reg [W-2:0] d;
    always @(posedge clk) d <= f_in[W-2:0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v <= 1'b0; cr_out <= '0; end
        else begin v <= f_in[W-1]; cr_out <= cr_in; end
    assign f_out = {v, d};
endmodule
`default_nettype wire
