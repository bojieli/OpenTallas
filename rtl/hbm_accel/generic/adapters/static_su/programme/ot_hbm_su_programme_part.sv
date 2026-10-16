`timescale 1ns/1ps
// ot_hbm_su_programme_part (H-SU 2026-10-16, opt-in): the whole-SU programme producer split into PARTS per-quarter
// producers ot_hbm_su_programme_pslice, each placed beside the quarter that consumes its SB = LINE_BITS/PARTS command
// bits (its own column dictionaries + its own edge-index table, lowered by su_programme_compile.py --partition), so
// the 4 x 2422-bit command never crosses the die. The default producer ot_hbm_su_programme is unchanged.
// What crosses the die: start (1 b) + length (16 b) from the root register to every producer through an equal-age
// registered path of DEPTH edges (root stage + DEPTH-1 producer pin stages), the host configuration bus (configuration
// time only; writes accepted only while idle; root-decoded per producer), and registered busy/valid/done/fault +
// edge_index back from producer 0 (faults of all producers OR-ed).
// Timing contract: start sampled at S -> every producer's controller samples it at S+DEPTH -> command line 0 sampled
// by its consumer at S+DEPTH+4 (monolithic: S+4). The compiler issues start DEPTH edges earlier, so every command bit
// reaches its consumer on the same edge as from the monolithic producer (fixed-cycle stream; no queue/credit/handshake).
// Configuration: global bank b in [BASE_k, BASE_k + SMACROS_k) is producer k's local bank b - BASE_k; a bank outside
// every range sets the sticky fault (as the monolithic producer does for b >= its capacity).
// MUT (bench only): 1 = producer MUT_SLICE gets one extra start stage (phase), 0 = none.
module ot_hbm_su_programme_pslice #(
  parameter integer SB=2422, EDGES=7111, SCOLS=(SB+255)/256,
  parameter [32*SCOLS-1:0] DICT_BANKS={SCOLS{32'd1}},
  parameter integer MACROS=SCOLS+1, STAGES=1
)(input logic clk, rst_n, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [SB-1:0] command);
  // input pin registers: STAGES start/length stages (equal-age tree leg), one configuration stage
  logic [STAGES-1:0] s_pipe; logic [16*STAGES-1:0] l_pipe;
  logic c_we; logic [15:0] c_bank; logic [6:0] c_row; logic [255:0] c_data;
  always_ff @(posedge clk) begin
    if(!rst_n) begin s_pipe<='0; l_pipe<='0; c_we<=0; end
    else begin
      s_pipe<={s_pipe,start}; l_pipe<={l_pipe,length}; c_we<=cfg_we;
    end
    c_bank<=cfg_bank; c_row<=cfg_row; c_data<=cfg_data;
  end
  ot_hbm_su_programme #(.LINE_BITS(SB),.EDGES(EDGES),.COLS(SCOLS),.DICT_BANKS(DICT_BANKS),.MACROS(MACROS)) u_p(
    .clk(clk),.rst_n(rst_n),.clk_macro(clk_macro),
    .cfg_we(c_we),.cfg_bank(c_bank),.cfg_row(c_row),.cfg_data(c_data),
    .start(s_pipe[STAGES-1]),.length(l_pipe[16*(STAGES-1)+:16]),
    .busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
endmodule

module ot_hbm_su_programme_part #(
  parameter integer LINE_BITS=9688, EDGES=7111, PARTS=4, DEPTH=2,
  parameter integer SB=LINE_BITS/PARTS,
  parameter integer SCOLS=(SB+255)/256,
  parameter [32*PARTS-1:0] SMACROS={PARTS{32'd1}},
  parameter [32*PARTS*SCOLS-1:0] DICT_BANKS={(PARTS*SCOLS){32'd1}},
  parameter integer MACROS=PARTS,
  parameter integer MUT=0, MUT_SLICE=1
)(input logic clk, rst_n, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault,
  output logic [15:0] edge_index,
  output logic [LINE_BITS-1:0] command);
  function automatic integer mbase(input integer k);
    integer v,i; begin v=0; for(i=0;i<k;i=i+1) v=v+SMACROS[32*i+:32]; mbase=v; end
  endfunction
  initial if(SB*PARTS!=LINE_BITS || MACROS!=mbase(PARTS) || DEPTH<2)
    $fatal(1,"programme partition: LINE_BITS/PARTS/MACROS/DEPTH mismatch (DEPTH >= 2: root + producer pin stage)");
  // root: one register stage (start/length shared; configuration decoded per producer)
  logic r_start; logic [15:0] r_len; logic [PARTS-1:0] r_we; logic [16*PARTS-1:0] r_bank;
  logic [6:0] r_row; logic [255:0] r_data; logic cfg_fault;
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
  wire [PARTS-1:0] p_busy, p_valid, p_done, p_fault;
  wire [16*PARTS-1:0] p_edge;
  genvar k;
  generate for(k=0;k<PARTS;k=k+1) begin:g_part
    ot_hbm_su_programme_pslice #(.SB(SB),.EDGES(EDGES),.SCOLS(SCOLS),
      .DICT_BANKS(DICT_BANKS[32*SCOLS*k+:32*SCOLS]),.MACROS(SMACROS[32*k+:32]),
      .STAGES(DEPTH-1+((MUT==1 && k==MUT_SLICE)?1:0))) u_ps(
      .clk(clk),.rst_n(rst_n),.clk_macro(clk_macro[mbase(k)+:SMACROS[32*k+:32]]),
      .cfg_we(r_we[k]),.cfg_bank(r_bank[16*k+:16]),.cfg_row(r_row),.cfg_data(r_data),
      .start(r_start),.length(r_len),
      .busy(p_busy[k]),.valid(p_valid[k]),.done(p_done[k]),.fault(p_fault[k]),
      .edge_index(p_edge[16*k+:16]),.command(command[SB*k+:SB]));
  end endgenerate
  assign busy=p_busy[0]; assign valid=p_valid[0]; assign done=p_done[0]; assign edge_index=p_edge[15:0];
  assign fault=cfg_fault | (|p_fault);
endmodule
