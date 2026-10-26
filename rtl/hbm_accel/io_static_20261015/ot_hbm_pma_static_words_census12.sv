`timescale 1ns/1fs
`default_nettype none
// Isolated actual TX+RX digital gearbox scope. No FEC/outer CDC/endpoint inference.
module ot_hbm_pma_static_words_census12(
 input wire fec_tx_clk,phy_tx_clk,phy_rx_clk,fec_rx_clk,
 input wire tx_bank0,tx_bank1,tx_bank2,tx_bank3,
 input wire rx_bank0,rx_bank1,rx_bank2,rx_bank3,
 input wire rst_n,ser_write_start,ser_read_start,des_write_start,des_read_start,
 input wire ser_observed_v,des_observed_v,
 input wire[543:0]coded_tx,input wire[511:0]pma_rx,
 output wire[511:0]pma_tx,output wire[543:0]coded_rx,
 output wire ser_q_v,des_q_v,ser_w_fault,ser_r_fault,des_w_fault,des_r_fault);
 ot_hbm_pma_block_gearbox_static_words #(.WI(544),.NI(16),.WO(512),.NO(17),.MUT(0)) ser(
 .wclk(fec_tx_clk),.rclk(phy_tx_clk),.rst_n(rst_n),.w_start(ser_write_start),.r_start(ser_read_start),
 .d(coded_tx),.observed_v(ser_observed_v),.q(pma_tx),.q_v(ser_q_v),.w_fault(ser_w_fault),.r_fault(ser_r_fault),
 .wclk_bank({tx_bank3,tx_bank2,tx_bank1,tx_bank0}));
 ot_hbm_pma_block_gearbox_static_words #(.WI(512),.NI(17),.WO(544),.NO(16),.MUT(0)) deser(
 .wclk(phy_rx_clk),.rclk(fec_rx_clk),.rst_n(rst_n),.w_start(des_write_start),.r_start(des_read_start),
 .d(pma_rx),.observed_v(des_observed_v),.q(coded_rx),.q_v(des_q_v),.w_fault(des_w_fault),.r_fault(des_r_fault),
 .wclk_bank({rx_bank3,rx_bank2,rx_bank1,rx_bank0}));
endmodule
`default_nettype wire
