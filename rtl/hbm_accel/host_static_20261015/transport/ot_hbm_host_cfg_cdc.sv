`timescale 1ns/1ps
`default_nettype none
// Bundled-data mailbox at the elastic off-die HOST installation boundary.
// No signal here is consumed by normal on-chip execution or its scheduler.
// A source payload is held until a two-flop returned completion toggle; the
// destination samples it only after a two-flop request synchronizer. Physical
// CDC timing/metastability and reset-tree qualification remain separate gates.
module ot_hbm_host_cfg_cdc #(parameter integer MUT=0)(
 input wire s_clk,m_clk,rst_n,
 input wire[11:0]s_awaddr,input wire s_awvalid,output reg s_awready,
 input wire[31:0]s_wdata,input wire[3:0]s_wstrb,input wire s_wvalid,output reg s_wready,
 output reg[1:0]s_bresp,output reg s_bvalid,input wire s_bready,
 input wire[11:0]s_araddr,input wire s_arvalid,output reg s_arready,
 output reg[31:0]s_rdata,output reg[1:0]s_rresp,output reg s_rvalid,input wire s_rready,
 output reg[11:0]m_awaddr,output reg m_awvalid,input wire m_awready,
 output reg[31:0]m_wdata,output reg[3:0]m_wstrb,output reg m_wvalid,input wire m_wready,
 input wire[1:0]m_bresp,input wire m_bvalid,output reg m_bready,
 output reg[11:0]m_araddr,output reg m_arvalid,input wire m_arready,
 input wire[31:0]m_rdata,input wire[1:0]m_rresp,input wire m_rvalid,output reg m_rready);
 reg aw_hold,w_hold,ar_hold,pending;
 reg[11:0]aw,ar,request_addr;reg[31:0]wd,request_data;reg[3:0]ws,request_strb;
 reg request_read,request_toggle;
 reg ack_meta,ack_sync,ack_seen;
 reg[31:0]response_data;reg[1:0]response_resp;
 reg ack_toggle;
 always @(posedge s_clk or negedge rst_n)begin
 if(!rst_n)begin
  aw_hold<=0;w_hold<=0;ar_hold<=0;pending<=0;request_toggle<=0;request_read<=0;
  ack_meta<=0;ack_sync<=0;ack_seen<=0;
  s_awready<=0;s_wready<=0;s_arready<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
 end else begin
  ack_meta<=ack_toggle;ack_sync<=ack_meta;
  s_awready<=!aw_hold&&!pending&&!s_bvalid;
  s_wready<=!w_hold&&!pending&&!s_bvalid;
  s_arready<=!ar_hold&&!s_rvalid;
  if(s_awvalid&&s_awready)begin aw_hold<=1;aw<=s_awaddr;s_awready<=0;end
  if(s_wvalid&&s_wready)begin w_hold<=1;wd<=s_wdata;ws<=s_wstrb;s_wready<=0;end
  if(s_arvalid&&s_arready)begin ar_hold<=1;ar<=s_araddr;s_arready<=0;end
  if(s_bvalid&&s_bready)s_bvalid<=0;
  if(s_rvalid&&s_rready)s_rvalid<=0;
  if(!pending)begin
   if(aw_hold&&w_hold&&!s_bvalid)begin
    request_addr<=aw;request_data<=wd;request_strb<=ws;request_read<=0;
    request_toggle<=!request_toggle;pending<=1;aw_hold<=0;w_hold<=0;
   end else if(ar_hold&&!s_rvalid)begin
    request_addr<=ar;request_data<=0;request_strb<=0;request_read<=1;
    request_toggle<=!request_toggle;pending<=1;ar_hold<=0;
   end
  end
  if(pending&&ack_sync!=ack_seen)begin
   ack_seen<=ack_sync;pending<=0;
   if(request_read)begin s_rvalid<=1;s_rdata<=response_data;s_rresp<=response_resp;end
   else begin s_bvalid<=1;s_bresp<=MUT==1?2'd0:response_resp;end
  end
 end end
 reg req_meta,req_sync,req_seen,busy,read_request;
 always @(posedge m_clk or negedge rst_n)begin
 if(!rst_n)begin
  req_meta<=0;req_sync<=0;req_seen<=0;busy<=0;read_request<=0;ack_toggle<=0;
  m_awvalid<=0;m_wvalid<=0;m_arvalid<=0;m_bready<=0;m_rready<=0;
  response_data<=0;response_resp<=0;
 end else begin
  req_meta<=request_toggle;req_sync<=req_meta;
  if(m_awvalid&&m_awready)m_awvalid<=0;
  if(m_wvalid&&m_wready)m_wvalid<=0;
  if(m_arvalid&&m_arready)m_arvalid<=0;
  if(!busy&&req_sync!=req_seen)begin
   req_seen<=req_sync;busy<=1;read_request<=request_read;
   if(request_read)begin m_arvalid<=1;m_araddr<=request_addr;m_rready<=1;end
   else begin m_awvalid<=1;m_wvalid<=1;m_awaddr<=request_addr;m_wdata<=request_data^(MUT==2?32'd1:32'd0);m_wstrb<=request_strb;m_bready<=1;end
  end
  if(busy&&!read_request&&m_bvalid&&m_bready)begin
   response_resp<=m_bresp;response_data<=0;ack_toggle<=req_seen;busy<=0;m_bready<=0;
  end
  if(busy&&read_request&&m_rvalid&&m_rready)begin
   response_resp<=m_rresp;response_data<=m_rdata;ack_toggle<=req_seen;busy<=0;m_rready<=0;
  end
 end end
endmodule
`default_nettype wire
