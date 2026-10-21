`timescale 1ns/1ps
// Real source hierarchy: current regional service entry plus optional all-quarter
// SO ingress. Compiler reserves q slots; a collision is a fault, never arbitration.
module dsdv_svc_rs_pvso_entry #(
 parameter integer PVSO_ENABLE=0,NTP=0,ST=0,DIE_ID=0,
 parameter bit SRAM_MACRO=0
)(
 input wire ck,rst,input wire[3:0]sid,
 input wire[32:0]j,output wire[1:0]jd,input wire[514:0]q,input wire[291:0]hw,output wire[8:0]hc,
 output wire fault,output wire[1:0]st_rg,
 input wire[4*805-1:0]dn_i,output wire[4*805-1:0]dn_o,
 input wire[4*16-1:0]up_i,output wire[4*16-1:0]up_o,
 input wire[4*514-1:0]ri,output wire[4*514-1:0]ro,
 input wire[3:0]gi_v,input wire[4*2132-1:0]gi_d,output wire[3:0]go_v,output wire[4*2132-1:0]go_d,
 input wire[3:0]si_v,input wire[4*1076-1:0]si_d,output wire[3:0]so_v,output wire[4*1076-1:0]so_d,
 output wire[681:0]rq,input wire[1:0]rk,wd,rv,input wire[511:0]r_data,input wire[33:0]r_tag,input wire[7:0]r_beat,input wire[1:0]hs,
 output wire pv_v,output wire[512:0]pv_d,output wire[47:0]pv_x,
 input wire cfg_v,input wire[19:0]cfg_owner,input wire[20:0]cfg_position,input wire[7:0]cfg_se_jid,cfg_so_jid,
 input wire quarter_v,input wire[1:0]quarter,input wire[512:0]quarter_d,
 input wire param_v,input wire[2:0]param_row,input wire[19:0]param_owner,input wire[20:0]param_position,input wire[511:0]param_d,
 input wire den_v,input wire[15:0]den_mask,input wire[19:0]den_owner,input wire[7:0]den_jid,input wire launch,
 output wire so_ready,so_done,output wire[11:0]so_fault_code
);
 wire v,inf,entry_f;wire[511:0]d;wire[514:0]q_to_entry;
 reg collision;
 always @(posedge ck or negedge rst)if(!rst)collision<=0;else if(v&&q[0])collision<=1;
 assign q_to_entry=v?{2'd0,d,1'b1}:q;
 assign fault=entry_f|inf|collision;
 dsdv_pv_so_ingress #(.ENABLE(PVSO_ENABLE)) u_ingress(.clk(ck),.rst_n(rst),
  .cfg_v(cfg_v),.cfg_owner(cfg_owner),.cfg_position(cfg_position),.cfg_se_jid(cfg_se_jid),.cfg_so_jid(cfg_so_jid),
  .pv_v(quarter_v),.pv_quarter(quarter),.pv_d(quarter_d),
  .param_v(param_v),.param_row(param_row),.param_owner(param_owner),.param_position(param_position),.param_d(param_d),
  .den_v(den_v),.den_mask(den_mask),.den_owner(den_owner),.den_jid(den_jid),.launch(launch),
  .q_v(v),.q_d(d),.ready(so_ready),.done(so_done),.fault(inf),.fault_code(so_fault_code));
 dsdv_svc_rs_entry #(.DIE_ID(DIE_ID),.ST(ST),.SRAM_MACRO(SRAM_MACRO),.SMT(1),.NTP(NTP),.PV_IDENTITY(PVSO_ENABLE)) u_entry(
  .ck(ck),.rst(rst),.sid(sid),.j(j),.jd(jd),.q(q_to_entry),.hw(hw),.hc(hc),.fault(entry_f),.st_rg(st_rg),
  .dn_i(dn_i),.dn_o(dn_o),.up_i(up_i),.up_o(up_o),.ri(ri),.ro(ro),
  .gi_v(gi_v),.gi_d(gi_d),.go_v(go_v),.go_d(go_d),.si_v(si_v),.si_d(si_d),.so_v(so_v),.so_d(so_d),
  .rq(rq),.rk(rk),.wd(wd),.rv(rv),.r_data(r_data),.r_tag(r_tag),.r_beat(r_beat),.hs(hs),.pv_v(pv_v),.pv_d(pv_d),.pv_x(pv_x));
endmodule
