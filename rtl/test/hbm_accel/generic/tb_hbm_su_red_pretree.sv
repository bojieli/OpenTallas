`timescale 1ns/1ps
`default_nettype none
// HH-6 / HBM-SURED 10-18: SU reducer ingress widening bench. One quarter: 4 x ot_hbm_su_red_pretree_s (G 0..3, the
// pgslice PRETREE leaf) + ot_hbm_su_static_qcore_r5 PRETREE 1 (join + the real reducer). Stimulus (su_pretree_bench.py,
// lowering tools/hbm_static/su_pretree_lower.py): per edge {tree_cmd 4 x 12 (slice G at [12G]), red_cmd74, ro_v128, ro_x 128 x 32 in quarter
// word order}; lane n of slice G = quarter word (n<16 ? 16G+n : 64+16G+n-16). Expected: every EXPORT scalar
// {red_cmd edge, tag, value} = hdc_golden_v41.csum / canonical max; scalar_valid must rise exactly SCL edges after the
// EXPORT command edge, in order, and no FAULT anywhere.  MUT: 1,3,4 pretree_s mutants (chunk order, max ignored, padding
// off by one); 512 qcore late tree operand; 1024 join pairing (pretree_j MUT 2).
module tb_hbm_su_red_pretree;
 parameter integer MUT=0, SCL=11;
 parameter integer N=4096, NX=64;
 localparam integer W=48+74+128+4096;
 reg clk=0, rst_n=0;
 always #1 clk=~clk;
 reg [W-1:0] stim [0:N-1];
 reg [95:0] exps [0:NX-1];
 integer ne, k, nexp, errs, cyc;
 reg [W-1:0] cur;
 wire [47:0] tree_cmd=cur[W-1-:48];   // slice G: [12G+:12]
 wire [73:0] red_cmd=cur[W-49-:74];
 wire [127:0] ro_vq=cur[4096+:128];
 wire [4095:0] ro_xq=cur[0+:4096];
 wire [4*67-1:0] slice_t; wire [3:0] sf;
 for(genvar g=0;g<4;g=g+1)begin:g_s
  wire [1023:0] rx; wire [31:0] rv;
  for(genvar n=0;n<32;n=n+1)begin:g_n
   localparam integer WD=(n<16)?16*g+n:64+16*g+(n-16);
   assign rx[n*32+:32]=ro_xq[WD*32+:32]; assign rv[n]=ro_vq[WD];
  end
  ot_hbm_su_red_pretree_s #(.LAT(6),.MUT((MUT==1||MUT==3||MUT==4)?MUT:0)) u_s(.clk(clk),.rst_n(rst_n),.tree_cmd(tree_cmd[12*g+:12]),
   .ro_x(rx),.ro_v(rv),.tree_o(slice_t[g*67+:67]),.fault(sf[g]));
 end
 wire red_sv, red_rf_v, cfault; wire [31:0] red_tag, red_x; wire [4*32-1:0] rf_bword; wire [4*9-1:0] rf_bcmd; wire [255:0] rf_dsec;
 ot_hbm_su_static_qcore_r5 #(.MUT((MUT==512||MUT==1024)?MUT:0),.COLLPORT(1),.RF_LOCAL(1),.PRETREE(1)) u_c(.clk_ctl(clk),.rst_n(rst_n),
  .rf_rd_cmd(54'd0),.red_cmd(red_cmd),.rf_drain_cmd(2'd0),.slice_x(128'd0),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),
  .rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),.red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.red_rf_v(red_rf_v),
  .rr_wv(1'b0),.rr_wa(5'd0),.rr_wd(256'd0),.sfu_x(32'd0),.slice_t(slice_t),.fault(cfault));
 initial begin
  for(k=0;k<N;k=k+1) stim[k]=0;
  $readmemh("stim.mem", stim);
  $readmemh("exps.mem", exps);
  if(!$value$plusargs("NE=%d", ne)) ne=N;
  if(!$value$plusargs("NEXP=%d", nexp)) nexp=0;
  errs=0; k=0; cur=0;
  // reset over edges 0..4; stimulus line c is sampled at edge c (driven after edge c-1)
  for(cyc=0;cyc<ne;cyc=cyc+1) begin
   @(negedge clk);
   if(cyc==5) rst_n=1;
   cur=stim[cyc];
   @(posedge clk); #0.1;
   if(red_sv) begin
    if(k>=nexp) begin errs=errs+1; $display("EXTRA scalar edge %0d tag %h x %h", cyc, red_tag, red_x); end
    else begin
     if(cyc!=exps[k][95:64]+SCL || red_tag!=exps[k][63:32] || red_x!=exps[k][31:0]) begin
      errs=errs+1;
      $display("MISMATCH %0d: edge %0d (exp %0d) tag %h (exp %h) x %h (exp %h)", k, cyc, exps[k][95:64]+SCL, red_tag,
               exps[k][63:32], red_x, exps[k][31:0]);
     end
     k=k+1;
    end
   end
  end
  if(k!=nexp) begin errs=errs+1; $display("MISSING scalars: %0d of %0d", k, nexp); end
  if(|sf || cfault) begin errs=errs+1; $display("FAULT slices %b core %b", sf, cfault); end
  if(errs==0) $display("PASS tb_hbm_su_red_pretree MUT=%0d: %0d exports bit-exact at fixed edges (+%0d), no fault", MUT, nexp, SCL);
  else $display("FAIL tb_hbm_su_red_pretree MUT=%0d: %0d errors", MUT, errs);
  $finish;
 end
endmodule
`default_nettype wire
