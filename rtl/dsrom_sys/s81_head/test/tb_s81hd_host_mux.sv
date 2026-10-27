`timescale 1ns/1ps
module tb_s81hd_host_mux #(parameter integer MUT=0);
 reg ck=0,rst_n=0,context_valid=0;always #0.4165 ck=~ck;
 reg h0v=0,h1v=0,cv=0;reg[552:0]h0=0,h1=0,cd=0;reg[1103:0]localring=0;
 reg[16:0]source_fault=0;wire[1103:0]fromprev;wire rv;wire[552:0]rd;
 wire[1:0]tv;wire[1105:0]td;wire[16:0]fault;
 ot_s81hd_host_frame_mux #(.MUT(MUT))dut(.ck(ck),.rst_n(rst_n),.context_valid(context_valid),
 .host0_v(h0v),.host1_v(h1v),.host0_d(h0),.host1_d(h1),.local_ring(localring),.source_fault(source_fault),
 .ctl_v(cv),.ctl_d(cd),.from_prev(fromprev),.ctl_rx_v(rv),.ctl_rx_d(rd),.lane_tx_v(tv),.lane_tx_d(td),.fault(fault));
 reg[16:0]rf=0,reported=0;integer gap=0,n=0,frames=0;reg[16:0]events;reg hf,fw,cs,cfg,result,status,statdue,req,expected_v;
 reg[552:0]expected_d;reg[1103:0]expected_ring;reg[1:0]expected_tv;
 task tick;
 begin
  #0.02;
  hf=h0v&&h0[552]&&h0[3:0]==7;fw=localring[0]&&localring[3:1]==6;
  cs=h1v&&h1[552]&&h1[3:0]==6;cfg=cs&&context_valid;
  result=cv&&cd[552]&&cd[3:0]==9;status=cv&&cd[552]&&cd[3:0]==8;
  statdue=(|(rf&~reported))&&gap==0&&!fw&&!cfg;req=fw||cfg||statdue;
  expected_v=req&&gap==0;
  expected_ring=0;expected_ring[532:21]=h0[527:16];expected_ring[8:4]=1;expected_ring[3:1]=6;expected_ring[0]=hf;
  expected_d=0;expected_d[552]=1;
  if(fw)begin expected_d[527:16]=localring[532:21];expected_d[3:0]=7;end
  else if(cfg)expected_d=h1;
  else begin expected_d[32:16]=rf;expected_d[3:0]=8;end
  expected_tv={status,result};
  if(fromprev!==expected_ring)$fatal(1,"ring metadata/payload miter n%0d",n);
  if(rv!==expected_v||(rv&&rd!==expected_d))$fatal(1,"host authority/frame miter n%0d",n);
  if(tv!==expected_tv||(tv[0]&&td[552:0]!==cd)||(tv[1]&&td[1105:553]!==cd))$fatal(1,"lane output miter n%0d",n);
  if(rv)frames++;
  events=source_fault;
  events[6]=events[6]||(cv&&!result&&!status);
  events[5]=events[5]||(req&&gap!=0);
  events[4]=events[4]||(fw&&cfg);
  events[3]=events[3]||(cs&&!context_valid);
  events[2]=events[2]||(h1v&&!cs);
  events[1]=events[1]||(h0v&&!hf);
  @(posedge ck);#0.02;
  if(expected_v&&statdue)reported=rf;
  rf=rf|events;
  if(expected_v)gap=2;else if(gap!=0)gap--;
  if(fault!==rf)$fatal(1,"sticky fault miter n%0d expected%h got%h",n,rf,fault);
  n++;
  @(negedge ck);
 end endtask
 integer i,j;
 initial begin
  repeat(4)@(negedge ck);rst_n=1;
  // A real CSR must not reach ctl before HBC context commit.
  h1v=1;h1[552]=1;h1[3:0]=6;h1[87:24]=64'hfedcba9876543210;tick();h1v=0;
  repeat(4)tick();context_valid=1;
  for(i=0;i<400;i++)begin
   for(j=0;j<16;j++)begin h0[16+j*32+:32]=$urandom;cd[16+j*32+:32]=$urandom;end
   h0[552]=1;h0[3:0]=7;
   localring=0;for(j=0;j<16;j++)localring[21+j*32+:32]=$urandom;
   localring[0]=1;localring[3:1]=6;
   h0v=1;cv=1;cd[552]=1;cd[3:0]=(i%2)?8:9;tick();
   h0v=0;cv=0;localring=0;repeat(2)tick();
   h1v=1;h1[552]=1;h1[3:0]=6;h1[87:24]={$urandom,$urandom};tick();
   h1v=0;repeat(3)tick();
  end
  // Deliberate arrival overlap plus independent physical fault bits.
  h1v=1;h1[552]=1;h1[3:0]=6;localring[0]=1;localring[3:1]=6;source_fault=17'h10081;tick();
  tick();h1v=0;localring=0;source_fault=0;repeat(5)tick();
  if(!(fault[3]&&fault[4]&&fault[5]&&fault[16]))$fatal(1,"directed fault controls missed");
  $display("HEAD_HOST_MUX PASS cycles%0d frames%0d fault%h",n,frames,fault);$finish;
 end
endmodule
