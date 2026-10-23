`timescale 1ns/1ps
// N36 minimum mechanism: actual production four-user kind12 codec vs canonical MU codec.
module tb_hkv_context_n36;
 reg ck=0; always #1 ck=~ck;
 reg rst_n=0,send_slot=0,request_v=0,token_epoch_valid=0;
 reg [58:0]request_tag=0;reg[1:0]request_gen=0;
 reg [17:0]request_token=0,request_position=0;
 reg[15:0]token_epoch=0;
 wire program_ready=1,installed_fusedcap=1;wire[15:0]program_epoch=16'h42;
 wire[63:0]program_digest=64'h1234;
 wire tx_v,tx_observed_v,fault;wire[547:0]tx_record;
 wire rv,ro,rf;wire[547:0]rr;
 qkd_host_native_context_tx_mu dut(.*);
 qkd_host_native_context_tx_mu_ref ref_dut(.ck(ck),.rst_n(rst_n),.send_slot(send_slot),
  .request_v(request_v),.request_tag(request_tag),.request_gen(request_gen),
  .request_token(request_token),.request_position(request_position),
  .token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),
  .program_ready(program_ready),.installed_fusedcap(installed_fusedcap),
  .program_epoch(program_epoch),.program_digest(program_digest),
  .tx_v(rv),.tx_observed_v(ro),.tx_record(rr),.fault(rf));
 integer checked=0;
 always @(negedge ck) if(rst_n)begin
  if({tx_v,tx_observed_v,fault}!=={rv,ro,rf})$fatal(1,"N36_CONTEXT control mismatch");
  if(fault||rf)$fatal(1,"N36_CONTEXT unexpected fault");
  if(tx_observed_v)begin
   if(tx_record!==rr)$fatal(1,"N36_CONTEXT valid payload mismatch");
   checked=checked+1;
  end
 end
 task req(input integer u,input integer pos,input integer seq);
 begin
  @(negedge ck); token_epoch=16'((seq<<2)|u);token_epoch_valid=1;
  @(negedge ck); token_epoch_valid=0;request_v=1;request_position=18'(pos);
  request_token=18'(2000+u*100+pos);request_gen=2'(seq);
  request_tag={token_epoch,6'd0,request_token,request_position[12:0],6'd0};
  @(negedge ck); request_v=0;
 end endtask
 task pair;
 begin @(negedge ck);send_slot=1;repeat(2)@(negedge ck);send_slot=0;@(negedge ck);end
 endtask
 integer round,u;
 initial begin
  repeat(3)@(negedge ck);rst_n=1;
  for(round=0;round<8;round=round+1)begin
   for(u=0;u<4;u=u+1)req(u,round,round+1);
   repeat(4)pair();
  end
  repeat(3)@(negedge ck);
  if(checked!=64)$fatal(1,"N36_CONTEXT checked %0d expected64",checked);
  $display("N36_CONTEXT PASS 64 valid records four users8rounds canonical bits and edges");$finish;
 end
endmodule
