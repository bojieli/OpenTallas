`timescale 1ns/1ps
// ot_hbm_su_programme_pslice_q2 (HBM-SU 2026-10-17): successor of ot_hbm_su_programme_pslice_q after its gate
// (hbm_su_pslice_1016, 2026-10-16) FAILED structurally: macro->macro -1112.9 ps (index SRAM data -> 56-bank mux ->
// dictionary SRAM address in one edge), reg->macro -938.5, in->reg -891.7 (rst_n sync reset on 2,422 command flops),
// trial GRT rc 137. Same per-quarter capacity (10 columns, dictionary banks {3,10,9,13,2,1,1,1,1,1}, 56 index banks
// = 98 SRAM macros, one clock root) with the pipelined producer ot_hbm_su_programme PIPE 1: every macro pair has its
// own output register, the index word is registered once more before the dictionary address, and the command
// register has no reset. +3 edges start -> command (compiler start advance DEPTH+3); lockstep vs the monolithic
// producer: tools/hbm_static/su_programme_part_run.sh PIPE=1.
module ot_hbm_su_programme_pslice_q2 (
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [2421:0] command);
  ot_hbm_su_programme_pslice #(.SB(2422),.EDGES(7111),.SCOLS(10),
    .DICT_BANKS({32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3}),.MACROS(98),.STAGES(1),.PIPE(1)) u_ps(
    .clk(clk),.rst_n(rst_n),.clk_macro({98{clk}}),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(start),.length(length),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
endmodule
