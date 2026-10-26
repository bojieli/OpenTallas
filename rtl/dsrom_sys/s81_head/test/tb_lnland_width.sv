`timescale 1ns/1ps
module tb_lnland_width;
 reg ck=0;always #5 ck=~ck;reg rst_n=0;
 reg[559:0] nk_i=0;reg[555:0]kn_i=0;
 wire[559:0] nk_ref,nk,nk_old;wire[557:0]ns,ns_old;
 wire[555:0]kn_ref,kn,kn_old,kns,kns_old;
 ot_s81_mu72_land #(.W(560))ref_n(.ck_w(ck),.ck_r(ck),.rs_w(rst_n),.rs_r(rst_n),.i(nk_i),.o(nk_ref));
 ot_s81_mu72_land #(.W(556))ref_k(.ck_w(ck),.ck_r(ck),.rs_w(rst_n),.rs_r(rst_n),.i(kn_i),.o(kn_ref));
 ot_s81_mu72_lnland d(.ck_k(ck),.ck_n(ck),.rs_k(rst_n),.rs_n(rst_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kn[555]),.n_rxv(kn[554]),.n_lo_v(kn[553]),.n_lo_d(kn[552:0]),
  .n_st(nk_i[559:558]),.n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_st(nk[559:558]),.k_flt(nk[557:555]),.k_lo_r(nk[554]),.k_li_v(nk[553]),.k_li_d(nk[552:0]));
 ot_s81_mu72_lnland_nst s(.ck_k(ck),.ck_n(ck),.rs_k(rst_n),.rs_n(rst_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kns[555]),.n_rxv(kns[554]),.n_lo_v(kns[553]),.n_lo_d(kns[552:0]),
  .n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_flt(ns[557:555]),.k_lo_r(ns[554]),.k_li_v(ns[553]),.k_li_d(ns[552:0]));
 ot_s81_mu72_lnland_old old(.ck_k(ck),.ck_n(ck),.rs_k(rst_n),.rs_n(rst_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kn_old[555]),.n_rxv(kn_old[554]),.n_lo_v(kn_old[553]),.n_lo_d(kn_old[552:0]),
  .n_st(nk_i[559:558]),.n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_st(nk_old[559:558]),.k_flt(nk_old[557:555]),.k_lo_r(nk_old[554]),.k_li_v(nk_old[553]),.k_li_d(nk_old[552:0]));
 ot_s81_mu72_lnland_nst_old olds(.ck_k(ck),.ck_n(ck),.rs_k(rst_n),.rs_n(rst_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kns_old[555]),.n_rxv(kns_old[554]),.n_lo_v(kns_old[553]),.n_lo_d(kns_old[552:0]),
  .n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_flt(ns_old[557:555]),.k_lo_r(ns_old[554]),.k_li_v(ns_old[553]),.k_li_d(ns_old[552:0]));
 integer edge_n=0,checks=0,full_mut=0,nst_mut=0,j;
 always @(posedge ck)begin
  #1;edge_n=edge_n+1;
  if(edge_n>32)begin
   if(nk!==nk_ref||ns!==nk_ref[557:0]||kn!==kn_ref||kns!==kn_ref)$fatal(1,"specified field/latency conservation failed edge%0d",edge_n);
   if(nk[558:0]!==nk_old[558:0]||ns[556:0]!==ns_old[556:0]||kn!==kn_old||kns!==kns_old)$fatal(1,"unchanged data/credit/fault bits changed");
   if(nk!==nk_old)full_mut=full_mut+1;
   if(ns!==ns_old)nst_mut=nst_mut+1;
   checks=checks+1;
  end
 end
 initial begin
  repeat(5)@(negedge ck);rst_n=1;
  repeat(32)@(negedge ck);
  for(integer i=0;i<560;i=i+1)begin
   nk_i=560'd1<<i;kn_i=556'd1<<(i%556);
   @(negedge ck);
  end
  for(integer i=0;i<256;i=i+1)begin
   for(j=0;j<18;j=j+1)nk_i=(nk_i<<32)|560'($urandom);
   for(j=0;j<18;j=j+1)kn_i=(kn_i<<32)|556'($urandom);
   @(negedge ck);
  end
  repeat(12)@(negedge ck);
  if(full_mut==0||nst_mut==0)$fatal(1,"original-width mutants escaped");
  $display("LNLAND_WIDTH PASS checks=%0d full_status_mutant=%0d phy_fault_mutant=%0d data_credit_cycles_unchanged",checks,full_mut,nst_mut);$finish;
 end
endmodule
