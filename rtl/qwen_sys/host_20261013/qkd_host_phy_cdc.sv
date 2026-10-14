`timescale 1ns/1ps
// Wires-only normalized DATA face of actual W1024/FDI1043 adapter.
// These TWO dedicated W546/PIPE2 CDC leaves are additional host instances;
// they do not consume any of the ten collective CDC instances.
// ck_pad and rx_wck are same-frequency/phase family; likewise tx_rck and
// adapter TX clock. Core RX/TX entry clocks may share a phase family.
module qkd_host_phy_cdc #(parameter integer MUT=0)(
 input wire ck_pad,rx_wck,rx_rck,tx_wck,tx_rck,rst_n,
 input wire phy_rx_v,input wire[1023:0]phy_rx_d,output wire phy_rx_cr,
 output wire phy_tx_v,output wire[1023:0]phy_tx_d,input wire phy_tx_cr,
 output wire core_rx_v,output wire[527:0]core_rx_d,input wire core_rx_cr,
 input wire core_tx_v,input wire[527:0]core_tx_d,output wire core_tx_cr,
 output wire[4:0]faults
);
 wire pad_v,pad_cr;wire[545:0]pad_d,rx_d,tx_d;
 qkd_host_rx_pad u_pad(.clk(ck_pad),.rst_n(rst_n),.in_v(phy_rx_v),.in_d(phy_rx_d),.in_cr(phy_rx_cr),
 .out_v(pad_v),.out_d(pad_d),.out_cr(pad_cr),.fault(faults[0]));
 ot_qwen_die_cdc_ch #(.W(546),.PIPE(2))u_rx(.wclk(rx_wck),.wrst_n(rst_n),.i_v(pad_v),.i_d(pad_d),.i_cr(pad_cr),.w_fault(faults[1]),
 .rclk(rx_rck),.rrst_n(rst_n),.o_v(core_rx_v),.o_d(rx_d),.o_cr(core_rx_cr),.r_fault(faults[2]));
 assign core_rx_d=rx_d[527:0]; // upper18 were generated constant-zero by u_pad
 ot_qwen_die_cdc_ch #(.W(546),.PIPE(2))u_tx(.wclk(tx_wck),.wrst_n(rst_n),.i_v(core_tx_v),
 .i_d({18'd0,core_tx_d}^{{545{1'b0}},(MUT==1)}),.i_cr(core_tx_cr),.w_fault(faults[3]),
 .rclk(tx_rck),.rrst_n(rst_n),.o_v(phy_tx_v),.o_d(tx_d),.o_cr(phy_tx_cr),.r_fault(faults[4]));
 assign phy_tx_d={478'd0,tx_d}; // W546 word is losslessly extended to DATA1024
endmodule
