`timescale 1ns/1ps
// Original item9 baseline, minimum actual caller mechanism. No SM compute array.
// Caller equations are the O_COLL/B_COLL_REQ/B_COLL_RSP slice of ot_gpu_simt_sm:
// capture va/mode/count on issue; hold request until accepted; capture response
// into the destination vector on response. Each of 32 destination vectors is
// a real receiver load, not a copied generic IO timing wrapper. This is NOT the
// selected sm_v/TU interface; that independent 256-bit result protocol is retained.
// Defaults inert. Existing source files and their protection remain unchanged.
module ot_gpu_coll_item9_context32_pipe #(
 parameter integer ENABLE=0, NSM=32, NL=128,
 parameter integer OWNER64=0, TX_MASK_LA=0, RXOH=0, RDUP=8, TXCTRL=0, TREE=0, PIPE=0
)(
 input wire por_n, clk_sm, clk_link, clk_mem, clk_host,
 input wire [NSM-1:0] issue, issue_mode,
 input wire [NSM*8-1:0] issue_count,
 input wire [NSM*NL*32-1:0] issue_va,
 output wire [NSM-1:0] caller_idle, caller_done,
 output wire [NSM*NL*32-1:0] caller_vr,
 input wire switch_rx_v, input wire [545:0] switch_rx_rec,
 output wire switch_tx_v, output wire [545:0] switch_tx_rec,
 output wire fault
);
generate if(ENABLE==0)begin:g_off
 assign caller_idle='0;assign caller_done='0;assign caller_vr='0;
 assign switch_tx_v=0;assign switch_tx_rec='0;assign fault=0;
end else begin:g_on
 wire rst_sm_n,rst_link_n,rst_mem_n,rst_host_n;
 ot_gpu_reset_ctrl #(.ENABLE(1)) u_rst(.por_n(por_n),.clk_mem(clk_mem),
 .clk_link(clk_link),.clk_sm(clk_sm),.clk_host(clk_host),
 .rst_mem_n(rst_mem_n),.rst_link_n(rst_link_n),.rst_sm_n(rst_sm_n),.rst_host_n(rst_host_n));
 wire [NSM-1:0] req_v,req_rdy,mode,rsp_v,rsp_rdy;
 wire [NSM*8-1:0] count;
 wire [NSM*NL*32-1:0] data;
 wire [NL*32-1:0] rsp_data;
 for(genvar s=0;s<NSM;s=s+1)begin:g_sm_caller
  localparam [1:0] B_IDLE=0,B_COLL_REQ=1,B_COLL_RSP=2;
  reg [1:0] bst;
  reg c_mode;reg [7:0] c_count;reg [NL*32-1:0] c_data,vr;
  // Data registers follow original source: not reset; only valid state enables use.
  always @(posedge clk_sm)begin
   if(bst==B_IDLE && issue[s])begin
    c_mode<=issue_mode[s];c_count<=issue_count[s*8+:8];c_data<=issue_va[s*NL*32+:NL*32];
   end
   if(bst==B_COLL_RSP && rsp_v[s])vr<=rsp_data;
  end
  always @(posedge clk_sm or negedge rst_sm_n)begin
   if(!rst_sm_n)bst<=B_IDLE;
   else case(bst)
    B_IDLE:if(issue[s])bst<=B_COLL_REQ;
    B_COLL_REQ:if(req_rdy[s])bst<=B_COLL_RSP;
    B_COLL_RSP:if(rsp_v[s])bst<=B_IDLE;
    default:bst<=B_IDLE;
   endcase
  end
  assign req_v[s]=bst==B_COLL_REQ;assign rsp_rdy[s]=bst==B_COLL_RSP;
  assign mode[s]=c_mode;assign count[s*8+:8]=c_count;
  assign data[s*NL*32+:NL*32]=c_data;
  assign caller_idle[s]=bst==B_IDLE;
  assign caller_done[s]=bst==B_COLL_RSP && rsp_v[s];
  assign caller_vr[s*NL*32+:NL*32]=vr;
 end
 wire mv,mready,mm,rv,rr;wire[7:0]mc;wire[NL*32-1:0]md,rd;
 ot_gpu_coll_mux_item9_pipe #(.ENABLE(1),.NSM(NSM),.NL(NL),.ODUP(OWNER64!=0?64:16),.TREE(TREE),.PIPE(PIPE)) u_mux(
 .clk(clk_sm),.rst_n(rst_sm_n),.s_req_v(req_v),.s_req_rdy(req_rdy),.s_mode(mode),
 .s_count(count),.s_data(data),.s_rsp_v(rsp_v),.s_rsp_rdy(rsp_rdy),.s_rsp_data(rsp_data),
 .m_req_v(mv),.m_req_rdy(mready),.m_mode(mm),.m_count(mc),.m_data(md),
 .m_rsp_v(rv),.m_rsp_rdy(rr),.m_rsp_data(rd));
 wire tx_v;wire[545:0]tx_rec;reg[1:0]uv,dv;reg[545:0]ud[0:1],dd[0:1];
 // Exact two-stage fabric g_port link boundary. No receiver-ready tie or new credit.
 always @(posedge clk_link or negedge rst_link_n)
  if(!rst_link_n)begin uv<=0;dv<=0;end
  else begin uv<={uv[0],tx_v};dv<={dv[0],switch_rx_v};end
 always @(posedge clk_link)begin
  ud[0]<=tx_rec;ud[1]<=ud[0];dd[0]<=switch_rx_rec;dd[1]<=dd[0];
 end
 assign switch_tx_v=uv[1];assign switch_tx_rec=ud[1];
 ot_gpu_coll_endpoint_item9_txctrl #(.TXCTRL(TXCTRL),.ENABLE(1),.NL(NL),.R(2),.RANK(0),.XREG(1),
 .TX_MASK_LA(TX_MASK_LA),.RXOH(RXOH),.RDUP(RDUP)) u_ep(
 .clk_sm(clk_sm),.rst_sm_n(rst_sm_n),.coll_req_v(mv),.coll_req_rdy(mready),
 .coll_mode(mm),.coll_count(mc),.coll_data(md),.coll_rsp_v(rv),.coll_rsp_rdy(rr),
 .coll_rsp_data(rd),.coll_fault(fault),.clk_link(clk_link),.rst_link_n(rst_link_n),
 .lk_tx_v(tx_v),.lk_tx_rec(tx_rec),.lk_rx_v(dv[1]),.lk_rx_rec(dd[1]));
end endgenerate
endmodule
