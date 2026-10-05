`timescale 1ns/1ps
// Interface-only stand-in for bounded service-wrapper lint. The real engine
// is source-pinned separately and this file must never enter an RTL build.
`ifdef V41X_ATTN_SERVICE_LINT_STUB
module ot_hdc_v41x_attn #(
    parameter integer H=16,D=512,TD=64,NL=4,TROWS=640,
    parameter integer SC_CRED=64,PV_CRED=64,
    parameter bit SRAM_MACRO=0
) (
    input wire clk,rst_n,job_v,
    input wire [15:0] job_t,
    output wire job_ready,
    input wire q_v,
    input wire [D*16-1:0] q_w,
    output wire q_ready,
    input wire kv_v,
    input wire [NL-1:0] kv_m,
    input wire [NL*(D/32)*265-1:0] kv_w,
    output wire kv_ready,
    output wire sc_v,
    output wire [15:0] sc_row,
    output wire [NL-1:0] sc_m,
    output wire [NL*H*32-1:0] sc_y,
    output wire [NL*H-1:0] sc_f,
    input wire sc_cr,p_v,
    input wire [TD*16-1:0] p_w,
    output wire p_ready,pv_v,
    output wire [7:0] pv_c,
    output wire [NL*(D/TD)*H*32-1:0] pv_y,
    output wire [NL*(D/TD)*H-1:0] pv_f,
    input wire pv_cr,
    output wire qk_iss,pv_iss
);
    assign job_ready=1; assign q_ready=1; assign kv_ready=1;
    assign sc_v=0; assign sc_row=0; assign sc_m=0; assign sc_y=0;
    assign sc_f=0; assign p_ready=1; assign pv_v=0; assign pv_c=0;
    assign pv_y=0; assign pv_f=0; assign qk_iss=0; assign pv_iss=0;
endmodule
`endif
