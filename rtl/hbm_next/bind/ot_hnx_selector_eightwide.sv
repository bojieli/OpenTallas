`default_nettype none
module ot_hbm_idx_selector_static_sel_eightwide #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [1183:0] in_line,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output reg fault
);
 wire [2367:0] full_line;
 assign full_line[0+:592]={296'd0,in_line[0+:296]};
 assign full_line[592+:592]={296'd0,in_line[296+:296]};
 assign full_line[1184+:592]={296'd0,in_line[592+:296]};
 assign full_line[1776+:592]={296'd0,in_line[888+:296]};
 ot_hbm_idx_selector_static_sel #(.MUT(MUT)) u_selector (
  .clk_ctl(clk_ctl),
  .clk_q(clk_q),
  .clk_mem(clk_mem),
  .rst_n(rst_n),
  .op(op),
  .pass(pass),
  .addr(addr),
  .k(k),
  .in_line(full_line),
  .selected_v(selected_v),
  .selected_line(selected_line),
  .fault(fault)
 );
endmodule
`default_nettype wire
