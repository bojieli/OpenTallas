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
// NATIVE-FIX3/pgs 2026-10-18 (NATIVE-3 audit, claude/native-3-1017 73adc87ea: pgcol_s capture rst_n 414.2 / cfg_we 390.6
// / cfg_any 388.4 / cfg_bank 284..304 ps > 190; pghead launch o_we 221..226 > 220, capture l_fault 199..205 > 190):
//   * leaf (CPIN 1): the configuration control pins (cfg_we, cfg_any, cfg_bank) land on pin registers; cfg_row/
//     cfg_data (already captured directly by the per-bank config copy registers) arrive from the head one edge later;
//     (RRLY 1) rst_n drives only an ot_rst_relay (release +3 edges: SYNC 2 + TREE 1, assert async/immediate).
//   * head (OREG 1): o_we/o_any/o_bank/o_row/o_data leave from export registers (o_we decoded into its own flop per
//     column); (FREG 1) l_fault lands on pin registers and the leaves report fault FADV 2 edges early (was 1), so the
//     cluster fault edge is unchanged; the head's own out-of-range fault is delayed CLAT 2 edges to stay on it;
//     (HRLY 1) the head's rst_n drives only an ot_rst_relay (release +3 edges, as the leaves).
//   Cluster timing: configuration pin -> leaf producer is +2 edges (head export +1, leaf pin +1): the host's
//   configuration (load-time, while idle) is issued 2 edges earlier / the start comes >= 2 edges later after the last
//   write; the write-on-start-edge rejection pairs a write on pin edge e with a start on pin edge e+2. Start advance
//   (DEPTH+4), command/valid/done/edge_index/busy/fault edges unchanged. Leaf reset release is 3 edges after the port:
//   the host waits >= 3 edges after reset release before configuring or starting.

// one command column: packed index (INDEX_PACK 16) + DB dictionary banks + 256 command bits
module ot_hbm_su_programme_pgcol #(
  parameter integer DB=3, EDGES=7111, CFGR=1, MUT=0, PMUT=0,
  parameter integer CPIN=0, RRLY=0, FADV=1,  // NATIVE-FIX3 (S/L masters: 1, 1, 2); defaults = the r5 leaf
  parameter integer NCX=0                    // HBMb/IDXSU-PS15: 1 = ot_hbm_su_programme_nc producer (native census); 0 = r5
)(input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  localparam integer IB=(EDGES+2047)/2048;
  localparam integer MAC=IB+DB;
  initial if(MAC>31) $fatal(1,"pgcol: local bank space is 5 bits (31 = reject)");
  // reset: RRLY 1 = the port drives only the relay; region 0 = pin stages, region 1 = the producer
  // NCX 1: regions 1..5 = the producer's five equal-age reset groups (ot_hbm_su_programme_nc rst_x)
  localparam integer NRL=(NCX!=0)?9:2;
  wire [NRL-1:0] rl;
  generate if(RRLY!=0) begin:g_rr
    ot_rst_relay #(.REGIONS(NRL),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rl));
  end else begin:g_nrr
    assign rl={NRL{rst_n}};
  end endgenerate
  wire rst_c=rl[0];
  // configuration pin stage (CPIN 1, +1 configuration edge) on the control pins cfg_we/cfg_any/cfg_bank. cfg_row/
  // cfg_data land, as in r5, directly on the producer's registered config copies (wrow_r/wdat_r = their pin registers):
  // the head presents them one edge after the control (its DLAT stage), so the copies capture them on the edge the
  // pin-registered enable reaches the producer. (Gate g1, all five cfg inputs pin-flopped: 263 data flops pulled to
  // the N face raised the TT pin-flop spread 63 -> 101 ps.)
  logic q_we, q_any; logic [4:0] q_bank;
  generate if(CPIN!=0) begin:g_cp
    always_ff @(posedge clk) begin
      if(!rst_c) begin q_we<=0; q_any<=0; end else begin q_we<=cfg_we; q_any<=cfg_any; end
      q_bank<=cfg_bank;
    end
  end else begin:g_ncp
    assign q_we=cfg_we; assign q_any=cfg_any; assign q_bank=cfg_bank;
  end endgenerate
  // start/length pin stage (the pslice STAGES 1 stage); PMUT 1 (bench phase mutant): one extra start stage
  logic [1:0] s_q; logic [31:0] l_q;
  always_ff @(posedge clk) begin
    if(!rst_c) s_q<='0; else s_q<={s_q[0],start};
    l_q<={l_q[15:0],length};
  end
  wire s_in=(PMUT==1)?s_q[1]:s_q[0];
  wire [15:0] l_in=(PMUT==1)?l_q[31:16]:l_q[15:0];
  // a configuration write to ANY column on the edge start is accepted rejects the start in every column (the r4
  // single-producer rule): present it to this producer as an out-of-range write (sets fault, writes nothing)
  wire p_we=q_we | (q_any & s_in);
  wire [15:0] p_bank=q_we ? {11'd0,q_bank} : 16'hffff;
  generate if(NCX==0) begin:g_p
  ot_hbm_su_programme #(.LINE_BITS(256),.EDGES(EDGES),.COLS(1),.INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(MAC),
    .PIPE(2),.CFGR(CFGR),.FADV(FADV),.MUT(MUT)) u_p(
    .clk(clk),.rst_n(rl[1]),.clk_macro({MAC{clk}}),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(s_in),.length(l_in),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),
    .command(command));
  end else begin:g_pn
  ot_hbm_su_programme_nc #(.EDGES(EDGES),.INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(MAC),.CFGR(CFGR),.FADV(FADV),.MUT(MUT),
    .IOG(4),.DOG(2),.RS(16),.NAI(4),.NAD(16),.NRX(8)) u_p(
    .clk(clk),.rst_x(rl[NRL-1:1]),.clk_macro({MAC{clk}}),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(s_in),.length(l_in),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),
    .command(command));
  end endgenerate
endmodule

// the S and L leaf masters (hardened once each)
module ot_hbm_su_programme_pgcol_s(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(3),.CFGR(1),.CPIN(1),.RRLY(1),.FADV(2)) u_c(.*);
endmodule
module ot_hbm_su_programme_pgcol_l(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol #(.DB(13),.CFGR(2),.CPIN(1),.RRLY(1),.FADV(2),.NCX(1)) u_c(.*);   // PS15: NCX producer
endmodule

// head: configuration pin stage + column decode, sticky fault OR (+ leaf valid lockstep check)
// NATIVE-FIX3 10-18: OREG 1 = export registers on every output (o_we decoded into its own flop), FREG 1 = l_fault pin
// registers (leaves FADV 2), CLAT = configuration edges from the head's pin stage to the leaf producer beyond the
// first (OREG + leaf CPIN = 2) -- the head's own out-of-range fault is delayed by it; HRLY 1 = reset relay at rst_n;
// DLAT 1 = o_row/o_data one edge after o_we/o_any/o_bank (the leaf pin-registers only the control pins).
// OREG 0 / FREG 0 / CLAT 0 / HRLY 0 = r5.
module ot_hbm_su_programme_pghead #(
  parameter integer NC=10, XP=4, MUT=0, OREG=1, FREG=1, CLAT=2, HRLY=1, DLAT=1
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic [NC-1:0] l_fault, l_valid,
  output logic [NC-1:0] o_we, output logic o_any, output logic [4:0] o_bank, output logic [6:0] o_row,
  output logic [255:0] o_data, output logic fault);
  // HRLY 1 (NATIVE-FIX3 gate g1: rst_n capture 238 ps with ~25 sync-reset flops on the port): the port drives only an
  // ot_rst_relay (release +3 edges, the same release as the leaves)
  wire hr;
  generate if(HRLY!=0) begin:g_hr
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(hr));
  end else begin:g_nhr
    assign hr=rst_n;
  end endgenerate
  logic c_we; logic [15:0] c_bank; logic [6:0] c_row; logic [255:0] c_data;
  always_ff @(posedge clk) begin
    if(!hr) c_we<=0; else c_we<=cfg_we;
    c_bank<=cfg_bank; c_row<=cfg_row; c_data<=cfg_data;
  end
  wire [NC-1:0] d_we;
  genvar c;
  for(c=0;c<NC;c=c+1) begin:dec
    assign d_we[c]=c_we && c_bank[15:5]==11'(c);
  end
  // MUT 1 (bench): cfg_any not driven (a write to another column on the start edge no longer rejects the start)
  wire d_any=(MUT==1)?1'b0:c_we;
  wire d_oor=c_we && c_bank[15:5]>=11'(NC);
  generate if(OREG!=0) begin:g_or
    logic [6:0] r2_row; logic [255:0] r2_data;
    always_ff @(posedge clk) begin
      if(!hr) begin o_we<='0; o_any<=0; end else begin o_we<=d_we; o_any<=d_any; end
      o_bank<=c_bank[4:0]; r2_row<=c_row; r2_data<=c_data;
    end
    // DLAT 1: row/data one more edge (the leaf pin-registers only the control pins)
    if(DLAT!=0) begin:g_dl
      always_ff @(posedge clk) begin o_row<=r2_row; o_data<=r2_data; end
    end else begin:g_ndl
      assign o_row=r2_row; assign o_data=r2_data;
    end
  end else begin:g_nor
    assign o_we=d_we; assign o_any=d_any; assign o_bank=c_bank[4:0]; assign o_row=c_row; assign o_data=c_data;
  end endgenerate
  // out-of-range term delayed CLAT edges (it lands with the leaves' view of the write)
  wire oor;
  generate if(CLAT>0) begin:g_cl
    logic [CLAT-1:0] oor_d;
    always_ff @(posedge clk) if(!hr) oor_d<='0; else oor_d<={oor_d,d_oor};
    assign oor=oor_d[CLAT-1];
  end else begin:g_ncl
    assign oor=d_oor;
  end endgenerate
  // leaf fault pin registers (FREG 1)
  logic [NC-1:0] lf;
  generate if(FREG!=0) begin:g_fr
    always_ff @(posedge clk) if(!hr) lf<='0; else lf<=l_fault;
  end else begin:g_nfr
    assign lf=l_fault;
  end endgenerate
  // own sticky fault: write to no column (as the r4 producer's bank >= capacity), or leaf valids out of lockstep;
  // delayed XP-1 edges so it lands on the r4 producer's fault edge; leaf faults arrive FADV (1 + FREG) early -> OR reg
  logic hf; logic [XP-2:0] hf_d;
  always_ff @(posedge clk) if(!hr) begin hf<=0; hf_d<='0; fault<=0; end
    else begin
      if(oor || (|(l_valid ^ {NC{l_valid[0]}}))) hf<=1;
      hf_d<={hf_d,hf};
      fault<=hf_d[XP-2] | (|lf);
    end
endmodule

// cluster top (bench + parent cluster RTL): same ports as ot_hbm_su_programme_pslice_q4.
// DICT_CAP: per column dictionary capacity needed (column 0 at the LSB); a column uses the S leaf if it fits 3 banks.
module ot_hbm_su_programme_pslice_c5 #(
  parameter integer SB=2422, NC=(SB+255)/256,
  parameter [32*NC-1:0] DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
  parameter integer MUT=0, MUT_COL=1,
  parameter integer NCX=0   // PS15 bench switch: 1 = the L columns (DB 13) use the NCX producer as pgcol_l does
  // MUT (bench) 4: leaf reset relay bypassed; 5: leaf configuration pin stage dropped; 6: head export registers
  // dropped (o_we combinational); 7: head l_fault pin registers dropped; 8: head reset relay bypassed
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [SB-1:0] command);
  wire [NC-1:0] we, l_busy, l_valid, l_done, l_fault; wire any; wire [4:0] bank; wire [6:0] row; wire [255:0] data;
  wire [16*NC-1:0] l_edge; wire [256*NC-1:0] cmd;
  ot_hbm_su_programme_pghead #(.NC(NC),.MUT(MUT==2),.OREG(MUT!=6),.FREG(MUT!=7),.CLAT(2),.HRLY(MUT!=8)) u_h(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.l_fault(l_fault),.l_valid(l_valid),.o_we(we),.o_any(any),.o_bank(bank),
    .o_row(row),.o_data(data),.fault(fault));
  genvar c;
  for(c=0;c<NC;c=c+1) begin:g_c
    localparam integer CAP=DICT_CAP[32*c+:32];
    initial if(CAP>13) $fatal(1,"pslice_c5: column dictionary over the L leaf (13 banks)");
    // MUT 1: column MUT_COL one start edge late (phase); MUT 3: that column's final dictionary mux on the live hit
    // CPIN/RRLY/FADV = the S/L leaf masters' values
    ot_hbm_su_programme_pgcol #(.DB((CAP<=3)?3:13),.CFGR((CAP<=3)?1:2),.PMUT(MUT==1 && c==MUT_COL),
      .CPIN(MUT!=5),.RRLY(MUT!=4),.FADV(2),.NCX((CAP>3)?NCX:0),
      .MUT((MUT==3 && c==MUT_COL)?1:0)) u_c(
      .clk(clk),.rst_n(rst_n),.cfg_we(we[c]),.cfg_any(any),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),
      .start(start),.length(length),.busy(l_busy[c]),.valid(l_valid[c]),.done(l_done[c]),.fault(l_fault[c]),
      .edge_index(l_edge[16*c+:16]),.command(cmd[256*c+:256]));
  end
  assign busy=l_busy[0]; assign valid=l_valid[0]; assign done=l_done[0]; assign edge_index=l_edge[15:0];
  assign command=cmd[SB-1:0];
endmodule

// =====================================================================================================================
// HBMb/IDXSU-PS15 2026-10-21 NCX (native-census successor of the PIPE 2 packed leaf producer; opt-in, pgcol NCX 1 only;
// NCX 0 = every module above unchanged).  The closed pgcol_l r5 RTL refuses the mapped native census (limit 32 loads,
// ep9 hbm_su_pgcol_l_r6a-20261021-191331: max 257, 76 drivers): mem_r4 select copies sl drive 256/RS x OG mux pins
// (129-257), hit copies h2 64, the packed word select ea 257/129, the command valid copies vd_c 64-98, the dictionary
// read enable vi_c 61 (+ its decode nets 33-52) and the producer reset 34.  Cycle-identical restructure:
//   * ot_hbm_su_programme_mem_r5 = mem_r4 GRP 0 with ONE-HOT select registers per (output register, RS slice) (each
//     bit drives 256/RS AND pins) and the read address / read enable taken from NA KEPT COPIES of their source
//     registers (each copy serves its share of the slots and macros);
//   * ot_hbm_su_programme_nc = ot_hbm_su_programme PIPE 2 packed (one column) with kept copies of pc/issue (index
//     address/enable), of the registered index word ixw (dictionary address) and of its valid vi, one ea copy per
//     index-word bit, and NRX equal-age reset inputs (pgcol's ot_rst_relay regions) spread over the reset flops.
// Every copy is loaded with exactly the value of its master on the same edge, so busy/valid/done/fault/edge_index/
// command are cycle-identical to ot_hbm_su_programme #(PIPE 2) (benches: pgcol_run.sh NCX=1, flat14 == pslice_c5).
module ot_hbm_su_programme_mem_r5 #(
  parameter integer BANKS=1, OG=2, RS=16, NA=4, NAA=NA, MUT=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic [NA-1:0] ren_c, input logic [16*NAA-1:0] addr_c,
  input logic [BANKS-1:0] w_ce, input logic [7*BANKS-1:0] w_row, input logic [256*BANKS-1:0] w_data,
  output logic [255:0] data);
  localparam integer LOG=(OG<=1)?0:$clog2(OG);
  localparam integer NOG=(BANKS+OG-1)/OG;
  localparam integer SW=256/RS;
`ifndef SYNTHESIS
  initial if((1<<LOG)!=OG || SW*RS!=256 || BANKS<1 || NA<1) $fatal(1,"mem_r5: OG power of two, RS divides 256");
`endif
  wire [256*BANKS-1:0] q;
  logic [255:0] og_q [0:NOG-1];
  (* keep *) logic [RS-1:0] h1 [0:NOG-1];
  (* keep *) logic [RS-1:0] h2 [0:NOG-1];
  genvar o, r, bank;
  generate for(o=0;o<NOG;o=o+1) begin:og
    localparam integer NB=((o+1)*OG<=BANKS)?OG:(BANKS-o*OG);
    for(r=0;r<RS;r=r+1) begin:rs
      localparam integer K=((o*RS+r)*NA)/(NOG*RS);
      localparam integer KA=((o*RS+r)*NAA)/(NOG*RS);
      wire ren_k=ren_c[K];
      wire [8:0] ba=addr_c[16*KA+7+:9];
      if(LOG>0) begin:lsel
        (* keep *) logic [NB-1:0] oh;
        integer b;
        always_ff @(posedge clk) if(ren_k) for(b=0;b<NB;b=b+1) oh[b] <= (ba[LOG-1:0]==b[LOG-1:0]);
        logic [SW-1:0] m;
        integer bb;
        always_comb begin
          m='0;
          for(bb=0;bb<NB;bb=bb+1) m=m | (q[256*(o*OG+bb)+SW*r+:SW] & {SW{oh[bb]}});
        end
        always_ff @(posedge clk) og_q[o][SW*r+:SW] <= m;
      end else begin:nsel
        always_ff @(posedge clk) og_q[o][SW*r+:SW] <= q[256*o+SW*r+:SW];
      end
      always_ff @(posedge clk) if(ren_k) h1[o][r] <= (ba>>LOG)==o && ba<BANKS;
      always_ff @(posedge clk) h2[o][r] <= h1[o][r];
    end
  end endgenerate
  integer mo, rr;
  always_comb begin
    data='0;
    for(mo=0;mo<NOG;mo=mo+1) for(rr=0;rr<RS;rr=rr+1)
      data[SW*rr+:SW]=data[SW*rr+:SW] | (og_q[mo][SW*rr+:SW] & {SW{(MUT==1)?h1[mo][rr]:h2[mo][rr]}});
  end
  generate for(bank=0;bank<BANKS;bank=bank+1) begin:g
    localparam integer KB=(bank*NA)/BANKS;
    localparam integer KBA=(bank*NAA)/BANKS;
    wire [255:0] bank_q;
    assign q[256*bank+:256]=bank_q;
    ot_sram_1r1w_128x256_m1_r2c2 mem(
      .clk(clk_macro[bank]), .r_ce_in(ren_c[KB] && addr_c[16*KBA+7+:9]==bank), .r_addr_in(addr_c[16*KBA+:7]),
      .rd_out(bank_q), .w_ce_in(w_ce[bank]), .w_addr_in(w_row[7*bank+:7]),
      .wd_in(w_data[256*bank+:256]), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end endgenerate
endmodule

module ot_hbm_su_programme_nc #(
  parameter integer EDGES=7111, INDEX_PACK=16, DICT_BANKS=13,
  parameter integer INDEX_BANKS=(EDGES+128*INDEX_PACK-1)/(128*INDEX_PACK),
  parameter integer MACROS=INDEX_BANKS+DICT_BANKS,
  parameter integer MUT=0, IOG=4, DOG=2, RS=16, CFGR=4, FADV=0,
  parameter integer NAI=4, NAD=16, NRX=8
)(input logic clk, input logic [NRX-1:0] rst_x, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault,
  output logic [15:0] edge_index,
  output logic [255:0] command);
  localparam integer TOTAL_BANKS=INDEX_BANKS+DICT_BANKS;
  localparam integer INDEX_SHIFT=$clog2(INDEX_PACK);
  localparam integer XP=4;   // PIPE 2 packed: index +3 (og reg, word select, indices) + dictionary +1
`ifndef SYNTHESIS
  initial if(MACROS!=TOTAL_BANKS || INDEX_PACK<2 || INDEX_PACK>16 || NRX!=8 || FADV<0 || FADV>XP-1)
    $fatal(1,"programme_nc: packed one-column PIPE 2 leaf only, NRX 8");
`endif
  // reset groups (equal-age copies): 0 main control, 1 valid chain + index copies, 2 dictionary read-enable copies,
  // 3 command valid copies, 4 per-bank write enables
  wire rst_n=rst_x[0];
  logic issue,v1,v2;
  logic [15:0] pc, count, e1,e2;
  logic busy_i, fault_i;
  wire [255:0] index_rows;
  logic nb;
  logic c_v; logic [15:0] c_e;
  always_comb begin
    nb=busy_i;
    if(start && !(busy_i || length==0 || length>EDGES || cfg_we)) nb=1;
    if(c_v && c_e==count-1) nb=0;
  end
  wire [255:0] templates;
  wire write_enable=cfg_we && !busy_i && cfg_bank<TOTAL_BANKS;
  wire accept=start && !(busy_i || length==0 || length>EDGES || cfg_we);
  wire last=(pc==count-1);
  // kept copies of the index read enable issue: NAI for the index memory slots + one for the pc increment + one for
  // the e1 capture (the index address itself is the one pc register: few loads).  idle_start (start while not busy)
  // loads count: equivalent to loading it on accept, because count is only read while busy_i (a rejected start while
  // idle leaves no run behind it, the next accepted start reloads it).
  (* keep *) logic [NAI+1:0] issue_k;
  wire idle_start=start && !busy_i;
  genvar k;
  generate for(k=0;k<NAI+2;k=k+1) begin:g_ik
    always_ff @(posedge clk) begin
      if(!rst_x[1]) issue_k[k]<=0;
      else begin
        if(accept) issue_k[k]<=1;
        if(issue_k[k] && last) issue_k[k]<=0;
      end
    end
  end endgenerate
  wire [15:0] ia_c=pc >> INDEX_SHIFT;
  // configuration write port (as ot_hbm_su_programme PIPE 2)
  logic [TOTAL_BANKS-1:0] wce_r;
  (* keep *) logic [6:0] wrow_r [0:CFGR-1];
  (* keep *) logic [255:0] wdat_r [0:CFGR-1];
  logic [6:0] row_late;
  always_ff @(posedge clk) row_late <= cfg_row;
  integer wb, wk;
  always_ff @(posedge clk) begin
    if(!rst_x[4]) wce_r<='0;
    else for(wb=0;wb<TOTAL_BANKS;wb=wb+1) wce_r[wb] <= write_enable && cfg_bank==wb;
    for(wk=0;wk<CFGR;wk=wk+1) begin
      wrow_r[wk] <= (MUT==3 && wk==CFGR-1) ? row_late : cfg_row;
      wdat_r[wk] <= cfg_data;
    end
  end
  wire [7*TOTAL_BANKS-1:0] w_row; wire [256*TOTAL_BANKS-1:0] w_data;
  genvar wbg;
  generate for(wbg=0;wbg<TOTAL_BANKS;wbg=wbg+1) begin:wmap
    assign w_row[7*wbg+:7]=wrow_r[(wbg*CFGR)/TOTAL_BANKS];
    assign w_data[256*wbg+:256]=wdat_r[(wbg*CFGR)/TOTAL_BANKS];
  end endgenerate
  ot_hbm_su_programme_mem_r5 #(.BANKS(INDEX_BANKS),.OG(IOG),.RS(RS),.NA(NAI),.NAA(1),.MUT(MUT==1)) u_ix(
    .clk(clk),.clk_macro(clk_macro[0+:INDEX_BANKS]),.ren_c(issue_k[NAI-1:0]),.addr_c(ia_c),
    .w_ce(wce_r[0+:INDEX_BANKS]),.w_row(w_row[0+:7*INDEX_BANKS]),.w_data(w_data[0+:256*INDEX_BANKS]),.data(index_rows));
  // index path: v1 -> va (og registers) -> vb (word select ixw) -> vi (dictionary read) ; vd = command stage
  logic va, vb, vi, vd; logic [15:0] ea, eb, ei, ed;
  logic [15:0] ixw;
  (* keep *) logic [INDEX_SHIFT-1:0] ea_k [0:15];
  (* keep *) logic [15:0] ix_k [0:NAD-1];
  (* keep *) logic [NAD-1:0] vi_k;
  (* keep *) logic [RS-1:0] vd_c;
  (* keep *) logic [1:0] vd_e; // equal-age copies, each drives eight edge bits
  (* keep *) logic vd_done;
  (* keep *) logic [1:0] vi_e; // independent equal-age capture enables for eight-bit e2 halves
  genvar j;
  generate for(j=0;j<16;j=j+1) begin:g_ea
    always_ff @(posedge clk) begin ea_k[j]<=e1[INDEX_SHIFT-1:0]; ixw[j]<=index_rows[16*ea_k[j]+j]; end
  end endgenerate
  integer kd;
  always_ff @(posedge clk) for(kd=0;kd<NAD;kd=kd+1) ix_k[kd]<=ixw;
  always_ff @(posedge clk) begin ea<=e1; eb<=ea; ei<=eb; ed<=e2; end
  always_ff @(posedge clk) if(!rst_x[1]) begin va<=0; vb<=0; vi<=0; vd<=0; vd_e<='0; vd_done<=0; end
    else begin va<=v1; vb<=va; vi<=vb; vd<=v2; vd_e<={2{v2}}; vd_done<=v2; end
  always_ff @(posedge clk) if(!rst_x[5]) vi_e<='0; else vi_e<={2{vb}};
  always_ff @(posedge clk) if(!rst_x[2]) vi_k<='0; else vi_k<={NAD{vb}};
  always_ff @(posedge clk) if(!rst_x[3]) vd_c<='0; else vd_c<={RS{v2}};
  wire [16*NAD-1:0] da_c;
  generate for(k=0;k<NAD;k=k+1) begin:g_dk
    assign da_c[16*k+:16]=ix_k[k];
  end endgenerate
  ot_hbm_su_programme_mem_r5 #(.BANKS(DICT_BANKS),.OG(DOG),.RS(RS),.NA(NAD),.MUT(MUT==1)) u_dt(
    .clk(clk),.clk_macro(clk_macro[INDEX_BANKS+:DICT_BANKS]),.ren_c(vi_k),.addr_c(da_c),
    .w_ce(wce_r[INDEX_BANKS+:DICT_BANKS]),.w_row(w_row[7*INDEX_BANKS+:7*DICT_BANKS]),
    .w_data(w_data[256*INDEX_BANKS+:256*DICT_BANKS]),.data(templates));
  wire d_ren=vi; wire [15:0] d_e=ei;
  assign c_v=vd; assign c_e=ed;
  logic [XP-1:0] busy_d, fault_d; logic busy_q;
  always_ff @(posedge clk) if(!rst_x[1]) begin busy_d<='0; fault_d<='0; busy_q<=0; end
    else begin
      busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i};
      busy_q<=(MUT==2)?nb:(nb && busy_d[XP-2]);
    end
  assign busy=busy_q;
  assign fault=fault_d[XP-1-FADV];
  always_ff @(posedge clk) begin
    if(!rst_n) begin
      busy_i<=0; issue<=0; valid<=0; done<=0; fault_i<=0;
      v1<=0; v2<=0;
    end else begin
      valid<=c_v; v1<=issue; v2<=d_ren; done<=0;
      if(cfg_we && (busy_i || cfg_bank>=TOTAL_BANKS)) fault_i<=1;
      busy_i<=nb;
      if(start) begin
        if(busy_i || length==0 || length>EDGES || cfg_we) fault_i<=1;
        else issue<=1;
      end
      if(issue && last) issue<=0;
      if(vd_done && c_e==count-1) done<=1;
    end
  end
  // Replicated source enables and equal-age reset branches keep each mapped capture cone below 32 loads.
  generate for(k=0;k<2;k=k+1) begin:g_capture_halves
    always_ff @(posedge clk) begin
      if(rst_x[6+k] && vi_e[k]) e2[8*k+:8]<=d_e[8*k+:8];
      if(!rst_x[6+k]) edge_index[8*k+:8]<=0;
      else if(vd_e[k]) edge_index[8*k+:8]<=c_e[8*k+:8];
    end
  end endgenerate
  // pc / e1 / count (not reset, as PIPE 2): pc zeroed on accept and stepped on its own issue copy, e1 captured on its
  // own copy, count loaded on idle_start (see above); the reset only holds them, exactly as the shared block did
  always_ff @(posedge clk) if(rst_n) begin
    if(idle_start) count<=length;
    if(accept) pc<=0;
    if(issue_k[NAI] && !last) pc<=pc+1;
    if(issue_k[NAI+1]) e1<=pc;
  end
  genvar cb;
  generate for(cb=0;cb<256;cb=cb+1) begin:cbit
    always_ff @(posedge clk) command[cb] <= vd_c[cb/(256/RS)] & templates[cb];
  end endgenerate
endmodule
