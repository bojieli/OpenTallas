`timescale 1ns/1ps
// Native successor: one hclk capture register on h_hand; hp2: h_wcon lands on ONE pin flop that also drives the
// column-group completion enables (cycle-identical). Other interfaces unchanged.
module qkd_cdc_wleaf_hpin (
    input  wire         clk,
    input  wire         c_arst_n,
    output wire         l_v,
    output wire [16:0]  l_sec,
    output wire [7:0]   l_row,
    output wire [255:0] l_data,
    input  wire         l_pop,
    input  wire         w_v,
    input  wire [23:0]  w_sec,
    input  wire [255:0] w_data,
    input  wire [8:0]   w_tag,
    output wire         w_room,
    output wire         wd_v,
    output wire [8:0]   wd_tag,
    output wire         c_fault,
    input  wire         hclk,
    input  wire         h_arst_n,
    input  wire         h_lv,
    input  wire [16:0]  h_lsec,
    input  wire [7:0]   h_lrow,
    input  wire [255:0] h_ldata,
    output wire [2:0]   h_cred,
    output wire         h_wv,
    output wire [23:0]  h_wsec,
    input  wire         h_hand,
    input  wire         h_wcon,
    output wire         h_cv,
    output wire [23:0]  h_csec,
    output wire [255:0] h_cdata,
    output wire [8:0]   h_ctag,
    input  wire         h_av,
    input  wire [8:0]   h_atag,
    output wire         h_fault
);
    qkd_cdc_wleaf #(.HANDPIPE(1), .WCPIN(1)) u (.*);
endmodule
