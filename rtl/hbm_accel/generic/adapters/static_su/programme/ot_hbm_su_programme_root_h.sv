`timescale 1ns/1ps
// ot_hbm_su_programme_root_h (HBM-SU 2026-10-17): the hard master of the partitioned SU programme root register
// (die instance su_pgr): ot_hbm_su_programme_root PARTS 4 x 98 macros with FREG 1, so every output is a register
// output and every input lands on a register (no combinational pin-to-pin path). Covered by the part lockstep bench
// (ot_hbm_su_programme_part PIPE 1 instantiates ot_hbm_su_programme_root FREG 1).
module ot_hbm_su_programme_root_h (
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  input logic [3:0] p_fault,
  output logic r_start, output logic [15:0] r_len,
  output logic [3:0] r_we, output logic [63:0] r_bank,
  output logic [6:0] r_row, output logic [255:0] r_data,
  output logic fault);
  ot_hbm_su_programme_root #(.PARTS(4),.SMACROS({4{32'd98}}),.FREG(1)) u_root(
    .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(start),.length(length),.p_fault(p_fault),.r_start(r_start),.r_len(r_len),.r_we(r_we),.r_bank(r_bank),
    .r_row(r_row),.r_data(r_data),.fault(fault));
endmodule
