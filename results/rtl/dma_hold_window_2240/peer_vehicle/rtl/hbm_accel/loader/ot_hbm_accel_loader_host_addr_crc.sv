// Additive width-selected facade, use ND1 per physical die.
`timescale 1ns/1ps
// Upper BAR: LOAD 0x800+die*0x100, STORE 0x840+die*0x100.
// Lower BAR and original ot_host_if are untouched. Real RLAST/B determine DMA ownership.
module ot_hbm_accel_loader_host_addr_crc #(parameter integer CRC_MATRIX=0,ENABLE=0,ND=2,ADDR_W=32,STACK_W=0, parameter [63:0] STACK_BYTES=0)(
 input wire clk_host,rst_host_n,clk_mem,rst_mem_n,
 input wire s_awvalid,output wire s_awready,input wire[11:0] s_awaddr,
 input wire s_wvalid,output wire s_wready,input wire[31:0] s_wdata,input wire[3:0] s_wstrb,
 output wire s_bvalid,input wire s_bready,input wire s_arvalid,output wire s_arready,input wire[11:0] s_araddr,
 output wire s_rvalid,input wire s_rready,output wire[31:0] s_rdata,
 output wire h_awvalid,input wire h_awready,output wire[11:0] h_awaddr,
 output wire h_wvalid,input wire h_wready,output wire[31:0] h_wdata,output wire[3:0] h_wstrb,
 input wire h_bvalid,output wire h_bready,output wire h_arvalid,input wire h_arready,output wire[11:0] h_araddr,
 input wire h_rvalid,output wire h_rready,input wire[31:0] h_rdata,
 input wire h_dma_arvalid,output wire h_dma_arready,input wire[63:0] h_dma_araddr,
 output wire h_dma_rvalid,input wire h_dma_rready,output wire[63:0] h_dma_rdata,output wire[1:0] h_dma_rresp,output wire h_dma_rlast,
 input wire h_dma_awvalid,output wire h_dma_awready,input wire[63:0] h_dma_awaddr,
 input wire h_dma_wvalid,output wire h_dma_wready,input wire[63:0] h_dma_wdata,input wire[7:0] h_dma_wstrb,
 output wire h_dma_bvalid,input wire h_dma_bready,output wire[1:0] h_dma_bresp,
 output wire m_arvalid,input wire m_arready,output wire[63:0] m_araddr,output wire[7:0] m_arlen,output wire[2:0] m_arsize,
 input wire m_rvalid,output wire m_rready,input wire[63:0] m_rdata,input wire[1:0] m_rresp,input wire m_rlast,
 output wire m_awvalid,input wire m_awready,output wire[63:0] m_awaddr,output wire[7:0] m_awlen,output wire[2:0] m_awsize,
 output wire m_wvalid,input wire m_wready,output wire[63:0] m_wdata,output wire[7:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire[1:0] m_bresp,
 output wire[ND-1:0] req_v,input wire[ND-1:0] req_rdy,output wire[ND-1:0] req_we,
 output wire[ND*ADDR_W-1:0] req_addr,output wire[ND*256-1:0] req_wdata,output wire[ND*32-1:0] req_wstrb,output wire[ND*16-1:0] req_tag,
 input wire[ND-1:0] rsp_v,output wire[ND-1:0] rsp_rdy,input wire[ND-1:0] rsp_we,
 input wire[ND*16-1:0] rsp_tag,input wire[ND*256-1:0] rsp_data,
 output wire irq,output wire fault);
 assign h_awaddr=s_awaddr;assign h_wdata=s_wdata;assign h_wstrb=s_wstrb;assign h_araddr=s_araddr;
 generate if(!ENABLE)begin:g_off
 assign h_awvalid=s_awvalid;assign s_awready=h_awready;assign h_wvalid=s_wvalid;assign s_wready=h_wready;
 assign s_bvalid=h_bvalid;assign h_bready=s_bready;assign h_arvalid=s_arvalid;assign s_arready=h_arready;
 assign s_rvalid=h_rvalid;assign h_rready=s_rready;assign s_rdata=h_rdata;
 assign m_arvalid=h_dma_arvalid;assign h_dma_arready=m_arready;assign m_araddr=h_dma_araddr;assign m_arlen=0;assign m_arsize=3;
 assign h_dma_rvalid=m_rvalid;assign m_rready=h_dma_rready;assign h_dma_rdata=m_rdata;assign h_dma_rresp=m_rresp;assign h_dma_rlast=m_rlast;
 assign m_awvalid=h_dma_awvalid;assign h_dma_awready=m_awready;assign m_awaddr=h_dma_awaddr;assign m_awlen=0;assign m_awsize=3;
 assign m_wvalid=h_dma_wvalid;assign h_dma_wready=m_wready;assign m_wdata=h_dma_wdata;assign m_wstrb=h_dma_wstrb;assign m_wlast=1;
 assign h_dma_bvalid=m_bvalid;assign m_bready=h_dma_bready;assign h_dma_bresp=m_bresp;
 assign req_v=0;assign req_we=0;assign req_addr=0;assign req_wdata=0;assign req_wstrb=0;assign req_tag=0;assign rsp_rdy=0;assign irq=0;assign fault=0;
 end else begin:g_on
 localparam integer OWN=$clog2(2*ND+2);
 initial if(ND<1||ND>8)$fatal(1,"loader BAR supports 1..8 dies");
 reg wp=0,rp=0;reg[OWN-1:0] wo=0,ro=0;reg csr_fault=0;
 wire[OWN-1:0] ws=!s_awaddr[11]?OWN'(0):((s_awaddr[10:8]<ND&&!s_awaddr[7]&&s_wstrb==4'hf)?OWN'(1+2*s_awaddr[10:8]+s_awaddr[6]):OWN'(2*ND+1));
 wire[OWN-1:0] rs=!s_araddr[11]?OWN'(0):((s_araddr[10:8]<ND&&!s_araddr[7])?OWN'(1+2*s_araddr[10:8]+s_araddr[6]):OWN'(2*ND+1));
 wire[2*ND-1:0] laready,lwready,lbvalid,laready_r,lrvalid;
 wire[2*ND*32-1:0] lrdata;
 assign h_awvalid=!wp&&ws==0&&s_awvalid;assign h_wvalid=!wp&&ws==0&&s_wvalid;
 assign h_bready=wp&&wo==0&&s_bready;
 assign h_arvalid=!rp&&rs==0&&s_arvalid;assign h_rready=rp&&ro==0&&s_rready;
 assign s_awready=!wp&&(ws==0?h_awready:(ws==2*ND+1?(s_awvalid&&s_wvalid):laready[ws-1]));
 assign s_wready=!wp&&(ws==0?h_wready:(ws==2*ND+1?(s_awvalid&&s_wvalid):lwready[ws-1]));
 assign s_bvalid=wp&&(wo==0?h_bvalid:(wo==2*ND+1?1'b1:lbvalid[wo-1]));
 assign s_arready=!rp&&(rs==0?h_arready:(rs==2*ND+1?s_arvalid:laready_r[rs-1]));
 assign s_rvalid=rp&&(ro==0?h_rvalid:(ro==2*ND+1?1'b1:lrvalid[ro-1]));
 assign s_rdata=ro==0?h_rdata:(ro==2*ND+1?32'hbad00800:lrdata[(ro-1)*32+:32]);
 always @(posedge clk_host or negedge rst_host_n)if(!rst_host_n)begin wp<=0;rp<=0;wo<=0;ro<=0;csr_fault<=0;end else begin
 if(s_awvalid&&s_awready&&s_wvalid&&s_wready)begin wp<=1;wo<=ws;if(ws==2*ND+1)csr_fault<=1;end
 if(s_bvalid&&s_bready)wp<=0;
 if(s_arvalid&&s_arready)begin rp<=1;ro<=rs;if(rs==2*ND+1)csr_fault<=1;end
 if(s_rvalid&&s_rready)rp<=0;
 end
 wire[ND-1:0] larv,larr,lr_v,lr_r,lawv,lawr,lwv,lwr,lwl,lbv,lbr,li,si;
 wire[ND*64-1:0] lara,lawa;wire[ND*8-1:0] larl,lawl;wire[ND*256-1:0] lwdata;wire[ND*32-1:0] lwstrb;
 wire[255:0] lr_d;wire[1:0] lr_e,lb_e;wire lr_l;wire dma_fault;
 ot_hbm_accel_dma64 #(.ND(ND)) u_dma(
 .clk(clk_host),.rst_n(rst_host_n),
 .h_arvalid(h_dma_arvalid),.h_arready(h_dma_arready),.h_araddr(h_dma_araddr),.h_rvalid(h_dma_rvalid),.h_rready(h_dma_rready),.h_rdata(h_dma_rdata),.h_rresp(h_dma_rresp),.h_rlast(h_dma_rlast),
 .h_awvalid(h_dma_awvalid),.h_awready(h_dma_awready),.h_awaddr(h_dma_awaddr),.h_wvalid(h_dma_wvalid),.h_wready(h_dma_wready),.h_wdata(h_dma_wdata),.h_wstrb(h_dma_wstrb),.h_bvalid(h_dma_bvalid),.h_bready(h_dma_bready),.h_bresp(h_dma_bresp),
 .l_arvalid(larv),.l_arready(larr),.l_araddr(lara),.l_arlen(larl),.l_rvalid(lr_v),.l_rready(lr_r),.l_rdata(lr_d),.l_rresp(lr_e),.l_rlast(lr_l),
 .l_awvalid(lawv),.l_awready(lawr),.l_awaddr(lawa),.l_awlen(lawl),.l_wvalid(lwv),.l_wready(lwr),.l_wdata(lwdata),.l_wstrb(lwstrb),.l_wlast(lwl),.l_bvalid(lbv),.l_bready(lbr),.l_bresp(lb_e),
 .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
 .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),.fault(dma_fault));
 for(genvar d=0;d<ND;d=d+1)begin:g_die
 wire lv,lr,lwe,lsv,lsr,lswe,sv,sr,ssv,ssr;
 wire[ADDR_W-1:0] la,sa;wire[31:0] lst;wire[255:0] ld,sd;wire[15:0] lt;wire[14:0] st;
 ot_hbm_accel_loader_addr_crc #(.CRC_MATRIX(CRC_MATRIX),.ENABLE(1),.ADDR_W(ADDR_W),.STACK_W(STACK_W),.STACK_BYTES(STACK_BYTES)) u_load(
 .clk_host(clk_host),.rst_host_n(rst_host_n),.clk_mem(clk_mem),.rst_mem_n(rst_mem_n),
 .s_awvalid(s_awvalid&&!wp&&ws==1+2*d),.s_awready(laready[2*d]),.s_awaddr({6'b0,s_awaddr[5:0]}),.s_wvalid(s_wvalid&&!wp&&ws==1+2*d),.s_wready(lwready[2*d]),.s_wdata(s_wdata),.s_bvalid(lbvalid[2*d]),.s_bready(s_bready&&wp&&wo==1+2*d),
 .s_arvalid(s_arvalid&&!rp&&rs==1+2*d),.s_arready(laready_r[2*d]),.s_araddr({6'b0,s_araddr[5:0]}),.s_rvalid(lrvalid[2*d]),.s_rready(s_rready&&rp&&ro==1+2*d),.s_rdata(lrdata[2*d*32+:32]),
 .m_arvalid(larv[d]),.m_arready(larr[d]),.m_araddr(lara[d*64+:64]),.m_arlen(larl[d*8+:8]),.m_arsize(),.m_arburst(),.m_rvalid(lr_v[d]),.m_rready(lr_r[d]),.m_rdata(lr_d),.m_rresp(lr_e),.m_rlast(lr_l),.irq(li[d]),
 .req_v(lv),.req_rdy(lr),.req_we(lwe),.req_addr(la),.req_wdata(ld),.req_wstrb(lst),.req_tag(lt),.rsp_v(lsv),.rsp_rdy(lsr),.rsp_tag({1'b0,rsp_tag[d*16+:15]}),.rsp_we(rsp_we[d]),.rsp_data(rsp_data[d*256+:256]));
 ot_hbm_accel_store_addr_crc #(.CRC_MATRIX(CRC_MATRIX),.ENABLE(1),.TW(15),.ADDR_W(ADDR_W),.STACK_W(STACK_W),.STACK_BYTES(STACK_BYTES)) u_store(
 .clk_host(clk_host),.rst_host_n(rst_host_n),.clk_mem(clk_mem),.rst_mem_n(rst_mem_n),
 .s_awvalid(s_awvalid&&!wp&&ws==2+2*d),.s_awready(laready[2*d+1]),.s_awaddr({6'b0,s_awaddr[5:0]}),.s_wvalid(s_wvalid&&!wp&&ws==2+2*d),.s_wready(lwready[2*d+1]),.s_wdata(s_wdata),.s_bvalid(lbvalid[2*d+1]),.s_bready(s_bready&&wp&&wo==2+2*d),
 .s_arvalid(s_arvalid&&!rp&&rs==2+2*d),.s_arready(laready_r[2*d+1]),.s_araddr({6'b0,s_araddr[5:0]}),.s_rvalid(lrvalid[2*d+1]),.s_rready(s_rready&&rp&&ro==2+2*d),.s_rdata(lrdata[(2*d+1)*32+:32]),
 .m_awvalid(lawv[d]),.m_awready(lawr[d]),.m_awaddr(lawa[d*64+:64]),.m_awlen(lawl[d*8+:8]),.m_awsize(),.m_awburst(),.m_wvalid(lwv[d]),.m_wready(lwr[d]),.m_wdata(lwdata[d*256+:256]),.m_wstrb(lwstrb[d*32+:32]),.m_wlast(lwl[d]),.m_bvalid(lbv[d]),.m_bready(lbr[d]),.m_bresp(lb_e),.irq(si[d]),
 .req_v(sv),.req_rdy(sr),.req_we(),.req_addr(sa),.req_wdata(),.req_wstrb(),.req_tag(st),.rsp_v(ssv),.rsp_rdy(ssr),.rsp_tag(rsp_tag[d*16+:15]),.rsp_we(rsp_we[d]),.rsp_data(rsp_data[d*256+:256]));
 reg mem_lock=0,mem_store=0;
 wire pick_store=mem_lock?mem_store:sv;
 assign req_v[d]=pick_store?sv:lv;assign req_we[d]=pick_store?1'b0:lwe;
 always @(posedge clk_mem or negedge rst_mem_n)if(!rst_mem_n)begin mem_lock<=0;mem_store<=0;end else begin
 if(req_v[d]&&!req_rdy[d])begin mem_lock<=1;mem_store<=pick_store;end
 if(req_v[d]&&req_rdy[d])mem_lock<=0;
 end
 assign req_addr[d*ADDR_W+:ADDR_W]=pick_store?sa:la;assign req_wdata[d*256+:256]=pick_store?256'b0:ld;assign req_wstrb[d*32+:32]=pick_store?32'b0:lst;
 assign req_tag[d*16+:16]=pick_store?{1'b1,st}:{1'b0,lt[14:0]};
 assign sr=req_rdy[d]&&pick_store;assign lr=req_rdy[d]&&!pick_store;
 assign ssv=rsp_v[d]&&rsp_tag[d*16+15];assign lsv=rsp_v[d]&&!rsp_tag[d*16+15];
 assign rsp_rdy[d]=rsp_tag[d*16+15]?ssr:lsr;
 end
 assign irq=|li||(|si);assign fault=csr_fault||dma_fault;
 end endgenerate
endmodule
