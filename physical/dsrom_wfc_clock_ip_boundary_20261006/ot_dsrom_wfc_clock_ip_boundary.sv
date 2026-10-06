`timescale 1ps/1fs
// Explicit external coherent-IP boundary, NOT a divider or PLL implementation.
// The external source owns acquisition and sticky invalidity until cold POR.
// No combinational clock gate, waveform change, or stop guarantee is added here.
module ot_dsrom_wfc_clock_ip_boundary #(parameter integer ENABLE=0)(
 input wire ip_fast_clk, ip_slow_clk, ip_phase_valid, ip_sticky_fault,
 output wire fast_clk, slow_clk, clock_source_fault
);
 generate if (ENABLE==0) begin:g_off
  assign fast_clk=0;
  assign slow_clk=0;
  assign clock_source_fault=1;
 end else begin:g_on
  assign fast_clk=ip_fast_clk;
  assign slow_clk=ip_slow_clk;
  assign clock_source_fault=ip_sticky_fault || !ip_phase_valid;
 end endgenerate
endmodule
