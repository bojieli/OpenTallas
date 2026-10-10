// ot_hfd_oreg1x / ot_hfd_oreg3x (vm8-seam 2026-10-09, face clocks): the die-view output registers of ot_hfd_oreg1 / 3
// with the pin register on the FACE die clock leaf (clkf) and a negedge lockup copy on the core clock (clk) in front of
// it (redesign-hbm --xroot lockup): core -> lockup is core-root local (T/2), lockup -> pin register gets T/2 of hold
// margin against any core / face insertion skew.  Same latency as ot_hfd_oreg1 / 3 (the lockup adds no cycle).
// Routed with SYNTH_KEEP_MODULES=... ot_hfd_oreg1x ot_hfd_oreg3x so equal-D output flops are never merged.
module ot_hfd_oreg1x (input wire clk, input wire clkf, input wire d, output reg q);
    reg l;
    always @(negedge clk) l <= d;
    always @(posedge clkf) q <= l;
endmodule
module ot_hfd_oreg3x (input wire clk, input wire clkf, input wire d, output reg q);
    reg s0, s1, l;
    always @(posedge clk) begin s0 <= d; s1 <= s0; end
    always @(negedge clk) l <= s1;
    always @(posedge clkf) q <= l;
endmodule
