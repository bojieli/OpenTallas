`timescale 1ns/1ps
// TOK-QK/C 10-24 MUTANT (ii) of rtl/physical/ot_fdi_phy_cdc.sv: the FIFOs replaced by direct wiring = the old crossing
// (each side samples the other clock's flops directly, as kv42 bound the PHY lanes into the clk_phy adapter).  Must FAIL.
module ot_fdi_phy_cdc #(parameter integer W = 522, parameter integer DEPTH = 8) (
    input  wire clk, input wire link_rst_n, input wire c_tx_v, input wire [W-1:0] c_tx_d,
    output reg c_rx_v, output reg [W-1:0] c_rx_d, output wire c_tx_up,
    input  wire clk_phy, output wire p_rst_n, output reg p_tx_v, output reg [W-1:0] p_tx_d,
    input  wire p_rx_v, input wire [W-1:0] p_rx_d, input wire p_tx_up);
    assign p_rst_n = link_rst_n;
    always @(posedge clk) begin c_rx_v <= link_rst_n & p_rx_v; c_rx_d <= p_rx_d; end
    always @(posedge clk_phy) begin p_tx_v <= link_rst_n & c_tx_v; p_tx_d <= c_tx_d; end
    assign c_tx_up = p_tx_up;
    integer n_rx_lost = 0, n_tx_lost = 0;
endmodule
