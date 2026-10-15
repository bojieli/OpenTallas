`timescale 1ns/1fs
`default_nettype none
// Two actual finite 16-entry registered CDCs, core->FEC and FEC->core.
// All reservations external/compiler fixed. Gray observations only fault.
// Fault outputs stay in their own clock domains; no unsafe aggregate control.
module ot_hbm_core_fec_word_window #(parameter integer WORDS=2048,TX_MUT=0,RX_MUT=0)(
 input wire core_clk,fec_clk,rst_n,
 input wire ctx_start,ctx_take,ctx_last,core_tx_v,input wire[486:0]core_tx_word,
 input wire ftx_start,ftx_take,ftx_last,output wire fec_tx_v,output wire[486:0]fec_tx_word,
 input wire frx_start,frx_take,frx_last,fec_rx_v,input wire[486:0]fec_rx_word,
 input wire crx_start,crx_take,crx_last,output wire core_rx_v,output wire[486:0]core_rx_word,
 output wire tx_core_fault,tx_fec_fault,rx_fec_fault,rx_core_fault
);
 ot_hbm_static_word_cdc #(.W(487),.AW(4),.WORDS(WORDS),.MUT(TX_MUT)) u_tx(
 .wclk(core_clk),.rclk(fec_clk),.rst_n(rst_n),
 .w_start(ctx_start),.w_take(ctx_take),.w_last(ctx_last),.w_observed_v(core_tx_v),.w_data(core_tx_word),
 .r_start(ftx_start),.r_take(ftx_take),.r_last(ftx_last),.r_v(fec_tx_v),.r_data(fec_tx_word),.w_fault(tx_core_fault),.r_fault(tx_fec_fault));
 ot_hbm_static_word_cdc #(.W(487),.AW(4),.WORDS(WORDS),.MUT(RX_MUT)) u_rx(
 .wclk(fec_clk),.rclk(core_clk),.rst_n(rst_n),
 .w_start(frx_start),.w_take(frx_take),.w_last(frx_last),.w_observed_v(fec_rx_v),.w_data(fec_rx_word),
 .r_start(crx_start),.r_take(crx_take),.r_last(crx_last),.r_v(core_rx_v),.r_data(core_rx_word),.w_fault(rx_fec_fault),.r_fault(rx_core_fault));
endmodule
`default_nettype wire
