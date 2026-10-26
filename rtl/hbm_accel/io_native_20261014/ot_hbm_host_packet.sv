`timescale 1ns/1ps
// Actual HBM host external-service packet controller. Source-exact reverse
// ports of ot_hfd_loader_hgi; no GPU command processor/token semantics.
// Four independent AXI directions each allow one outstanding transaction.
// Packet acceptance/retirement is external host service, never core issue.
module ot_hbm_host_packet #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire rx_valid,input wire [511:0] rx_packet,output wire rx_ready,
 output reg tx_valid,output reg [511:0] tx_packet,input wire tx_ready,
 output reg protocol_fault,
 output reg  s_awvalid,
 input wire  s_awready,
 output reg [11:0] s_awaddr,
 output reg  s_wvalid,
 input wire  s_wready,
 output reg [31:0] s_wdata,
 output reg [3:0] s_wstrb,
 input wire  s_bvalid,
 input wire [1:0] s_bresp,
 output reg  s_bready,
 output reg  s_arvalid,
 input wire  s_arready,
 output reg [11:0] s_araddr,
 input wire  s_rvalid,
 output reg  s_rready,
 input wire [31:0] s_rdata,
 input wire  h_awvalid,
 output reg  h_awready,
 input wire [11:0] h_awaddr,
 input wire  h_wvalid,
 output reg  h_wready,
 input wire [31:0] h_wdata,
 input wire [3:0] h_wstrb,
 output reg  h_bvalid,
 input wire  h_bready,
 input wire  h_arvalid,
 output reg  h_arready,
 input wire [11:0] h_araddr,
 output reg  h_rvalid,
 input wire  h_rready,
 output reg [31:0] h_rdata,
 output reg  h_dma_arvalid,
 input wire  h_dma_arready,
 output reg [63:0] h_dma_araddr,
 input wire  h_dma_rvalid,
 output reg  h_dma_rready,
 input wire [63:0] h_dma_rdata,
 input wire [1:0] h_dma_rresp,
 input wire  h_dma_rlast,
 output reg  h_dma_awvalid,
 input wire  h_dma_awready,
 output reg [63:0] h_dma_awaddr,
 output reg  h_dma_wvalid,
 input wire  h_dma_wready,
 output reg [63:0] h_dma_wdata,
 output reg [7:0] h_dma_wstrb,
 input wire  h_dma_bvalid,
 output reg  h_dma_bready,
 input wire [1:0] h_dma_bresp,
 input wire  m_arvalid,
 output reg  m_arready,
 input wire [63:0] m_araddr,
 input wire [7:0] m_arlen,
 input wire [2:0] m_arsize,
 output reg  m_rvalid,
 input wire  m_rready,
 output reg [63:0] m_rdata,
 output reg [1:0] m_rresp,
 output reg  m_rlast,
 input wire  m_awvalid,
 output reg  m_awready,
 input wire [63:0] m_awaddr,
 input wire [7:0] m_awlen,
 input wire [2:0] m_awsize,
 input wire  m_wvalid,
 output reg  m_wready,
 input wire [63:0] m_wdata,
 input wire [7:0] m_wstrb,
 input wire  m_wlast,
 output reg  m_bvalid,
 input wire  m_bready,
 output reg [1:0] m_bresp,
 input wire  irq,
 input wire  fault
);
 reg sbw,sbr,hdw,hdr,hbw,hbr,mdw,mdr;
 reg hb_sent,hr_sent,md_sent,mr_sent;
 reg sb_resp,sr_resp,hdw_resp,hdr_resp;
 reg hb_aw,hb_w,md_aw,md_w,hb_req,hr_req,md_req,mr_req;
 reg [15:0] sb_id,sr_id,hdw_id,hdr_id;
 reg [63:0] hd_read_data;reg [1:0] hd_read_resp,hd_write_resp;reg hd_read_last;
 reg [31:0] s_read_data;reg [1:0] s_write_resp;
 reg [11:0] hb_addr,hr_addr;
 reg [31:0] hb_data;reg [3:0] hb_strb;
 reg [63:0] md_addr,mr_addr,md_data;reg [7:0] md_strb;
 reg status_pending;reg [1:0] last_status;
 wire accept=rx_valid&&rx_ready;
 wire [7:0] op=rx_packet[7:0];
 wire [15:0] tid=rx_packet[31:16];
 wire malformed=rx_packet[15:8]!==8'd1 || rx_packet[511:171]!==341'd0;
 assign rx_ready=malformed?1'b1:
  op==8'h01 ? !sbw:op==8'h02 ? !sbr:op==8'h03 ? !hdr:op==8'h04 ? !hdw:
  op==8'h91 ? !h_bvalid:op==8'h92 ? !h_rvalid:op==8'h93 ? !m_rvalid:op==8'h94 ? !m_bvalid:1'b1;
 function automatic [511:0] packet(input [7:0] code,input [15:0] id,input [63:0] addr,input [63:0] data,input [7:0] strb,input [1:0] resp,input last);
 begin packet={341'd0,last,resp,strb,data,addr,id,8'd1,code};end endfunction
 // Data leaves packet and AXI ports from registers. Response valid is held
 // until the actual external-side transaction consumer accepts it.
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  tx_valid<=0;tx_packet<=0;protocol_fault<=0;
  sbw<=0;sbr<=0;hdw<=0;hdr<=0;hbw<=0;hbr<=0;mdw<=0;mdr<=0;
  sb_resp<=0;sr_resp<=0;hdw_resp<=0;hdr_resp<=0;s_write_resp<=0;
  hb_aw<=0;hb_w<=0;md_aw<=0;md_w<=0;hb_req<=0;hr_req<=0;md_req<=0;mr_req<=0;
  status_pending<=0;last_status<=0;hb_sent<=0;hr_sent<=0;md_sent<=0;mr_sent<=0;
  s_awvalid<=0;s_wvalid<=0;s_bready<=0;s_arvalid<=0;s_rready<=0;
  s_awaddr<=0;s_wdata<=0;s_wstrb<=0;s_araddr<=0;
  h_awready<=0;h_wready<=0;h_bvalid<=0;h_arready<=0;h_rvalid<=0;h_rdata<=0;
  h_dma_arvalid<=0;h_dma_rready<=0;h_dma_awvalid<=0;h_dma_wvalid<=0;h_dma_bready<=0;
  h_dma_araddr<=0;h_dma_awaddr<=0;h_dma_wdata<=0;h_dma_wstrb<=0;
  m_arready<=0;m_rvalid<=0;m_rdata<=0;m_rresp<=0;m_rlast<=0;
  m_awready<=0;m_wready<=0;m_bvalid<=0;m_bresp<=0;
 end else begin
  if({fault,irq}!==last_status)begin status_pending<=1;last_status<={fault,irq};end
  if(tx_valid&&tx_ready)case(tx_packet[7:0])8'h11:hb_sent<=1;8'h12:hr_sent<=1;8'h13:mr_sent<=1;8'h14:md_sent<=1;default:;endcase
  // Actual AXI handshakes; independent AW and W channels are joined once.
  h_awready<=!hbw&&!hb_aw;h_wready<=!hbw&&!hb_w;h_arready<=!hbr;
  m_awready<=!mdw&&!md_aw;m_wready<=!mdw&&!md_w;m_arready<=!mdr;
  if(h_awvalid&&h_awready)begin hb_aw<=1;hb_addr<=h_awaddr;h_awready<=0;end
  if(h_wvalid&&h_wready)begin hb_w<=1;hb_data<=h_wdata;hb_strb<=h_wstrb;h_wready<=0;end
  if(hb_aw&&hb_w&&!hbw)begin hbw<=1;hb_req<=1;end
  if(h_arvalid&&h_arready)begin hbr<=1;hr_req<=1;hr_addr<=h_araddr;h_arready<=0;end
  if(m_awvalid&&m_awready)begin if(m_awlen!==8'd0 || m_awsize!==3'd3)protocol_fault<=1; md_aw<=1;md_addr<=m_awaddr;m_awready<=0;end
  if(m_wvalid&&m_wready)begin if(m_wlast!==1'b1)protocol_fault<=1; md_w<=1;md_data<=m_wdata;md_strb<=m_wstrb;m_wready<=0;end
  if(md_aw&&md_w&&!mdw)begin mdw<=1;md_req<=1;end
  if(m_arvalid&&m_arready)begin if(m_arlen!==8'd0 || m_arsize!==3'd3)protocol_fault<=1; mdr<=1;mr_req<=1;mr_addr<=m_araddr;m_arready<=0;end
  if(h_bvalid&&h_bready)begin h_bvalid<=0;hbw<=0;hb_sent<=0;hb_aw<=0;hb_w<=0;end
  if(h_rvalid&&h_rready)begin h_rvalid<=0;hbr<=0;hr_sent<=0;end
  if(m_bvalid&&m_bready)begin m_bvalid<=0;mdw<=0;md_sent<=0;md_aw<=0;md_w<=0;end
  if(m_rvalid&&m_rready)begin m_rvalid<=0;mdr<=0;mr_sent<=0;end
  if(s_awvalid&&s_awready)s_awvalid<=0;
  if(s_wvalid&&s_wready)s_wvalid<=0;
  if(s_arvalid&&s_arready)s_arvalid<=0;
  if(s_bvalid&&s_bready)begin s_bready<=0;sb_resp<=1;s_write_resp<=MUT==3?2'd0:s_bresp;if(s_bresp!=0)protocol_fault<=1;end
  if(s_rvalid&&s_rready)begin s_rready<=0;sr_resp<=1;s_read_data<=s_rdata;end
  if(h_dma_awvalid&&h_dma_awready)h_dma_awvalid<=0;
  if(h_dma_wvalid&&h_dma_wready)h_dma_wvalid<=0;
  if(h_dma_arvalid&&h_dma_arready)h_dma_arvalid<=0;
  if(h_dma_bvalid&&h_dma_bready)begin h_dma_bready<=0;hdw_resp<=1;hd_write_resp<=h_dma_bresp;end
  if(h_dma_rvalid&&h_dma_rready)begin h_dma_rready<=0;hdr_resp<=1;hd_read_data<=h_dma_rdata;hd_read_resp<=h_dma_rresp;hd_read_last<=h_dma_rlast;if(h_dma_rlast!==1'b1)protocol_fault<=1;end
  if(accept)begin
   if(malformed)protocol_fault<=1;
   else case(op)
    8'h01:begin
     if(rx_packet[95:44]!=0||rx_packet[159:128]!=0||rx_packet[167:164]!=0)protocol_fault<=1;
     else begin sbw<=1;sb_id<=tid;s_awvalid<=1;s_awaddr<=rx_packet[43:32];s_wvalid<=1;s_wdata<=rx_packet[127:96]^(MUT==1?32'd1:32'd0);s_wstrb<=rx_packet[163:160];s_bready<=1;end
    end
    8'h02:begin
     if(rx_packet[95:44]!=0)protocol_fault<=1;
     else begin sbr<=1;sr_id<=tid;s_arvalid<=1;s_araddr<=rx_packet[43:32];s_rready<=1;end
    end
    8'h03:begin hdr<=1;hdr_id<=tid;h_dma_arvalid<=1;h_dma_araddr<=rx_packet[95:32];h_dma_rready<=1;end
    8'h04:begin hdw<=1;hdw_id<=tid;h_dma_awvalid<=1;h_dma_awaddr<=rx_packet[95:32];h_dma_wvalid<=1;h_dma_wdata<=rx_packet[159:96];h_dma_wstrb<=rx_packet[167:160];h_dma_bready<=1;end
    8'h91:if(!hbw||!hb_sent||tid!=0)protocol_fault<=1;else h_bvalid<=1;
    8'h92:if(!hbr||!hr_sent||tid!=0)protocol_fault<=1;else begin h_rvalid<=1;h_rdata<=rx_packet[127:96];end
    8'h93:if(!mdr||!mr_sent||tid!=0)protocol_fault<=1;else begin m_rvalid<=1;m_rdata<=rx_packet[159:96];m_rresp<=rx_packet[169:168];m_rlast<=rx_packet[170];if(rx_packet[170]!==1'b1)protocol_fault<=1;end
    8'h94:if(!mdw||!md_sent||tid!=0)protocol_fault<=1;else begin m_bvalid<=1;m_bresp<=rx_packet[169:168];end
    default:protocol_fault<=1;
   endcase
  end
  // All choices here arbitrate only exceptional/initial external host
  // service. They are never a replacement for compiler compute issue.
  if(!tx_valid||tx_ready)begin
   tx_valid<=1;
   if(sb_resp)begin tx_packet<=packet(8'h81,sb_id,0,0,0,s_write_resp,1);sb_resp<=0;sbw<=0;end
   else if(sr_resp)begin tx_packet<=packet(8'h82,sr_id,0,{32'd0,s_read_data},0,0,1);sr_resp<=0;sbr<=0;end
   else if(hdr_resp)begin tx_packet<=packet(8'h83,hdr_id,0,hd_read_data,0,hd_read_resp,hd_read_last);hdr_resp<=0;hdr<=0;end
   else if(hdw_resp)begin tx_packet<=packet(8'h84,hdw_id,0,0,0,hd_write_resp,1);hdw_resp<=0;hdw<=0;end
   else if(hb_req)begin tx_packet<=packet(8'h11,0,{52'd0,hb_addr},{32'd0,hb_data},{4'd0,hb_strb},0,1);hb_req<=0;end
   else if(hr_req)begin tx_packet<=packet(8'h12,0,{52'd0,hr_addr},0,0,0,1);hr_req<=0;end
   else if(mr_req)begin tx_packet<=packet(8'h13,0,mr_addr,0,0,0,1);mr_req<=0;end
   else if(md_req)begin tx_packet<=packet(8'h14,0,md_addr,md_data,md_strb,0,1);md_req<=0;end
   else if(status_pending)begin tx_packet<=packet(8'hff,0,0,{62'd0,fault,irq},0,0,1);status_pending<=0;end
   else tx_valid<=0;
  end
 end
 end
endmodule
