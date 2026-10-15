`timescale 1ns/1ps
`default_nettype none
// New layer-die master: original engines0..7 + VM12 + PQ13. Engines8..11
// retain their global meanings and are absent here. New host/PQ lanes and
// engine13 hardware require new physical pin/area/clock qualification.
module dsfd_stage_seq_static_c9 #(parameter integer NOPS=128,STAGE=0)(
 input wire[0:0]ckv,rsv,ck,rst,
 input wire[52:0]f_ks,output wire[53:0]t_kd,
 input wire[35:0]f_pw,input wire[7:0]f_plen,output reg[5:0]t_st,
 input wire[35:0]f_pq_pw,output wire[35:0]t_pq_desc_pw,
 output wire calendar_prime,stage_start,
 output wire[11:0]calendar_base,output wire[12:0]calendar_length,
 input wire pq_image_sealed,pq_calendar_primed,pq_calendar_fault,
 output wire[84:0]c0,c1,c2,c3,c4,c5,c6,c7,c12,c13,
 input wire[8:0]d0,d1,d2,d3,d4,d5,d6,d7,d12,d13,
 input wire[1:0]s0,s1,s2,s3,s4,s5,s6,s7,s12,s13
);
 reg[1:0]rr,rv;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ckv[0] or negedge rsv[0])if(!rsv[0])rv<=0;else rv<={rv[0],1'b1};
 reg[2:0]pq_status;
 always @(posedge ck[0] or negedge rr[1])if(!rr[1])pq_status<=0;
  else pq_status<={pq_image_sealed,pq_calendar_primed,pq_calendar_fault};
 wire pv;wire[34:0]pd;wire job_launch,job_busy,boot_fault;wire[5:0]core_st;
 ot_s81_fixed_mailbox #(.W(35))pq_pw(.s_clk(ckv[0]),.s_rst_n(rv[1]),.s_v(f_pq_pw[35]),.s_d(f_pq_pw[34:0]),
  .d_clk(ck[0]),.d_rst_n(rr[1]),.d_v(pv),.d_d(pd));
 ot_s81_pq_boot_control u_boot(.ck(ck[0]),.rst_n(rr[1]),.pw({pv,pd}),.job_launch(job_launch),.busy(job_busy),
  .image_sealed(pq_status[2]),.calendar_primed(pq_status[1]),.calendar_fault(pq_status[0]),
  .f_desc_pw(t_pq_desc_pw),.calendar_prime(calendar_prime),.stage_start(stage_start),
  .calendar_base(calendar_base),.calendar_length(calendar_length),.fault(boot_fault));
 // Sticky source faults return through the existing serialized status plane.
 reg[1:0]bf;
 always @(posedge ckv[0] or negedge rsv[0])if(!rsv[0])bf<=0;else bf<={bf[0],boot_fault};
 always @(posedge ckv[0] or negedge rsv[0])if(!rsv[0])t_st<=0;
  else t_st<={core_st[5]|bf[1],core_st[4:0]};
`ifdef OT_SSEQS_MUT_PQ_ABSENT
 localparam[13:0]PRESENT=14'h10ff;
`else
 localparam[13:0]PRESENT=14'h30ff;
`endif
 dsfd_stage_seq_static_c #(.NOPS(NOPS),.STAGE(STAGE),.ENG_PRESENT(PRESENT))u_s(
  .ckv(ckv),.rsv(rsv),.ck(ck),.rst(rst),.f_ks(f_ks),.t_kd(t_kd),.f_pw(f_pw),.f_plen(f_plen),.t_st(core_st),.job_launch(job_launch),.job_busy(job_busy),
  .c0(c0),.c1(c1),.c2(c2),.c3(c3),.c4(c4),.c5(c5),.c6(c6),.c7(c7),.c12(c12),.c13(c13),
  .d0(d0),.d1(d1),.d2(d2),.d3(d3),.d4(d4),.d5(d5),.d6(d6),.d7(d7),.d12(d12),.d13(d13),
  .s0(s0),.s1(s1),.s2(s2),.s3(s3),.s4(s4),.s5(s5),.s6(s6),.s7(s7),.s12(s12),.s13(s13),
  .d8(9'd0),.d9(9'd0),.d10(9'd0),.d11(9'd0),.s8(2'd0),.s9(2'd0),.s10(2'd0),.s11(2'd0));
endmodule
`default_nettype wire
