`timescale 1ns/1ps
// Four HBM3E stacks with 32 pseudo-channels each. Every traffic class shares
// the same physical request lane and finite outstanding credits at each PC.
// Flattening is PC-major: [pc*NC + client]. Address low seven bits select the
// physical PC (stack=pc/32, local channel=pc%32). This module arbitrates and
// routes; controller timing, FP8 KV packing and macro placement live outside.
module ot_hdc_qwen_hbm_service #(
    parameter integer STACKS=4,
    parameter integer PCS_PER_STACK=32,
    parameter integer NC=6,
    parameter integer AW=32,
    parameter integer CTAGW=17,
    parameter integer MAX_OUT=16,
    parameter integer NPC=STACKS*PCS_PER_STACK,
    parameter integer PTAGW=$clog2(NC)+CTAGW
) (
    input wire clk, rst_n,
    input wire [NPC*NC-1:0] c_req_v,
    output wire [NPC*NC-1:0] c_req_rdy,
    input wire [NPC*NC-1:0] c_req_we,
    input wire [NPC*NC*AW-1:0] c_req_addr,
    input wire [NPC*NC*CTAGW-1:0] c_req_tag,
    input wire [NPC*NC*256-1:0] c_req_data,
    output wire [NPC*NC-1:0] c_rsp_v,
    input wire [NPC*NC-1:0] c_rsp_rdy,
    output wire [NPC*NC*CTAGW-1:0] c_rsp_tag,
    output wire [NPC*NC*256-1:0] c_rsp_data,
    output wire [NPC*NC-1:0] c_wr_done_v,
    output wire [NPC*NC*CTAGW-1:0] c_wr_done_tag,
    output wire [NPC-1:0] p_req_v,
    input wire [NPC-1:0] p_req_rdy,
    output wire [NPC-1:0] p_req_we,
    output wire [NPC*AW-1:0] p_req_addr,
    output wire [NPC*PTAGW-1:0] p_req_tag,
    output wire [NPC*256-1:0] p_req_data,
    input wire [NPC-1:0] p_rsp_v,
    output wire [NPC-1:0] p_rsp_rdy,
    input wire [NPC*PTAGW-1:0] p_rsp_tag,
    input wire [NPC*256-1:0] p_rsp_data,
    input wire [NPC-1:0] p_wr_done_v,
    input wire [NPC*PTAGW-1:0] p_wr_done_tag,
    output wire [NPC-1:0] pc_fault
);
    initial if (STACKS!=4 || PCS_PER_STACK!=32 || NPC!=128 || AW<32)
        $fatal(1,"Qwen O4 shared HBM service requires four 32-PC stacks");
    for (genvar p=0;p<NPC;p=p+1) begin : g_pc
        wire local_fault;
        reg address_fault;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) address_fault<=0;
            else if (p_req_v[p] && p_req_rdy[p] &&
                     p_req_addr[p*AW +: 7] != 7'(p)) address_fault<=1;
        end
        assign pc_fault[p]=local_fault|address_fault;
        ot_hdc_qwen_pc_service #(.NC(NC),.AW(AW),.CTAGW(CTAGW),
            .MAX_OUT(MAX_OUT),.PTAGW(PTAGW)) u_pc (
            .clk(clk),.rst_n(rst_n),
            .c_req_v(c_req_v[p*NC +: NC]),.c_req_rdy(c_req_rdy[p*NC +: NC]),
            .c_req_we(c_req_we[p*NC +: NC]),
            .c_req_addr(c_req_addr[p*NC*AW +: NC*AW]),
            .c_req_tag(c_req_tag[p*NC*CTAGW +: NC*CTAGW]),
            .c_req_data(c_req_data[p*NC*256 +: NC*256]),
            .c_rsp_v(c_rsp_v[p*NC +: NC]),.c_rsp_rdy(c_rsp_rdy[p*NC +: NC]),
            .c_rsp_tag(c_rsp_tag[p*NC*CTAGW +: NC*CTAGW]),
            .c_rsp_data(c_rsp_data[p*NC*256 +: NC*256]),
            .c_wr_done_v(c_wr_done_v[p*NC +: NC]),
            .c_wr_done_tag(c_wr_done_tag[p*NC*CTAGW +: NC*CTAGW]),
            .p_req_v(p_req_v[p]),.p_req_rdy(p_req_rdy[p]),
            .p_req_we(p_req_we[p]),.p_req_addr(p_req_addr[p*AW +: AW]),
            .p_req_tag(p_req_tag[p*PTAGW +: PTAGW]),
            .p_req_data(p_req_data[p*256 +: 256]),
            .p_rsp_v(p_rsp_v[p]),.p_rsp_rdy(p_rsp_rdy[p]),
            .p_rsp_tag(p_rsp_tag[p*PTAGW +: PTAGW]),
            .p_rsp_data(p_rsp_data[p*256 +: 256]),
            .p_wr_done_v(p_wr_done_v[p]),
            .p_wr_done_tag(p_wr_done_tag[p*PTAGW +: PTAGW]),
            .fault(local_fault));
    end
endmodule
