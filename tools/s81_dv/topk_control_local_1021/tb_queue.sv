`timescale 1ns/1ps
module tb_queue;
 parameter integer MUT=0;
 localparam integer W=358,NS=(W+15)/16;
 reg clk=0;always #5 clk=~clk;
 reg[NS-1:0]rst_n=0;
 reg push=0,want_pop=0;
 wire pop=want_pop&&(count!=0); // exact original take/lv rule
 reg[W-1:0]data=0;
 wire[W-1:0]head;wire[2:0]count;
 ot_s81pa_queue #(.W(W),.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.push(push),.pop(pop),.data(data),.head(head),.count(count));
 reg[W-1:0]refq[0:3];integer n=0,k=0,cycle=0,empty_arrival=0,full_replace=0,wraps=0,samehead=0;
 reg oldpop;
 always @(posedge clk) begin
  oldpop=pop;
  if(!rst_n[0])n=0;
  else begin
   if(n==0&&push&&want_pop)empty_arrival=empty_arrival+1;
   if(n==4&&push&&pop)full_replace=full_replace+1;
   if(pop)begin for(k=0;k<3;k=k+1)refq[k]=refq[k+1];n=n-1;end
   if(push)begin refq[n]=data;n=n+1;end
  end
  #1;
  if(count!==3'(n))$fatal(1,"COUNT cycle%0d count%0d ref%0d",cycle,count,n);
  if(n!=0&&head!==refq[0])$fatal(1,"HEAD cycle%0d count%0d got%h ref%h",cycle,n,head,refq[0]);
 end
 task step(input bit ps,input bit pp,input integer id);
  begin
   @(negedge clk);push=ps;want_pop=pp;
   for(integer b=0;b<W;b=b+1)data[b]=(((id*7919+b*53)^(id>>(b%13)))&1)!=0;
   cycle=cycle+1;
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);rst_n={NS{1'b1}};
  step(1,1,1); // empty arrival with pop requested: source guard keeps pop0
  step(0,0,2);step(0,0,3);step(0,1,4);
  step(1,0,5);step(1,0,6);step(1,0,7);step(1,0,8);
  repeat(12)step(1,1,cycle+100); // full replacement and wrap
  repeat(4)step(0,1,cycle+200);
  repeat(12)begin step(1,0,cycle+300);step(0,0,cycle+400);step(0,1,cycle+500);end
  // Seeded deterministic legal source traffic, including back-to-back writes,
  // delayed reads, and same-address forwarding around the registered macro write.
  for(integer j=0;j<512;j=j+1)begin
   if(n==0)step(1,1,j+1000);
   else if(n==4)step(j%3!=0,1,j+1000);
   else step(j%5!=0,j%3!=0,j+1000);
  end
  while(n!=0)step(0,1,cycle+2000);
  step(0,0,0);@(negedge clk);
  if(empty_arrival==0||full_replace==0)$fatal(1,"COVERAGE");
  $display("QUEUE_PASS cycles%0d empty_arrival%0d full_replace%0d",cycle,empty_arrival,full_replace);$finish;
 end
endmodule
