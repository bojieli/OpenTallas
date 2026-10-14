`timescale 1ns/1ps
// Inject one real regional valid loss after the registered receive face.
// The native tail must flag the broken multi-root seam; underlying exact bench fails on actual fault.
module tb_hdc_vred_phase_mut;
 tb_hdc_vreduce_entries64 u_test();
 initial begin
  repeat(200)@(negedge u_test.clk);
  force u_test.split.u_tail.ival[7]=1'b0;
 end
endmodule
