`timescale 1ns/1ps
// Actual native helper descriptor row0 extension and8-rank join; fixture core/gather inputs.
module tb_qwen_native59_argmax;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,start=0,rv=0,rl=0,cdone=0;
 always #0.5 clk=~clk;
 wire cs,dr,cv,cl,cm,done,fault;wire[5:0]da;
 wire[511:0]cd;wire[58:0]tag;
 wire[17:0]next_token;wire[31:0]next_val;
 reg[63:0]dq=0;reg[511:0]rd=0;reg[2:0]rank=0;
 ot_qwen_tp_seq_w12_vrl_native59 #(.N(8),.NW(18),.RB(3),.CRED(32),.QWEN_FULLSHAPE(1)) dut(
 .clk(clk),.rst_n(rst_n),.rst_nw(rst_n),.start(start),.token(18'd151935),.pos(18'd8191),
 .tag_epoch(16'd19),.tag_stage(6'd37),.r_tag(tag),.done(done),.fault(fault),.next_token(next_token),.next_val(next_val),
 .core_start(cs),.core_done(cdone),.core_next_token(18'd18991),.core_next_val(32'h3f800000),.core_fault(1'b0),
 .desc_re(dr),.desc_addr(da),.desc_q(dq),.vm_rq(512'd0),
 .c_valid(cv),.c_ready(cv),.c_data(cd),.c_last(cl),.c_mode(cm),.c_tag(tag),
 .r_valid(rv),.r_data(rd),.r_last(rl),.r_rank(rank),.r_err(1'b0));
 always @(posedge clk)begin
  cdone<=cs;
  if(dr)dq<=(64'd2 | ((64'd132944 & 65535)<<48) | ((64'd132944>>16)<<18));
 end
 integer k=0,waits=0,bad=0;
 initial begin
  #0.1;rst_n=1;#0.1;rst_n=0;repeat(4)@(negedge clk);rst_n=1;
  start=1;@(negedge clk);start=0;
  while(!cv&&waits<100)begin @(negedge clk);waits=waits+1;end
  if(!cv||cd[32+:18]!=151935||!cm||!cl||tag!=={16'd19,6'd37,18'd151935,13'd8191,6'd0})bad=bad+1;
  @(negedge clk);
  for(k=0;k<8;k=k+1)begin
   rv=1;rl=(k==7);rank=(MUT&&k==7)?3'd3:3'(k);
   rd={462'd0,18'(k*18992+18991),32'(32'h3f800000+k*32'h00800000)};
   @(negedge clk);
  end
  rv=0;rl=0;@(negedge clk);
  if(!done||next_token!=151935||next_val!=32'h43000000||(fault!=(MUT!=0)))bad=bad+1;
  if(bad)$fatal(1,"ARGMAX59 bad=%0d token=%0d value=%x fault=%0d",bad,next_token,next_val,fault);
  $display("PASS ARGMAX59 mutant=%0d actual_row0=132944 local_row=18991 global_token=%0d rank_returns=8 fault=%0d",MUT,next_token,fault);$finish;
 end
endmodule
