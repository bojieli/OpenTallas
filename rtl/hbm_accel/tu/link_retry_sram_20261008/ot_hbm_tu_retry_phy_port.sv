`timescale 1ns/1ps
// Real TU PHY/core pulse binding. Native endpoint continues to own its RXFIFO.
// Link management supplies an atomic PHY-session epoch after both clocks reset
// and link/FEC training. No binary epoch is sampled across clocks in this block.
// Bridge outputs are actual core credit pulses, not same-cycle ready proxies.
module ot_hbm_tu_retry_phy_port_core #(
 parameter ENABLE=0,W=545,SW=12,EW=24,CW=10,CAPACITY=256,
 parameter TIMEOUT=2048
)(
 input wire pclk,prst_n,phy_link_up,input wire[EW-1:0]phy_session,
 input wire clk,rst_n,core_link_up,
 input wire ph_tx_v,input wire[W-1:0]ph_tx_flit,
 output wire ph_rx_v,output wire[W-1:0]ph_rx_flit,
 input wire rx_credit,output wire sw_cr_ret,
 output wire fec_tx_v,input wire fec_tx_ready,output wire[W-1:0]fec_tx_data,
 output wire[SW-1:0]fec_tx_seq,output wire[EW-1:0]fec_tx_session,
 input wire fec_rx_v,output wire fec_rx_ready,input wire fec_rx_ue,
 input wire[W-1:0]fec_rx_data,input wire[SW-1:0]fec_rx_seq,input wire[EW-1:0]fec_rx_session,
 output wire[SW-1:0]ack_seq,output wire ack_nak,output wire[EW-1:0]ack_session,
 output wire[CW-1:0]ack_pop,
 input wire fb_valid,fb_good,fb_nak,input wire[SW-1:0]fb_seq,
 input wire[EW-1:0]fb_session,input wire[CW-1:0]fb_pop,
 output wire fault,output wire[SW-1:0]retained,
 output wire[SW-1:0]ingress_debt,output wire[CW-1:0]rx_debt
);
 generate if(ENABLE)begin:g_enabled
 wire phy_run=prst_n && phy_link_up;
 wire core_run=rst_n && core_link_up;
 wire local_pop,local_cdc_fault,ret_cdc_fault;
 ot_hbm_retry_pop_cdc #(.CAPACITY(CAPACITY),.CW(CW)) u_rx_pop_cdc(
 .s_clk(clk),.s_rst_n(core_run),.s_pop(rx_credit),.d_clk(pclk),.d_rst_n(phy_run),.d_pop(local_pop),.fault(local_cdc_fault),.pending());
 wire iq_valid,iq_ready,iq_fault;wire[W-1:0]iq_data;
 ot_hbm_retry_phy_ingress #(.W(W),.EW(EW),.DEPTH(CAPACITY)) u_ingress(
 .clk(pclk),.rst_n(phy_run),.session(phy_session),.in_valid(ph_tx_v && phy_run),.in_data(ph_tx_flit),.in_ready(),
 .out_valid(iq_valid),.out_ready(iq_ready),.out_data(iq_data),.fault(iq_fault),.debt(ingress_debt));
 wire port_fault;wire[CW-1:0]available;
 wire raw_tx_v,raw_rx_v,raw_rx_ready;
 assign fec_tx_v=raw_tx_v && !fault;
 assign ph_rx_v=raw_rx_v && !fault;
 assign fec_rx_ready=raw_rx_ready && !fault;
 ot_hbm_tu_retry_port #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.CAPACITY(CAPACITY),.CW(CW),.TIMEOUT(TIMEOUT)) u_port(
 .clk(pclk),.rst_n(prst_n),.link_up(phy_link_up),.session(phy_session),
 .in_valid(iq_valid),.in_ready(iq_ready),.in_data(iq_data),
 .tx_valid(raw_tx_v),.tx_ready(fec_tx_ready && !fault),.tx_data(fec_tx_data),.tx_seq(fec_tx_seq),.tx_session(fec_tx_session),
 .rx_valid(fec_rx_v && !fault),.rx_ready(raw_rx_ready),.rx_ue(fec_rx_ue),.rx_data(fec_rx_data),.rx_seq(fec_rx_seq),.rx_session(fec_rx_session),
 .out_valid(raw_rx_v),.out_ready(1'b1),.out_data(ph_rx_flit),.rx_consumed(local_pop),
 .ack_seq(ack_seq),.ack_nak(ack_nak),.ack_session(ack_session),.ack_pop(ack_pop),
 .fb_valid(fb_valid),.fb_good(fb_good),.fb_nak(fb_nak),.fb_seq(fb_seq),.fb_session(fb_session),.fb_pop(fb_pop),
 .fault(port_fault),.retained(retained),.available(available),.rx_debt(rx_debt),.replay_count());
 // Translate cumulative remote pops into individual source events before Gray.
 // Source Gray counter always changes by one; directly Gray-encoding a batch
 // count would permit multiple bits to cross and is deliberately avoided.
 reg[CW-1:0]return_seen,return_pending;
 reg return_fault;
 wire[CW-1:0]delta=fb_pop-return_seen;
 wire return_new=fb_valid && fb_good && fb_session==phy_session && delta!=0 && !delta[CW-1];
 wire return_emit=return_pending!=0 && !port_fault && !return_fault;
 always@(posedge pclk or negedge phy_run)begin
 if(!phy_run)begin return_seen<=0;return_pending<=0;return_fault<=0;end
 else if(!return_fault)begin
 return_pending<=return_pending+(return_new?delta:0)-(return_emit?1'b1:1'b0);
 if(return_new)begin return_seen<=fb_pop;if(delta>CAPACITY)return_fault<=1;end
 if(return_pending>CAPACITY)return_fault<=1;
 end end
 ot_hbm_retry_pop_cdc #(.CAPACITY(CAPACITY),.CW(CW)) u_tx_credit_cdc(
 .s_clk(pclk),.s_rst_n(phy_run),.s_pop(return_emit),.d_clk(clk),.d_rst_n(core_run),.d_pop(sw_cr_ret),.fault(ret_cdc_fault),.pending());
 assign fault=iq_fault || port_fault || local_cdc_fault || ret_cdc_fault || return_fault;
 end else begin:g_disabled
 assign ph_rx_v=0;assign ph_rx_flit=0;assign sw_cr_ret=0;
 assign fec_tx_v=0;assign fec_tx_data=0;assign fec_tx_seq=0;assign fec_tx_session=0;
 assign fec_rx_ready=0;assign ack_seq=0;assign ack_nak=0;assign ack_session=0;assign ack_pop=0;
 assign fault=0;assign retained=0;assign ingress_debt=0;assign rx_debt=0;
 end endgenerate
endmodule

// cont-takeover 2026-10-09: REG_IO=1 registers every functional boundary of the TU PHY retry port (owner rule: no logic
// between a pin and its flop; review-0443 X4 submit lint: 573 combinational in->out bits, in->reg 256 / reg->out 31 levels).
// pclk side: ph_tx / fb_* / phy_session land in flops; ph_rx / ack_* / fault / retained / debts leave from flops; the FEC
// tx (valid/ready out) and rx (valid/ready in) channels pass two-entry skids.  clk side: rx_credit lands in a flop and
// sw_cr_ret leaves from one.  Boundary flops reset with the run gates (link down clears them at once).  Latency: +1 cycle
// each way on every channel, inside the 256-entry replay / landing credit window; default REG_IO=0 is the core unchanged.
`ifdef OT_TU_REG_IO
`define OT_TU_REG_IO_DEF 1
`else
`define OT_TU_REG_IO_DEF 0
`endif
module ot_hbm_tu_skid #(parameter integer W=8)(input wire clk,rst_n,input wire i_valid,output wire i_ready,
 input wire[W-1:0]i_data,output wire o_valid,input wire o_ready,output wire[W-1:0]o_data);
 reg v0,v1;reg[W-1:0]d0,d1;
 assign i_ready=!v1;assign o_valid=v0;assign o_data=d0;
 wire push=i_valid&&!v1,pop=v0&&o_ready;
 always@(posedge clk or negedge rst_n)
 if(!rst_n)begin v0<=0;v1<=0;end
 else if(pop)begin if(v1)v1<=0;else v0<=push;end
 else if(push)begin if(!v0)v0<=1;else v1<=1;end
 always@(posedge clk)
 if(pop)begin if(v1)d0<=d1;else if(push)d0<=i_data;end
 else if(push)begin if(!v0)d0<=i_data;else d1<=i_data;end
endmodule
module ot_hbm_tu_retry_phy_port #(
 parameter ENABLE=0,W=545,SW=12,EW=24,CW=10,CAPACITY=256,
 parameter TIMEOUT=2048,parameter REG_IO=`OT_TU_REG_IO_DEF,
 // LINK_CREDIT (cont-takeover 2026-10-09, REVIEW ~11:30; needs REG_IO): the FEC tx / rx channels are die-link credit
 // relays (rtl/common/ot_link_credit.sv): fec_tx_ready / fec_rx_ready carry credit pulses; landing overflow = fault.
 parameter LINK_CREDIT=0,LINK_DEPTH=8
)(
 input wire pclk,prst_n,phy_link_up,input wire[EW-1:0]phy_session,
 input wire clk,rst_n,core_link_up,
 input wire ph_tx_v,input wire[W-1:0]ph_tx_flit,
 output wire ph_rx_v,output wire[W-1:0]ph_rx_flit,
 input wire rx_credit,output wire sw_cr_ret,
 output wire fec_tx_v,input wire fec_tx_ready,output wire[W-1:0]fec_tx_data,
 output wire[SW-1:0]fec_tx_seq,output wire[EW-1:0]fec_tx_session,
 input wire fec_rx_v,output wire fec_rx_ready,input wire fec_rx_ue,
 input wire[W-1:0]fec_rx_data,input wire[SW-1:0]fec_rx_seq,input wire[EW-1:0]fec_rx_session,
 output wire[SW-1:0]ack_seq,output wire ack_nak,output wire[EW-1:0]ack_session,
 output wire[CW-1:0]ack_pop,
 input wire fb_valid,fb_good,fb_nak,input wire[SW-1:0]fb_seq,
 input wire[EW-1:0]fb_session,input wire[CW-1:0]fb_pop,
 output wire fault,output wire[SW-1:0]retained,
 output wire[SW-1:0]ingress_debt,output wire[CW-1:0]rx_debt
);
 generate if(!(REG_IO&&ENABLE))begin:g_core
 ot_hbm_tu_retry_phy_port_core #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.CW(CW),.CAPACITY(CAPACITY),.TIMEOUT(TIMEOUT)) u(.*);
 end else begin:g_reg
 wire phy_run=prst_n&&phy_link_up,core_run=rst_n&&core_link_up;
 // pclk input flops
 reg tx_v_q,fb_v_q,fb_g_q,fb_n_q;reg[W-1:0]tx_f_q;reg[SW-1:0]fb_s_q;reg[EW-1:0]fb_e_q,ses_q;reg[CW-1:0]fb_p_q;
 always@(posedge pclk or negedge phy_run)if(!phy_run)begin tx_v_q<=0;fb_v_q<=0;fb_g_q<=0;fb_n_q<=0;end
  else begin tx_v_q<=ph_tx_v;fb_v_q<=fb_valid;fb_g_q<=fb_good;fb_n_q<=fb_nak;end
 always@(posedge pclk)begin tx_f_q<=ph_tx_flit;fb_s_q<=fb_seq;fb_e_q<=fb_session;fb_p_q<=fb_pop;ses_q<=phy_session;end
 // reset / link-up into the core from flops (the core uses its run gates as data): async-assert, sync-release
 // reset synchronisers and registered link-up per domain (+2 cycles on reset release, +1 on link-up)
 reg[1:0]prs;reg[1:0]crs;reg pup_q,cup_q;
 always@(posedge pclk or negedge prst_n)if(!prst_n)prs<=0;else prs<={prs[0],1'b1};
 always@(posedge clk or negedge rst_n)if(!rst_n)crs<=0;else crs<={crs[0],1'b1};
 always@(posedge pclk or negedge prst_n)if(!prst_n)pup_q<=0;else pup_q<=phy_link_up;
 always@(posedge clk or negedge rst_n)if(!rst_n)cup_q<=0;else cup_q<=core_link_up;
 // clk input flop
 reg cred_q;always@(posedge clk or negedge core_run)if(!core_run)cred_q<=0;else cred_q<=rx_credit;
 // core
 wire c_rx_v,c_cr,c_tx_v,c_tx_r,c_rxin_r,c_nak,c_fault;wire[W-1:0]c_rx_f,c_tx_d;wire[SW-1:0]c_tx_s,c_ack,c_ret,c_ing;
 wire[EW-1:0]c_tx_e,c_ack_e;wire[CW-1:0]c_ack_p,c_debt;
 wire r_v,r_ue;wire[W-1:0]r_d;wire[SW-1:0]r_s;wire[EW-1:0]r_e;
 ot_hbm_tu_retry_phy_port_core #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.CW(CW),.CAPACITY(CAPACITY),.TIMEOUT(TIMEOUT)) u(
 .pclk(pclk),.prst_n(prs[1]),.phy_link_up(pup_q),.phy_session(ses_q),.clk(clk),.rst_n(crs[1]),.core_link_up(cup_q),
 .ph_tx_v(tx_v_q),.ph_tx_flit(tx_f_q),.ph_rx_v(c_rx_v),.ph_rx_flit(c_rx_f),.rx_credit(cred_q),.sw_cr_ret(c_cr),
 .fec_tx_v(c_tx_v),.fec_tx_ready(c_tx_r),.fec_tx_data(c_tx_d),.fec_tx_seq(c_tx_s),.fec_tx_session(c_tx_e),
 .fec_rx_v(r_v),.fec_rx_ready(c_rxin_r),.fec_rx_ue(r_ue),.fec_rx_data(r_d),.fec_rx_seq(r_s),.fec_rx_session(r_e),
 .ack_seq(c_ack),.ack_nak(c_nak),.ack_session(c_ack_e),.ack_pop(c_ack_p),
 .fb_valid(fb_v_q),.fb_good(fb_g_q),.fb_nak(fb_n_q),.fb_seq(fb_s_q),.fb_session(fb_e_q),.fb_pop(fb_p_q),
 .fault(c_fault),.retained(c_ret),.ingress_debt(c_ing),.rx_debt(c_debt));
 // FEC channels through skids
 wire lk_fault;
 if(LINK_CREDIT)begin:g_flink
 ot_link_credit_tx #(.W(W+SW+EW),.CRED(LINK_DEPTH)) u_tx(.clk(pclk),.rst_n(phy_run),.i_valid(c_tx_v),.i_ready(c_tx_r),.i_data({c_tx_d,c_tx_s,c_tx_e}),
  .l_valid(fec_tx_v),.l_data({fec_tx_data,fec_tx_seq,fec_tx_session}),.l_credit(fec_tx_ready));
 ot_link_credit_rx #(.W(1+W+SW+EW),.DEPTH(LINK_DEPTH)) u_rx(.clk(pclk),.rst_n(phy_run),.l_valid(fec_rx_v),
  .l_data({fec_rx_ue,fec_rx_data,fec_rx_seq,fec_rx_session}),.l_credit(fec_rx_ready),.o_valid(r_v),.o_ready(c_rxin_r),
  .o_data({r_ue,r_d,r_s,r_e}),.fault(lk_fault));
 end else begin:g_fskid
 assign lk_fault=1'b0;
 ot_hbm_tu_skid #(.W(W+SW+EW)) u_tx(.clk(pclk),.rst_n(phy_run),.i_valid(c_tx_v),.i_ready(c_tx_r),.i_data({c_tx_d,c_tx_s,c_tx_e}),
  .o_valid(fec_tx_v),.o_ready(fec_tx_ready),.o_data({fec_tx_data,fec_tx_seq,fec_tx_session}));
 ot_hbm_tu_skid #(.W(1+W+SW+EW)) u_rx(.clk(pclk),.rst_n(phy_run),.i_valid(fec_rx_v),.i_ready(fec_rx_ready),
  .i_data({fec_rx_ue,fec_rx_data,fec_rx_seq,fec_rx_session}),.o_valid(r_v),.o_ready(c_rxin_r),.o_data({r_ue,r_d,r_s,r_e}));
 end

 // pclk output flops
 reg rx_v_o,nak_o,fault_o;reg[W-1:0]rx_f_o;reg[SW-1:0]ack_o,ret_o,ing_o;reg[EW-1:0]ack_e_o;reg[CW-1:0]ack_p_o,debt_o;
 always@(posedge pclk or negedge phy_run)if(!phy_run)begin rx_v_o<=0;nak_o<=0;fault_o<=0;ack_o<=0;ret_o<=0;ing_o<=0;ack_e_o<=0;ack_p_o<=0;debt_o<=0;end
  else begin rx_v_o<=c_rx_v;nak_o<=c_nak;fault_o<=c_fault||lk_fault;ack_o<=c_ack;ret_o<=c_ret;ing_o<=c_ing;ack_e_o<=c_ack_e;ack_p_o<=c_ack_p;debt_o<=c_debt;end
 always@(posedge pclk)rx_f_o<=c_rx_f;
 reg cr_o;always@(posedge clk or negedge core_run)if(!core_run)cr_o<=0;else cr_o<=c_cr;
 assign ph_rx_v=rx_v_o;assign ph_rx_flit=rx_f_o;assign sw_cr_ret=cr_o;assign ack_seq=ack_o;assign ack_nak=nak_o;
 assign ack_session=ack_e_o;assign ack_pop=ack_p_o;assign fault=fault_o;assign retained=ret_o;assign ingress_debt=ing_o;assign rx_debt=debt_o;
 end endgenerate
endmodule

// cont-takeover 2026-10-09: testbench-only valid/ready view of the REG_IO=1 LINK_CREDIT=1 port: the FEC tx and rx channels
// cross ot_link_credit_tb_chan (LAT link flops each way), so tb_hbm_tu_retry_phy_port drives the credit boundary unchanged.
module ot_hbm_tu_retry_phy_port_lk #(
 parameter ENABLE=0,W=545,SW=12,EW=24,CW=10,CAPACITY=256,TIMEOUT=2048,LAT=2,DEPTH=8,MUT_CRED=0
)(
 input wire pclk,prst_n,phy_link_up,input wire[EW-1:0]phy_session,
 input wire clk,rst_n,core_link_up,
 input wire ph_tx_v,input wire[W-1:0]ph_tx_flit,
 output wire ph_rx_v,output wire[W-1:0]ph_rx_flit,
 input wire rx_credit,output wire sw_cr_ret,
 output wire fec_tx_v,input wire fec_tx_ready,output wire[W-1:0]fec_tx_data,
 output wire[SW-1:0]fec_tx_seq,output wire[EW-1:0]fec_tx_session,
 input wire fec_rx_v,output wire fec_rx_ready,input wire fec_rx_ue,
 input wire[W-1:0]fec_rx_data,input wire[SW-1:0]fec_rx_seq,input wire[EW-1:0]fec_rx_session,
 output wire[SW-1:0]ack_seq,output wire ack_nak,output wire[EW-1:0]ack_session,
 output wire[CW-1:0]ack_pop,
 input wire fb_valid,fb_good,fb_nak,input wire[SW-1:0]fb_seq,
 input wire[EW-1:0]fb_session,input wire[CW-1:0]fb_pop,
 output wire fault,output wire[SW-1:0]retained,
 output wire[SW-1:0]ingress_debt,output wire[CW-1:0]rx_debt
);
 wire run=prst_n&&phy_link_up;
 wire tv,tc,rv,rc,tf;wire[W+SW+EW-1:0]td;wire[1+W+SW+EW-1:0]rd;
 ot_link_credit_tb_chan #(.W(W+SW+EW),.DIR(1),.DEPTH(DEPTH),.LAT(LAT)) ct(.clk(pclk),.rst_n(run),.t_valid(1'b0),.t_ready(),.t_data('0),
  .r_valid(fec_tx_v),.r_ready(fec_tx_ready),.r_data({fec_tx_data,fec_tx_seq,fec_tx_session}),.fault(tf),
  .d_valid(),.d_data(),.d_credit(1'b0),.u_valid(tv),.u_data(td),.u_credit(tc));
 ot_link_credit_tb_chan #(.W(1+W+SW+EW),.DIR(0),.DEPTH(DEPTH),.LAT(LAT),.LEAK(MUT_CRED?DEPTH:0)) cr(.clk(pclk),.rst_n(run),
  .t_valid(fec_rx_v),.t_ready(fec_rx_ready),.t_data({fec_rx_ue,fec_rx_data,fec_rx_seq,fec_rx_session}),
  .r_valid(),.r_ready(1'b0),.r_data(),.fault(),.d_valid(rv),.d_data(rd),.d_credit(rc),.u_valid(1'b0),.u_data('0),.u_credit());
 wire[W-1:0]a;wire[SW-1:0]b;wire[EW-1:0]c;assign td={a,b,c};
 wire e;wire[W-1:0]f;wire[SW-1:0]g;wire[EW-1:0]h;assign {e,f,g,h}=rd;
 wire df;
 ot_hbm_tu_retry_phy_port #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.CW(CW),.CAPACITY(CAPACITY),.TIMEOUT(TIMEOUT),.REG_IO(1),
  .LINK_CREDIT(1),.LINK_DEPTH(DEPTH)) u(.pclk(pclk),.prst_n(prst_n),.phy_link_up(phy_link_up),.phy_session(phy_session),
  .clk(clk),.rst_n(rst_n),.core_link_up(core_link_up),.ph_tx_v(ph_tx_v),.ph_tx_flit(ph_tx_flit),.ph_rx_v(ph_rx_v),
  .ph_rx_flit(ph_rx_flit),.rx_credit(rx_credit),.sw_cr_ret(sw_cr_ret),
  .fec_tx_v(tv),.fec_tx_ready(tc),.fec_tx_data(a),.fec_tx_seq(b),.fec_tx_session(c),
  .fec_rx_v(rv),.fec_rx_ready(rc),.fec_rx_ue(e),.fec_rx_data(f),.fec_rx_seq(g),.fec_rx_session(h),
  .ack_seq(ack_seq),.ack_nak(ack_nak),.ack_session(ack_session),.ack_pop(ack_pop),
  .fb_valid(fb_valid),.fb_good(fb_good),.fb_nak(fb_nak),.fb_seq(fb_seq),.fb_session(fb_session),.fb_pop(fb_pop),
  .fault(df),.retained(retained),.ingress_debt(ingress_debt),.rx_debt(rx_debt));
 assign fault=df|tf;
endmodule
