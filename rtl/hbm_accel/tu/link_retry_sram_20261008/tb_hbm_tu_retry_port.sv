`timescale 1ns/1ps
module tb_hbm_tu_retry_port;
 localparam W=545,SW=12,CW=10,CAP=256;
 reg clk=0;always#5 clk=~clk;
 reg rst=0,up=0;reg[15:0]epoch=1;
 reg iv=0;wire ir,tv,tr,rr,ov,fault;reg[W-1:0]id=0;
 wire[W-1:0]td,od;wire[SW-1:0]ts,ack,debt;wire[15:0]te,ae;
 reg rv=0,ue=0,ordy=1;reg[W-1:0]rd=0;reg[SW-1:0]rs=0;reg[15:0]re=1;
 wire nak;wire[CW-1:0]ap,available,rx_debt;wire[31:0]retries;
 reg fv=0,fg=1,fn=0;reg[SW-1:0]fs=0;reg[15:0]fe=1;reg[CW-1:0]fp=0;
 reg permit_pop=0;wire pop=permit_pop && rx_debt!=0;
 assign tr=!rv||rr;
 ot_hbm_tu_retry_port #(.ENABLE(1),.TIMEOUT(2048)) dut(
 .clk(clk),.rst_n(rst),.link_up(up),.session(epoch),.in_valid(iv),.in_ready(ir),.in_data(id),
 .tx_valid(tv),.tx_ready(tr),.tx_data(td),.tx_seq(ts),.tx_session(te),
 .rx_valid(rv),.rx_ready(rr),.rx_ue(ue),.rx_data(rd),.rx_seq(rs),.rx_session(re),
 .out_valid(ov),.out_ready(ordy),.out_data(od),.rx_consumed(pop),
 .ack_seq(ack),.ack_nak(nak),.ack_session(ae),.ack_pop(ap),
 .fb_valid(fv),.fb_good(fg),.fb_nak(fn),.fb_seq(fs),.fb_session(fe),.fb_pop(fp),
 .fault(fault),.retained(debt),.available(available),.rx_debt(rx_debt),.replay_count(retries));
 function[W-1:0]payload(input integer n);integer j;begin
 for(j=0;j<W;j=j+1)payload[j]=((j*13+n*31)^(n>>(j%7)))&1;payload[31:0]=n;end endfunction
 reg run=0,corrupt=0;integer sent=0,seen=0,popped=0,inject=0,cyc=0;
 always@(negedge clk)if(run)begin
 cyc=cyc+1;iv=sent<1300;id=payload(sent);ordy=cyc%7!=0;
 fv=1;fg=1;fs=ack;fn=nak;fe=epoch;fp=ap;
 end
 always@(posedge clk)if(run&&rst&&up)begin
 if(tr)begin rv<=tv;rd<=td;rs<=ts;re<=te;ue<=0;
  if(corrupt&&tv&&ts==5&&inject==0)begin ue<=1;inject<=1;end end
 if(iv&&ir)sent<=sent+1;
 if(ov&&ordy)begin if(od!==payload(seen))$fatal(1,"TU545 payload expected%0d got%0d",seen,od[31:0]);seen<=seen+1;end
 if(pop)popped<=popped+1;
 if(sent-popped>CAP)$fatal(1,"conserved landing debt overflow%0d",sent-popped);
 if(fault)$fatal(1,"unexpected retry port fault");
 end
 task tick;begin @(posedge clk);#1;end endtask
 task reset_link;begin run=0;@(negedge clk);rst=0;up=0;iv=0;rv=0;fv=0;ue=0;permit_pop=0;tick;@(negedge clk);rst=1;up=1;tick;end endtask
 integer k;
 initial begin
 reset_link;run=1;
 for(k=0;k<1500&&seen<CAP;k=k+1)tick;
 repeat(16)tick;
 if(seen!=CAP||sent!=CAP||available!=0||rx_debt!=CAP||ir)$fatal(1,"full actual landing credit count");
 $display("PASS TU545 full256 landing debt blocks producer; ACK alone never returns popcredit");
 permit_pop=1;
 for(k=0;k<4000&&popped<1300;k=k+1)tick;
 run=0;iv=0;rv=0;
 if(seen!=1300||popped!=1300||retries!=0)$fatal(1,"TU545 normal delivery");
 $display("PASS full545bit normalstream, cumulativepop wrap, zero faultfree replay");
 reset_link;epoch=2;sent=0;seen=0;popped=0;cyc=0;inject=0;corrupt=1;permit_pop=1;run=1;
 for(k=0;k<6000&&popped<1300;k=k+1)tick;
 run=0;iv=0;rv=0;
 if(seen!=1300||popped!=1300||retries==0)$fatal(1,"TU545 FECUE replay credit ownership");
 $display("PASS FECUE replay exact545; retries consume no duplicate landingcredit");
 @(negedge clk);up=0;iv=1;tick;if(tv||ir||ov)$fatal(1,"linkdown interface escaped");
 epoch=3;reset_link;fv=1;fg=1;fe=2;fs=1300;fp=1300;fn=1;tick;
 if(fault||available!=CAP||debt!=0)$fatal(1,"reset oldsession credits");
 fe=3;fn=0;fs=0;fp=1;tick;if(!fault)$fatal(1,"forged future popcredit accepted");
 $display("PASS coordinated linkdown reset, staleepoch controls, futurepop fault");
 $display("PASS_ALL");$finish;
 end
 initial begin#200000;$fatal(1,"watchdog");end
endmodule
