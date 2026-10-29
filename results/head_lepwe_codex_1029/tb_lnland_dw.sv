`timescale 1ns/1ps
// DIE-HEAD-21 lepwe: cycle-exact compare of ot_s81hd_lnland_dw (lep_pair landing, decoded slot write) against the
// ACTUAL ot_s81_mu72_lnland_nst (portfix178, MUT 0) at full shape: all 556 + 558 inputs random every edge, random
// reset pulses on rs_k / rs_n (both sides reset independently), every output compared every edge after the first reset.
module tb_lnland_dw;
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0; wire rs_k=rst_n, rs_n=rst_n; integer hold=0;
 reg [555:0] kn_i=0; reg [557:0] nk_i=0;
 wire [555:0] kn_o, kn_n; wire [557:0] nk_o, nk_n;
 ot_s81_mu72_lnland_nst #(.MUT(0)) uo(.ck_k(ck),.ck_n(ck),.rs_k(rs_k),.rs_n(rs_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kn_o[555]),.n_rxv(kn_o[554]),.n_lo_v(kn_o[553]),.n_lo_d(kn_o[552:0]),
  .n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_flt(nk_o[557:555]),.k_lo_r(nk_o[554]),.k_li_v(nk_o[553]),.k_li_d(nk_o[552:0]));
 ot_s81hd_lnland_dw un(.ck_k(ck),.ck_n(ck),.rs_k(rs_k),.rs_n(rs_n),
  .k_li_r(kn_i[555]),.k_rxv(kn_i[554]),.k_lo_v(kn_i[553]),.k_lo_d(kn_i[552:0]),
  .n_li_r(kn_n[555]),.n_rxv(kn_n[554]),.n_lo_v(kn_n[553]),.n_lo_d(kn_n[552:0]),
  .n_flt(nk_i[557:555]),.n_lo_r(nk_i[554]),.n_li_v(nk_i[553]),.n_li_d(nk_i[552:0]),
  .k_flt(nk_n[557:555]),.k_lo_r(nk_n[554]),.k_li_v(nk_n[553]),.k_li_d(nk_n[552:0]));
 integer cyc=0, checks=0, nz=0, resets=0, j;
 always @(posedge ck) begin
  #1; cyc=cyc+1;
  if (cyc>12) begin
   if (kn_o!==kn_n || nk_o!==nk_n) $fatal(1,"LNLAND_DW MISMATCH cycle %0d", cyc);
   checks=checks+1; if (|kn_n) nz=nz+1;
  end
 end
 initial begin
  repeat(8) @(negedge ck); rst_n=1;
  for (integer c=0;c<`NCYC;c=c+1) begin
   for (j=0;j<18;j=j+1) begin kn_i=(kn_i<<32)|556'($urandom); nk_i=(nk_i<<32)|558'($urandom); end
   if (hold>0) begin hold=hold-1; if (hold==0) rst_n=1; end
   else if ($urandom%997==0) begin rst_n=0; hold=8; resets=resets+1; end
   @(negedge ck);
  end
  if (nz < `NCYC/2) $fatal(1,"LNLAND_DW too few live output cycles %0d", nz);
  $display("LNLAND_DW PASS checks=%0d nonzero_kn_cycles=%0d reset_pulses=%0d", checks, nz, resets); $finish;
 end
endmodule
