`timescale 1ns/1ps
// Per-die ND1 loader DMA outputs -> ONE system host64 DMA, no burst loss.
// One bounded cyclic probe per direction/edge, retained AXI ownership through
// actual RLAST/B. No checkpoint/model data are produced by this transport.
module ot_hbm_host_dma_shared64 #(parameter integer ENABLE=0, ND=96)(
 input wire clk,rst_n,
 input wire [ND-1:0] arvalid,output wire [ND-1:0] arready,
 input wire [ND*64-1:0] araddr,input wire [ND*8-1:0] arlen,input wire [ND*3-1:0] arsize,
 output wire [ND-1:0] rvalid,input wire [ND-1:0] rready,
 output wire [63:0] rdata,output wire [1:0] rresp,output wire rlast,
 input wire [ND-1:0] awvalid,output wire [ND-1:0] awready,
 input wire [ND*64-1:0] awaddr,input wire [ND*8-1:0] awlen,input wire [ND*3-1:0] awsize,
 input wire [ND-1:0] wvalid,output wire [ND-1:0] wready,
 input wire [ND*64-1:0] wdata,input wire [ND*8-1:0] wstrb,input wire [ND-1:0] wlast,
 output wire [ND-1:0] bvalid,input wire [ND-1:0] bready,output wire [1:0] bresp,
 output wire m_arvalid,input wire m_arready,output wire [63:0] m_araddr,output wire [7:0] m_arlen,output wire [2:0] m_arsize,
 input wire m_rvalid,output wire m_rready,input wire [63:0] m_rdata,input wire [1:0] m_rresp,input wire m_rlast,
 output wire m_awvalid,input wire m_awready,output wire [63:0] m_awaddr,output wire [7:0] m_awlen,output wire [2:0] m_awsize,
 output wire m_wvalid,input wire m_wready,output wire [63:0] m_wdata,output wire [7:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire [1:0] m_bresp,
 output wire fault
);
 localparam integer RW=(ND>1)?$clog2(ND):1;
 initial if(ND<1||ND>96)$fatal(1,"selected shared DMA rank range1..96");
 generate if(!ENABLE)begin:g_off
 assign arready=0;assign rvalid=0;assign rdata=0;assign rresp=0;assign rlast=0;
 assign awready=0;assign wready=0;assign bvalid=0;assign bresp=0;
 assign m_arvalid=0;assign m_araddr=0;assign m_arlen=0;assign m_arsize=0;
 assign m_awvalid=0;assign m_awaddr=0;assign m_awlen=0;assign m_awsize=0;
 assign m_wvalid=0;assign m_wdata=0;assign m_wstrb=0;assign m_wlast=0;
 assign m_rready=0;assign m_bready=0;assign fault=0;
 end else begin:g_on
 reg [RW-1:0] rp,wp,ro,wo;
 reg rb,wb,sticky;
 reg [8:0] rleft,wleft;
 wire rmatch=m_rlast==(rleft==1);
 wire wmatch=wlast[wo]==(wleft==1);
 assign m_arvalid=rst_n&&!sticky&&!rb&&arvalid[rp];
 assign m_araddr=araddr[rp*64+:64];assign m_arlen=arlen[rp*8+:8];assign m_arsize=arsize[rp*3+:3];
 assign m_awvalid=rst_n&&!sticky&&!wb&&awvalid[wp];
 assign m_awaddr=awaddr[wp*64+:64];assign m_awlen=awlen[wp*8+:8];assign m_awsize=awsize[wp*3+:3];
 assign rdata=m_rdata;assign rresp=m_rresp;assign rlast=m_rlast;assign bresp=m_bresp;
 assign m_rready=rb&&!sticky&&rmatch&&rready[ro];
 assign m_wvalid=wb&&!sticky&&wleft!=0&&wvalid[wo]&&wmatch;
 assign m_wdata=wdata[wo*64+:64];assign m_wstrb=wstrb[wo*8+:8];assign m_wlast=wlast[wo];
 assign m_bready=wb&&!sticky&&wleft==0&&bready[wo];
 for(genvar d=0;d<ND;d=d+1)begin:g_d
 assign arready[d]=m_arvalid&&m_arready&&rp==RW'(d);
 assign awready[d]=m_awvalid&&m_awready&&wp==RW'(d);
 assign rvalid[d]=rb&&!sticky&&rmatch&&ro==RW'(d)&&m_rvalid;
 assign wready[d]=wb&&!sticky&&wleft!=0&&wmatch&&wo==RW'(d)&&m_wready;
 assign bvalid[d]=wb&&!sticky&&wleft==0&&wo==RW'(d)&&m_bvalid;
 end
 assign fault=sticky;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 rp<=0;wp<=0;ro<=0;wo<=0;rb<=0;wb<=0;rleft<=0;wleft<=0;sticky<=0;
 end else begin
 if(!rb&&!arvalid[rp])rp<=rp==RW'(ND-1)?0:rp+1'b1;
 if(!wb&&!awvalid[wp])wp<=wp==RW'(ND-1)?0:wp+1'b1;
 if(m_arvalid&&m_arready)begin ro<=rp;rb<=1;rleft<={1'b0,m_arlen}+1'b1;rp<=rp==RW'(ND-1)?0:rp+1'b1;end
 if(m_awvalid&&m_awready)begin wo<=wp;wb<=1;wleft<={1'b0,m_awlen}+1'b1;wp<=wp==RW'(ND-1)?0:wp+1'b1;end
 if(rb&&m_rvalid&&!rmatch)sticky<=1;
 if(wb&&wvalid[wo]&&wleft!=0&&!wmatch)sticky<=1;
 if(m_rvalid&&m_rready)begin rleft<=rleft-1'b1;if(m_rlast)rb<=0;end
 if(m_wvalid&&m_wready)wleft<=wleft-1'b1;
 if(m_bvalid&&m_bready)wb<=0;
 end
 end endgenerate
endmodule
