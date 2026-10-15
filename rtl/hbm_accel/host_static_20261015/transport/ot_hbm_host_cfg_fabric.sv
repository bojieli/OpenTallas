`timescale 1ns/1ps
`default_nettype none
// Actual host-boundary configuration composition. Target RTL connects to
// explicit m_ ports; these signals never schedule normal on-chip execution.
module ot_hbm_host_cfg_fabric #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire[2:0]clk_target,
 input wire[11:0]s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire[31:0]s_wdata,input wire[3:0]s_wstrb,input wire s_wvalid,output wire s_wready,
 output wire[1:0]s_bresp,output wire s_bvalid,input wire s_bready,
 input wire[11:0]s_araddr,input wire s_arvalid,output wire s_arready,
 output wire[31:0]s_rdata,output wire[1:0]s_rresp,output wire s_rvalid,input wire s_rready,
 output wire[2:0][11:0]m_awaddr,output wire[2:0]m_awvalid,input wire[2:0]m_awready,
 output wire[2:0][31:0]m_wdata,output wire[2:0][3:0]m_wstrb,output wire[2:0]m_wvalid,input wire[2:0]m_wready,
 input wire[2:0][1:0]m_bresp,input wire[2:0]m_bvalid,output wire[2:0]m_bready,
 output wire[2:0][11:0]m_araddr,output wire[2:0]m_arvalid,input wire[2:0]m_arready,
 input wire[2:0][31:0]m_rdata,input wire[2:0][1:0]m_rresp,input wire[2:0]m_rvalid,output wire[2:0]m_rready,
 output wire fault);
 wire[2:0][11:0]x_awaddr,x_araddr;wire[2:0][31:0]x_wdata,x_rdata;
 wire[2:0][3:0]x_wstrb;wire[2:0][1:0]x_bresp,x_rresp;
 wire[2:0]x_awvalid,x_awready,x_wvalid,x_wready,x_bvalid,x_bready,x_arvalid,x_arready,x_rvalid,x_rready;
 ot_hbm_host_cfg_demux #(.MUT(MUT==3?1:0)) u_route(.clk(clk),.rst_n(rst_n),
.s_awaddr(s_awaddr),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_bresp(s_bresp),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_araddr(s_araddr),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_rdata(s_rdata),.s_rresp(s_rresp),.s_rvalid(s_rvalid),.s_rready(s_rready),
.m_awaddr(x_awaddr),.m_awvalid(x_awvalid),.m_awready(x_awready),.m_wdata(x_wdata),.m_wstrb(x_wstrb),.m_wvalid(x_wvalid),.m_wready(x_wready),.m_bresp(x_bresp),.m_bvalid(x_bvalid),.m_bready(x_bready),.m_araddr(x_araddr),.m_arvalid(x_arvalid),.m_arready(x_arready),.m_rdata(x_rdata),.m_rresp(x_rresp),.m_rvalid(x_rvalid),.m_rready(x_rready),.fault(fault));
 for(genvar g=0;g<3;g=g+1)begin:targets
 ot_hbm_host_cfg_cdc #(.MUT(MUT<=2?MUT:0)) u_cdc(.s_clk(clk),.m_clk(clk_target[g]),.rst_n(rst_n),
.s_awaddr(x_awaddr[g]),.s_awvalid(x_awvalid[g]),.s_awready(x_awready[g]),.s_wdata(x_wdata[g]),.s_wstrb(x_wstrb[g]),.s_wvalid(x_wvalid[g]),.s_wready(x_wready[g]),.s_bresp(x_bresp[g]),.s_bvalid(x_bvalid[g]),.s_bready(x_bready[g]),.s_araddr(x_araddr[g]),.s_arvalid(x_arvalid[g]),.s_arready(x_arready[g]),.s_rdata(x_rdata[g]),.s_rresp(x_rresp[g]),.s_rvalid(x_rvalid[g]),.s_rready(x_rready[g]),
.m_awaddr(m_awaddr[g]),.m_awvalid(m_awvalid[g]),.m_awready(m_awready[g]),.m_wdata(m_wdata[g]),.m_wstrb(m_wstrb[g]),.m_wvalid(m_wvalid[g]),.m_wready(m_wready[g]),.m_bresp(m_bresp[g]),.m_bvalid(m_bvalid[g]),.m_bready(m_bready[g]),.m_araddr(m_araddr[g]),.m_arvalid(m_arvalid[g]),.m_arready(m_arready[g]),.m_rdata(m_rdata[g]),.m_rresp(m_rresp[g]),.m_rvalid(m_rvalid[g]),.m_rready(m_rready[g]));
 end
endmodule
`default_nettype wire
