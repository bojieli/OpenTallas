`timescale 1ns/1ps
`default_nettype none
// Static successor of the actual dsfd_stage_seq_c command-plane interface.
// PW36 paging is compiled, not the predecessor's eng/arg-only memory image.
// Every clock crossing is a fixed alternating mailbox, with no queue or credit.
// Program emission requires a separately measured physical clock/launch epoch.
module dsfd_stage_seq_static_c #(
 parameter integer NOPS=128,STAGE=0,MUT=0,
 parameter[13:0]ENG_PRESENT=14'h1fff
)(
 input wire[0:0]ckv,rsv,ck,rst,
 input wire[52:0]f_ks,output wire[53:0]t_kd,
 input wire[35:0]f_pw,input wire[7:0]f_plen,output wire[5:0]t_st,
 output wire[84:0]c0,c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,
 input wire[8:0]d0,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,
 input wire[1:0]s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13,
 output wire job_launch,job_busy
);
 reg[1:0]rr,rv;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ckv[0] or negedge rsv[0])if(!rsv[0])rv<=0;else rv<={rv[0],1'b1};
 wire rn=rr[1],vn=rv[1];
 wire kv,pv;wire[51:0]kd;wire[34:0]pd;
 ot_s81_fixed_mailbox #(.W(52))ks(.s_clk(ckv[0]),.s_rst_n(vn),.s_v(f_ks[52]),.s_d(f_ks[51:0]),
  .d_clk(ck[0]),.d_rst_n(rn),.d_v(kv),.d_d(kd));
 ot_s81_fixed_mailbox #(.W(35))pw(.s_clk(ckv[0]),.s_rst_n(vn),.s_v(f_pw[35]),.s_d(f_pw[34:0]),
  .d_clk(ck[0]),.d_rst_n(rn),.d_v(pv),.d_d(pd));
 reg[7:0]l1,l2;
 always @(posedge ck[0] or negedge rn)if(!rn)begin l1<=0;l2<=0;end else begin l1<=f_plen;l2<=l1;end
 wire[125:0]dw={d13,d12,d11,d10,d9,d8,d7,d6,d5,d4,d3,d2,d1,d0};
 wire[27:0]sw={s13,s12,s11,s10,s9,s8,s7,s6,s5,s4,s3,s2,s1,s0};
 wire[13:0]cv,dv,av,sfault;wire[1175:0]cd;wire[111:0]dt;
 assign job_launch=kv;
 assign job_busy=busy;
 genvar e;
 generate for(e=0;e<14;e=e+1)begin:g_ports
  assign dv[e]=ENG_PRESENT[e]&dw[9*e+8];assign dt[8*e+:8]=dw[9*e+:8];
  assign av[e]=ENG_PRESENT[e]&sw[2*e+1]&!sw[2*e];
  assign sfault[e]=ENG_PRESENT[e]&sw[2*e];
 end endgenerate
 assign {c13,c12,c11,c10,c9,c8,c7,c6,c5,c4,c3,c2,c1,c0}=
  {cv[13],cd[1092+:84],cv[12],cd[1008+:84],cv[11],cd[924+:84],cv[10],cd[840+:84],cv[9],cd[756+:84],
   cv[8],cd[672+:84],cv[7],cd[588+:84],cv[6],cd[504+:84],cv[5],cd[420+:84],
   cv[4],cd[336+:84],cv[3],cd[252+:84],cv[2],cd[168+:84],cv[1],cd[84+:84],cv[0],cd[0+:84]};
 wire done,kdone,slot,busy,fault;wire[3:0]code;wire[20:0]tok;wire[1:0]phase;
 ot_s81_fixed_issue #(.NOPS(NOPS),.NENG(14),.STAGE(STAGE),.ENG_PRESENT(ENG_PRESENT),.MUT(MUT))u_issue(
  .clk(ck[0]),.rst_n(rn),.pw_v(pv),.pw_a(pd[34:28]),.pw_d(pd[27:0]),.prog_len(l2),
  .job_v(kv),.job_user(kd[51:42]),.job_pos(kd[20:0]),.job_tok(kd[41:21]),.job_rdy(),
  .busy(busy),.job_done(done),.job_kdone(kdone),.done_slot(slot),.kit_tok(tok),
  .cmd_v(cv),.cmd_d(cd),.engine_available(av),.dn_v(dv),.dn_tag(dt),
  .fault(fault),.fault_code(code),.st_jobs(),.st_cmds(),.phase(phase));
 wire kvdone;wire[20:0]ret_tok;
 ot_s81_fixed_mailbox #(.W(21))ret(.s_clk(ck[0]),.s_rst_n(rn),.s_v(kdone),.s_d(tok),
  .d_clk(ckv[0]),.d_rst_n(vn),.d_v(kvdone),.d_d(ret_tok));
 assign t_kd={kvdone,ret_tok,32'd0};
 reg engine_fault;
 wire any_engine_fault=|sfault;
 always @(posedge ck[0] or negedge rn)if(!rn)engine_fault<=0;else if(any_engine_fault)engine_fault<=1;
 reg[5:0]st1,st2;
 always @(posedge ckv[0] or negedge vn)if(!vn)begin st1<=0;st2<=0;end
  else begin st1<={fault|engine_fault,(code==0&&engine_fault?4'd11:code),busy};st2<=st1;end
 assign t_st=st2;
endmodule
`default_nettype wire
