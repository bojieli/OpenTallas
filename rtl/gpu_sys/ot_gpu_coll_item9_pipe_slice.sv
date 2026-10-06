`timescale 1ns/1ps
// Timed 64-bit slice of the actual 32-caller/register/mux mechanism.
// Full4096-bit exactness is measured separately. No substitute endpoint receiver.
// Caller equations are the O_COLL/B_COLL_REQ/B_COLL_RSP slice of ot_gpu_simt_sm:
// capture va/mode/count on issue; hold request until accepted; capture response
// into the destination vector on response. Each of 32 destination vectors is
// a real receiver load, not a copied generic IO timing wrapper. This is NOT the
// selected sm_v/TU interface; that independent 256-bit result protocol is retained.
// Defaults inert. Existing source files and their protection remain unchanged.
module ot_gpu_coll_item9_pipe_slice #(
 parameter integer ENABLE=0, NSM=32, NL=2,
 parameter integer OWNER64=0, TX_MASK_LA=0, RXOH=0, RDUP=8, TXCTRL=0, TREE=0, PIPE=0
)(
 input wire por_n, clk_sm, clk_link, clk_mem, clk_host,
 input wire [NSM-1:0] issue, issue_mode,
 input wire [NSM*8-1:0] issue_count,
 input wire [NSM*NL*32-1:0] issue_va,
 output wire [NSM-1:0] caller_idle, caller_done,
 output wire [NSM*NL*32-1:0] caller_vr,
 output wire endpoint_req_v, endpoint_mode,
 output wire [7:0] endpoint_count,
 output wire [NL*32-1:0] endpoint_data,
 input wire endpoint_req_rdy,endpoint_rsp_v,
 input wire [NL*32-1:0] endpoint_rsp_data,
 output wire endpoint_rsp_rdy
);
generate if(ENABLE==0)begin:g_off
 assign caller_idle='0;assign caller_done='0;assign caller_vr='0;
 assign endpoint_req_v=0;assign endpoint_mode=0;assign endpoint_count=0;
 assign endpoint_data='0;assign endpoint_rsp_rdy=0;
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
 ot_gpu_coll_mux_item9_pipe #(.ENABLE(1),.NSM(NSM),.NL(NL),.ODUP(1),.TREE(TREE),.PIPE(PIPE)) u_mux(
 .clk(clk_sm),.rst_n(rst_sm_n),.s_req_v(req_v),.s_req_rdy(req_rdy),.s_mode(mode),
 .s_count(count),.s_data(data),.s_rsp_v(rsp_v),.s_rsp_rdy(rsp_rdy),.s_rsp_data(rsp_data),
 .m_req_v(mv),.m_req_rdy(mready),.m_mode(mm),.m_count(mc),.m_data(md),
 .m_rsp_v(rv),.m_rsp_rdy(rr),.m_rsp_data(rd));
 // Physical cut at the actual endpoint request/response interface. The parent
 // must bind these ports to its real endpoint; this vehicle is not a new endpoint.
 assign endpoint_req_v=mv;assign endpoint_mode=mm;assign endpoint_count=mc;
 assign endpoint_data=md;assign mready=endpoint_req_rdy;
 assign rv=endpoint_rsp_v;assign rd=endpoint_rsp_data;assign endpoint_rsp_rdy=rr;
end endgenerate
endmodule
