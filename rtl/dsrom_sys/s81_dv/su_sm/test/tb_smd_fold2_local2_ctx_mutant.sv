`timescale 1ns/1ps
module tb_smd_fold2_local2_ctx_mutant;
 tb_smd_fold2_local2 #(.MUT(0)) u();
 // Corrupt one new sine selector's cloned context; production RTL stays exact.
 always @(negedge u.clk) force u.D.cs_ctx[2] = ~u.D.ctxd[33];
endmodule
