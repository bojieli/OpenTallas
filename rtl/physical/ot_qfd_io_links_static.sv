`timescale 1ns/1ps
// Native static normal board endpoint. Five independently delivered clock
// entries (control + four real SRAM banks), no credit/ready ports. The PHY
// data clock carries the codec's fixed TX3/RX1 protocol. Compiler commands
// reserve every wr/rd/rx_expect edge; exceptions abort the epoch explicitly.
module qfd_io_serdes_static #(parameter integer MUT=0) (
 input wire ck,ckb0,ckb1,ckb2,ckb3,rst_n,epoch_begin,
 input wire [7:0] epoch,
 input wire wr_v,wr_observed_v,input wire [5:0] wr_slot,input wire [545:0] wr_word,
 input wire rd_v,input wire [5:0] rd_slot,
 input wire rx_expect_v,input wire [5:0] rx_expect_slot,
 input wire phy_up,output wire phy_tx_v,output wire [596:0] phy_tx,
 input wire phy_rx_v,input wire [596:0] phy_rx,
 output wire rx_v,output wire [545:0] rx_word,
 output wire epoch_abort,output wire [7:0] fault_cause);
 ot_qwen_static_slot_link #(.FW(546),.CW(32),.MUT(MUT)) u_codec (
 .ck({ckb3,ckb2,ckb1,ckb0,ck}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
 .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_slot(wr_slot),.wr_flit(wr_word),.rd_v(rd_v),.rd_slot(rd_slot),
 .rx_expect_v(rx_expect_v),.rx_expect_slot(rx_expect_slot),.p_tx_up(phy_up),
 .p_tx_v(phy_tx_v),.p_tx_flit(phy_tx),.p_rx_v(phy_rx_v),.p_rx_flit(phy_rx),
 .rx_v(rx_v),.rx_flit(rx_word),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
// Independent logical P/R channels retain their exact 546/514-bit records.
// Every PHY subchannel has explicit scheduled ports; their combined use must
// be reserved against the licensed PHY capacity in the actual compiler table.
// No implicit runtime arbitration or invented extra bandwidth is hidden here.
module qfd_io_ucie_static #(parameter integer MUT=0) (
input wire rst_n,epoch_begin,
input wire [7:0] epoch,
input wire p_ck,p_ckb0,p_ckb1,p_ckb2,p_ckb3,
input wire p_wr_v,p_wr_observed_v,p_rd_v,p_rx_expect_v,p_phy_up,p_phy_rx_v,
input wire [5:0] p_wr_slot,p_rd_slot,p_rx_expect_slot,
input wire [545:0] p_wr_word,
output wire p_phy_tx_v,p_rx_v,p_epoch_abort,
output wire [596:0] p_phy_tx,
input wire [596:0] p_phy_rx,
output wire [545:0] p_rx_word,
output wire [7:0] p_fault_cause,
input wire r_ck,r_ckb0,r_ckb1,r_ckb2,r_ckb3,
input wire r_wr_v,r_wr_observed_v,r_rd_v,r_rx_expect_v,r_phy_up,r_phy_rx_v,
input wire [5:0] r_wr_slot,r_rd_slot,r_rx_expect_slot,
input wire [513:0] r_wr_word,
output wire r_phy_tx_v,r_rx_v,r_epoch_abort,
output wire [564:0] r_phy_tx,
input wire [564:0] r_phy_rx,
output wire [513:0] r_rx_word,
output wire [7:0] r_fault_cause
);
 ot_qwen_static_slot_link #(.FW(546),.CW(32),.MUT(MUT)) u_p (.ck({p_ckb3,p_ckb2,p_ckb1,p_ckb0,p_ck}),
.rst_n(rst_n),
.epoch_begin(epoch_begin),
.epoch(epoch),
.wr_v(p_wr_v),
.wr_observed_v(p_wr_observed_v),
.wr_slot(p_wr_slot),
.wr_flit(p_wr_word),
.rd_v(p_rd_v),
.rd_slot(p_rd_slot),
.rx_expect_v(p_rx_expect_v),
.rx_expect_slot(p_rx_expect_slot),
.p_tx_up(p_phy_up),
.p_tx_v(p_phy_tx_v),
.p_tx_flit(p_phy_tx),
.p_rx_v(p_phy_rx_v),
.p_rx_flit(p_phy_rx),
.rx_v(p_rx_v),
.rx_flit(p_rx_word),
.epoch_abort(p_epoch_abort),
.fault_cause(p_fault_cause));
 ot_qwen_static_slot_link #(.FW(514),.CW(32),.MUT(0)) u_r (.ck({r_ckb3,r_ckb2,r_ckb1,r_ckb0,r_ck}),
.rst_n(rst_n),
.epoch_begin(epoch_begin),
.epoch(epoch),
.wr_v(r_wr_v),
.wr_observed_v(r_wr_observed_v),
.wr_slot(r_wr_slot),
.wr_flit(r_wr_word),
.rd_v(r_rd_v),
.rd_slot(r_rd_slot),
.rx_expect_v(r_rx_expect_v),
.rx_expect_slot(r_rx_expect_slot),
.p_tx_up(r_phy_up),
.p_tx_v(r_phy_tx_v),
.p_tx_flit(r_phy_tx),
.p_rx_v(r_phy_rx_v),
.p_rx_flit(r_phy_rx),
.rx_v(r_rx_v),
.rx_flit(r_rx_word),
.epoch_abort(r_epoch_abort),
.fault_cause(r_fault_cause));
endmodule
