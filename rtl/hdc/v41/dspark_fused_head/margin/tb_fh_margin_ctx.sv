`timescale 1ns/1ps
// ctx MARGIN=1 (zero-cycle group-copy trees) == ctx MARGIN=0, cycle for cycle, open loop.
module tb_fh_margin_ctx;
 parameter integer MUT=0;   // 1: DUT row copy wrong (MUT built into a duplicate check), see below
 localparam integer W=16,G=4,AW=24,NW=16,TW=1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1;
 reg clk=0,rst_n=0; always #0.5 clk=~clk;
 reg s3_v_in,go_fus,tv_in,ov1_in,rb,wack; reg [TW-1:0] tag; reg [G*W*32-1:0] res_in,ra_q;
 reg [AW-1:0] i_iaddr; reg [4:0] busy_in; reg [G-1:0] o_we1_in; reg [G*AW-1:0] o_addr1_in;
 reg [G*W-1:0] o_mask1_in,leaf_mask_in; reg [NW-1:0] leaf_row_in,am_idx_in;
 wire [TW-1:0] rt0,rt1; wire rv0,rv1,we0,we1,lv0,lv1,ov0,ov1,f0,f1; wire [G-1:0] gf0,gf1,owe0,owe1,re0,re1;
 wire [(1+32+NW)*G*W-1:0] lf0,lf1; wire [G*AW-1:0] oa0,oa1,ra0,ra1; wire [G*W-1:0] om0,om1; wire [G*W*32-1:0] od0,od1;
`define CTXP(M) .W(W),.G(G),.IL(8),.AW(AW),.NW(NW),.ALAT(7),.CAPTURE(1),.RETURN_EXTRA(5),.RETIRE(1),.MARGIN(M)
`define CTXC .clk(clk),.rst_n(rst_n),.retire_busy(rb),.retire_warm_ack(wack),.s3_v_in(s3_v_in),.a_tag_p_in(tag),.res_in(res_in),.ra_q(ra_q),.go_fus(go_fus),.i_iaddr(i_iaddr),.busy_in(busy_in),.o_we1_in(o_we1_in),.o_addr1_in(o_addr1_in),.o_mask1_in(o_mask1_in),.leaf_mask_in(leaf_mask_in),.leaf_row_in(leaf_row_in),.tv_in(tv_in),.ov1_in(ov1_in),.am_idx_in(am_idx_in)
 ot_hdc_v41_fh_ctx #(`CTXP(0)) ref0(`CTXC,.warm_emit(we0),.leaf_valid(lv0),.result_valid(ov0),.ra_re(re0),.ra_addr(ra0),.r_tag(rt0),.r_v(rv0),.leaf(lf0),.o_we(owe0),.o_addr(oa0),.o_mask(om0),.o_data(od0),.fault(f0),.group_fault(gf0));
 ot_hdc_v41_fh_ctx #(`CTXP(1)) dut(`CTXC,.warm_emit(we1),.leaf_valid(lv1),.result_valid(ov1),.ra_re(re1),.ra_addr(ra1),.r_tag(rt1),.r_v(rv1),.leaf(lf1),.o_we(owe1),.o_addr(oa1),.o_mask(om1),.o_data(od1),.fault(f1),.group_fault(gf1));
 integer i,j,seed=5,fused=0,iw=0;
 initial begin
  {s3_v_in,go_fus,tv_in,ov1_in,rb,wack,tag,res_in,ra_q,i_iaddr,busy_in,o_we1_in,o_addr1_in,o_mask1_in,leaf_mask_in,leaf_row_in,am_idx_in}=0;
  repeat(3)@(negedge clk); rst_n=1;
  for(i=0;i<3000;i=i+1) begin
   @(negedge clk);
   if(i>40 && {we1,lv1,ov1,re1,ra1,rt1,rv1,lf1,owe1,oa1,om1,od1,f1,gf1}!=={we0,lv0,ov0,re0,ra0,rt0,rv0,lf0,owe0,oa0,om0,od0,f0,gf0}) $fatal(1,"ctx lockstep %0d",i);
   if(MUT && i>40 && lf1===lf0 && i==2999) $fatal(1,"no-op");
   if(ref0.u_fh.protected_v) fused=fused+1; if(ref0.iw_go) iw=iw+1;
   s3_v_in=(($random(seed)&3)==0); go_fus=(($random(seed)&63)==0); tv_in=$random(seed); ov1_in=$random(seed);
   rb=(($random(seed)&7)==0); wack=(($random(seed)&15)==0);
   for(j=0;j<TW;j=j+32) tag[j+:32]=$random(seed);
   tag[0]=$random(seed); // fused
   for(j=0;j<G*W;j=j+1) begin res_in[32*j+:32]=$random(seed); ra_q[32*j+:32]=$random(seed); end
   i_iaddr=$random(seed); busy_in=(($random(seed)&3)==0)?$random(seed):0; o_we1_in=$random(seed);
   for(j=0;j<G;j=j+1) o_addr1_in[24*j+:24]=$random(seed);
   o_mask1_in={$random(seed),$random(seed)}; leaf_mask_in={$random(seed),$random(seed)};
   leaf_row_in=$random(seed); am_idx_in=$random(seed);
  end
  if(fused<100||iw<5) $fatal(1,"coverage fused=%0d iw=%0d",fused,iw);
  $display("PASS ctx MARGIN=1 == MARGIN=0 cycles=3000 return_valid=%0d index_writes=%0d",fused,iw); $finish;
 end
endmodule
