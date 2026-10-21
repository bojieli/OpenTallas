`timescale 1ns/1ps
module tb_hkv_mu4_record_pair #(parameter integer MUT=0);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[1:0]send_kind=0;reg request_v=0,token_epoch_valid=0;
 reg[58:0]request_tag=0;reg[1:0]request_gen=0;reg[17:0]request_token=0,request_position=0;
 reg[15:0]token_epoch=0;wire tx_v,tx_observed_v,fault;wire[547:0]tx_record;
 wire commit_v,installed_valid,installed_fusedcap;wire[15:0]commit_epoch;wire[63:0]commit_digest;
 qkd_host_record_port_mu #(.MU(1),.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.send_kind(send_kind),
 .request_v(request_v),.request_tag(request_tag),.request_gen(request_gen),.request_token(request_token),.request_position(request_position),
 .token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),.begin_v(1'b0),.begin_epoch(16'b0),.expected_pw(11'b0),.expected_dw(4'b0),
 .auth_v(1'b0),.auth_epoch(16'b0),.auth_digest(64'b0),.program_ready(1'b1),.program_epoch(16'h1234),.program_digest(64'h0123456789abcdef),
 .authorized_footer_valid(1'b0),.authorized_footer(64'b0),.witness_slot(1'b0),.rx_v(1'b0),.rx_record(548'b0),
 .commit_v(commit_v),.installed_valid(installed_valid),.installed_fusedcap(installed_fusedcap),.commit_epoch(commit_epoch),.commit_digest(commit_digest),
 .tx_v(tx_v),.tx_observed_v(tx_observed_v),.tx_record(tx_record),.fault(fault));
 reg[58:0]expected[0:3];integer checks=0,pairs=0;
 task tick;begin @(posedge ck);#1;end endtask
 task req(input integer u,input integer seq,input integer pos);reg[15:0]e;begin
  e=16'(16'h1000+seq*4+u);
  @(negedge ck);token_epoch_valid=1;token_epoch=e;tick();
  @(negedge ck);token_epoch_valid=0;request_v=1;request_token=18'(100+u);request_position=18'(pos);request_gen=2'(seq);
  request_tag={e,6'd0,18'(100+u),13'(pos),6'd0};expected[u]=request_tag;tick();
  @(negedge ck);request_v=0;tick();
 end endtask
 task check_record(input integer u);begin
  checks=checks+1;
  if(!tx_v||!tx_observed_v||tx_record[58:0]!==expected[u]||tx_record[542:539]!=4'd12)
   $fatal(1,"MU4_RECORD_PAIR FAIL user=%0d gotuid=%0d observed=%b tag=%h expected=%h",u,tx_record[44:43],tx_observed_v,tx_record[58:0],expected[u]);
 end endtask
 task pair(input integer filler);begin
  @(negedge ck);send_kind=3;tick();
  @(negedge ck);send_kind=3;tick();check_record(filler);
  @(negedge ck);send_kind=0;tick();check_record(0);
  tick();pairs=pairs+1;
 end endtask
 initial begin
  repeat(4)tick();@(negedge ck);rst_n=1;repeat(4)tick();
  for(integer u=0;u<4;u=u+1)req(u,0,0);
  pair(1);pair(2);pair(3);
  req(2,1,1);pair(0); // continuing step updates own epoch without readmitting filler
  req(2,2,17);pair(2); // discontinuous position establishes a fresh admission
  if(fault)$fatal(1,"MU4_RECORD_PAIR FAIL sticky fault");
  $display("MU4_RECORD_PAIR PASS contexts4 pairs=%0d checks=%0d independent_epochs continuing_then_readmit",pairs,checks);$finish;
 end
endmodule
