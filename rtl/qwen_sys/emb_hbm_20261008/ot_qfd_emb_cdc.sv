`timescale 1ns/1ps
// Explicit embedding crossing; model takeover/r21c_binding_model.json.
// Pulse interfaces are credit bounded: no pulse may arrive while its FIFO is
// offline/full. Unlike a ready/valid source, a lost pulse cannot be retried.
// Each domain therefore records pulse rejection locally as a sticky fault.
module ot_qfd_emb_cdc #(parameter integer ENABLE=0, DEPTH=8)(
 input wire clk,rst_n,hclk,hrst_n,
 input wire s_v,input wire [286:0] s_d,
 output wire c_v,output wire [286:0] c_d,
 input wire h_credit,output wire s_credit,
 input wire h_v,input wire [257:0] h_d,
 output wire e_v,output wire [257:0] e_d,
 output reg fault_core,output reg fault_hbm
);
 wire down_ready,up_ready,credit_ready;
 wire down_valid,up_valid,credit_valid;
 wire [286:0] down_data;
 wire [257:0] up_data;
 wire [0:0] credit_data;
 ot_async_fifo #(.WIDTH(287),.DEPTH(DEPTH)) down(
  .wr_clk(clk),.wr_rst_n(rst_n),.wr_valid(ENABLE!=0 && s_v),
  .wr_ready(down_ready),.wr_data(s_d),.wr_overflow(),
  .rd_clk(hclk),.rd_rst_n(hrst_n),.rd_valid(down_valid),
  .rd_ready(1'b1),.rd_data(down_data),.rd_underflow());
 ot_async_fifo #(.WIDTH(258),.DEPTH(DEPTH)) up(
  .wr_clk(hclk),.wr_rst_n(hrst_n),.wr_valid(ENABLE!=0 && h_v),
  .wr_ready(up_ready),.wr_data(h_d),.wr_overflow(),
  .rd_clk(clk),.rd_rst_n(rst_n),.rd_valid(up_valid),
  .rd_ready(1'b1),.rd_data(up_data),.rd_underflow());
 ot_async_fifo #(.WIDTH(1),.DEPTH(DEPTH)) credit(
  .wr_clk(hclk),.wr_rst_n(hrst_n),.wr_valid(ENABLE!=0 && h_credit),
  .wr_ready(credit_ready),.wr_data(1'b1),.wr_overflow(),
  .rd_clk(clk),.rd_rst_n(rst_n),.rd_valid(credit_valid),
  .rd_ready(1'b1),.rd_data(credit_data),.rd_underflow());
 assign c_v=ENABLE!=0 && down_valid;
 assign c_d=down_data;
 assign e_v=ENABLE!=0 && up_valid;
 assign e_d=up_data;
 assign s_credit=ENABLE!=0 && credit_valid;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) fault_core<=0;
  else if(ENABLE!=0 && s_v && !down_ready) fault_core<=1;
 always @(posedge hclk or negedge hrst_n)
  if(!hrst_n) fault_hbm<=0;
  else if(ENABLE!=0 && ((h_v && !up_ready) || (h_credit && !credit_ready))) fault_hbm<=1;
endmodule
