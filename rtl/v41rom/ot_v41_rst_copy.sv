`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rst_copy (S81-C199 reset partition, 2026-10-19): one KEPT copy of a reset synchroniser's last register.
// q is 0 while rst_pin is low (asynchronous assert) and loads 1 on every rising clk edge after it (synchronous
// release).  Every copy fed by the same rst_pin on the same clock is the same register function, so N copies release
// on exactly the edge the single original register released on (no added cycle, no new data edge); each copy drives
// only its own region's asynchronous resets (<= ~32 loads), so no reset register drives the whole column.
// NOT parameterised (Yosys renames parameterised modules to $paramod..., and a keep by module name would then match
// nothing); keep_hierarchy makes every instance its own cell, so opt_merge cannot fold the copies back together.
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_v41_rst_copy (
    input  wire clk,
    input  wire rst_pin,    // asynchronous, active low
    output reg  rst_n
);
    always @(posedge clk or negedge rst_pin) if (!rst_pin) rst_n <= 1'b0; else rst_n <= 1'b1;
endmodule
