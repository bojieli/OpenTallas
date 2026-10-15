`timescale 1ns/1ps
`default_nettype none
// Source-pinned 9,489-edge stream plane. All six stores are real mapped SRAMs.
// Registers every functional input before the producer; start/config/reset
// delivery each take one extra edge. Normal command interval remains one.
// The compiler/installer must reserve this lead; this is an opt-in candidate.
module ot_hbm_su_stream_calendar6_pin(
 input wire clk,clk_macro0,clk_macro1,clk_macro2,
 input wire clk_macro3,clk_macro4,clk_macro5,rst_n,
 input wire cfg_we,input wire [15:0] cfg_bank,
 input wire [6:0] cfg_row,input wire [255:0] cfg_data,
 input wire start,input wire [15:0] length,
 output wire busy,valid,done,fault,
 output wire [15:0] edge_index,output wire [63:0] command
);
 reg reset_q,cfg_we_q,start_q;
 reg [15:0] cfg_bank_q,length_q;
 reg [6:0] cfg_row_q;
 reg [255:0] cfg_data_q;
 always @(posedge clk)begin
  reset_q<=rst_n;
  cfg_bank_q<=cfg_bank;cfg_row_q<=cfg_row;cfg_data_q<=cfg_data;
  length_q<=length;
  cfg_we_q<=rst_n && cfg_we;
  start_q<=rst_n && start;
 end
 localparam integer DB[0:0]='{1};
 ot_hbm_su_programme #(.LINE_BITS(64),.COLS(1),.EDGES(9489),
  .INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(6)) u_programme(
  .clk(clk),.clk_macro({clk_macro5,clk_macro4,clk_macro3,
                      clk_macro2,clk_macro1,clk_macro0}),.rst_n(reset_q),
  .cfg_we(cfg_we_q),.cfg_bank(cfg_bank_q),.cfg_row(cfg_row_q),
  .cfg_data(cfg_data_q),.start(start_q),.length(length_q),
  .busy(busy),.valid(valid),.done(done),.fault(fault),
  .edge_index(edge_index),.command(command));
endmodule
`default_nettype wire
