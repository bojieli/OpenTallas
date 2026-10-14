`timescale 1ns/1ps
module tb_hgi_qdq_wr_fin;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,snapshot_v=0;reg [63:0] snapshot=0;reg [7:0] ack=0;
 wire fin,bad,idle;
 ot_hgi_qdq_wr_fin #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.snapshot_v(snapshot_v),.snapshot(snapshot),.wwq_done(ack),.o_fin(fin),.o_bad(bad),.o_idle(idle));
 integer issued[0:7],committed[0:7],eligible[0:7][0:2047];
 integer target[0:511][0:7],posted[0:511];
 integer cycle,npost,nfin,totalfin=0,maxpending=0,wraps=0,seed=32'h451ef;
 reg expected,previous_fin=0;integer inc;
 task clear_score;
 begin
  npost=0;nfin=0;previous_fin=0;
  for(integer b=0;b<8;b=b+1)begin issued[b]=0;committed[b]=0;end
  snapshot_v=0;snapshot=0;ack=0;
 end
 endtask
 task reset_dut;
 begin
  @(negedge clk);rst_n=0;clear_score();
  repeat(8)@(negedge clk);rst_n=1;
  repeat(8)@(negedge clk);
 end
 endtask
 task campaign(input integer records,input integer abort_after,input integer interval_cycles,input integer ack_delay);
 begin
  begin:run_campaign
  for(cycle=0;cycle<10000;cycle=cycle+1)begin
   snapshot_v=0;ack=0;
   if(npost<records&&(npost-nfin)<16&&(cycle%interval_cycles)==0)begin
    snapshot_v=1;
    for(integer b=0;b<8;b=b+1)begin
     inc=1+(npost+b)%3;
     for(integer k=0;k<inc;k=k+1)eligible[b][issued[b]+k]=cycle+ack_delay+k;
     issued[b]=issued[b]+inc;target[npost][b]=issued[b];snapshot[b*8+:8]=8'(issued[b]);
    end
    posted[npost]=cycle;npost=npost+1;
    if(npost-nfin>maxpending)maxpending=npost-nfin;
   end
   for(integer b=0;b<8;b=b+1)begin
    seed=(seed*1103515245+12345)&32'h7fffffff;
    if(committed[b]<issued[b]&&eligible[b][committed[b]]<=cycle&&(seed%5)!=0)begin ack[b]=1;committed[b]=committed[b]+1;end
   end
   expected=(nfin<npost)&&!previous_fin;
   if(expected)begin
    if(cycle<posted[nfin]+2)expected=0;
    for(integer b=0;b<8;b=b+1)if(committed[b]<target[nfin][b])expected=0;
   end
   @(posedge clk);#1;
   if(bad)$fatal(1,"unexpected FIFO overflow");
   if(fin!==expected)$fatal(1,"FIN scoreboard mismatch cycle%0d issued%0d retired%0d actual%b expected%b",cycle,npost,nfin,fin,expected);
   if(fin)begin nfin=nfin+1;totalfin=totalfin+1;end
   previous_fin=fin;
   @(negedge clk);
   if(abort_after>0&&cycle==abort_after)begin
    if(npost==nfin)$fatal(1,"warm reset did not interrupt pending records");
    disable run_campaign;
   end
   if(nfin==records)begin
    for(integer b=0;b<8;b=b+1)wraps=wraps+issued[b]/256;
    disable run_campaign;
   end
  end
  end
  if(cycle==10000)$fatal(1,"completion timeout");
 end
 endtask
 initial begin
  clear_score();reset_dut();campaign(400,0,5,4);
  reset_dut();campaign(400,17,5,4);
  reset_dut();campaign(400,0,5,4);
  reset_dut();campaign(64,0,1,24);
  snapshot_v=0;ack=0;repeat(10)begin @(posedge clk);#1;if(fin)$fatal(1,"stale completion after drain");@(negedge clk);end
  if(totalfin<864||wraps<16||maxpending<16)$fatal(1,"insufficient coverage");
  $display("PASS QDQ_WR_FIN records=%0d wraps=%0d max_pending=%0d warm_reset=1 no_early_finish=1",totalfin,wraps,maxpending);$finish;
 end
endmodule
