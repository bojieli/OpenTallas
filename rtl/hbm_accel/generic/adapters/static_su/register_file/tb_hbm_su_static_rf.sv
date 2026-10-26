`timescale 1ns/1ps
module tb_hbm_su_static_rf;
 parameter MUT_COHERENCE=0;
 localparam B=64,R=6;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg[B*R-1:0]rv=0;reg[B*R*2-1:0]ra=0;wire[B*R*32-1:0]rd;wire[B*R-1:0]ret;
 reg[B-1:0]wv=0;reg[B*2-1:0]wa=0;reg[B*32-1:0]wd=0;
 ot_hbm_su_static_rf #(.MUT_COHERENCE(MUT_COHERENCE))d(.clk_bank({B{clk}}),.rst_n(rst_n),
 .read_v(rv),.read_addr(ra),.read_data(rd),.read_return(ret),.write_v(wv),.write_addr(wa),.write_data(wd));
 integer c,b,r,checks=0,errors=0;function automatic[31:0]word(input integer a,input integer bank);word=32'h12340000+32'(a*1024+bank+1);endfunction
 initial begin
  repeat(3)@(negedge clk);rst_n=1;wv='1;
  for(c=0;c<4;c=c+1)begin for(b=0;b<B;b=b+1)begin wa[b*2+:2]=2'(c);wd[b*32+:32]=word(c,b);end @(negedge clk);end
  wv=0;repeat(2)@(negedge clk);
  for(c=0;c<130;c=c+1)begin
   rv=c<128?'1:'0;
   for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)ra[(b*R+r)*2+:2]=2'((c+r)%4);
   @(posedge clk);#1;
   checks=checks+1;if(ret!==(c>=2?{B*R{1'b1}}:{B*R{1'b0}}))errors=errors+1;
   if(c>=2)for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)begin
    checks=checks+1;if(rd[(b*R+r)*32+:32]!==word((c-2+r)%4,b))errors=errors+1;
   end
   @(negedge clk);
  end
  // Reset clears valids, never payload. A later read must retain real data.
  rst_n=0;rv=0;repeat(3)@(negedge clk);rst_n=1;rv='1;ra=0;
  repeat(3)@(negedge clk);
  for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)begin checks=checks+1;if(rd[(b*R+r)*32+:32]!==word(0,b))errors=errors+1;end
  if(errors)$fatal(1,"SU_RF FAIL checks=%0d errors=%0d",checks,errors);
  $display("SU_RF PASS banks=64 logical_words=256 replicas=6 checks=%0d read_latency=2 write_commit=1 reset_retains_data",checks);$finish;
 end
endmodule
