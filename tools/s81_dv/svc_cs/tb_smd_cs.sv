`timescale 1ns/1ps
// DIE-S81-85 svc census: lock-step bench, ot_s81_su_smd_fold2 (original) vs ot_s81_su_smd_fold2_cs (census-safe).
// Random stimulus in the fold2 schedule (a PV vector is never followed by another on the next edge), random cos /
// sin sets (complete and short, so the sticky fault fires), den updates, cfg_p 0..3, warm resets; every output
// compared every edge (o_ov / o_f always, o_o on o_ov).  Run: tools/s81_dv/svc_cs/run_bench.sh smd.
module tb_smd_fold2_cs;
 parameter integer SEED=1, SETS=24;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg pv=0,dv=0,csv=0;reg[4:0]csi=0;reg[63:0]csd=0;reg[31:0]den=32'h3f800000;reg[127:0]pa=0;reg[1:0]cp=1;
 wire aov,bov;wire[1:0]af,bf;wire[63:0]ao,bo;
 ot_s81_su_smd_fold2    A(.clk(clk),.rst_in(rst),.cfg_p(cp),.i_pv(pv),.i_pa(pa),.i_dv(dv),.i_den(den),.i_csv(csv),.i_csi(csi),
  .i_csd(csd),.o_ov(aov),.o_o(ao),.o_f(af));
 ot_s81_su_smd_fold2_cs B(.clk(clk),.rst_in(rst),.cfg_p(cp),.i_pv(pv),.i_pa(pa),.i_dv(dv),.i_den(den),.i_csv(csv),.i_csi(csi),
  .i_csd(csd),.o_ov(bov),.o_o(bo),.o_f(bf));
 integer err=0,checks=0,nov=0,nf=0;
 always @(negedge clk) if(rst) begin
  checks++;
  if({aov,af}!=={bov,bf}) begin err++; if(err<10)$display("%0t ctl %b %b",$time,{aov,af},{bov,bf}); end
  if(aov) begin nov++; if(ao!==bo) begin err++; if(err<10)$display("%0t o %h %h",$time,ao,bo); end end
  if(|af) nf++;
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 function automatic[31:0]val(input integer k);val={1'($urandom),8'(110+$urandom%30),23'($urandom)};endfunction
 integer j,k,n,seed;
 initial begin
  seed=SEED; if($value$plusargs("seed=%d",seed)) n=0; n=$urandom(seed);
  for(j=0;j<SETS;j++)begin
   if(j%8==0) begin rst=0;repeat(3+$urandom%4)tick;rst=1;repeat(64)tick; cp=$urandom; end
   den=val(0);dv=1;tick;dv=0;repeat($urandom%3)tick;
   n=($urandom%4==0)?($urandom%32):32;                     // short sets: the tail fault path
   for(k=0;k<n;k++)begin csv=1;csi=5'(k);csd={val(k),val(k+1)};tick;csv=0;csd=$urandom;repeat($urandom%2)tick;end
   repeat(2+$urandom%6)tick;
   for(k=0;k<32;k++)begin pa={val(k),val(k+1),val(k+2),val(k+3)};pv=1;tick;pv=0;pa={4{$urandom}};repeat(1+$urandom%3)tick;end
   repeat(120+$urandom%40)tick;
  end
  repeat(100)tick;
  if(err||nov<200) $fatal(1,"SMD_CS FAIL seed%0d checks%0d ov%0d fault_edges%0d errors%0d",seed,checks,nov,nf,err);
  $display("SMD_CS PASS seed%0d checks%0d ov%0d fault_edges%0d",seed,checks,nov,nf);$finish;
 end
endmodule
