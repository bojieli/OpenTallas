`timescale 1ns/1ps
// Original de062 source, module name only changed. Compare every sampled edge
// of the unmodified existing canonical four-user/epoch/fault stimulus.
module kvn_ctx_copy_equiv #(parameter integer MUT_USER=0,MUT_STALE=0)(
 input wire ck,rst_n,input wire[551:0]head_record,input wire[3:0]ovl_users,calrx,
 input wire adm_done,reseed,input wire[58:0]compiled_identity,
 input wire[1:0]compiled_generation,input wire fault
);
 wire[58:0]ri;wire[1:0]rg;wire rf;
 qkd_kvn_ctx_de062_ref #(.MUT_USER(MUT_USER),.MUT_STALE(MUT_STALE)) reference_dut
 (.ck(ck),.rst_n(rst_n),.head_record(head_record),.ovl_users(ovl_users),.calrx(calrx),
  .adm_done(adm_done),.reseed(reseed),.compiled_identity(ri),.compiled_generation(rg),.fault(rf));
 always @(posedge ck)begin
  #1;
  if({compiled_identity,compiled_generation,fault}!=={ri,rg,rf})
   $fatal(1,"CTX_SOURCE_EQUIV_FAIL got=%h expected=%h",{compiled_identity,compiled_generation,fault},{ri,rg,rf});
 end
endmodule
bind qkd_kvn_ctx_ovl_rope kvn_ctx_copy_equiv #(.MUT_USER(MUT_USER),.MUT_STALE(MUT_STALE))
 actual_context_equiv (.ck(ck),.rst_n(rst_n),.head_record(head_record),.ovl_users(ovl_users),.calrx(calrx),
 .adm_done(adm_done),.reseed(reseed),.compiled_identity(compiled_identity),
 .compiled_generation(compiled_generation),.fault(fault));
