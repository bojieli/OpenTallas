`timescale 1ns/1ps
// SFU/NORM admit guard for the SU_PIN_MARGIN CP (2026-10-06). With the margin
// CP the pending/selected/owned outputs reflect a launch only SHADOW edges
// later, so an admit evaluated in that window would read a stale idle CP.
// SHADOW=0 (default) is a pure pass-through: byte-identical behaviour.
// SHADOW=3 holds busy in the launch cycle (the canonical CP selects combinationally on launch_v) and 3 edges after any launch, covering the 2 input + 1
// output pin edges. Reset clears the shadow (a reset-held CP is already blocked
// by cp_reset_wait in the admit terms).
module ot_hbm_integrated_admit_guard #(parameter integer SHADOW=0)(
 input wire clk,input wire por_n,input wire launch_any,input wire cp_busy,output wire busy);
 generate if(SHADOW==0)begin:off
  assign busy=cp_busy;
 end else begin:on
  reg [SHADOW-1:0] sr;
  always @(posedge clk or negedge por_n)if(!por_n)sr<=0;else sr<={sr[SHADOW-2:0],launch_any};
  assign busy=cp_busy|launch_any|(|sr);
 end endgenerate
endmodule
