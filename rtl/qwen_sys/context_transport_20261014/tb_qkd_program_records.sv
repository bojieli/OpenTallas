`timescale 1ns/1ps
// Component proof: actual metadata parsers, strict1032 ledger and witness.
// The macro-consumed event boundary has separate real-SRAM proofs.
module tb_qkd_program_records;
 parameter integer MUT=0;
 reg ck=0;always #0.5 ck=~ck;
 reg rst=0,b=0,a=0,send=0,receive=0;reg[1:0]typ=0;
 wire tv,ov,tf,rb,ra,rf;wire[547:0]tr;wire[15:0]be,ae;wire[10:0]np;wire[3:0]nd;wire[63:0]ad;
 reg[63:0]digest=64'h51484f5354505247;
 localparam[63:0]FOOTER={32'h58504631,19'd0,1'b1,6'd1,4'd1,2'd2};
 qkd_program_auth_tx tx(.ck(ck),.rst_n(rst),.send_slot(send),.send_type(typ),.begin_v(b),.begin_epoch(16'hface),.expected_pw(11'd1024),.expected_dw(4'd8),.auth_v(a),.auth_epoch(16'hface),.auth_digest(digest),.tx_v(tv),.tx_observed_v(ov),.tx_record(tr),.fault(tf));
 qfd_program_auth_rx rx(.ck(ck),.rst_n(rst),.receive_slot(receive),.rx_v(tv),.rx_record(tr^(MUT==1&&typ==2?(548'd1<<2):548'd0)),.begin_v(rb),.begin_epoch(be),.expected_pw(np),.expected_dw(nd),.auth_v(ra),.auth_epoch(ae),.auth_digest(ad),.fault(rf));
 reg pv=0,dv=0;reg[9:0]pa=0;reg[2:0]da=0;reg[63:0]pd=0,dd=0;
 wire ready,cap,commit,lf;wire[15:0]epoch;wire[63:0]actual_digest;
 qkd_program_commit ledger(.ck(ck),.rst_n(rst),.execution_active(1'b0),.control_stores_ready(1'b1),.begin_v(rb),.begin_epoch(be),.expected_pw(np),.expected_dw(nd),.auth_v(ra),.auth_epoch(ae),.auth_digest(ad),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.pw_full_word(1'b1),.dw_v(dv),.dw_addr(da),.dw_data(dd),.dw_full_word(1'b1),.commit_v(commit),.ready(ready),.fault(lf),.installed_fusedcap(cap),.commit_epoch(epoch),.commit_digest(actual_digest));
 reg ws=0,wr=0,valid_override=1,host_begin=0;wire wtv,wov,wtf,wcf,wcap,installed,wfault;wire[547:0]record;wire[15:0]we;wire[63:0]wd;
 qfd_program_witness_tx wt(.ck(ck),.rst_n(rst),.send_slot(ws),.commit_v(MUT==3?1'b0:commit),.program_ready(ready&&valid_override),.installed_fusedcap(cap),.program_fault(lf),.program_epoch(epoch),.program_digest(actual_digest),.tx_v(wtv),.tx_observed_v(wov),.tx_record(record),.fault(wtf));
 qkd_program_witness_rx witness(.ck(ck),.rst_n(rst),.program_begin_v(host_begin),.receive_slot(wr),.rx_v(wtv),.rx_record(record^(MUT==2?(548'd1<<64):548'd0)),.expected_epoch(16'hface),.expected_digest(digest),.authorized_footer_valid(1'b1),.authorized_footer(FOOTER),.program_commit_v(wcf),.program_commit_epoch(we),.program_commit_digest(wd),.program_installed_valid(installed),.installed_fusedcap(wcap),.fault(wfault));
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task auth_slot(input[1:0]t);begin typ=t;send=1;tick(1);send=0;receive=1;tick(1);receive=0;tick(3);end endtask
 task witness_slot;begin ws=1;tick(1);if(!wov)$fatal(1,"witness slot had no real commit/revocation observation");ws=0;wr=1;tick(1);wr=0;tick(2);end endtask
 integer i;
 initial begin
  tick(5);rst=1;tick(3);
  for(i=0;i<1024;i=i+1)digest={digest[56:0],digest[63:57]}^(i==1023?FOOTER:64'(i+9))^64'(i);
  for(i=0;i<8;i=i+1)digest={digest[56:0],digest[63:57]}^64'(i+2)^64'(1024+i);
  b=1;tick(1);b=0;tick(1);auth_slot(1);
  a=1;tick(1);a=0;tick(1);auth_slot(2);
  for(i=0;i<1024;i=i+1)begin pv=1;pa=i;pd=i==1023?FOOTER:64'(i+9);tick(1);end
  pv=0;for(i=0;i<8;i=i+1)begin dv=1;da=i;dd=i+2;tick(1);end
  dv=0;tick(5);
  if(!ready||!cap||tf||rf||lf)$fatal(1,"actual decoded metadata failed ledger authorization");
  witness_slot();
  if(!installed||!wcap||we!=16'hface||wd!=digest||wfault||wtf)$fatal(1,"actual image commit witness failed");
  valid_override=0;tick(1);witness_slot();
  if(installed||wcap||wfault||wtf)$fatal(1,"real installed-valid revocation did not clear HOST readiness");
  $display("PASS kind13 real metadata->strict1032 ledger->kind14 verified cap and ready0 revocation");$finish;
 end
 initial begin tick(2000);$fatal(1,"timeout");end
endmodule
