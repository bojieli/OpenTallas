`timescale 1ns/1ps
module tb_age;
 parameter integer N=3;
 localparam integer W=3749,B=1875,S=1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,started=0;
 reg[W-1:0] producer=0;
 wire[B-1:0] beat,link_beat;wire side_beat,link_side,side_q;
 wire[W-1:0] q;wire slot0,tf,rf;
 reg[W-1:0] baseline[0:N+1];
 reg[W-1:0] consumer=0,wide_consumer=0;reg side_consumer=0;
 integer cycle=0,seq=0,launch[0:1023],seen=0,wide_seen=0;
 ot_hbm_static_2beat_tx #(.W(W),.B(B),.CONTROL_MASK(W'(1))) tx(clk,rst_n,start,producer,producer[0],beat,side_beat,tf,slot0);
 if(N==0)begin assign link_beat=beat;assign link_side=side_beat;end
 else begin
  reg[B:0] station[0:N-1];
  always @(posedge clk)begin
   station[0]<={side_beat,beat};for(integer j=1;j<N;j=j+1)station[j]<=station[j-1];
  end
  assign{link_side,link_beat}=station[N-1];
 end
 ot_hbm_static_2beat_rx #(.W(W),.B(B),.LINK_STAGES(N),.CONTROL_MASK(W'(1))) rx(clk,rst_n,start,link_beat,link_side,q,side_q,rf);
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!rst_n)begin producer<=0;started<=0;end
  else if(start)begin producer<=0;started<=1;end
  else if(started)begin
   // Publish on the edge BEFORE TX slot0; pulse valid exactly one edge.
   if(!slot0)begin seq=seq+1;launch[seq]=cycle;producer<=(W'(seq)<<32)|W'(1);end
   else producer<=0;
  end
 end
 always @(posedge clk)begin
  baseline[0]<=producer;for(integer j=1;j<N+2;j=j+1)baseline[j]<=baseline[j-1];
  consumer<=q;wide_consumer<=baseline[N+1];side_consumer<=side_q;
  #2;
  if(consumer[0])begin
   if(cycle-launch[consumer[63:32]]!=N+4)$fatal(1,"TDM external flop-to-consumer age wrong");
   if(!side_consumer)$fatal(1,"correlated CTL valid skewed");
   seen=seen+1;
  end
  if(wide_consumer[0])begin
   if(cycle-launch[wide_consumer[63:32]]!=N+3)$fatal(1,"wide baseline age wrong");
   wide_seen=wide_seen+1;
  end
  if(rst_n&&(tf||rf))$fatal(1,"age vehicle faulted");
 end
 initial begin
  for(integer i=0;i<N+2;i=i+1)baseline[i]=0;
  for(integer i=0;i<1024;i=i+1)launch[i]=-1;
  repeat(4)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
  repeat(300)@(negedge clk);
  if(seen<128||wide_seen<128)$fatal(1,"missing age vehicle words");
  $display("2BEAT_AGE PASS channel_stations=%0d baseline_owned=2 tdm_owned=3 source_to_consumer_wide=%0d tdm=%0d extra=1 II=2 words=%0d",N,N+3,N+4,seen);$finish;
 end
endmodule
