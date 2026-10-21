`timescale 1ns/1ps
// Same source root/group/local three-edge reset tree + one enable edge as the
// original ot_s81sl_lep rr[2] -> rxv_r producer. One copy beside each lane RX[0].
module ot_s81hd_lane_rx_enable_local(input wire ck,rst_n,output reg enable);
    wire [0:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(1)) u_rr(.clk(ck),.rst_n_in(rst_n),.rst_n(rr));
`ifdef OT_HEAD_RXLOCAL_MUT_EARLY
    always @(posedge ck or negedge rst_n) if(!rst_n) enable<=0;else enable<=1;
`else
    always @(posedge ck or negedge rr[0]) if(!rr[0]) enable<=0;else enable<=1;
`endif
endmodule
