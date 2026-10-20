// PROOF ONLY. Each singleton actual macro instance has one shared arbitrary
// read stream for all its cloned consumers. Overapproximates every real memory
// trace; used only for register-copy convergence, never payload equivalence.
module ot_sram_1r1w_32x546_m1_p192_mir(input clk,r_ce_in,input[4:0]r_addr_in,output wire[545:0]rd_out,input w_ce_in,input[4:0]w_addr_in,input[545:0]wd_in,w_mask_in);
 (* anyseq *) reg[545:0]shared_read;
 assign rd_out=shared_read;
endmodule
