`timescale 1ns/1ps
// DIE-S81-85 svc census: lock-step bench, ot_s81_su_smr (original) vs ot_s81_su_smr_cs (census-safe).
// Random configuration (lt 0..LTMAX, the original's range), random row maxima / sink / vector-sum streams (random
// valid / last), warm resets; o_mv / o_dv compared every edge, o_nmb / o_den on their valids.
// Run: tools/s81_dv/svc_cs/run_bench.sh smr.
module tb_smr_cs;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg cv=0,mxv=0,skv=0,vv=0,vl=0;reg[2:0]lt=0;reg[511:0]mx=0;reg[31:0]sk=0,vs=0;
 wire amv,adv,bmv,bdv;wire[31:0]anmb,aden,bnmb,bden;
 ot_s81_su_smr #(.LPH(16),.LA(4)) A(.clk(clk),.rst_in(rst),.i_cv(cv),.i_lt(lt),.i_mxv(mxv),.i_mx(mx),.i_skv(skv),.i_sk(sk),
  .i_vv(vv),.i_vl(vl),.i_vs(vs),.o_mv(amv),.o_nmb(anmb),.o_dv(adv),.o_den(aden));
 ot_s81_su_smr_cs #(.LPH(16),.LA(4)) B(.clk(clk),.rst_in(rst),.i_cv(cv),.i_lt(lt),.i_mxv(mxv),.i_mx(mx),.i_skv(skv),.i_sk(sk),
  .i_vv(vv),.i_vl(vl),.i_vs(vs),.o_mv(bmv),.o_nmb(bnmb),.o_dv(bdv),.o_den(bden));
 integer err=0,checks=0,nmv=0,ndv=0,seed=1,r,j,k;
 always @(negedge clk) if(rst) begin
  checks++;
  if({amv,adv}!=={bmv,bdv}) begin err++; if(err<10)$display("%0t ctl %b %b",$time,{amv,adv},{bmv,bdv}); end
  if(amv) begin nmv++; if(anmb!==bnmb) begin err++; if(err<10)$display("%0t nmb %h %h",$time,anmb,bnmb); end end
  if(adv) begin ndv++; if(aden!==bden) begin err++; if(err<10)$display("%0t den %h %h",$time,aden,bden); end end
 end
 function automatic[31:0]fv();
  case($urandom%12) 0: fv=32'h80000000; 1: fv=32'hff800000; 2: fv=32'd0;
   default: fv={1'($urandom),8'(112+$urandom%24),23'($urandom)}; endcase
 endfunction
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  if($value$plusargs("seed=%d",seed)) r=0; r=$urandom(seed);
  for(j=0;j<12000;j++)begin
   if(j%3000==0) begin rst=0;repeat(3+$urandom%4)tick;rst=1;repeat(64)tick; cv=1;lt=$urandom%7;tick;cv=0; end
   cv=($urandom%400==0); lt=$urandom%7;
   mxv=$urandom%4==0; for(k=0;k<16;k++) mx[32*k+:32]=fv();
   skv=$urandom%6==0; sk=fv(); vv=$urandom%2; vl=vv&&($urandom%5==0); vs=fv(); tick;
  end
  {cv,mxv,skv,vv}=0;repeat(100)tick;
  if(err||nmv<1000||ndv<300) $fatal(1,"SMR_CS FAIL seed%0d checks%0d mv%0d dv%0d errors%0d",seed,checks,nmv,ndv,err);
  $display("SMR_CS PASS seed%0d checks%0d mv%0d dv%0d",seed,checks,nmv,ndv);$finish;
 end
endmodule
