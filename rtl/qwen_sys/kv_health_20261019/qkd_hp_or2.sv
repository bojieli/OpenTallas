`timescale 1ns/1ps
// KV-HEALTH 10-19: the health-plane join.  Owner 10-19: per-layer health retirement, STATUS after the complete closed
// fault path from every source; continuous sticky global health, never gated / cleared / masked.
// A pure registered 2-input OR (one core edge), NO reset: stickiness is held by the sticky sources (landing ring
// faults, DCAL) and by the explicit sticky qkd_astk_fault_join cells (non-sticky sources, the final sink).  After a
// reset the plane flushes by data (sources clear -> zeros propagate in <= the plane depth); the sink's region reset is
// held until then (qkd_rst_region HOLD 273 >= the 263-edge source-clear + path requirement).  No reset fanout added.
// MUT 1 (bench negative control): input b dropped.
module qkd_hp_or2 #(parameter integer MUT = 0) (
    input  wire ck,
    input  wire a,
    input  wire b,
    output reg  q
);
    always @(posedge ck) q <= (MUT == 1) ? a : (a | b);
endmodule
