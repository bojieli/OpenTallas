// ot_hfd_oreg1: one die-view output register bit (tools/hbm_die_wrap.py kept_out_regs).  Routed with
// SYNTH_KEEP_MODULES=ot_hfd_oreg1 so equal-D output flops of a wrapper are never merged into one driver of many ports.
module ot_hfd_oreg1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
