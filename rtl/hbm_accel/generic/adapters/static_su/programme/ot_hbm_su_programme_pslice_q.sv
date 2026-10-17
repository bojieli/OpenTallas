`timescale 1ns/1ps
// ot_hbm_su_programme_pslice_q (H-SU 2026-10-16): the hard master for ONE per-quarter programme producer of
// ot_hbm_su_programme_part, with the uniform capacity of the current 7111-edge image (su_programme_compile.py
// --partition 4: 10 columns, dictionary banks {3,10,9,13,2,1,1,1,1,1}, 56 index banks = 98 SRAM macros), one clock
// root (all 98 macro clocks tied to clk inside the master). Same RTL/latency as ot_hbm_su_programme_pslice STAGES=1.
module ot_hbm_su_programme_pslice_q (
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [2421:0] command);
  ot_hbm_su_programme_pslice #(.SB(2422),.EDGES(7111),.SCOLS(10),
    .DICT_BANKS({32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3}),.MACROS(98),.STAGES(1)) u_ps(
    .clk(clk),.rst_n(rst_n),.clk_macro({98{clk}}),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(start),.length(length),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
endmodule
