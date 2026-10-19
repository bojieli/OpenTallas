`timescale 1ns/1ps
// Production per-face transport. Only PHY frame pins leave the digital RTL.
// Each root is explicit: calendar core/link; TX CDC write/read; RX CDC
// write/read; codec controller plus four SRAM banks. Related roots must retain
// the measured mesochronous phase used by the compiler. This wrapper adds no
// stage beyond the source-bound calendar/CDC/codec composition.
// TOK_REG (Q-DIE11-COLL 10-18, opt-in, default 0 = byte-identical behaviour): one core-side pin register per face
// input (tx_slot/tx_valid/tx_data/peer_slot on cal_ck) and a cal_ck register on the cdc_fault output, so every face
// pin has exactly one capture/launch root and the CDC roots tx_wck/tx_rck/rx_wck/rx_rck and codec_ck[1..4] clock only
// their hard children (static CDC channels, codec banks): hardened face cluster qfd_coll_face_*.  The
// calendar's crossing delays are shortened by the same one edge (KC-1, L-1), so every compiled slot, the CDC
// read/write slots, the PHY frame and rx_valid keep their exact cycles (tb_coll_static_face: latency L).
module qfd_coll_static_face #(
 parameter integer FW=546, PHY=339, L=376, R=0, PEER_R=R, KC=4, KW=2,
 parameter integer PW=FW+51, TOK_REG=0, SAFE=0
)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire [4:0] codec_ck,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[FW-1:0]tx_data,
 output wire rx_valid,output wire[FW-1:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[PW-1:0]phy_rx,
 output wire phy_tx_valid,output wire[PW-1:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 wire tx_slot_i,peer_slot_i,tx_valid_i;wire[FW-1:0]tx_data_i;wire[3:0]cdc_fault_i;
 if(TOK_REG)begin:g_tok_reg
  reg ts_q,tv_q,ps_q;reg[FW-1:0]td_q;reg[3:0]cf_q;
  always @(posedge cal_ck)begin ts_q<=tx_slot;tv_q<=tx_valid;td_q<=tx_data;ps_q<=peer_slot;end
  always @(posedge cal_ck)cf_q<=cdc_fault_i;
  assign {tx_slot_i,tx_valid_i,tx_data_i,peer_slot_i}={ts_q,tv_q,td_q,ps_q};assign cdc_fault=cf_q;
 end else begin:g_tok_direct
  assign {tx_slot_i,tx_valid_i,tx_data_i,peer_slot_i}={tx_slot,tx_valid,tx_data,peer_slot};assign cdc_fault=cdc_fault_i;
 end
 initial if(TOK_REG && KC<2)$error("qfd_coll_static_face TOK_REG needs KC>=2");
 wire rs_c,rs_l;
 wire[2:0]rs_core;wire[3:0]rs_link;
 if(SAFE)begin:g_safe_reset
  // Kept local copies release at the original two-edge depth, not one
  // common 400-load reset output followed by extra startup cycles.
  ot_qwen_slot_reset_copies #(.COPIES(3))u_core(.clk(cal_ck),.rst_n(rst_n),.released(rs_core));
  ot_qwen_slot_reset_copies #(.COPIES(4))u_link(.clk(cal_lck),.rst_n(rst_n),.released(rs_link));
 end else begin:g_original_reset
  ot_reset_sync u_rc(.clk(cal_ck),.async_rst_n(rst_n),.sync_rst_n(rs_c));
  ot_reset_sync u_rl(.clk(cal_lck),.async_rst_n(rst_n),.sync_rst_n(rs_l));
  assign rs_core={3{rs_c}};assign rs_link={4{rs_l}};
 end
 reg[1:0] ec;reg epoch_begin;
 always @(posedge cal_lck or negedge rs_link[2])
 if(!rs_link[2])begin ec<=0;epoch_begin<=0;end else begin
 if(ec!=3)ec<=ec+1'b1;epoch_begin<=(ec==1);end
 wire tws,twsver,trs,trsver,wr_v,rd_v,rxe,rws,rwv,rrs,rrv;
 wire[5:0]twa,tra,wr_slot,rd_slot,rx_slot,rwa,rra;
 ot_coll_lcal_tx #(.KC(KC-TOK_REG),.KW(KW),.SAFE_RING(SAFE),.LAND_CORE(SAFE)) u_txcal(
 .clk(cal_ck),.lck(cal_lck),.rs_c(rs_core[0]),.rs_l(rs_link[0]),.slot(tx_slot_i),
 .w_slot(tws),.w_addr(twa),.w_version(twsver),.r_slot(trs),.r_addr(tra),.r_version(trsver),
 .wr_v(wr_v),.wr_slot(wr_slot),.rd_v(rd_v),.rd_slot(rd_slot));
 ot_coll_lcal_rx #(.KC(KC-TOK_REG),.KW(KW),.PHY(PHY),.L(L-TOK_REG),.R(R),.PEER_R(PEER_R),.SAFE_RING(SAFE),.LAND_CORE(SAFE))u_rxcal(
 .clk(cal_ck),.lck(cal_lck),.rs_c(rs_core[1]),.rs_l(rs_link[1]),.exp(peer_slot_i),
 .rx_expect_v(rxe),.rx_expect_slot(rx_slot),.w_slot(rws),.w_addr(rwa),.w_version(rwv),
 .r_slot(rrs),.r_addr(rra),.r_version(rrv));
 // Expected PHY ownership comes only from compiled calendar reads, never
 // from observed producer/codec validity. Matches actual codec TX3 boundary.
 if(SAFE)begin:g_safe_phy_slots
  ot_coll_dly1 #(.N(4),.SAFE_RING(1))u_slots(.clk(cal_lck),.rs_n(rs_link[3]),.d(rd_v),.q(phy_tx_slot));
 end else begin:g_original_phy_slots
  reg[3:0]phy_slots;
  always @(posedge cal_lck or negedge rs_link[3])
  if(!rs_link[3])phy_slots<=0;else if(epoch_begin)phy_slots<=0;else phy_slots<={phy_slots[2:0],rd_v};
  assign phy_tx_slot=phy_slots[3];
 end
 assign phy_rx_slot=rxe;
 wire tx_observed,codec_valid;wire[FW-1:0]tx_word,codec_data;
 wire[545:0]tx_full,rx_full;
 assign tx_word=tx_full[FW-1:0];assign rx_data=rx_full[FW-1:0];
 // Source-identical storage to qfd_io_xfifo_static: R514 pads its high32
 // storage bits, retaining the same546-bit physical CDC master and latency.
 qfd_static_ch546 u_tx(.wck(tx_wck),.rck(tx_rck),.rst_n(rst_n),
 .w_slot(tws),.w_addr(twa),.w_version(twsver),.i_valid(tx_valid_i),.i_data({{(546-FW){1'b0}},tx_data_i}),
 .r_slot(trs),.r_addr(tra),.r_version(trsver),.o_valid(tx_observed),.o_data(tx_full),.w_fault(cdc_fault_i[0]),.r_fault(cdc_fault_i[1]));
 qfd_static_ch546 u_rx(.wck(rx_wck),.rck(rx_rck),.rst_n(rst_n),
 .w_slot(rws),.w_addr(rwa),.w_version(rwv),.i_valid(codec_valid),.i_data({{(546-FW){1'b0}},codec_data}),
 .r_slot(rrs),.r_addr(rra),.r_version(rrv),.o_valid(rx_valid),.o_data(rx_full),.w_fault(cdc_fault_i[2]),.r_fault(cdc_fault_i[3]));
 initial if(FW!=546 && FW!=514)$error("collectiveface546/514only");
 ot_qwen_static_slot_link #(.FW(FW),.CW(32),.SAFE(SAFE))u_codec(.ck(codec_ck),.rst_n(rst_n),
 .epoch_begin(epoch_begin),.epoch(8'h01),.wr_v(wr_v),.wr_observed_v(tx_observed),.wr_slot(wr_slot),.wr_flit(tx_word),
 .rd_v(rd_v),.rd_slot(rd_slot),.rx_expect_v(rxe),.rx_expect_slot(rx_slot),
 .p_tx_up(phy_up),.p_tx_v(phy_tx_valid),.p_tx_flit(phy_tx),.p_rx_v(phy_rx_valid),.p_rx_flit(phy_rx),
 .rx_v(codec_valid),.rx_flit(codec_data),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
