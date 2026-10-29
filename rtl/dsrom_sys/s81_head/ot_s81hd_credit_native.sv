`timescale 1ns/1ps
`default_nettype none
// Two existing credit endpoints in the exact HEAD CORE_CRED=12 profile.
// The parent keeps its current g_lo2 stage and up gating; this cut adds no cycles.
module ot_s81hd_credit_native (
    input wire clk,
    input wire rst_in_n,
    input wire [34:0] head_rst_n,
    input wire rst_out_n,
    input wire lo_v,
    input wire [552:0] lo_d,
    output wire lo_r,
    output wire ep_in_v,
    input wire ep_in_r,
    output wire [552:0] ep_in_d,
    input wire ep_out_v,
    output wire [2:0] ep_out_r,
    input wire [552:0] ep_out_d,
    output wire li_v,
    output wire [552:0] li_d,
    input wire li_r,
    output wire fault
);
    ot_link_credit_rx_b64 #(
        .W(553), .DEPTH(12), .WFREE(1), .LOCAL_HIT(1), .LOCAL_POP(1)
    ) u_ski (
        .clk(clk), .rst_n(rst_in_n), .head_rst_n(head_rst_n),
        .l_valid(lo_v), .l_data(lo_d), .l_credit(lo_r),
        .o_valid(ep_in_v), .o_ready(ep_in_r), .o_data(ep_in_d), .fault(fault)
    );
    ot_link_credit_tx_rc #(.W(553), .CRED(12), .NR(3)) u_sko (
        .clk(clk), .rst_n(rst_out_n), .i_valid(ep_out_v), .i_ready(ep_out_r),
        .i_data(ep_out_d), .l_valid(li_v), .l_data(li_d), .l_credit(li_r)
    );
endmodule
`default_nettype wire
