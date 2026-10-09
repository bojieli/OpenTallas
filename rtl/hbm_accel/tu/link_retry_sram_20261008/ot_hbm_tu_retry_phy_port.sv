`timescale 1ns/1ps
// Real TU PHY/core pulse binding. Native endpoint continues to own its RXFIFO.
// Link management supplies an atomic PHY-session epoch after both clocks reset
// and link/FEC training. No binary epoch is sampled across clocks in this block.
// Bridge outputs are actual core credit pulses, not same-cycle ready proxies.
module ot_hbm_tu_retry_phy_port #(
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
