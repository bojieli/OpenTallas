`timescale 1ns/1ps
// A low-phase transparent alarm qualifier holds through the actual launch
// edge and all new-Q settling. It suppresses healthy DMR/complementary-state
// comparison hazards without waiving a clock, reset, or data path. Persistent
// faults detected while high propagate at the next low phase before a new
// rising-edge authorization. POR is required for real clocks as elsewhere.
module ot_w5_fault_low(input wire clk,rst_n,alarm,output wire settled);
 wire d=rst_n & alarm;
`ifdef SYNTHESIS
 (* keep,dont_touch *) DLLx1_ASAP7_75t_R u_latch(.CLK(clk),.D(d),.Q(settled));
`else
 reg q;
 always @* if(!clk) q=d;
 assign settled=q;
`endif
endmodule
