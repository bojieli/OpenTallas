`timescale 1ns/1ps
// Synchronous SRAM prefetches the post-edge queue head; same-edge writes bypass.
// Control pointers/admission remain owned by the unchanged caller.
module ot_hkv_prompt_mem #(parameter integer W=120,A=4)(
 input wire ck,put,input wire[A-1:0]wa,ra_next,input wire[W-1:0]data,
 output wire[W-1:0]head);
 localparam integer NS=(W+15)/16;
 (* keep *) reg[NS-1:0]bypass;
 reg[W-1:0]bd;
 wire[545:0]mq;
 always @(posedge ck) bd<=data;
 for(genvar s=0;s<NS;s=s+1)begin:g_sel
  localparam integer L=16*s,BW=(W-L<16)?W-L:16;
  always @(posedge ck)bypass[s]<=put&&(wa==ra_next);
`ifdef OT_PROMPT_MUT_BYPASS
  assign head[L+:BW]=mq[L+:BW];
`else
  assign head[L+:BW]=bypass[s]?bd[L+:BW]:mq[L+:BW];
`endif
 end
`ifdef OT_PROMPT_MUT_ADDR
 wire[A-1:0]ra=ra_next+1'b1;
`else
 wire[A-1:0]ra=ra_next;
`endif
 ot_sram_1r1w_32x546_m1_p192_mir u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in(5'(ra)),.rd_out(mq),
 .w_ce_in(put),.w_addr_in(5'(wa)),.wd_in(546'(data)),.w_mask_in({546{1'b1}}));
endmodule
