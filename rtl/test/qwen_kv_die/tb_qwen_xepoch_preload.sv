`timescale 1ns/1ps
module tb_qwen_xepoch_preload;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,lv=0,rv=0;reg [15:0] le=0,re=0;reg [127:0] lx=0;
 wire qv,f;wire [127:0] q;
 ot_qwen_xepoch_cache #(.DEPTH(64)) dut(clk,rst_n,clear,lv,le,lx,rv,re,qv,q,f);
 function automatic [127:0] px(input integer k);
  px={32'h12345678 ^ k,32'ha55aa55a ^ (k*32'd11),32'h98765432 ^ k,32'hffffffff ^ k};
 endfunction
 integer k,j,p;
 initial begin
  repeat(2) @(negedge clk);rst_n=1;
  // SMAX11: each root cycles16 lines per k; a tile captures one phase.
  for(k=0;k<64;k=k+1) for(p=0;p<16;p=p+1) begin
   le=k;lx=px(k);lv=(p==11);@(negedge clk);
  end
  lv=0;
  for(k=0;k<64;k=k+1) for(j=0;j<8;j=j+1) begin
   rv=1;re=k;@(negedge clk);
   if(!qv || f || q!==px(k)) $fatal(1,"preload replay mismatch k=%0d j=%0d",k,j);
  end
  rv=0;
  // Stale epoch after modulo64 wrap must fault; never silently alias.
  rv=1;re=64;@(negedge clk);
  if(qv || !f) $fatal(1,"stale cache tag accepted");
  rv=0;clear=1;@(negedge clk);clear=0;rv=1;re=0;@(negedge clk);
  if(qv) $fatal(1,"previous instruction cache accepted after clear");
  $display("PASS SMAX11 preload phases=16 epochs=64 load_edges=1024 replay_reads=512 missing_epoch_rejected=1");$finish;
 end
endmodule
