`timescale 1ns/1ps
module tb_qwen_xcache_split32;
 reg lc=0,cc=0,rst=0,clear=0,jr=0,lv=0;
 reg [20:0] le=0,re=0;reg [127:0] lx=0;reg [3:0] rv=0;
 wire ha,hb,fa,fb;wire [127:0] qa,qb;
 ot_qwen_xcache_indexed a(lc,cc,rst,clear,jr,lv,le,lx,rv,re,ha,qa,fa);
 ot_qwen_xcache_split32 b(lc,cc,rst,clear,jr,lv,le,lx,rv,re,hb,qb,fb);
 integer edges=0,hits=0,misses=0,pauses=0,i;
 task check;
 begin
  if({ha,qa,fa} !== {hb,qb,fb}) $fatal(1,"split cache differential mismatch edge%0d",edges);
 end endtask
 task step(input run_core);
 begin
  #2;lc=1;if(run_core)cc=1;
  #1;edges=edges+1;check();
  if(rv) begin if(ha)hits=hits+1;else misses=misses+1;end
  if(!run_core)pauses=pauses+1;
  #2;lc=0;cc=0;#1;check();
 end endtask
 initial begin
  #1;rst=1;#1;rst=0;#1;check();rst=1;
  for(i=0;i<5000;i=i+1)begin
   lv=(i%4!=0);le=(i*8) ^ ((i%7)<<14);
   lx={32'hfed12345^i,32'hc7d8e9ab+i,32'hface9191-i,32'habcd1234+i};
   jr=(i/100)%2;rv=(i%3==0)?0:4'b1011;
   re=(i%5==0)?le:(le-8);clear=(i%97==0);
   if(i%503==0)rst=0;else rst=1;
   step(i%13>=4);
  end
  rst=0;step(0);rst=1;clear=0;jr=0;lv=1;rv=0;le=21'h12345;lx=128'h12345678;step(0);
  lv=0;rv=15;re=21'h12345;step(1);
  re=21'h12445;step(1); // same slot, different full tag; must miss
  clear=1;step(0);clear=0;re=21'h12345;step(1);
  if(!hits||!misses||!pauses)$fatal(1,"missing coverage");
  $display("PASS split cache differential edges%0d hits%0d misses%0d paused%0d resetclear/fulltag/Jmode",edges,hits,misses,pauses);$finish;
 end
endmodule
