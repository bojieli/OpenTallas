`timescale 1ns/1ps
// DIE-HBM-62/CUTS 11-04: pslice_c5 RE-FORM masters (COORD 01:03). Per-column sub-cores of the kept 939.6 x 760.32 slot:
// S (7 macros) and L (17 macros) column leaves = the recipe's own pgcol parameters (NCX 0), H = the configuration head
// plus the per-column start/length relay. The relay flops are the H output face flops, one per column bit, so synthesis
// cannot merge them into one shared flop (the k3 root cause). Composition + cycles: results/die_hbm_1103/reform/split_p8.
module ot_hbm_su_pcol_s #(parameter integer MUT=0, PMUT=0)(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(3),.CFGR(1),.CPIN(1),.RRLY(1),.FADV(2),.NCX(0),.MUT(MUT),.PMUT(PMUT)) u_c(.valid_pin(),.edge_index_pin(),.*);
endmodule
module ot_hbm_su_pcol_l #(parameter integer MUT=0, PMUT=0)(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(13),.CFGR(2),.CPIN(1),.RRLY(1),.FADV(2),.NCX(0),.MUT(MUT),.PMUT(PMUT)) u_c(.valid_pin(),.edge_index_pin(),.*);
endmodule
// CLAT 6 = the gold 2 + 4: the head's own out-of-range fault lands on the same edge as a leaf fault, which reaches the
// head 4 edges later than in the flat slice (+2 start/config relay, leaf output face, head input face).
// HMUT (bench): 1 cfg_any dropped; 2 CLAT 2; 3 DLAT 0; 4 column 7 length bit 4 stuck low
module ot_hbm_su_pcol_h #(parameter integer HMUT=0)(
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  input logic [9:0] l_fault, l_valid,
  output logic [9:0] o_we, output logic o_any, output logic [4:0] o_bank, output logic [6:0] o_row, output logic [255:0] o_data,
  output logic [9:0] o_start, output logic [159:0] o_length, output logic fault);
  ot_hbm_su_programme_pghead #(.NC(10),.XP(4),.MUT(HMUT==1),.OREG(1),.FREG(1),.CLAT((HMUT==2)?2:6),.HRLY(1),.DLAT(HMUT!=3)) u_h(.*);
  genvar c;
  for(c=0;c<10;c=c+1) begin:g_r
    assign o_start[c]=start;
    assign o_length[16*c+:16]=(HMUT==4 && c==7)?(length&16'hffef):length;
  end
endmodule
