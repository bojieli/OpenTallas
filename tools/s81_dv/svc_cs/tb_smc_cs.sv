`timescale 1ns/1ps
// DIE-S81-85 svc census: lock-step bench, ot_s81_su_smc (original) vs ot_s81_su_smc_cs (census-safe).
// Random e vectors (random valid / last, -0 / -inf / random floats), warm resets; o_v / o_l compared every edge,
// o_s on o_v.  Run: tools/s81_dv/svc_cs/run_bench.sh smc.
module tb_smc_cs;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg v=0,l=0;reg[511:0]e=0;
 wire av,al,bv,bl;wire[31:0]as,bs;
 ot_s81_su_smc #(.LPH(16),.LA(4)) A(.clk(clk),.rst_in(rst),.i_v(v),.i_l(l),.i_e(e),.o_v(av),.o_l(al),.o_s(as));
 ot_s81_su_smc_cs #(.LPH(16),.LA(4)) B(.clk(clk),.rst_in(rst),.i_v(v),.i_l(l),.i_e(e),.o_v(bv),.o_l(bl),.o_s(bs));
 integer err=0,checks=0,nv=0,nl=0,seed=1,r,j,k;
 always @(negedge clk) if(rst) begin
  checks++;
  if({av,al}!=={bv,bl}) begin err++; if(err<10)$display("%0t ctl %b %b",$time,{av,al},{bv,bl}); end
  if(av) begin nv++; nl+=al; if(as!==bs) begin err++; if(err<10)$display("%0t s %h %h",$time,as,bs); end end
 end
 function automatic[31:0]fv();
  case($urandom%12) 0: fv=32'h80000000; 1: fv=32'hff800000; 2: fv=32'd0;
   default: fv={1'($urandom),8'(112+$urandom%24),23'($urandom)}; endcase
 endfunction
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  if($value$plusargs("seed=%d",seed)) r=0; r=$urandom(seed);
  for(j=0;j<6000;j++)begin
   if(j%1500==0) begin rst=0;repeat(3+$urandom%4)tick;rst=1;repeat(64)tick; end
   v=$urandom%3!=0; l=v&&($urandom%4==0); for(k=0;k<16;k++) e[32*k+:32]=fv(); tick;
  end
  v=0;repeat(100)tick;
  if(err||nv<2000) $fatal(1,"SMC_CS FAIL seed%0d checks%0d v%0d l%0d errors%0d",seed,checks,nv,nl,err);
  $display("SMC_CS PASS seed%0d checks%0d v%0d l%0d",seed,checks,nv,nl);$finish;
 end
endmodule
