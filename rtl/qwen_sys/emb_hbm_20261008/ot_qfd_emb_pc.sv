`timescale 1ns/1ps
// Composite physical vehicle in the existing controller reservation.
// The KV command and raw landing interfaces remain separate from embedding.
// PHY must supply the full 288-bit protected codeword (provider still OPEN).
// KVW (sys-takeover 2026-10-09, default 0): 2 = the KV write side-band provider at the die's write timing: kw_v / kw_d are
// the per-PC STREAM4 CDC completion entry (h_cv / h_cdata, one edge after the KV WR column col_v && col_we && !col_sr);
// the port encodes it and presents every WR's 288-b PHY write data on wd two edges after its column.
module ot_qfd_emb_pc #(
 parameter integer ENABLE=0,PC=0,PHASE=0,SQD=4,S_STARVE=8,TWIN=0,TWIN_ROFF=0,KVW=0
)(
 input wire clk,rst_n,hclk,hrst_n,
 input wire cmd_v,input wire [31:0] cmd,input wire [2:0] read_credit,
 output wire cmd_credit,
 input wire s_v,w_v,s_we,input wire [4:0] s_bank,s_col,
 input wire [18:0] s_row,input wire [255:0] w_d,
 output wire s_credit,e_v,output wire [257:0] e_d,
 output wire row_v,output wire [2:0] row_op,output wire [4:0] row_bank,
 output wire [18:0] row_row,output wire col_v,col_we,col_sr,
 output wire [4:0] col_bank,col_col,output wire busy,
 input wire r_v,input wire [287:0] r_d,output wire [287:0] wd,
 input wire kw_v,input wire [255:0] kw_d,
 output wire kv_v,output wire [287:0] kv_d,
 output wire fault_core,fault_hbm
);
 wire c_v,c_credit,p_v,controller_fault,port_fault,cdc_fault_hbm;
 wire [286:0] c_d;
 wire [257:0] p_d;
 ot_qfd_emb_cdc #(.ENABLE(ENABLE)) cdc(
  .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(hrst_n),
  .s_v(s_v),.s_d({w_v,s_we,s_bank,s_col,s_row,w_d}),
  .c_v(c_v),.c_d(c_d),.h_credit(c_credit),.s_credit(s_credit),
  .h_v(p_v),.h_d(p_d),.e_v(e_v),.e_d(e_d),
  .fault_core(fault_core),.fault_hbm(cdc_fault_hbm));
 ot_qwen_ctrl_pc_emb #(.ENABLE(ENABLE),.PC(PC),.PHASE(PHASE),.SQD(SQD),
  .S_STARVE(S_STARVE),.TWIN(TWIN),.TWIN_ROFF(TWIN_ROFF)) controller(
  .clk(hclk),.rst_n(hrst_n),.cmd_v(cmd_v),.cmd(cmd),
  .read_credit(read_credit),.cmd_credit(cmd_credit),
  .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),
  .busy(busy),.fault(controller_fault),
  .s_v(c_v),.s_we(c_d[285]),.s_bank(c_d[284:280]),
  .s_col(c_d[279:275]),.s_row(c_d[274:256]),.s_cr(c_credit));
 ot_qfd_emb_pcport #(.KVW(KVW)) port(
  .clk(hclk),.rst_n(hrst_n),.col_v(col_v),.col_we(col_we),.col_sr(col_sr),
  .w_v(c_v && c_d[286]),.w_d(c_d[255:0]),.wd(wd),.kw_v(ENABLE!=0 && kw_v),.kw_d(kw_d),
  .r_v(ENABLE!=0 && r_v),.r_d(r_d),.kv_v(kv_v),.kv_d(kv_d),
  .em_v(p_v),.em_d(p_d),.fault(port_fault));
 assign fault_hbm=controller_fault|port_fault|cdc_fault_hbm;
endmodule
