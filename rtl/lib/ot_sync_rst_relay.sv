`timescale 1ns/1ps
// Fully synchronous reset distribution for related same-frequency clocks.
// rst_n_in is sampled only on clk_sync; a kept local relay uses destination
// clk. With equal fixed phases, assertion/release reaches the relay after
// exactly three edges, and its consumers observe the new value at edge four.
// Keep clocks running and hold reset low at least four edges. This module
// deliberately contains no asynchronous clear/preset. Identical sync_q pairs
// may merge on clk_sync; the destination relay must remain region-local.
module ot_sync_rst_relay (
    input wire clk_sync,
    input wire clk,
    input wire rst_n_in,
    output wire rst_n
);
    (* async_reg = "true" *) reg [1:0] sync_q;
    (* keep = "true", dont_touch = "true" *) reg local_reset_q;
    always @(posedge clk_sync) sync_q <= {sync_q[0],rst_n_in};
    always @(posedge clk) local_reset_q <= sync_q[1];
    assign rst_n = local_reset_q;
endmodule
