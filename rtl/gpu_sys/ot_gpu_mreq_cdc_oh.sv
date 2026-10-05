`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_mreq_cdc_oh: ot_gpu_mreq_cdc with both FIFOs as ot_gpu_cdc_fifo_oh (replicated one-hot read select;
// identical behaviour and cycles; 1.2 GHz closure, noc family, 2026-10-04).  Original header follows.
// ot_gpu_mreq_cdc: one SM memory client crossing from the SM clock domain into
// the crossbar/L2/HBM-service domain (the GPC <-> XBAR asynchronous boundary
// of a GPU): a request FIFO (we, address, write data, byte enables, tag) and a
// response FIFO (tag, kind, data), both ot_gpu_cdc_fifo at the depth the
// sizing model gives for one entry per cycle across 833 ps <-> 1000 ps
// (tools/gpu_sys/cdc_sizing.py: 8 entries, measured >= 0.99 entries/cycle).
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_mreq_cdc_oh #(
    parameter integer ENABLE = 0,
    parameter integer AW     = 3
) (
    input  wire          clk_s,
    input  wire          rst_s_n,
    input  wire          clk_m,
    input  wire          rst_m_n,
    // SM side (clk_s)
    input  wire          s_req_v,
    output wire          s_req_rdy,
    input  wire          s_req_we,
    input  wire [31:0]   s_req_addr,
    input  wire [255:0]  s_req_wdata,
    input  wire [31:0]   s_req_wstrb,
    input  wire [15:0]   s_req_tag,
    output wire          s_rsp_v,
    input  wire          s_rsp_rdy,
    output wire [15:0]   s_rsp_tag,
    output wire          s_rsp_we,
    output wire [255:0]  s_rsp_data,
    // memory side (clk_m)
    output wire          m_req_v,
    input  wire          m_req_rdy,
    output wire          m_req_we,
    output wire [31:0]   m_req_addr,
    output wire [255:0]  m_req_wdata,
    output wire [31:0]   m_req_wstrb,
    output wire [15:0]   m_req_tag,
    input  wire          m_rsp_v,
    output wire          m_rsp_rdy,
    input  wire [15:0]   m_rsp_tag,
    input  wire          m_rsp_we,
    input  wire [255:0]  m_rsp_data,
    output wire          fault
);
generate if (ENABLE == 0) begin : g_off
    assign s_req_rdy = 1'b0; assign s_rsp_v = 1'b0; assign s_rsp_tag = 16'd0; assign s_rsp_we = 1'b0;
    assign s_rsp_data = 256'd0; assign m_req_v = 1'b0; assign m_req_we = 1'b0; assign m_req_addr = 32'd0;
    assign m_req_wdata = 256'd0; assign m_req_wstrb = 32'd0; assign m_req_tag = 16'd0; assign m_rsp_rdy = 1'b0;
    assign fault = 1'b0;
end else begin : g_on
    wire f0, f1;
    ot_gpu_cdc_fifo_oh #(.ENABLE(1), .W(1 + 32 + 256 + 32 + 16), .AW(AW)) u_req (
        .wclk(clk_s), .wrst_n(rst_s_n), .in_v(s_req_v), .in_rdy(s_req_rdy),
        .in_d({s_req_we, s_req_addr, s_req_wdata, s_req_wstrb, s_req_tag}),
        .rclk(clk_m), .rrst_n(rst_m_n), .out_v(m_req_v), .out_rdy(m_req_rdy),
        .out_d({m_req_we, m_req_addr, m_req_wdata, m_req_wstrb, m_req_tag}), .ovf_fault(f0));
    ot_gpu_cdc_fifo_oh #(.ENABLE(1), .W(16 + 1 + 256), .AW(AW)) u_rsp (
        .wclk(clk_m), .wrst_n(rst_m_n), .in_v(m_rsp_v), .in_rdy(m_rsp_rdy), .in_d({m_rsp_tag, m_rsp_we, m_rsp_data}),
        .rclk(clk_s), .rrst_n(rst_s_n), .out_v(s_rsp_v), .out_rdy(s_rsp_rdy), .out_d({s_rsp_tag, s_rsp_we, s_rsp_data}),
        .ovf_fault(f1));
    assign fault = f0 | f1;
end endgenerate
endmodule
