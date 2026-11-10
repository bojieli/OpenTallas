`timescale 1ns/1ps
// DIE-S81-85 svc census: lock-step bench, ot_s81_su_sml_fold2 (original) vs ot_s81_su_sml_fold2_cs (census-safe).
// Same random stimulus on both (the fold2 schedule: an idle edge after every two-lane vector, rows of 1..NVMAX,
// random sink / mv / config timing, warm resets); every output compared every edge (valids / fault always, data on
// their valid).  Run: tools/s81_dv/svc_cs/run_bench.sh sml.
module tb_sml_fold2_cs;
 parameter integer SEED=1, ROWS=60;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg cv=0,sv=0,mv=0,ske=1;reg[6:0]nv=1;
 reg[31:0]scale=32'h3e800000,sink=32'h3f000000,nmb=32'hbf800000;
 reg[63:0]s=0;
 wire amxv,aev,aes,ael,af,bmxv,bev,bes,bel,bf;wire[63:0]amx,ae,bmx,be;
 ot_s81_su_sml_fold2 A(.clk(clk),.rst_in(rst),.sk_en(ske),.i_cv(cv),.i_nv(nv),.i_scale(scale),.i_sink(sink),
  .i_sv(sv),.i_s(s),.i_mv(mv),.i_nmb(nmb),.o_mxv(amxv),.o_mx(amx),.o_ev(aev),.o_es(aes),.o_el(ael),.o_e(ae),.o_fault(af));
 ot_s81_su_sml_fold2_cs B(.clk(clk),.rst_in(rst),.sk_en(ske),.i_cv(cv),.i_nv(nv),.i_scale(scale),.i_sink(sink),
  .i_sv(sv),.i_s(s),.i_mv(mv),.i_nmb(nmb),.o_mxv(bmxv),.o_mx(bmx),.o_ev(bev),.o_es(bes),.o_el(bel),.o_e(be),.o_fault(bf));
 integer err=0,checks=0,nev=0,nmx=0;
 always @(negedge clk) if(rst) begin
  checks++;
  if({amxv,aev,aes,ael,af}!=={bmxv,bev,bes,bel,bf}) begin err++; if(err<10)$display("%0t ctl %b %b",$time,{amxv,aev,aes,ael,af},{bmxv,bev,bes,bel,bf}); end
  if(amxv) begin nmx++; if(amx!==bmx) begin err++; if(err<10)$display("%0t mx %h %h",$time,amx,bmx); end end
  if(aev) begin nev++; if(aes ? (ae[31:0]!==be[31:0]) : (ae!==be)) begin err++; if(err<10)$display("%0t e %h %h",$time,ae,be); end end
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 function automatic[31:0]score(input integer k);
  if($urandom%9==0)score=32'hff800000;else score={1'($urandom),8'(118+$urandom%12),23'($urandom)};
 endfunction
 integer j,k,r,seed;
 initial begin
  seed=SEED; if($value$plusargs("seed=%d",seed)) r=0; r=$urandom(seed);
  for(j=0;j<ROWS;j++)begin
   if(j%20==0) begin rst=0;repeat(3+$urandom%4)tick;rst=1;repeat(64)tick; end   // boot holds reset; warm resets
   if(j==0||$urandom%3==0) begin
    nv=1+$urandom%40; scale={1'b0,8'(120+$urandom%8),23'($urandom)}; sink=score(0);
    cv=1;tick;cv=0;repeat(2+$urandom%5)tick;
   end
   for(k=0;k<nv;k++)begin sv=1;s={score(k+1),score(k)};tick;sv=0;s={$urandom,$urandom};repeat(1+$urandom%3)tick;end
   repeat(20+$urandom%20)tick;
   ske=$urandom%4!=0; nmb={1'b1,8'(124+$urandom%6),23'($urandom)};
   mv=1;tick;mv=0;ske=$urandom%2;repeat(2*nv+80+$urandom%30)tick;
  end
  repeat(100)tick;
  if(err||nev<100||nmx<20) $fatal(1,"SML_CS FAIL seed%0d checks%0d ev%0d mx%0d errors%0d",seed,checks,nev,nmx,err);
  $display("SML_CS PASS seed%0d checks%0d ev%0d mx%0d",seed,checks,nev,nmx);$finish;
 end
endmodule
