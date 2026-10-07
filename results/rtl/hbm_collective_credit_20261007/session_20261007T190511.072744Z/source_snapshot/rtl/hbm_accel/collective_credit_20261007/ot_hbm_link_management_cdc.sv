// Actual protected management crossing. Both reset inputs are derived from the
// SAME always-on management POR, independently synchronized at each clock.
// Neither reset may be driven by a data-session reset or operation arm.
module ot_hbm_link_management_cdc #(parameter integer ENABLE=0)(
 input wire tx_clk,tx_rst_n,tx_valid,output wire tx_ready,input wire[71:0]tx_word,
 input wire rx_clk,rx_rst_n,output wire rx_valid,input wire rx_ready,output wire[71:0]rx_word,
 output wire tx_empty,rx_empty,fault
);
 ot_hbm_collective_protected_cdc #(.ENABLE(ENABLE),.W(72),.AW(3)) fifo(
 .wclk(tx_clk),.wrst_n(tx_rst_n),.in_v(tx_valid),.in_r(tx_ready),.in_d(tx_word),
 .rclk(rx_clk),.rrst_n(rx_rst_n),.out_v(rx_valid),.out_r(rx_ready),.out_d(rx_word),
 .wempty(tx_empty),.rempty(rx_empty),.fault(fault));
endmodule
