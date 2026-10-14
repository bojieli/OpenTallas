`timescale 1ns/1ps
// Retains the host's real 64-bit DMA and arbitrates ND loader engines.
// Read ownership is held to actual RLAST; write ownership to actual B.
// Each engine sector is four physical 64-bit beats, with retained byte strobes.
module ot_hbm_accel_dma64 #(parameter integer ND=2)(
 input wire clk,rst_n,
 input wire h_arvalid,output wire h_arready,input wire[63:0] h_araddr,
 output wire h_rvalid,input wire h_rready,output wire[63:0] h_rdata,output wire[1:0] h_rresp,output wire h_rlast,
 input wire h_awvalid,output wire h_awready,input wire[63:0] h_awaddr,
 input wire h_wvalid,output wire h_wready,input wire[63:0] h_wdata,input wire[7:0] h_wstrb,
 output wire h_bvalid,input wire h_bready,output wire[1:0] h_bresp,
 input wire[ND-1:0] l_arvalid,output wire[ND-1:0] l_arready,input wire[ND*64-1:0] l_araddr,input wire[ND*8-1:0] l_arlen,
 output wire[ND-1:0] l_rvalid,input wire[ND-1:0] l_rready,output wire[255:0] l_rdata,output wire[1:0] l_rresp,output wire l_rlast,
 input wire[ND-1:0] l_awvalid,output wire[ND-1:0] l_awready,input wire[ND*64-1:0] l_awaddr,input wire[ND*8-1:0] l_awlen,
 input wire[ND-1:0] l_wvalid,output wire[ND-1:0] l_wready,input wire[ND*256-1:0] l_wdata,input wire[ND*32-1:0] l_wstrb,input wire[ND-1:0] l_wlast,
 output wire[ND-1:0] l_bvalid,input wire[ND-1:0] l_bready,output wire[1:0] l_bresp,
 output wire m_arvalid,input wire m_arready,output wire[63:0] m_araddr,output wire[7:0] m_arlen,output wire[2:0] m_arsize,
 input wire m_rvalid,output wire m_rready,input wire[63:0] m_rdata,input wire[1:0] m_rresp,input wire m_rlast,
 output wire m_awvalid,input wire m_awready,output wire[63:0] m_awaddr,output wire[7:0] m_awlen,output wire[2:0] m_awsize,
 output wire m_wvalid,input wire m_wready,output wire[63:0] m_wdata,output wire[7:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire[1:0] m_bresp,output reg fault);
 localparam integer CW=$clog2(ND+1);
 reg rbusy=0,wbusy=0,rlock=0,wlock=0;reg[CW-1:0] ro=0,wo=0,rr=0,wr=0,rhold=0,whold=0;
 reg[1:0] rp=0,wp=0,pe=0;reg pv=0,pl=0;reg[255:0] packet;
 reg[8:0] rleft=0;reg[8:0] wleft=0;
 reg[CW-1:0] rpick,wpick;reg rf,wf;integer k,x;
 always @*begin
 rpick=rhold;wpick=whold;rf=rlock;wf=wlock;
 if(!rlock)begin rpick=rr;rf=0;for(k=0;k<ND+1;k=k+1)begin x=(int'(rr)+k)%(ND+1);if(!rf&&(x==0?h_arvalid:l_arvalid[x-1]))begin rf=1;rpick=CW'(x);end end end
 if(!wlock)begin wpick=wr;wf=0;for(k=0;k<ND+1;k=k+1)begin x=(int'(wr)+k)%(ND+1);if(!wf&&(x==0?h_awvalid:l_awvalid[x-1]))begin wf=1;wpick=CW'(x);end end end
 end
 assign m_arvalid=rst_n&&!rbusy&&rf;
 assign m_araddr=rpick==0?h_araddr:l_araddr[(rpick-1)*64+:64];
 assign m_arlen=rpick==0?8'b0:{l_arlen[(rpick-1)*8+:6],2'b11};assign m_arsize=3;
 assign h_arready=m_arvalid&&m_arready&&rpick==0;
 assign h_rvalid=rbusy&&ro==0&&m_rvalid;assign h_rdata=m_rdata;assign h_rresp=m_rresp;assign h_rlast=m_rlast;
 assign l_rdata=packet;assign l_rresp=pe;assign l_rlast=pl;
 assign m_rready=rbusy&&(ro==0?h_rready:(!pv||l_rready[ro-1]));
 assign m_awvalid=rst_n&&!wbusy&&wf;
 assign m_awaddr=wpick==0?h_awaddr:l_awaddr[(wpick-1)*64+:64];
 assign m_awlen=wpick==0?8'b0:{l_awlen[(wpick-1)*8+:6],2'b11};assign m_awsize=3;
 assign h_awready=m_awvalid&&m_awready&&wpick==0;
 assign m_wvalid=wbusy&&(wo==0?h_wvalid:l_wvalid[wo-1]);
 assign m_wdata=wo==0?h_wdata:l_wdata[(wo-1)*256+wp*64+:64];
 assign m_wstrb=wo==0?h_wstrb:l_wstrb[(wo-1)*32+wp*8+:8];
 assign m_wlast=wo==0?1'b1:l_wlast[wo-1]&&wp==3;
 assign h_wready=wbusy&&wo==0&&m_wready;
 assign h_bvalid=wbusy&&wo==0&&m_bvalid;assign h_bresp=m_bresp;assign l_bresp=m_bresp;
 assign m_bready=wbusy&&(wo==0?h_bready:l_bready[wo-1]);
 for(genvar d=0;d<ND;d=d+1)begin:g_d
 assign l_arready[d]=m_arvalid&&m_arready&&rpick==d+1;
 assign l_rvalid[d]=rbusy&&ro==d+1&&pv;
 assign l_awready[d]=m_awvalid&&m_awready&&wpick==d+1;
 assign l_wready[d]=wbusy&&wo==d+1&&m_wready&&wp==3;
 assign l_bvalid[d]=wbusy&&wo==d+1&&m_bvalid;
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 rbusy<=0;wbusy<=0;rlock<=0;wlock<=0;ro<=0;wo<=0;rr<=0;wr<=0;rhold<=0;whold<=0;
 rp<=0;wp<=0;pe<=0;pv<=0;pl<=0;rleft<=0;wleft<=0;fault<=0;
 end else begin
 if(m_arvalid&&!m_arready)begin rlock<=1;rhold<=rpick;end
 if(m_awvalid&&!m_awready)begin wlock<=1;whold<=wpick;end
 if(m_arvalid&&m_arready)begin rlock<=0;rbusy<=1;ro<=rpick;rp<=0;pv<=0;pe<=0;rleft<={1'b0,m_arlen}+1;rr<=rpick==ND?CW'(0):rpick+1'b1;if(rpick!=0&&l_arlen[(rpick-1)*8+:8]>=64)fault<=1;end
 if(m_awvalid&&m_awready)begin wlock<=0;wbusy<=1;wo<=wpick;wp<=0;wleft<={1'b0,m_awlen}+1;wr<=wpick==ND?CW'(0):wpick+1'b1;if(wpick!=0&&l_awlen[(wpick-1)*8+:8]>=64)fault<=1;end
 if(rbusy&&ro!=0&&pv&&l_rready[ro-1])begin pv<=0;pe<=0;if(pl)rbusy<=0;end
 if(m_rvalid&&m_rready)begin
 if(m_rlast!=(rleft==1))fault<=1;rleft<=rleft-1'b1;
 if(ro==0)begin if(m_rlast)rbusy<=0;end
 else begin packet[rp*64+:64]<=m_rdata;pe<=((pv&&l_rready[ro-1])?2'b0:pe)|m_rresp;rp<=rp+1'b1;if(rp==3)begin pv<=1;pl<=m_rlast;end end
 end
 if(m_wvalid&&m_wready)begin if(m_wlast!=(wleft==1))fault<=1;wleft<=wleft-1'b1;if(wo!=0)wp<=wp+1'b1;end
 if(m_bvalid&&m_bready)begin if(wleft!=0)fault<=1;wbusy<=0;end
 end
endmodule
