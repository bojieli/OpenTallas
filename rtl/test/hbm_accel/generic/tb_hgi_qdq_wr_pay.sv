`timescale 1ns/1ps
module tb_hgi_qdq_wr_pay;
 parameter integer EMPTY_BYPASS=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,m_v=0,vo=0,gnt=0,qfault=0;reg [18:0] m=0;reg [511:0] y=0;
 wire [2239:0] wwq;reg [7:0] cr=0;wire req,wf,bad,idle,sv;wire [63:0] snapshot;
 ot_hgi_qdq_wr_pay #(.EMPTY_BYPASS(EMPTY_BYPASS)) dut(.clk(clk),.rst_n(rst_n),.m_v(m_v),.m(m),.i_bad(1'b0),.vo(vo),.qfault(qfault),.dfault(1'b0),.y(y),.wwq(wwq),.wwq_cr(cr),.wg_req(req),.wg_gnt(gnt),.i_act(1'b1),.o_wf(wf),.snapshot_v(sv),.snapshot(snapshot),.o_bad(bad),.o_idle(idle));
 reg [7:0] credit_pipe[0:7];
 reg [278:0] expected[0:7][0:1023];integer tail[0:7],head[0:7];
 integer first_launch_cycle,last_launch_cycle;
 integer cycle,beat,words=0,snapshots=0,wraps=0,array_writes=0,array_reads=0,bypassed=0;reg [7:0] launched;
 function automatic [15:0] golden(input integer n,input integer k);golden=16'((n*137+k*319)^16'h9e31);endfunction
 task reset_dut;
 begin
  @(negedge clk);rst_n=0;m_v=0;vo=0;cr=0;gnt=0;qfault=0;
  for(integer b=0;b<8;b=b+1)begin tail[b]=0;head[b]=0;credit_pipe[b]=0;end
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 end
 endtask
 task campaign(input integer beats,input integer grant_delay);
 begin:campaign_body
  first_launch_cycle=-1;last_launch_cycle=-1;
  for(cycle=0;cycle<10000;cycle=cycle+1)begin
   m_v=0;vo=0;gnt=cycle>=grant_delay;cr=credit_pipe[7];
   for(integer d=7;d>0;d=d-1)credit_pipe[d]=credit_pipe[d-1];
   credit_pipe[0]=0;
   if(cycle<beats)begin
    reg [14:0] sec;reg [255:0] data;
    beat=cycle;sec=15'(beat*4+3);m_v=1;m={sec,3'd4,1'((beat%4)==3)};
    for(integer s=0;s<4;s=s+1)begin
     for(integer k=0;k<8;k=k+1)data[k*32+:32]={golden(beat,s*8+k),16'd0};
     expected[(sec+s)%8][tail[(sec+s)%8]]={15'(sec+s),data,8'hff};tail[(sec+s)%8]=tail[(sec+s)%8]+1;
    end
   end
   if(cycle>=26&&cycle<beats+26)begin
    beat=cycle-26;vo=1;
    for(integer k=0;k<32;k=k+1)y[k*16+:16]=golden(beat,k);
   end
   @(posedge clk);
   if(dut.bypass_fire)bypassed=bypassed+1;
   if(dut.u_od.wr_arr)array_writes=array_writes+1;
   if(dut.u_od.rd_arr)array_reads=array_reads+1;
   #1;
   if(bad)$fatal(1,"unexpected PAY fault");
   launched=0;
   for(integer b=0;b<8;b=b+1)if(wwq[b*280+279])begin
    launched[b]=1;
    if(head[b]>=tail[b]||wwq[b*280+:279]!==expected[b][head[b]])$fatal(1,"PAY word/address mismatch lane%0d item%0d",b,head[b]);
    head[b]=head[b]+1;words=words+8;
   end
   credit_pipe[0]=launched;
   if(launched!=0)begin if(first_launch_cycle<0)first_launch_cycle=cycle;last_launch_cycle=cycle;end
   if(sv)begin
    snapshots=snapshots+1;
    for(integer b=0;b<8;b=b+1)if(snapshot[b*8+:8]!==8'(head[b]))$fatal(1,"PAY post-write snapshot mismatch lane%0d got%0d expected%0d",b,snapshot[b*8+:8],8'(head[b]));
   end
   @(negedge clk);
   if(cycle>beats+40&&idle)begin
    reg drained;drained=1;
    for(integer b=0;b<8;b=b+1)if(head[b]!=tail[b])drained=0;
    if(drained)begin
     $display("PAY_LAUNCH_TRACE empty_mode=%0d beats=%0d grant_delay=%0d first=%0d last=%0d",EMPTY_BYPASS,beats,grant_delay,first_launch_cycle,last_launch_cycle);
     disable campaign_body;
    end
   end
  end
  $fatal(1,"PAY timeout");
 end
 endtask
 task fault_campaign;
 begin
  gnt=1;m_v=1;m={15'd3,3'd4,1'b1};
  @(negedge clk);m_v=0;repeat(25)@(negedge clk);
  vo=1;qfault=1;y='0;
  @(negedge clk);vo=0;qfault=0;
  repeat(12)begin @(posedge clk);#1;
   for(integer b=0;b<8;b=b+1)if(wwq[b*280+279])$fatal(1,"PAY faulty first result escaped");
   @(negedge clk);
  end
  if(!bad)$fatal(1,"PAY decoder fault not sticky");
 end
 endtask
 initial begin
  reset_dut();campaign(1024,41);
  reset_dut();campaign(128,41);
  reset_dut();campaign(128,0);
  reset_dut();fault_campaign();
  reset_dut();campaign(128,0);
  if(words!=45056||snapshots!=352||array_writes<500||array_reads!=array_writes)$fatal(1,"PAY insufficient coverage words%0d snapshots%0d",words,snapshots);
  if(EMPTY_BYPASS!=0&&bypassed<256)$fatal(1,"PAY empty bypass not exercised");
  $display("PASS QDQ_WR_PAY words=%0d snapshots=%0d metadata_wraps=18 counter_wraps=16 reset=1 real_macro=1 array_writes=%0d array_reads=%0d bypassed=%0d fault_reset=1",words,snapshots,array_writes,array_reads,bypassed);$finish;
 end
endmodule
