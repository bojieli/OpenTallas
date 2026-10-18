`timescale 1ns/1ps
// HBM-SU r5 (2026-10-17): the per-quarter SU programme producer as a CLUSTER of hardened leaves.
// Why: the flat per-quarter tile (ot_hbm_su_programme_pslice_q2 r3 / _q4 r4, 98 SRAM macros + ~14k flops on one local
// clock root over 940 x 760 um) measured TT clock insertion 830..1280 ps (spread 318..429 ps) at its CTS gate and its
// trial global route did not finish in 4 h (r3 GRT rc137, r4 killed after 3.5 h with clock NDRs dropped for congestion):
// it fails the measured clock rule (<= 300 ps insertion, <= 80 ps spread) and cannot be closed by placement.
// Structure (top-down contract: glue in tiles, replicated leaves hardened once):
//   * one leaf per command column (ot_hbm_su_programme_pgcol): its own packed edge-index table (16 edges per 256-bit
//     row, 4 banks for 7111 edges) + its own dictionary + its own 256 command registers + a replica of the tiny
//     controller (pc/count/valid chain). The column's index no longer rides a 56-bank, 10-column index row across the
//     tile: index bits drop from 56 x 256 to 10 x 4 x 256 macro bits, and each leaf is a 7- or 17-macro block with its
//     own clock root. Two leaf masters: S (3 dictionary banks, 7 macros) and L (13 dictionary banks, 17 macros).
//   * one head leaf (ot_hbm_su_programme_pghead): the configuration pin stage + column decode (bank[15:5] = column,
//     bank[4:0] = bank inside the column), the sticky fault OR of all leaves and a lockstep check of the leaf valids.
// Timing contract unchanged from r4: start pin -> leaf pin register (= the pslice STAGES 1 stage) -> producer PIPE 2
// (+4 edges): the compiler start advance stays DEPTH+4. Configuration: pin -> head register (= the pslice c_* stage)
// -> leaf producer, as before. fault: leaf reports FADV 1 edge early, head OR register restores the r4 edge.
// Config bank numbering inside a quarter: 32 x column + local bank (local 0..3 index, 4.. dictionary), so the root's
// per-part range is 32 x columns (SMACROS 320 for 10 columns).

// one command column: packed index (INDEX_PACK 16) + DB dictionary banks + 256 command bits
module ot_hbm_su_programme_pgcol #(
  parameter integer DB=3, EDGES=7111, CFGR=1, MUT=0, PMUT=0
)(input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  localparam integer IB=(EDGES+2047)/2048;
  localparam integer MAC=IB+DB;
  initial if(MAC>31) $fatal(1,"pgcol: local bank space is 5 bits (31 = reject)");
  // start/length pin stage (the pslice STAGES 1 stage); PMUT 1 (bench phase mutant): one extra start stage
  logic [1:0] s_q; logic [31:0] l_q;
  always_ff @(posedge clk) begin
    if(!rst_n) s_q<='0; else s_q<={s_q[0],start};
    l_q<={l_q[15:0],length};
  end
  wire s_in=(PMUT==1)?s_q[1]:s_q[0];
  wire [15:0] l_in=(PMUT==1)?l_q[31:16]:l_q[15:0];
  // a configuration write to ANY column on the edge start is accepted rejects the start in every column (the r4
  // single-producer rule): present it to this producer as an out-of-range write (sets fault, writes nothing)
  wire p_we=cfg_we | (cfg_any & s_in);
  wire [15:0] p_bank=cfg_we ? {11'd0,cfg_bank} : 16'hffff;
  ot_hbm_su_programme #(.LINE_BITS(256),.EDGES(EDGES),.COLS(1),.INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(MAC),
    .PIPE(2),.CFGR(CFGR),.FADV(1),.MUT(MUT)) u_p(
    .clk(clk),.rst_n(rst_n),.clk_macro({MAC{clk}}),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(s_in),.length(l_in),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),
    .command(command));
endmodule

// the S and L leaf masters (hardened once each)
module ot_hbm_su_programme_pgcol_s(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(3),.CFGR(1)) u_c(.*);
endmodule
module ot_hbm_su_programme_pgcol_l(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(13),.CFGR(2)) u_c(.*);
endmodule

// head: configuration pin stage + column decode, sticky fault OR (+ leaf valid lockstep check)
module ot_hbm_su_programme_pghead #(
  parameter integer NC=10, XP=4, MUT=0
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic [NC-1:0] l_fault, l_valid,
  output logic [NC-1:0] o_we, output logic o_any, output logic [4:0] o_bank, output logic [6:0] o_row,
  output logic [255:0] o_data, output logic fault);
  logic c_we; logic [15:0] c_bank;
  always_ff @(posedge clk) begin
    if(!rst_n) c_we<=0; else c_we<=cfg_we;
    c_bank<=cfg_bank; o_row<=cfg_row; o_data<=cfg_data;
  end
  genvar c;
  for(c=0;c<NC;c=c+1) begin:dec
    assign o_we[c]=c_we && c_bank[15:5]==11'(c);
  end
  // MUT 1 (bench): cfg_any not driven (a write to another column on the start edge no longer rejects the start)
  assign o_any=(MUT==1)?1'b0:c_we;
  assign o_bank=c_bank[4:0];
  // own sticky fault: write to no column (as the r4 producer's bank >= capacity), or leaf valids out of lockstep;
  // delayed XP-1 edges so it lands on the r4 producer's fault edge; leaf faults arrive FADV 1 early -> OR register
  logic hf; logic [XP-2:0] hf_d;
  always_ff @(posedge clk) if(!rst_n) begin hf<=0; hf_d<='0; fault<=0; end
    else begin
      if((c_we && c_bank[15:5]>=11'(NC)) || (|(l_valid ^ {NC{l_valid[0]}}))) hf<=1;
      hf_d<={hf_d,hf};
      fault<=hf_d[XP-2] | (|l_fault);
    end
endmodule

// cluster top (bench + parent cluster RTL): same ports as ot_hbm_su_programme_pslice_q4.
// DICT_CAP: per column dictionary capacity needed (column 0 at the LSB); a column uses the S leaf if it fits 3 banks.
module ot_hbm_su_programme_pslice_c5 #(
  parameter integer SB=2422, NC=(SB+255)/256,
  parameter [32*NC-1:0] DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
  parameter integer MUT=0, MUT_COL=1
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [SB-1:0] command);
  wire [NC-1:0] we, l_busy, l_valid, l_done, l_fault; wire any; wire [4:0] bank; wire [6:0] row; wire [255:0] data;
  wire [16*NC-1:0] l_edge; wire [256*NC-1:0] cmd;
  ot_hbm_su_programme_pghead #(.NC(NC),.MUT(MUT==2)) u_h(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.l_fault(l_fault),.l_valid(l_valid),.o_we(we),.o_any(any),.o_bank(bank),
    .o_row(row),.o_data(data),.fault(fault));
  genvar c;
  for(c=0;c<NC;c=c+1) begin:g_c
    localparam integer CAP=DICT_CAP[32*c+:32];
    initial if(CAP>13) $fatal(1,"pslice_c5: column dictionary over the L leaf (13 banks)");
    // MUT 1: column MUT_COL one start edge late (phase); MUT 3: that column's final dictionary mux on the live hit
    ot_hbm_su_programme_pgcol #(.DB((CAP<=3)?3:13),.CFGR((CAP<=3)?1:2),.PMUT(MUT==1 && c==MUT_COL),
      .MUT((MUT==3 && c==MUT_COL)?1:0)) u_c(
      .clk(clk),.rst_n(rst_n),.cfg_we(we[c]),.cfg_any(any),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),
      .start(start),.length(length),.busy(l_busy[c]),.valid(l_valid[c]),.done(l_done[c]),.fault(l_fault[c]),
      .edge_index(l_edge[16*c+:16]),.command(cmd[256*c+:256]));
  end
  assign busy=l_busy[0]; assign valid=l_valid[0]; assign done=l_done[0]; assign edge_index=l_edge[15:0];
  assign command=cmd[SB-1:0];
endmodule
