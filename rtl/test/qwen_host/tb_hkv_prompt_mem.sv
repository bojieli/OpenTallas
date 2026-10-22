`timescale 1ns/1ps
module tb_hkv_prompt_mem #(parameter integer W=120,A=4);
 reg ck=0;always #5 ck=~ck;
 reg put,pop;reg[A-1:0]wp=0,rp=0;reg[W-1:0]d;wire[W-1:0]h;
 reg[W-1:0]q[0:(1<<A)-1];integer n=0,seed=251,steps=0;
 ot_hkv_prompt_mem #(.W(W),.A(A)) u(.ck(ck),.put(put),.wa(wp),.ra_next(rp+A'(pop)),.data(d),.head(h));
 initial begin
  put=0;pop=0;d=0;
  repeat(20000)begin
   @(negedge ck);
   put=(n<(1<<A))&&(($random(seed)&3)!=0);pop=(n>0)&&(($random(seed)&3)!=0);
   for(integer b=0;b<W;b=b+1)d[b]=$random(seed)&1;
   @(posedge ck);
   if(n>0&&h!==q[rp])begin $fatal(1,"PROMPT_MEM FAIL cycle=%0d n=%0d",steps,n);end
   if(put)begin q[wp]<=d;wp<=wp+1'b1;end
   if(pop)rp<=rp+1'b1;
   n=n+integer'(put)-integer'(pop);steps=steps+1;
   #1;
   if(n>0&&h!==q[rp])begin $fatal(1,"PROMPT_MEM FAIL post cycle=%0d n=%0d",steps,n);end
  end
  $display("PROMPT_MEM PASS cycles=%0d",steps);$finish;
 end
endmodule
