`timescale 1ns/1ps
// Plain native provider at the actual composite's HBM-clock cmd32 boundary.
// External descriptor, drain, credit and raw288 PHY owners remain explicit.
module ot_qfd_emb_pc_native #(
 parameter integer ENABLE=0,PC=0,PHASE=0,SQD=4,S_STARVE=8,TWIN=0,TWIN_ROFF=0
)(
 input wire clk,rst_n,hclk,hrst_n,
 input wire desc_v,input wire [18:0] desc_row,input wire [10:0] desc_n,
 input wire go_v,wr_v,input wire [4:0] wr_bank,wr_col,
 input wire window_retired,write_quiet,transport_quiet,
 input wire [2:0] read_release,
 output wire desc_take,go_take,wr_take,
 input wire s_v,w_v,s_we,input wire [4:0] s_bank,s_col,
 input wire [18:0] s_row,input wire [255:0] w_d,
 output wire s_credit,e_v,output wire [257:0] e_d,
 output wire row_v,output wire [2:0] row_op,output wire [4:0] row_bank,
 output wire [18:0] row_row,output wire col_v,col_we,col_sr,
 output wire [4:0] col_bank,col_col,output wire busy,
 input wire r_v,input wire [287:0] r_d,output wire [287:0] wd,
 output wire kv_v,output wire [287:0] kv_d,
 output wire fault_core,fault_hbm
);
 wire cmd_v,cmd_credit,provider_fault,composite_fault;
 wire [31:0] cmd;wire [2:0] read_credit;
 ot_qfd_native_cmd_plain #(.ENABLE(ENABLE)) native(
 .clk(hclk),.rst_n(hrst_n),.desc_v(desc_v),.desc_row(desc_row),.desc_n(desc_n),
 .go_v(go_v),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),
 .window_retired(window_retired),.write_quiet(write_quiet),.transport_quiet(transport_quiet),
 .cmd_credit_return(cmd_credit),.read_release(read_release),
 .desc_take(desc_take),.go_take(go_take),.wr_take(wr_take),
 .cmd_v(cmd_v),.cmd(cmd),.read_credit(read_credit),.fault(provider_fault));
 ot_qfd_emb_pc #(.ENABLE(ENABLE),.PC(PC),.PHASE(PHASE),.SQD(SQD),
 .S_STARVE(S_STARVE),.TWIN(TWIN),.TWIN_ROFF(TWIN_ROFF)) core(
 .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(hrst_n),
 .cmd_v(cmd_v),.cmd(cmd),.read_credit(read_credit),.cmd_credit(cmd_credit),
 .s_v(s_v),.w_v(w_v),.s_we(s_we),.s_bank(s_bank),.s_col(s_col),.s_row(s_row),.w_d(w_d),
 .s_credit(s_credit),.e_v(e_v),.e_d(e_d),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_we(col_we),.col_sr(col_sr),.col_bank(col_bank),.col_col(col_col),.busy(busy),
 .r_v(r_v),.r_d(r_d),.wd(wd),.kv_v(kv_v),.kv_d(kv_d),
 .fault_core(fault_core),.fault_hbm(composite_fault));
 assign fault_hbm=composite_fault|provider_fault;
endmodule
