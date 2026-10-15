`timescale 1ns/1fs
`default_nettype none
// Actual wires-only functional composition. Endpoints remain in the caller.
// Explicit physical root ports are preserved; numerical benches may declare
// same-family same-phase clocks, never infer physical phase from that tie.
module ot_hbm_core_fec_frame_link #(
 parameter integer WORDS=2048,EMUT=0,DMUT=0
)(
 input wire core_clk,rst_n,
 input wire [15:0] fec_clks,input wire[5:0]phy_clks,
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
 wire transport_tx_v,fec_tx_v,fec_rx_v,transport_rx_v;
 wire[486:0]transport_tx_word,fec_tx_word,fec_rx_word,transport_rx_word;
 ot_hbm_static_frame_transport_step u_tx(
 .clk(core_clk),.rst_n(rst_n),.tx_start(tx_start),.rx_start(1'b0),
 .tx_word_step(tx_word_step),.rx_word_step(1'b0),.tx_slot_v(tx_slot_v),
 .endpoint_tx_v(endpoint_tx_v),.endpoint_tx_frame(endpoint_tx_frame),.expected_tx_slot(expected_tx_slot),
 .transport_tx_v(transport_tx_v),.transport_tx_word(transport_tx_word),
 .transport_rx_v(1'b0),.transport_rx_word(487'b0),.endpoint_rx_v(),.endpoint_rx_frame(),.fault(fault_core[0]));
 ot_hbm_core_fec_word_window #(.WORDS(WORDS)) u_crossing(
 .core_clk(core_clk),.fec_clk(fec_clks[0]),.rst_n(rst_n),
 .ctx_start(ctx_start),.ctx_take(ctx_take),.ctx_last(ctx_last),.core_tx_v(transport_tx_v),.core_tx_word(transport_tx_word),
 .ftx_start(ftx_start),.ftx_take(ftx_take),.ftx_last(ftx_last),.fec_tx_v(fec_tx_v),.fec_tx_word(fec_tx_word),
 .frx_start(frx_start),.frx_take(frx_take),.frx_last(frx_last),.fec_rx_v(fec_rx_v),.fec_rx_word(fec_rx_word),
 .crx_start(crx_start),.crx_take(crx_take),.crx_last(crx_last),.core_rx_v(transport_rx_v),.core_rx_word(transport_rx_word),
 .tx_core_fault(fault_core[2]),.tx_fec_fault(crossing_fault_fec[0]),.rx_fec_fault(crossing_fault_fec[1]),.rx_core_fault(fault_core[3]));
 hfd_serdes487_phy512_static_window #(.EMUT(EMUT),.DMUT(DMUT),.WINDOW_WORDS(WORDS)) u_phy(
 .clk(fec_clks[0]),.clk_collect(fec_clks[1]),.clk_encode(fec_clks[2]),.clk_codeword(fec_clks[3]),
 .rclk_capture(fec_clks[4]),.rclk_syndrome(fec_clks[5]),.rclk_bm0(fec_clks[6]),.rclk_bm1(fec_clks[7]),
 .rclk_bm2(fec_clks[8]),.rclk_bm3(fec_clks[9]),.rclk_chien(fec_clks[10]),.rclk_emit(fec_clks[11]),
 .phy_tclk(phy_clks[0]),.phy_rclk(phy_clks[1]),.tx_bank_clks(fec_clks[15:12]),.rx_bank_clks(phy_clks[5:2]),
 .rst_n(rst_n),.tx(fec_tx_word),
 .capture_start(capture_start),.capture_take(capture_take),.capture_last(capture_last),
 .read_start(read_start),.read_take(read_take),.read_last(read_last),
 .ser_write_start(ser_write_start),.ser_read_start(ser_read_start),.des_write_start(des_write_start),.des_read_start(des_read_start),
 .rx(fec_rx_word),.rx_v(fec_rx_v),.st(status),.padding_fault(padding_fault),.pma_tx(pma_tx),.pma_rx(pma_rx),
 .tx_write_fault(pma_fault[0]),.tx_read_fault(pma_fault[1]),.rx_write_fault(pma_fault[2]),.rx_read_fault(pma_fault[3]));
 ot_hbm_static_frame_transport_step u_rx(
 .clk(core_clk),.rst_n(rst_n),.tx_start(1'b0),.rx_start(rx_start),
 .tx_word_step(1'b0),.rx_word_step(rx_word_step),.tx_slot_v(1'b0),.endpoint_tx_v(1'b0),.endpoint_tx_frame(612'b0),
 .expected_tx_slot(),.transport_tx_v(),.transport_tx_word(),.transport_rx_v(transport_rx_v),.transport_rx_word(transport_rx_word),
 .endpoint_rx_v(endpoint_rx_v),.endpoint_rx_frame(endpoint_rx_frame),.fault(fault_core[1]));
endmodule
`default_nettype wire
