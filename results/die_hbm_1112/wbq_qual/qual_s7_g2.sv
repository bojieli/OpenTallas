`timescale 1ns/1ps
`default_nettype none
// HBM-WBQ-QUAL-1 (DIE-HBM-100, 11-12): NEW root slot glue = ot_wbq_root_g2 pin list, built from the ROOT S7 private source
// (ot_wbq_root_g0__fcore = group 0, ot_wbq_root_s7_g1 = group 1; same instance names u_g0/u_g1/u_grp as ot_wbq_root_g2 so one
// hierarchical probe set serves both). Bench-only negative controls on the parent pins of the roots:
//   MUTCB 1: copy_bank one more fifo_clk late (total +2); 2: copy_bank inverted (wrong bank)
//   MUTSTOP 1: s_stop dropped (tied 0); 2: s_stop three fifo_clk late; 3: s_stop dropped on group 1 only
module qual_s7_g2 #(parameter integer CRED=4, parameter integer CBREG=1, parameter integer SSTOPREG=1, parameter integer GREG=1,
                    parameter integer MUTCB=0, parameter integer MUTSTOP=0)(
 input wire hbm_clk,fifo_clk,stream_rst_n,hbm_rst_n,
 input wire [1:0] root_id,
 input wire reserve_v,reserve_bank,input wire [11:0] reserve_total,input wire [29:0] reserve_base,
 input wire fill_start,fill_start_bank,
 input wire [255:0] wd0,wd1,wd2,wd3,wd4,wd5,wd6,wd7,input wire [7:0] wd_v,
 input wire copy_on,copy_bank,s_stop,h_stop,
 input wire [1:0] g_credit,
 output wire root_ready,
 output wire [1:0] g_v,output wire [571:0] g_d
);
 reg cb_l;reg [2:0] st_l;
 always @(posedge fifo_clk)begin cb_l<=copy_bank;st_l<={st_l[1:0],s_stop};end
 wire cb_m=(MUTCB==1)?cb_l:(MUTCB==2)?!copy_bank:copy_bank;
 wire st_m=(MUTSTOP==1)?1'b0:(MUTSTOP==2)?st_l[2]:s_stop;
 wire st_m1=(MUTSTOP==3)?1'b0:st_m;
 wire rr1;
 ot_wbq_root_g0__fcore #(.CRED(CRED),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.GREG(GREG)) u_g0(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  .root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),
  .fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd0),.wd1(wd1),.wd2(wd2),.wd3(wd3),.wd_v(wd_v[3:0]),
  .copy_on(copy_on),.copy_bank(cb_m),.s_stop(st_m),.h_stop(h_stop),.g_credit(g_credit[0]),
  .root_ready(root_ready),.g_v(g_v[0]),.g_d(g_d[285:0]));
`ifdef QUAL_G1RR
 // g1 candidate of the kit codex-hbm-root-s7-1107/kit_g1_vS7_RR_reviewed: ot_wbq_root_g1__fcore, RPIPE ingress record pipeline (rr_fifo)
 ot_wbq_root_g1__fcore #(.CRED(CRED),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.GREG(GREG)) u_g1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  .root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),
  .fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd4),.wd1(wd5),.wd2(wd6),.wd3(wd7),.wd_v(wd_v[7:4]),
  .copy_on(copy_on),.copy_bank(cb_m),.s_stop(st_m1),.h_stop(h_stop),.g_credit(g_credit[1]),
  .root_ready(rr1),.g_v(g_v[1]),.g_d(g_d[571:286]));
`else
 ot_wbq_root_s7_g1 #(.CRED(CRED),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.GREG(GREG)) u_g1(.hbm_clk(hbm_clk),.fifo_clk(fifo_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  .root_id(root_id),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_total(reserve_total),.reserve_base(reserve_base),
  .fill_start(fill_start),.fill_start_bank(fill_start_bank),.wd0(wd4),.wd1(wd5),.wd2(wd6),.wd3(wd7),.wd_v(wd_v[7:4]),
  .copy_on(copy_on),.copy_bank(cb_m),.s_stop(st_m1),.h_stop(h_stop),.g_credit(g_credit[1]),
  .root_ready(rr1),.g_v(g_v[1]),.g_d(g_d[571:286]));
`endif
endmodule
`default_nettype wire
