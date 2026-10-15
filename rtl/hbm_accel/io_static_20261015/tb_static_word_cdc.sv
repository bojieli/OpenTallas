`timescale 1ns/1fs
module tb_static_word_cdc;
 parameter integer MUT=0, WPPM=0;
 localparam integer N=2048;
 reg wc=0,rc=0,rst_n=0;
 always #(0.416667*(1.0+WPPM/1000000.0))wc=~wc;
 always #0.416667 rc=~rc;
 reg ws=0,wt=0,wl=0,wv=0,rs=0,rt=0,rl=0;
 reg [486:0] wd=0;
 wire rv,wf,rf;
 wire [486:0] rd;
 integer checked=0,e;
 realtime last_write_edge=0, measured_write_period=0;
 always @(posedge wc)begin
  if(last_write_edge>0)measured_write_period=$realtime-last_write_edge;
  last_write_edge=$realtime;
 end
 ot_hbm_static_word_cdc #(.MUT(MUT==1?1:(MUT==2?2:0)))u(wc,rc,rst_n,ws,wt,wl,wv,wd,rs,rt,rl,rv,rd,wf,rf);
 function automatic [486:0] data(input integer epoch,index);
  integer k;begin
   data=0;
   for(k=0;k<487;k=k+1)data[k]=((index*17+epoch*23+k*71) >> (k%13))&1;
   if(index%13==0)data=487'd2; // Must survive unchanged: legacy idle collision.
  end
 endfunction
 task automatic writer(input integer ep);
  integer i;begin
   @(negedge wc);ws=1;
   @(negedge wc);ws=0;
   for(i=0;i<N;i=i+1)begin
    wt=1;wv=1;wl=(i==N-1);wd=data(ep,i);
    if(MUT==3 && i==19)wv=0;
    @(posedge wc);#0.001;if(wf)$fatal(1,"write fault ep%0d word%0d",ep,i);
    @(negedge wc);
   end
   wt=0;wv=0;wl=0;
  end
 endtask
 task automatic reader(input integer ep);
  integer i;begin
   // Fixed reservation offset; no observation of FIFO/producer controls issue.
   repeat(MUT==4?0:6)@(negedge rc);
   rs=1;
   @(negedge rc);rs=0;
   for(i=0;i<N;i=i+1)begin
    rt=1;rl=(i==N-1);
    @(posedge rc);#0.001;
    if(rf || !rv)$fatal(1,"read ownership fault ep%0d word%0d",ep,i);
    if(rd!==data(ep,i))$fatal(1,"read payload ep%0d word%0d",ep,i);
    checked=checked+1;
    @(negedge rc);
   end
   rt=0;rl=0;
  end
 endtask
 initial begin
  repeat(8)@(negedge rc);rst_n=1;
  for(e=0;e<2;e=e+1)begin
   fork writer(e);reader(e);join
   repeat(12)@(negedge rc);
  end
  if(checked!=4096 || wf || rf)$fatal(1,"coverage");
  if(measured_write_period < 0.833334*(1.0+WPPM/1000000.0)-0.000002 ||
     measured_write_period > 0.833334*(1.0+WPPM/1000000.0)+0.000002)$fatal(1,"clock resolution/period");
  $display("PASS static word CDC words=%0d epochs2 writeppm=%0d measured_period_ns=%0.9f exactidlewords",checked,WPPM,measured_write_period);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
