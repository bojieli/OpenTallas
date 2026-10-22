`timescale 1ns/1ps
// QE3-HROOT-PROMPT 10-21: tb_hkv_prompt_mem for the registered-read ot_hkv_prompt_mem_r (same random put/pop queue
// model; a pop is taken only on head_ok, and head must equal the model head whenever head_ok).
module tb_hkv_prompt_mem_r #(parameter integer W=120,A=4);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg put,pop;reg[A-1:0]wp=0,rp=0;reg[A:0]cnt=0;reg[W-1:0]d;wire[W-1:0]h;wire ok;
 reg[W-1:0]q[0:(1<<A)-1];integer n=0,seed=251,steps=0,pops=0,oks=0;
 ot_hkv_prompt_mem_r #(.W(W),.A(A)) u(.ck(ck),.rst_n(rst_n),.put(put),.enq(put),.wa(wp),.rp(rp),.count(cnt),.data(d),.head(h),.head_ok(ok));
 initial begin
  put=0;pop=0;d=0;repeat(3)@(posedge ck);#1 rst_n=1;
  repeat(20000)begin
   @(negedge ck);
   if(ok)begin oks=oks+1;if(n==0||h!==q[rp])$fatal(1,"PROMPT_MEM FAIL cycle=%0d n=%0d",steps,n);end
   put=(n<(1<<A))&&(($random(seed)&3)!=0);pop=ok&&(($random(seed)&3)!=0);
   for(integer b=0;b<W;b=b+1)d[b]=$random(seed)&1;
   @(posedge ck);
   if(put)begin q[wp]<=d;wp<=wp+1'b1;end
   if(pop)begin rp<=rp+1'b1;pops=pops+1;end
   n=n+integer'(put)-integer'(pop);cnt<=(A+1)'(n);steps=steps+1;
  end
  if(pops<2000)$fatal(1,"PROMPT_MEM FAIL liveness pops=%0d",pops);
  $display("PROMPT_MEM PASS cycles=%0d pops=%0d head_ok=%0d",steps,pops,oks);$finish;
 end
endmodule
