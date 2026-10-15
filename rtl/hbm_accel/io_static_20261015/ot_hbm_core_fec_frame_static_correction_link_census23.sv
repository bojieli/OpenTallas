`timescale 1ns/1fs
`default_nettype none
// Census-only pure wires adapter: exact passed opt-in151-edge joined profile.
// All23 clocks remain independent scalar ports. Native endpoints stay caller-owned.
// No parameter overrides: production numerical binding WORDS2048/EMUT0/DMUT0.
module ot_hbm_core_fec_frame_static_correction_link_census23(

 input wire core_clk,rst_n,
 input wire fec_clk_0,fec_clk_1,fec_clk_2,fec_clk_3,fec_clk_4,fec_clk_5,fec_clk_6,fec_clk_7,fec_clk_8,fec_clk_9,fec_clk_10,fec_clk_11,fec_clk_12,fec_clk_13,fec_clk_14,fec_clk_15,
 input wire phy_clk_0,phy_clk_1,phy_clk_2,phy_clk_3,phy_clk_4,phy_clk_5,
 input wire tx_start,rx_start,tx_word_step,rx_word_step,tx_slot_v,
 input wire endpoint_tx_v,input wire[611:0]endpoint_tx_frame,
 output wire expected_tx_slot,endpoint_rx_v,output wire[611:0]endpoint_rx_frame,
 input wire ctx_start,ctx_take,ctx_last,ftx_start,ftx_take,ftx_last,
 input wire frx_start,frx_take,frx_last,crx_start,crx_take,crx_last,
 input wire capture_start,capture_take,capture_last,read_start,read_take,read_last,
 input wire ser_write_start,ser_read_start,des_write_start,des_read_start,
 output wire[511:0]pma_tx,input wire[511:0]pma_rx,
 output wire[3:0]fault_core,output wire[1:0]crossing_fault_fec,
 output wire[3:0]pma_fault,output wire[1:0]status,output wire padding_fault
);
 ot_hbm_core_fec_frame_static_correction_link #(.WORDS(2048),.EMUT(0),.DMUT(0)) u_profile(
 .core_clk(core_clk),
 .rst_n(rst_n),
 .tx_start(tx_start),
 .rx_start(rx_start),
 .tx_word_step(tx_word_step),
 .rx_word_step(rx_word_step),
 .tx_slot_v(tx_slot_v),
 .endpoint_tx_v(endpoint_tx_v),
 .endpoint_tx_frame(endpoint_tx_frame),
 .expected_tx_slot(expected_tx_slot),
 .endpoint_rx_v(endpoint_rx_v),
 .endpoint_rx_frame(endpoint_rx_frame),
 .ctx_start(ctx_start),
 .ctx_take(ctx_take),
 .ctx_last(ctx_last),
 .ftx_start(ftx_start),
 .ftx_take(ftx_take),
 .ftx_last(ftx_last),
 .frx_start(frx_start),
 .frx_take(frx_take),
 .frx_last(frx_last),
 .crx_start(crx_start),
 .crx_take(crx_take),
 .crx_last(crx_last),
 .capture_start(capture_start),
 .capture_take(capture_take),
 .capture_last(capture_last),
 .read_start(read_start),
 .read_take(read_take),
 .read_last(read_last),
 .ser_write_start(ser_write_start),
 .ser_read_start(ser_read_start),
 .des_write_start(des_write_start),
 .des_read_start(des_read_start),
 .pma_tx(pma_tx),
 .pma_rx(pma_rx),
 .fault_core(fault_core),
 .crossing_fault_fec(crossing_fault_fec),
 .pma_fault(pma_fault),
 .status(status),
 .padding_fault(padding_fault),
 .fec_clks({fec_clk_15,fec_clk_14,fec_clk_13,fec_clk_12,fec_clk_11,fec_clk_10,fec_clk_9,fec_clk_8,fec_clk_7,fec_clk_6,fec_clk_5,fec_clk_4,fec_clk_3,fec_clk_2,fec_clk_1,fec_clk_0}),
 .phy_clks({phy_clk_5,phy_clk_4,phy_clk_3,phy_clk_2,phy_clk_1,phy_clk_0})
 );
endmodule
`default_nettype wire
