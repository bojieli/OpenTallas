`timescale 1ns/1ps
// ot_hbm_su_programme_root_h5 (HBM-RTL5 2026-10-18): the SU programme root register (die instance su_pgr) for the r5
// per-column producer clusters ot_hbm_su_programme_pslice_c5 (pgp_<q>), replacing ot_hbm_su_programme_root_h (4 x 98
// banks, r4 pslice_q4 producers). The closed root (ot_hbm_su_programme_root / _root_h, hbm_su_pgroot_1017) is unchanged.
// Why: the NATIVE-FIX3/pgs r5 leaves (pgcol_s/pgcol_l CPIN 1 RRLY 1 FADV 2, pghead OREG/FREG/HRLY/DLAT 1 CLAT 2) make the
// cluster's configuration path 2 edges longer than its start path (write on cluster pin edge e pairs with start on e+2)
// and release their reset 3 edges after the port. This root absorbs both, so the HOST-facing programme contract is the
// r4 one (a write on root pin edge e pairs with a start on root pin edge e; configuration may be written up to the edge
// before start) and every output (command/valid/done/edge_index/busy/fault) is the r4 output exactly SDLY edges later:
//   * SMACROS 4 x 320: per-part bank space = 32 x column (10 columns) + local bank (su_programme_compile.py --root5);
//     a bank >= 4 x 320 sets the sticky configuration fault (a bank inside a part but on no column / no local bank is
//     rejected by the cluster head / leaf, as before).
//   * SDLY 2: start/length are delayed SDLY extra edges (configuration is NOT), so the configuration reaches every
//     cluster leaf producer on the same edge relative to the start as in r4 (= the +2 cluster configuration edges);
//     the root's own out-of-range fault is delayed SDLY edges with it (lands on the shifted r4 fault edge).
//   * RRLY 1: rst_n drives only an ot_rst_relay (SYNC 2 + TREE 1, release +3, assert immediate) = the same release as
//     every pghead / pgcol leaf, so root and clusters leave reset on one edge; a host write or start in the 3 edges
//     after the port release is dropped everywhere (the host waits >= 3 edges, as the leaves require).
// Compiler (HBM SU programme): start -> command line 0 at the consumer is DEPTH + 4 + SDLY edges (r4: DEPTH + 4), i.e.
// start advance DEPTH + 6 with SDLY 2; configuration writes unchanged (any edge while idle, >= 0 edges before start, the
// write-on-start-edge rejection unchanged); reset: wait >= 3 edges after rst_n release; config image numbering
// 320 x part + 32 x column + local (su_programme_compile.py --root5). SDLY 0 = configuration lowered 2 edges earlier
// by the compiler instead (no start cost; write-on-start pairing then at e/e+2).
// MUT (bench only): 1 SDLY forced 0 (old root timing with the r5 clusters), 2 SMACROS 4 x 98 (r4 decode), 3 RRLY 0
// (reset relay bypassed), 4 root out-of-range fault not delayed.
module ot_hbm_su_programme_root5 #(
  parameter integer PARTS=4,
  parameter [32*PARTS-1:0] SMACROS={PARTS{32'd320}},
  parameter integer SDLY=2, RRLY=1, MUT=0
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  input logic [PARTS-1:0] p_fault,
  output logic r_start, output logic [15:0] r_len,
  output logic [PARTS-1:0] r_we, output logic [16*PARTS-1:0] r_bank,
  output logic [6:0] r_row, output logic [255:0] r_data,
  output logic fault);
  localparam [32*PARTS-1:0] SM=(MUT==2)?{PARTS{32'd98}}:SMACROS;
  localparam integer SD=(MUT==1)?0:SDLY;
  localparam integer FD=(MUT==4)?0:SD;
  function automatic integer mbase(input integer k);
    integer v,i; begin v=0; for(i=0;i<k;i=i+1) v=v+SM[32*i+:32]; mbase=v; end
  endfunction
  wire rr;
  generate if(RRLY!=0 && MUT!=3) begin:g_rr
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  end else begin:g_nrr
    assign rr=rst_n;
  end endgenerate
  // start/length: SD delay stages, then the root register
  logic s_in; logic [15:0] l_in;
  generate if(SD>0) begin:g_sd
    logic [SD-1:0] s_d; logic [16*SD-1:0] l_d;
    always_ff @(posedge clk) begin
      if(!rr) s_d<='0; else s_d<={s_d,start};
      l_d<={l_d,length};
    end
    assign s_in=s_d[SD-1]; assign l_in=l_d[16*(SD-1)+:16];
  end else begin:g_nsd
    assign s_in=start; assign l_in=length;
  end endgenerate
  logic cfg_oor;
  integer i;
  always_ff @(posedge clk) begin
    if(!rr) begin r_start<=0; r_len<=0; r_we<='0; cfg_oor<=0; end
    else begin
      r_start<=s_in; r_len<=l_in;
      for(i=0;i<PARTS;i=i+1) r_we[i]<=cfg_we && cfg_bank>=mbase(i) && cfg_bank<mbase(i+1);
      cfg_oor<=cfg_we && cfg_bank>=mbase(PARTS);
    end
    for(i=0;i<PARTS;i=i+1) r_bank[16*i+:16]<=cfg_bank-16'(mbase(i));
    r_row<=cfg_row; r_data<=cfg_data;
  end
  // own out-of-range term delayed FD edges, then sticky; fault = registered OR (FREG 1 as root_h)
  wire oor_d;
  generate if(FD>0) begin:g_fd
    logic [FD-1:0] o_d;
    always_ff @(posedge clk) if(!rr) o_d<='0; else o_d<={o_d,cfg_oor};
    assign oor_d=o_d[FD-1];
  end else begin:g_nfd
    assign oor_d=cfg_oor;
  end endgenerate
  logic cfg_fault;
  always_ff @(posedge clk) if(!rr) begin cfg_fault<=0; fault<=0; end
    else begin if(oor_d) cfg_fault<=1; fault<=cfg_fault | oor_d | (|p_fault); end
endmodule

// hard master (die instance su_pgr, d4g GEN1 with pgp_<q> = ot_hbm_su_programme_pslice_c5): same ports as root_h
// PARTS (HBM-BIND B2 2026-10-24; default 4 = unchanged, r18h5 part k = quadrant k: 0 SW, 1 SE, 2 NW, 3 NE): the number of
// programme parts pgp_* = per-part ports p_fault[k], r_we[k], r_bank[16k+:16]. PARTS 2 = the B2 die (part 0 = pgp_NW,
// part 1 = pgp_NE): bank space 2 x 320 (part k = banks 320k .. 320k + 319; a write to bank >= 640 sets the sticky
// configuration fault), compiler su_programme_compile.lower_root5(parts=2). Same edges (SDLY 2, RRLY 1, FREG 1).
// MUT (bench only): passed to ot_hbm_su_programme_root5 (1 SDLY 0, 2 SMACROS 98, 3 RRLY 0, 4 fault not delayed).
module ot_hbm_su_programme_root_h5 #(parameter integer PARTS=4, MUT=0) (
  input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  input logic [PARTS-1:0] p_fault,
  output logic r_start, output logic [15:0] r_len,
  output logic [PARTS-1:0] r_we, output logic [16*PARTS-1:0] r_bank,
  output logic [6:0] r_row, output logic [255:0] r_data,
  output logic fault);
  initial if (PARTS != 4 && PARTS != 2) $fatal(1, "ot_hbm_su_programme_root_h5: PARTS must be 4 or 2");
  ot_hbm_su_programme_root5 #(.PARTS(PARTS),.SMACROS({PARTS{32'd320}}),.SDLY(2),.RRLY(1),.MUT(MUT)) u_root(.*);
endmodule
