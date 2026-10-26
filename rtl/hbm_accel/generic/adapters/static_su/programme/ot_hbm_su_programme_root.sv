`timescale 1ns/1ps
// ot_hbm_su_programme_root (H-NETLIST/SU-PART 2026-10-17): the root register of the partitioned SU programme
// (ot_hbm_su_programme_part), factored out so the die contract can place it as its own small instance (su_pgr, homed at
// the minimax of the PARTS producer slots) while the producers ot_hbm_su_programme_pslice_q sit in their quadrant slots.
// ot_hbm_su_programme_part instantiates this module, so the part lockstep bench (tb_hbm_su_programme_part) covers it.
// One register stage: start/length shared by every producer; host configuration decoded per producer (producer k owns
// global banks [base_k, base_k + SMACROS_k), sees local bank b - base_k); a bank outside every range sets the sticky
// configuration fault. fault = configuration fault | any producer fault (producer faults are registered at the producer).
// busy/valid/done/edge_index are NOT routed through the root: every producer emits them on the same edge (same start,
// same length), so each consumer takes them from its own producer (die: col_su from producer 0).
// FREG (HBM-SU 2026-10-17, default 0 = unchanged): 1 = fault is a register output (fault <= cfg fault | any producer
// fault), so the hard root has no combinational input -> output path (native pin rule); faults report one edge later.
module ot_hbm_su_programme_root #(
  parameter integer PARTS=4,
  parameter [32*PARTS-1:0] SMACROS={PARTS{32'd98}},
  parameter integer FREG=0
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  input logic [PARTS-1:0] p_fault,
  output logic r_start, output logic [15:0] r_len,
  output logic [PARTS-1:0] r_we, output logic [16*PARTS-1:0] r_bank,
  output logic [6:0] r_row, output logic [255:0] r_data,
  output logic fault);
  function automatic integer mbase(input integer k);
    integer v,i; begin v=0; for(i=0;i<k;i=i+1) v=v+SMACROS[32*i+:32]; mbase=v; end
  endfunction
  logic cfg_fault;
  integer i;
  always_ff @(posedge clk) begin
    if(!rst_n) begin r_start<=0; r_len<=0; r_we<='0; cfg_fault<=0; end
    else begin
      r_start<=start; r_len<=length;
      for(i=0;i<PARTS;i=i+1) r_we[i]<=cfg_we && cfg_bank>=mbase(i) && cfg_bank<mbase(i+1);
      if(cfg_we && cfg_bank>=mbase(PARTS)) cfg_fault<=1;
    end
    for(i=0;i<PARTS;i=i+1) r_bank[16*i+:16]<=cfg_bank-16'(mbase(i));
    r_row<=cfg_row; r_data<=cfg_data;
  end
  generate if(FREG==0) begin:g_fc
    assign fault=cfg_fault | (|p_fault);
  end else begin:g_fr
    logic fault_r;
    always_ff @(posedge clk) if(!rst_n) fault_r<=0; else fault_r<=cfg_fault | (|p_fault);
    assign fault=fault_r;
  end endgenerate
endmodule
