`timescale 1ns/1ps
// Minimum W5 source-owned producer/consumer context. No native parent change.
// The only integration opt-in is ENABLE=0. Full NB2/PP1 element and real first
// return node; port arrival timing never substitutes for these launch flops.
module ot_w5_context #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire cfg_go,input wire [5:0] cfg_ph,input wire [2:0] cfg_np,
 input wire [47:0] cm_q,input wire go,
 input wire xs_v,input wire [7:0] xs_p,input wire [2:0] xs_b,
 input wire [1:0] xs_sv,input wire [255:0] xs_q0,xs_q1,
 input wire [9:0] xs_e0,xs_e1,input wire [2:0] xs_pos,
 input wire pg_en,sched_v,input wire [23:0] sched_gap,
 input wire [23:0] pg_lead,pg_bet,input wire [7:0] pg_idle,pg_rst,
 input wire [15:0] pg_step,pg_ack_to,input wire [3:0] sw_ack,
 output wire [10:0] cm_a,output wire [3:0] sw_en,
 output wire ready,late,pg_fault,fault,busy,
 output wire o_v,output wire [31:0] o_t,o_d,output wire o_e
);
 wire [548:0] xs;
 // Literal BST payload includes valid/pair/bank/subvalid/Q/exponents/position.
 ot_hdc_delay #(.W(549),.D(3)) u_bst(.clk(clk),.rst_n(por_n),
 .d({xs_v,xs_p,xs_b,xs_sv,xs_q0,xs_e0,xs_q1,xs_e1,xs_pos}),.q(xs));
 wire c_v,go_e,ld_busy,ld_fault,settings_bad,go_bad;
 wire [2:0] go_q;
 ot_qwen_s4_checked_state #(.W(3)) u_go_source(.clk(clk),.por_n(por_n),.en(!go_bad),
 .d({go_q[1:0],go}),.q(go_q),.bad(go_bad));
 wire b_go=go_q[2];
 wire context_fault=(ENABLE!=0)&&(settings_bad|go_bad|ld_fault);
 wire [4:0] c_a;wire [47:0] c_d;
 ot_w5_loader_checked #(.ENABLE(ENABLE)) u_ld(.clk(clk),.por_n(por_n),
 .cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(b_go),.cm_a(cm_a),.cm_q(cm_q),
 .c_v(c_v),.c_a(c_a),.c_d(c_d),.go_e(go_e),.ld_busy(ld_busy),.fault(ld_fault));
 // Real root launch register for settings and ring tail samples. Real path
 // from these Q pins through scheduler/controller to the gated domain.
 wire [125:0] settings;
 ot_qwen_s4_checked_state #(.W(126)) u_settings(.clk(clk),.por_n(por_n),.en(!settings_bad),
 .d({pg_en,sched_v,sched_gap,pg_lead,pg_bet,pg_idle,pg_rst,pg_step,pg_ack_to,sw_ack}),
 .q(settings),.bad(settings_bad));
 wire [1:0] pv,pe; wire [63:0] pd;wire [31:0] pr;
 wire [9:0] ps,pn;wire [5:0] pp;wire ef;
 wire rst_n=por_n;
 ot_w5_stage_q_pg_cdc_w10 #(.K(1),.NB(2),.MTP(1),.EARLY(1),.FAST(1),.PP(1),
 .PROTECTED_AO(ENABLE),.RETENTION_EDGE_WRITE(ENABLE)) u_stage(
 .context_fault(context_fault),.clk(clk),.aon_clk(clk),.rst_n(rst_n),.cfg_v(c_v),.cfg_a(c_a),.cfg_d(c_d),.go(go_e),
 .xs_v(xs[548]),.xs_p(xs[547:540]),.xs_b(xs[539:537]),.xs_sv(xs[536:535]),
 .xs_q0(xs[534:279]),.xs_e0(xs[278:269]),.xs_q1(xs[268:13]),.xs_e1(xs[12:3]),.xs_pos(xs[2:0]),
 .pv(pv),.pval(pd),.prow(pr),.pseg(ps),.pnseg(pn),.perr(pe),.ppos(pp),.busy(busy),.fault(ef),
 .pg_en(settings[125]),.sched_v(settings[124]),.sched_gap(settings[123:100]),
 .pg_lead(settings[99:76]),.pg_bet(settings[75:52]),.pg_idle(settings[51:44]),
 .pg_rst(settings[43:36]),.pg_step(settings[35:20]),.pg_ack_to(settings[19:4]),
 .sw_ack(settings[3:0]),.sw_en(sw_en),.pg_ready(ready),.pg_late(late),.pg_fault(pg_fault));
 // Actual first queue capture, not a disconnected output-delay constraint.
 // Current return ABI has k=3 bits from the physical element's segment field.
 wire rf;
 ot_v41_retn_w17w10 #(.RD(64),.RST(1),.BYPASS(1)) u_return(
 .clk(clk),.rst_n(por_n),.a_v(pv[0]),.a_t({pp[2:0],pr[15:0],ps[4:0],3'b0,pn[4:0]}),.a_d(pd[31:0]),.a_e(pe[0]),
 .b_v(pv[1]),.b_t({pp[5:3],pr[31:16],ps[9:5],3'b0,pn[9:5]}),.b_d(pd[63:32]),.b_e(pe[1]),
 .o_v(o_v),.o_t(o_t),.o_d(o_d),.o_e(o_e),.fault(rf));
 assign fault=ef|pg_fault|late|ld_fault|rf;
endmodule
