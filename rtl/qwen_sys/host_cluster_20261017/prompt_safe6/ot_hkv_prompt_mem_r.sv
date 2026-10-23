`timescale 1ns/1ps
// QE3-HROOT-PROMPT 10-21 (prompt n34a/b: macro->reg -399 / macro->macro -301 ps TT at 833 ps; the 32x546 SRAM
// clk->rd_out is ~470 ps and fed a 17-level header compare + the next read address).  Registered-read successor of
// ot_hkv_prompt_mem: capture flops sit DIRECTLY on every used macro rd_out bit (no logic on the macro->flop
// boundary) and the SRAM read address is the caller's REGISTERED read pointer (no rd_out -> r_addr_in path).
// Cost: +2 edges write->head visibility and +2 edges after each pop (static, no backpressure).
//   head    = rd_q = mem[rp] read at the previous edge (read-before-write macro model).
//   head_ok = head belongs to the current rp (rp unchanged for the last two edges) AND that entry was enqueued
//             before the read edge (count minus the enqueues of the last two edges is non-zero; pops only ever
//             remove visible entries, so the subtraction never underflows).  No bypass path is needed.
// Callers keep their pointers/count/admission; they gate every use of head with head_ok.
module ot_hkv_prompt_mem_r #(parameter integer W=120,A=4)(
 input wire ck,rst_n,
 input wire put,enq,                 // put: macro write strobe; enq: the caller's counted enqueue this edge
 input wire[A-1:0]wa,rp,             // write address; registered read pointer (queue head)
 input wire[A:0]count,               // caller's registered occupancy
 input wire[W-1:0]data,
 output wire[W-1:0]head,
 output wire head_ok);
 wire[545:0]mq;
 (* keep *) reg[W-1:0]rd_q;          // direct macro-output capture
 always @(posedge ck) rd_q<=mq[W-1:0];
 reg[A-1:0]a1,a2;reg e1,e2;reg v1,v2;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin a1<=0;a2<=0;e1<=0;e2<=0;v1<=0;v2<=0;end
  else begin a1<=rp;a2<=a1;e1<=enq;e2<=e1;v1<=1'b1;v2<=v1;end
`ifdef OT_PROMPT_MUT_VIS
 wire[A:0]vis=count-(A+1)'(e1);
`else
 wire[A:0]vis=count-(A+1)'(e1)-(A+1)'(e2);
`endif
 assign head=rd_q;
 assign head_ok=v2&&(a2==rp)&&(vis!=0);
`ifdef OT_PROMPT_MUT_ADDR
 wire[A-1:0]ra=rp+1'b1;
`else
 wire[A-1:0]ra=rp;
`endif
 ot_sram_1r1w_32x546_m1_p192_mir u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in(5'(ra)),.rd_out(mq),
 .w_ce_in(put),.w_addr_in(5'(wa)),.wd_in(546'(data)),.w_mask_in({546{1'b1}}));
endmodule
