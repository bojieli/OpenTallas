`timescale 1ns/1ps
// Reserved two protected SM-domain transport stages in each direction.
module ot_hbm_w2_gateway_cdc(
 input wire clk_s,rst_s_n,clk_m,rst_m_n,
 input wire s_req_v,output wire s_req_rdy,input wire s_req_we,
 input wire [31:0] s_req_addr,input wire [255:0] s_req_wdata,
 input wire [31:0] s_req_wstrb,input wire [15:0] s_req_tag,
 output wire s_rsp_v,input wire s_rsp_rdy,output wire [15:0] s_rsp_tag,
 output wire s_rsp_we,output wire [255:0] s_rsp_data,
 output wire m_req_v,input wire m_req_rdy,output wire m_req_we,
 output wire [31:0] m_req_addr,output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb,output wire [15:0] m_req_tag,
 input wire m_rsp_v,output wire m_rsp_rdy,input wire [15:0] m_rsp_tag,
 input wire m_rsp_we,input wire [255:0] m_rsp_data,
 output wire drained_s,fault
);
 wire rq0v,rq0r,rq1v,rq1r,rs0v,rs0r,rs1v,rs1r,cv,cr;
 wire [336:0] rq0,rq1;wire [272:0] rs0,rs1,cd;
 wire [3:0] empty,cut_fault;wire cdc_empty,cdc_fault;
 ot_hbm_w2_protected_cut #(.W(337)) u_request_cut0(
  .clk(clk_s),.por_n(rst_s_n),.in_v(s_req_v),.in_r(s_req_rdy),
  .in_d({s_req_we,s_req_addr,s_req_wdata,s_req_wstrb,s_req_tag}),
  .out_v(rq0v),.out_r(rq0r),.out_d(rq0),.empty(empty[0]),.fault(cut_fault[0]));
 ot_hbm_w2_protected_cut #(.W(337)) u_request_cut1(
  .clk(clk_s),.por_n(rst_s_n),.in_v(rq0v),.in_r(rq0r),.in_d(rq0),
  .out_v(rq1v),.out_r(rq1r),.out_d(rq1),.empty(empty[1]),.fault(cut_fault[1]));
 ot_hbm_w2_protected_cut #(.W(273)) u_response_cut0(
  .clk(clk_s),.por_n(rst_s_n),.in_v(cv),.in_r(cr),.in_d(cd),
  .out_v(rs0v),.out_r(rs0r),.out_d(rs0),.empty(empty[2]),.fault(cut_fault[2]));
 ot_hbm_w2_protected_cut #(.W(273)) u_response_cut1(
  .clk(clk_s),.por_n(rst_s_n),.in_v(rs0v),.in_r(rs0r),.in_d(rs0),
  .out_v(s_rsp_v),.out_r(s_rsp_rdy),.out_d({s_rsp_tag,s_rsp_we,s_rsp_data}),
  .empty(empty[3]),.fault(cut_fault[3]));
 ot_hbm_w2_protected_mreq_cdc u_existing_shape_cdc(
  .clk_s(clk_s),.rst_s_n(rst_s_n),.clk_m(clk_m),.rst_m_n(rst_m_n),
  .s_req_v(rq1v),.s_req_rdy(rq1r),.s_req_we(rq1[336]),.s_req_addr(rq1[335:304]),
  .s_req_wdata(rq1[303:48]),.s_req_wstrb(rq1[47:16]),.s_req_tag(rq1[15:0]),
  .s_rsp_v(cv),.s_rsp_rdy(cr),.s_rsp_tag(cd[272:257]),.s_rsp_we(cd[256]),.s_rsp_data(cd[255:0]),
  .m_req_v(m_req_v),.m_req_rdy(m_req_rdy),.m_req_we(m_req_we),.m_req_addr(m_req_addr),
  .m_req_wdata(m_req_wdata),.m_req_wstrb(m_req_wstrb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),.m_rsp_tag(m_rsp_tag),.m_rsp_we(m_rsp_we),.m_rsp_data(m_rsp_data),
  .drained_s(cdc_empty),.fault(cdc_fault));
 assign fault=(|cut_fault)||cdc_fault;
 assign drained_s=(&empty)&&cdc_empty&&!fault;
endmodule
