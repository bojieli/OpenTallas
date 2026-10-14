`timescale 1ns/1ps
`default_nettype none
// Independent serial clock root; pin command/response registers and registered status.
module ot_hgi_b2_dma_serial #(parameter integer MUT_RNE=0, parameter integer MUT_SEAM=0)(
 input wire clk,rst_n,
 input wire mv_v,
 input wire [226:0] mv,
 output wire mv_rdy,
 output wire mv_done,
 output wire mv_fault,
 output wire fence_rdy,
 output wire k_req_v,
 input wire k_req_rdy,
 output wire k_req_we,
 output wire [36:0] k_req_addr,
 output wire [255:0] k_req_wdata,
 output wire [31:0] k_req_wstrb,
 output wire [15:0] k_req_tag,
 input wire k_rsp_v,
 output wire k_rsp_rdy,
 input wire k_rsp_we,
 input wire [255:0] k_rsp_data,
 input wire k_fault,
 output wire [337:0] vmq,
 input wire [273:0] vmr
);
 reg p_mv_v;
 always @(posedge clk or negedge rst_n) if (!rst_n) p_mv_v<=0; else p_mv_v<=mv_v;
 reg [226:0] p_mv;
 always @(posedge clk) p_mv<=mv ^ ((MUT_SEAM==7) ? (227'd1<<206) : 227'd0);
 reg p_k_rsp_v;
 always @(posedge clk or negedge rst_n) if (!rst_n) p_k_rsp_v<=0; else p_k_rsp_v<=k_rsp_v;
 reg p_k_rsp_we;
 always @(posedge clk) p_k_rsp_we<=k_rsp_we;
 reg [255:0] p_k_rsp_data;
 always @(posedge clk) p_k_rsp_data<=k_rsp_data;
 reg p_k_fault;
 always @(posedge clk or negedge rst_n) if (!rst_n) p_k_fault<=0; else p_k_fault<=k_fault;
 reg [273:0] p_vmr;
 always @(posedge clk or negedge rst_n) if (!rst_n) p_vmr[273]<=0; else p_vmr[273]<=vmr[273];
 always @(posedge clk) p_vmr[272:0]<=vmr[272:0];
 wire c_mv_rdy; reg q_mv_rdy;
 always @(posedge clk or negedge rst_n) if (!rst_n) q_mv_rdy<=1; else q_mv_rdy<=c_mv_rdy;
 assign mv_rdy=q_mv_rdy;
 wire c_mv_done; reg q_mv_done;
 always @(posedge clk or negedge rst_n) if (!rst_n) q_mv_done<=0; else q_mv_done<=c_mv_done;
 assign mv_done=q_mv_done;
 wire c_mv_fault; reg q_mv_fault;
 always @(posedge clk or negedge rst_n) if (!rst_n) q_mv_fault<=0; else q_mv_fault<=c_mv_fault;
 assign mv_fault=q_mv_fault;
 wire c_fence_rdy; reg q_fence_rdy;
 always @(posedge clk or negedge rst_n) if (!rst_n) q_fence_rdy<=1; else q_fence_rdy<=c_fence_rdy;
 assign fence_rdy=q_fence_rdy;
 ot_hgi_dma_mover_serial #(.MUT_RNE(MUT_RNE),.SXP(1)) u_serial(.clk(clk),.rst_n(rst_n),.fence_v(1'b0),.fence_done(),
 .mv_v(p_mv_v),
 .mv(p_mv),
 .mv_rdy(c_mv_rdy),
 .mv_done(c_mv_done),
 .mv_fault(c_mv_fault),
 .fence_rdy(c_fence_rdy),
 .k_req_v(k_req_v),
 .k_req_rdy(k_req_rdy),
 .k_req_we(k_req_we),
 .k_req_addr(k_req_addr),
 .k_req_wdata(k_req_wdata),
 .k_req_wstrb(k_req_wstrb),
 .k_req_tag(k_req_tag),
 .k_rsp_v(p_k_rsp_v),
 .k_rsp_rdy(k_rsp_rdy),
 .k_rsp_we(p_k_rsp_we),
 .k_rsp_data(p_k_rsp_data),
 .k_fault(p_k_fault),
 .vmq(vmq),
 .vmr(p_vmr));
endmodule
`default_nettype wire
