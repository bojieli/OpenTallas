`timescale 1ns/1fs
module tb;
 parameter integer KNBIAS=0,NKBIAS=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rk=0,rn=0;integer cyc=0,skew=0,checks=0;
 reg[31:0]prng=32'h42531549;reg[555:0]ki=0;reg[559:0]ni=0;
 wire[555:0]ko,ko_nst;wire[559:0]no;wire[557:0]no_nst;
 reg[555:0]kh[0:2];reg[559:0]nh[0:2];
 ot_s81_mu72_lnland #(.KN_EPOCH_BIAS(KNBIAS),.NK_EPOCH_BIAS(NKBIAS)) full(
  .ck_k(clk),.ck_n(clk),.rs_k(rk),.rs_n(rn),
  .k_li_r(ki[555]),.k_rxv(ki[554]),.k_lo_v(ki[553]),.k_lo_d(ki[552:0]),
  .n_li_r(ko[555]),.n_rxv(ko[554]),.n_lo_v(ko[553]),.n_lo_d(ko[552:0]),
  .n_st(ni[559:558]),.n_flt(ni[557:555]),.n_lo_r(ni[554]),.n_li_v(ni[553]),.n_li_d(ni[552:0]),
  .k_st(no[559:558]),.k_flt(no[557:555]),.k_lo_r(no[554]),.k_li_v(no[553]),.k_li_d(no[552:0]));
 ot_s81_mu72_lnland_nst #(.KN_EPOCH_BIAS(KNBIAS),.NK_EPOCH_BIAS(NKBIAS)) nst(
  .ck_k(clk),.ck_n(clk),.rs_k(rk),.rs_n(rn),
  .k_li_r(ki[555]),.k_rxv(ki[554]),.k_lo_v(ki[553]),.k_lo_d(ki[552:0]),
  .n_li_r(ko_nst[555]),.n_rxv(ko_nst[554]),.n_lo_v(ko_nst[553]),.n_lo_d(ko_nst[552:0]),
  .n_flt(ni[557:555]),.n_lo_r(ni[554]),.n_li_v(ni[553]),.n_li_d(ni[552:0]),
  .k_flt(no_nst[557:555]),.k_lo_r(no_nst[554]),.k_li_v(no_nst[553]),.k_li_d(no_nst[552:0]));
 initial begin
  if($value$plusargs("SKEW=%d",skew));
  repeat(16)@(negedge clk);rk=1;repeat(skew)@(negedge clk);rn=1;
  repeat(80)@(negedge clk);
  if(checks<40)$fatal(1,"few data checks");
  $display("LNLAND_EPOCH_PASS skew=%0d KN=%0d NK=%0d words_each=%0d widths556/560/558",skew,KNBIAS,NKBIAS,checks);$finish;
 end
 always @(posedge clk)begin:stim
  reg[31:0]p;p=prng;cyc<=cyc+1;
  for(integer j=0;j<556;j=j+1)begin ki[j]<=p[0];p={p[30:0],p[31]^p[21]^p[1]^p[0]};end
  for(integer j=0;j<560;j=j+1)begin ni[j]<=p[0];p={p[30:0],p[31]^p[21]^p[1]^p[0]};end
  prng<=p;kh[0]<=ki;kh[1]<=kh[0];kh[2]<=kh[1];nh[0]<=ni;nh[1]<=nh[0];nh[2]<=nh[1];
 end
 always @(negedge clk)if(cyc>40&&rk&&rn)begin
  if(ko!==kh[2]||ko_nst!==kh[2])$fatal(1,"LNLAND_KN_DATA edge%0d",cyc);
  if(no!==nh[2]||no_nst!==nh[2][557:0])$fatal(1,"LNLAND_NK_DATA edge%0d",cyc);
  checks=checks+1;
 end
endmodule
