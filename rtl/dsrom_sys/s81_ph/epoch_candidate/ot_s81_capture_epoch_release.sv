`timescale 1ns/1ps
// Engineering candidate; ENABLE=0 preserves the existing reset wiring.
// ENABLE=1 REQUIRES a qualified PLL/source paired precommit interface.
// Each precommit is stable before the last local falling edge preceding the
// SAME common rising edge. Source may commit only after both armed outputs.
// These inputs do not exist on the current closed clock tile. Never tie them
// to refclk, lock, local reset counters or guessed divider phase.
module ot_s81_capture_epoch_release #(parameter integer ENABLE=0)(
 input wire stream_clk, serial_clk,
 input wire legacy_stream_n, legacy_serial_n,
 input wire precommit_stream, precommit_serial,
 output wire armed_stream, armed_serial,
 output wire capture_stream_n, capture_serial_n
);
 generate if (ENABLE) begin: g_epoch
   wire reset_n = legacy_stream_n & legacy_serial_n;
   reg [1:0] arm_s, arm_v;
   reg release_s, release_v;
   always @(posedge stream_clk or negedge reset_n)
     if (!reset_n) arm_s <= 0; else arm_s <= {arm_s[0],1'b1};
   always @(posedge serial_clk or negedge reset_n)
     if (!reset_n) arm_v <= 0; else arm_v <= {arm_v[0],1'b1};
   always @(negedge stream_clk or negedge reset_n)
     if (!reset_n) release_s <= 0;
     else if (arm_s[1] && precommit_stream) release_s <= 1;
   always @(negedge serial_clk or negedge reset_n)
     if (!reset_n) release_v <= 0;
`ifdef S81_EPOCH_MUT_EARLY_SERIAL
     else if (arm_v[1]) release_v <= 1;
`else
     else if (arm_v[1] && precommit_serial) release_v <= 1;
`endif
   assign armed_stream=arm_s[1];
   assign armed_serial=arm_v[1];
   assign capture_stream_n=release_s;
   assign capture_serial_n=release_v;
 end else begin: g_legacy
   assign armed_stream=1'b0;
   assign armed_serial=1'b0;
   assign capture_stream_n=legacy_stream_n;
   assign capture_serial_n=legacy_serial_n;
 end endgenerate
endmodule
