`timescale 1ns/1ps
module tb;
reg ck=0; always begin #0.416 ck=1; #0.417 ck=0; end
reg rs_k=0,rs_n=0;
reg [0:0] k_lo_v=0;
reg [552:0] k_lo_d=0;
reg [0:0] k_li_r=0;
reg [0:0] k_rxv=0;
reg [0:0] n_lo_r=0;
reg [0:0] n_li_v=0;
reg [552:0] n_li_d=0;
reg [2:0] n_flt=0;
wire [0:0] g_k_lo_r;
wire [0:0] g_k_li_v;
wire [552:0] g_k_li_d;
wire [2:0] g_k_flt;
wire [0:0] g_n_lo_v;
wire [552:0] g_n_lo_d;
wire [0:0] g_n_li_r;
wire [0:0] g_n_rxv;
wire [0:0] d_k_lo_r;
wire [0:0] d_k_li_v;
wire [552:0] d_k_li_d;
wire [2:0] d_k_flt;
wire [0:0] d_n_lo_v;
wire [552:0] d_n_lo_d;
wire [0:0] d_n_li_r;
wire [0:0] d_n_rxv;
wire [0:0] m_k_lo_r;
wire [0:0] m_k_li_v;
wire [552:0] m_k_li_d;
wire [2:0] m_k_flt;
wire [0:0] m_n_lo_v;
wire [552:0] m_n_lo_d;
wire [0:0] m_n_li_r;
wire [0:0] m_n_rxv;
wire [0:0] r_k_lo_r;
wire [0:0] r_k_li_v;
wire [552:0] r_k_li_d;
wire [2:0] r_k_flt;
wire [0:0] r_n_lo_v;
wire [552:0] r_n_lo_d;
wire [0:0] r_n_li_r;
wire [0:0] r_n_rxv;
ot_s81_mu72_lnland_nst #(.MUT(0)) u_g (.ck_k(ck), .ck_n(ck), .rs_k(rs_k), .rs_n(rs_n), .k_lo_v(k_lo_v), .k_lo_d(k_lo_d), .k_li_r(k_li_r), .k_rxv(k_rxv), .n_lo_r(n_lo_r), .n_li_v(n_li_v), .n_li_d(n_li_d), .n_flt(n_flt), .k_lo_r(g_k_lo_r), .k_li_v(g_k_li_v), .k_li_d(g_k_li_d), .k_flt(g_k_flt), .n_lo_v(g_n_lo_v), .n_lo_d(g_n_lo_d), .n_li_r(g_n_li_r), .n_rxv(g_n_rxv));
ot_s81_mu72_lnland_nst_1ck #(.MUT(0)) u_d (.ck_k(ck), .rs_k(rs_k), .rs_n(rs_n), .k_lo_v(k_lo_v), .k_lo_d(k_lo_d), .k_li_r(k_li_r), .k_rxv(k_rxv), .n_lo_r(n_lo_r), .n_li_v(n_li_v), .n_li_d(n_li_d), .n_flt(n_flt), .k_lo_r(d_k_lo_r), .k_li_v(d_k_li_v), .k_li_d(d_k_li_d), .k_flt(d_k_flt), .n_lo_v(d_n_lo_v), .n_lo_d(d_n_lo_d), .n_li_r(d_n_li_r), .n_rxv(d_n_rxv));
ot_s81_mu72_lnland_nst_1ck #(.MUT(1)) u_m (.ck_k(ck), .rs_k(rs_k), .rs_n(rs_n), .k_lo_v(k_lo_v), .k_lo_d(k_lo_d), .k_li_r(k_li_r), .k_rxv(k_rxv), .n_lo_r(n_lo_r), .n_li_v(n_li_v), .n_li_d(n_li_d), .n_flt(n_flt), .k_lo_r(m_k_lo_r), .k_li_v(m_k_li_v), .k_li_d(m_k_li_d), .k_flt(m_k_flt), .n_lo_v(m_n_lo_v), .n_lo_d(m_n_lo_d), .n_li_r(m_n_li_r), .n_rxv(m_n_rxv));
ot_s81_mu72_lnland_nst_1ck #(.MUT(0)) u_r (.ck_k(ck), .rs_k(rs_n), .rs_n(rs_n), .k_lo_v(k_lo_v), .k_lo_d(k_lo_d), .k_li_r(k_li_r), .k_rxv(k_rxv), .n_lo_r(n_lo_r), .n_li_v(n_li_v), .n_li_d(n_li_d), .n_flt(n_flt), .k_lo_r(r_k_lo_r), .k_li_v(r_k_li_v), .k_li_d(r_k_li_d), .k_flt(r_k_flt), .n_lo_v(r_n_lo_v), .n_lo_d(r_n_lo_d), .n_li_r(r_n_li_r), .n_rxv(r_n_rxv));
wire [1113:0] g_all = {g_k_lo_r, g_k_li_v, g_k_li_d, g_k_flt, g_n_lo_v, g_n_lo_d, g_n_li_r, g_n_rxv};
wire [1113:0] d_all = {d_k_lo_r, d_k_li_v, d_k_li_d, d_k_flt, d_n_lo_v, d_n_lo_d, d_n_li_r, d_n_rxv};
wire [1113:0] m_all = {m_k_lo_r, m_k_li_v, m_k_li_d, m_k_flt, m_n_lo_v, m_n_lo_d, m_n_li_r, m_n_rxv};
wire [1113:0] r_all = {r_k_lo_r, r_k_li_v, r_k_li_d, r_k_flt, r_n_lo_v, r_n_lo_d, r_n_li_r, r_n_rxv};
integer cycle,j; integer checks=0, mbad=0,rbad=0;
initial begin
 for(cycle=0;cycle<4096;cycle=cycle+1) begin
  @(negedge ck);
  rs_k=(cycle>=16 && (cycle%211<202)); rs_n=(cycle>=20 && (cycle%197<187));
  k_lo_v=1'($urandom);
  for(j=0;j<553;j=j+1) k_lo_d[j]=1'($urandom);
  k_li_r=1'($urandom);
  k_rxv=1'($urandom);
  n_lo_r=1'($urandom);
  n_li_v=1'($urandom);
  for(j=0;j<553;j=j+1) n_li_d[j]=1'($urandom);
  for(j=0;j<3;j=j+1) n_flt[j]=1'($urandom);
  @(posedge ck); #0.01;
  if(cycle>=32) begin
   if(g_all !== d_all) $fatal(1,"LOCKSTEP_MISMATCH cycle=%0d",cycle);
   if(^g_all === 1'bx) $fatal(1,"OBSERVED_UNKNOWN cycle=%0d",cycle);
   checks=checks+1114;
   if(g_all !== m_all) mbad=mbad+1;
   if(g_all !== r_all) rbad=rbad+1;
  end
 end
 if(mbad==0 || rbad==0) $fatal(1,"MUTANTS_NOT_CAUGHT %0d %0d",mbad,rbad);
 $display("LN_ONECLK_PASS cycles=%0d checks=%0d latency_mutant=%0d reset_mutant=%0d",4096,checks,mbad,rbad); $finish;
end
endmodule
