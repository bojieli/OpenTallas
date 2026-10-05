`timescale 1ns/1ps
// Timing wrapper (fmax closure, noc family): ot_gpu_mreq_cdc with clk_s = clk_m = clk (both sides timed at the
// 1.2 GHz target; single-cycle timing of the synchroniser/afifo paths is pessimistic).
module noc_tw_mreq_cdc #(parameter integer AW = 3) (
    input  wire clk, input wire rst_n,
    input  wire s_req_v, output wire s_req_rdy, input wire s_req_we, input wire [31:0] s_req_addr,
    input  wire [255:0] s_req_wdata, input wire [31:0] s_req_wstrb, input wire [15:0] s_req_tag,
    output wire s_rsp_v, input wire s_rsp_rdy, output wire [15:0] s_rsp_tag, output wire s_rsp_we,
    output wire [255:0] s_rsp_data,
    output wire m_req_v, input wire m_req_rdy, output wire m_req_we, output wire [31:0] m_req_addr,
    output wire [255:0] m_req_wdata, output wire [31:0] m_req_wstrb, output wire [15:0] m_req_tag,
    input  wire m_rsp_v, output wire m_rsp_rdy, input wire [15:0] m_rsp_tag, input wire m_rsp_we,
    input  wire [255:0] m_rsp_data, output wire fault
);
    ot_gpu_mreq_cdc #(.ENABLE(1), .AW(AW)) u (
        .clk_s(clk), .rst_s_n(rst_n), .clk_m(clk), .rst_m_n(rst_n),
        .s_req_v(s_req_v), .s_req_rdy(s_req_rdy), .s_req_we(s_req_we), .s_req_addr(s_req_addr),
        .s_req_wdata(s_req_wdata), .s_req_wstrb(s_req_wstrb), .s_req_tag(s_req_tag),
        .s_rsp_v(s_rsp_v), .s_rsp_rdy(s_rsp_rdy), .s_rsp_tag(s_rsp_tag), .s_rsp_we(s_rsp_we), .s_rsp_data(s_rsp_data),
        .m_req_v(m_req_v), .m_req_rdy(m_req_rdy), .m_req_we(m_req_we), .m_req_addr(m_req_addr),
        .m_req_wdata(m_req_wdata), .m_req_wstrb(m_req_wstrb), .m_req_tag(m_req_tag),
        .m_rsp_v(m_rsp_v), .m_rsp_rdy(m_rsp_rdy), .m_rsp_tag(m_rsp_tag), .m_rsp_we(m_rsp_we), .m_rsp_data(m_rsp_data),
        .fault(fault));
endmodule
