// OPT-IN static correction profile; frozen151 baseline preserved.
`timescale 1ns/1fs
`default_nettype none
// Candidate full digital composition at the actual512-pin PHY boundary.
// FEC family and PHY family have16:17 frequency ratio, NOT equal rates.
// All starts are external compiled epochs; no start derives from availability.
module hfd_serdes487_phy512_static_correction_window #(
 parameter integer EMUT=0,DMUT=0,WINDOW_WORDS=2048,CDC_AW=4
)(input wire clk,clk_collect,clk_encode,clk_codeword,
 input wire rclk_capture,rclk_syndrome,rclk_bm0,rclk_bm1,rclk_bm2,rclk_bm3,rclk_chien,rclk_emit,
 input wire phy_tclk,phy_rclk,input wire [3:0] tx_bank_clks,rx_bank_clks,
 input wire rst_n,input wire [486:0] tx,
 input wire capture_start,capture_take,capture_last,read_start,read_take,read_last,
 input wire ser_write_start,ser_read_start,des_write_start,des_read_start,
 output wire [486:0] rx,output wire rx_v,output wire [1:0] st,output wire padding_fault,
 output wire [511:0] pma_tx,input wire [511:0] pma_rx,
 output wire tx_write_fault,tx_read_fault,rx_write_fault,rx_read_fault);
 wire [543:0] coded_tx,coded_rx;wire ignored_tck,pv,rv;
 hfd_serdes487_static_correction_window #(.EMUT(EMUT),.DMUT(DMUT),.WINDOW_WORDS(WINDOW_WORDS),.CDC_AW(CDC_AW)) u_fec(
 .clk(clk),.clk_collect(clk_collect),.clk_encode(clk_encode),.clk_codeword(clk_codeword),
 .rclk_syndrome(rclk_syndrome),.rclk_bm0(rclk_bm0),.rclk_bm1(rclk_bm1),.rclk_bm2(rclk_bm2),.rclk_bm3(rclk_bm3),.rclk_chien(rclk_chien),.rclk_emit(rclk_emit),
 .rst_n(rst_n),.tx(tx),.capture_start(capture_start),.capture_take(capture_take),.capture_last(capture_last),
 .read_start(read_start),.read_take(read_take),.read_last(read_last),.rx(rx),.rx_v(rx_v),.st(st),.padding_fault(padding_fault),
 .pma_tx(coded_tx),.pma_tck(ignored_tck),.pma_rx(coded_rx),.pma_rck(rclk_capture));
 ot_hbm_pma_block_gearbox ser(.wclk(clk),.rclk(phy_tclk),.rst_n(rst_n),.w_start(ser_write_start),.r_start(ser_read_start),
 .d(coded_tx),.observed_v(1'b1),.q(pma_tx),.q_v(pv),.w_fault(tx_write_fault),.r_fault(tx_read_fault),.wclk_bank(tx_bank_clks));
 // External pins have no data-valid port: des_write_start is the compiled
 // boundary epoch. Fault detection cannot invent a PHY valid signal.
 ot_hbm_pma_block_gearbox #(.WI(512),.NI(17),.WO(544),.NO(16)) deser(
 .wclk(phy_rclk),.rclk(rclk_capture),.rst_n(rst_n),.w_start(des_write_start),.r_start(des_read_start),
 .d(pma_rx),.observed_v(1'b1),.q(coded_rx),.q_v(rv),.w_fault(rx_write_fault),.r_fault(rx_read_fault),.wclk_bank(rx_bank_clks));
endmodule
`default_nettype wire
