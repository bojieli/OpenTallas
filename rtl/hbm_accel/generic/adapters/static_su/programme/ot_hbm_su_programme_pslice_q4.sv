`timescale 1ns/1ps
// ot_hbm_su_programme_pslice_q4 (HBM-SU r4 2026-10-17): successor of ot_hbm_su_programme_pslice_q2 after its r2 gate
// (hbm_su_pslice_r2_1017, 9272b2f43) FAILED on fan-out, not depth: dt select_q[0] 8,961 loads (macro->pair_q -1253),
// c_v -> 2,422 command flops (-898), cfg c_bank/c_data -> 98 macros (-418/-385), the 28-pair index funnel
// (psel->indices_r -408). Same ports, same per-quarter capacity (10 columns, dictionary banks {3,10,9,13,2,1,1,1,1,1},
// 56 index banks = 98 SRAM macros, one clock root), producer ot_hbm_su_programme PIPE 2: index 4 banks per output
// register + one registered funnel group stage (4 output registers per group), dictionary 2 banks per output register,
// select/hit registers replicated per output register x 4 slices, per-bank write enables + 4 replicated config copies,
// per-column read-enable and per-column x slice command-valid copies. +4 edges start -> command (compiler start advance
// DEPTH+4); lockstep vs the monolithic producer: tools/hbm_static/su_programme_part_run.sh PIPE=2.
// Clock sinks (estimate): command 2,422 + dictionary og 25 x 256 + index og 14 x 256 + group 4 x 256 + indices_r +
// config 4 x 263 + 98 enables + ~200 control/replicas ~= 14.5k (synthesis prunes unused index bits 160..255) + 98 macros.
module ot_hbm_su_programme_pslice_q4 (
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [2421:0] command);
  ot_hbm_su_programme_pslice #(.SB(2422),.EDGES(7111),.SCOLS(10),
    .DICT_BANKS({32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3}),.MACROS(98),.STAGES(1),.PIPE(2)) u_ps(
    .clk(clk),.rst_n(rst_n),.clk_macro({98{clk}}),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(start),.length(length),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
endmodule
