`timescale 1ns/1ps
// Host-configured, fixed-cycle programme producer. Each logical memory is made
// exclusively from target 128x256 SRAM macros. No simulation-only DUT storage.
// OREG (HBM-SU 2026-10-17, default 0 = unchanged): 1 = every macro pair {2p, 2p+1} has its own output register
// beside the pair (pair_q, captured on the edge after the read), and the bank mux runs one edge later from the pair
// registers (sel2 = the read's bank, registered with them). +1 edge from read to data; the macro clk->q path ends at
// a register within one macro pitch instead of crossing a 13..56-bank mux and the tile. MUT 1 (bench): the pair mux
// uses the current select_q instead of sel2 (stale-select bug: a read into another pair one edge later corrupts data).
module ot_hbm_su_programme_mem #(
  parameter integer BANKS=1, BASE=0, OREG=0, MUT=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic ren, input logic [15:0] addr,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data, output logic [255:0] data);
  wire [256*BANKS-1:0] q;
  logic [8:0] select_q;
  always_ff @(posedge clk) if (ren) select_q <= addr[15:7];
  integer mux_bank;
  generate if (OREG == 0) begin:g_direct
    always_comb begin
      data='0;
      for(mux_bank=0;mux_bank<BANKS;mux_bank=mux_bank+1) if(select_q==mux_bank) data=q[256*mux_bank+:256];
    end
  end else begin:g_pairreg
    localparam integer PAIRS=(BANKS+1)/2;
    logic [255:0] pair_q [0:PAIRS-1];
    logic [8:0] sel2;
    always_ff @(posedge clk) sel2 <= select_q;
    for (genvar p=0;p<PAIRS;p=p+1) begin:pr
      if (2*p+1 < BANKS) begin:two
        always_ff @(posedge clk) pair_q[p] <= select_q[0] ? q[256*(2*p+1)+:256] : q[256*(2*p)+:256];
      end else begin:one
        always_ff @(posedge clk) pair_q[p] <= q[256*(2*p)+:256];
      end
    end
    wire [8:0] psel = (MUT==1) ? select_q : sel2;
    integer mp;
    always_comb begin
      data='0;
      for(mp=0;mp<PAIRS;mp=mp+1) if(psel[8:1]==mp[7:0]) data=pair_q[mp];
    end
  end endgenerate
  genvar bank;
  generate for(bank=0;bank<BANKS;bank=bank+1) begin:g
    wire [255:0] bank_q;
    assign q[256*bank+:256]=bank_q;
    ot_sram_1r1w_128x256_m1_r2c2 mem(
      .clk(clk_macro[bank]), .r_ce_in(ren && addr[15:7]==bank), .r_addr_in(addr[6:0]), .rd_out(bank_q),
      .w_ce_in(cfg_we && cfg_bank==BASE+bank), .w_addr_in(cfg_row),
      .wd_in(cfg_data), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end endgenerate
endmodule

// ot_hbm_su_programme_mem_r4 (HBM-SU r4 2026-10-17, used only by ot_hbm_su_programme PIPE 2). Same macros, same read
// semantics as ot_hbm_su_programme_mem OREG 1 (data of the bank addressed at a read, 0 for an out-of-range bank), with
// the r2 gate's fan-out nets removed structurally:
//   * OG banks share one output register og_q (OG:1 mux beside the OG-macro stack). Its low-select sl and its one-hot
//     hit h1/h2 are REPLICATED per output register and per RS bit slice ((* keep *) copies, each driving 256/RS bits):
//     the r2 select_q[0] net (8,961 loads) becomes RS x NOG nets of <= 256/RS loads.
//   * the bank mux is an AND-OR over one-hot registered hits (neutral: exactly one or zero hits).
//   * GRP > 0: one more registered funnel stage, GRP output registers per group register gq (+1 edge); the final mux is
//     ceil(NOG/GRP):1 (the r2 28-pair index funnel psel->indices_r, -408 ps).
//   * write port: per-bank write enable, row and data come registered from outside (the producer's replicated config
//     copies), so no c_bank compare or c_data net spans the tile.
// Latency read -> data: 1 edge (GRP 0, as OREG 1) or 2 edges (GRP > 0). MUT 1 (bench): final mux on the live hit h1
// instead of its registered copy (stale-select bug).
module ot_hbm_su_programme_mem_r4 #(
  parameter integer BANKS=1, OG=2, GRP=0, RS=4, MUT=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic ren, input logic [15:0] addr,
  input logic [BANKS-1:0] w_ce, input logic [7*BANKS-1:0] w_row, input logic [256*BANKS-1:0] w_data,
  output logic [255:0] data);
  localparam integer LOG=(OG<=1)?0:$clog2(OG);
  localparam integer NOG=(BANKS+OG-1)/OG;
  localparam integer SW=256/RS;
  localparam integer NG=(GRP>0)?(NOG+GRP-1)/GRP:NOG;
`ifndef SYNTHESIS
  initial if((1<<LOG)!=OG || SW*RS!=256 || BANKS<1) $fatal(1,"mem_r4: OG power of two, RS divides 256");
`endif
  wire [256*BANKS-1:0] q;
  wire [8:0] bank_a = addr[15:7];
  logic [255:0] og_q [0:NOG-1];
  (* keep *) logic [RS-1:0] h1 [0:NOG-1];
  (* keep *) logic [RS-1:0] h2 [0:NOG-1];
  genvar o, r, bank, gg;
  generate for(o=0;o<NOG;o=o+1) begin:og
    localparam integer NB=((o+1)*OG<=BANKS)?OG:(BANKS-o*OG);
    if(LOG>0) begin:lsel
      (* keep *) logic [LOG-1:0] sl [0:RS-1];
      for(r=0;r<RS;r=r+1) begin:rs
        always_ff @(posedge clk) if(ren) sl[r] <= bank_a[LOG-1:0];
        logic [SW-1:0] m;
        integer b;
        always_comb begin
          m='0;
          for(b=0;b<NB;b=b+1) if(sl[r]==b[LOG-1:0]) m=q[256*(o*OG+b)+SW*r+:SW];
        end
        always_ff @(posedge clk) og_q[o][SW*r+:SW] <= m;
      end
    end else begin:nsel
      always_ff @(posedge clk) og_q[o] <= q[256*o+:256];
    end
    for(r=0;r<RS;r=r+1) begin:hr
      always_ff @(posedge clk) if(ren) h1[o][r] <= (bank_a>>LOG)==o && bank_a<BANKS;
      always_ff @(posedge clk) h2[o][r] <= h1[o][r];
    end
  end endgenerate
  // final AND-OR (GRP 0: over og_q with h2; GRP > 0: registered group stage, then over gq with h3)
  generate if(GRP==0) begin:g_flat
    integer mo, rr;
    always_comb begin
      data='0;
      for(mo=0;mo<NOG;mo=mo+1) for(rr=0;rr<RS;rr=rr+1)
        data[SW*rr+:SW]=data[SW*rr+:SW] | (og_q[mo][SW*rr+:SW] & {SW{(MUT==1)?h1[mo][rr]:h2[mo][rr]}});
    end
  end else begin:g_grp
    logic [255:0] gq [0:NG-1];
    (* keep *) logic [RS-1:0] h3 [0:NG-1];
    for(gg=0;gg<NG;gg=gg+1) begin:gr
      for(r=0;r<RS;r=r+1) begin:rs
        logic [SW-1:0] m; logic hit;
        integer mo;
        always_comb begin
          m='0; hit=0;
          for(mo=gg*GRP;mo<(gg+1)*GRP && mo<NOG;mo=mo+1) begin
            m=m | (og_q[mo][SW*r+:SW] & {SW{(MUT==1)?h1[mo][r]:h2[mo][r]}});
            hit=hit | h2[mo][r];
          end
        end
        always_ff @(posedge clk) begin gq[gg][SW*r+:SW] <= m; h3[gg][r] <= hit; end
      end
    end
    integer mg, rr;
    always_comb begin
      data='0;
      for(mg=0;mg<NG;mg=mg+1) for(rr=0;rr<RS;rr=rr+1)
        data[SW*rr+:SW]=data[SW*rr+:SW] | (gq[mg][SW*rr+:SW] & {SW{h3[mg][rr]}});
    end
  end endgenerate
  generate for(bank=0;bank<BANKS;bank=bank+1) begin:g
    wire [255:0] bank_q;
    assign q[256*bank+:256]=bank_q;
    ot_sram_1r1w_128x256_m1_r2c2 mem(
      .clk(clk_macro[bank]), .r_ce_in(ren && bank_a==bank), .r_addr_in(addr[6:0]), .rd_out(bank_q),
      .w_ce_in(w_ce[bank]), .w_addr_in(w_row[7*bank+:7]),
      .wd_in(w_data[256*bank+:256]), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end endgenerate
endmodule

// PIPE (HBM-SU 2026-10-17, default 0 = unchanged): 1 = the pipelined producer for the hard per-quarter master.
//   index read -> pair register (OREG) -> 1-of-N pair mux -> index register indices_r -> dictionary read -> pair
//   register (OREG) -> 1-of-N pair mux -> command register. Index path +2 edges, dictionary path +1 edge: command 0
//   is presented 3 edges later than PIPE 0 (start sampled at S -> consumer samples command 0 at S+7). The compiler
//   issues start 3 edges earlier (the same start-advance mechanism as the partition DEPTH), so every command bit
//   reaches its consumer on the same edge as from the PIPE 0 producer.
//   Output busy (a register) rises 3 edges after the internal busy and falls with it, so busy/valid/done/
//   edge_index/command are cycle-identical to a PIPE 0 producer started 3 edges later; fault is reported 3 edges
//   later (sticky diagnostic). The command and internal data registers carry no reset (command clears the edge after
//   reset reaches the valid chain; rst_n fans out to the ~30 control flops only).
//   MUT 1 (bench): pair-mux stale select (see the mem module); MUT 2: output busy not rise-delayed.
// PIPE 2 (HBM-SU r4 2026-10-17, opt-in): the r2 gate's (hbm_su_pslice_r2_1017, 9272b2f43) fan-out classes removed in
// RTL. Memories are ot_hbm_su_programme_mem_r4: index IOG banks per output register + IGRP output registers per
// registered funnel group (+1 edge), dictionary DOG banks per output register, select/hit registers replicated per
// output register x RS bit slices. Configuration: the accepted write is registered once more as per-bank write
// enables + CFGR replicated row/data copies (bank b uses copy b*CFGR/MACROS), so cfg reaches each macro from a copy in
// its own region (+1 edge from acceptance to the macro write; a write accepted on the edge start is accepted would race
// the first index read, so that coincidence sets the sticky fault -- the host configures while idle). Dictionary read
// enables and command valids are replicated per column (x RS slices). Index path +3 edges, dictionary +1: XP 4 (start
// advance DEPTH+4). busy/valid/done/edge_index/command cycle-identical to PIPE 0 started 4 edges later. MUT 1: final
// bank mux on the live hit; MUT 2: busy not rise-delayed; MUT 3: the last configuration copy's row one edge late.
module ot_hbm_su_programme #(
  parameter integer LINE_BITS=9688, EDGES=7111,
  parameter integer COLS=(LINE_BITS+255)/256,
  parameter integer INDEX_GROUPS=(COLS+15)/16,
  parameter integer INDEX_PACK=1,
  parameter integer INDEX_BANKS=(EDGES+128*INDEX_PACK-1)/(128*INDEX_PACK),
  // Packed little-column vector keeps the production source legal in Yosys.
  parameter [32*COLS-1:0] DICT_BANKS={COLS{32'd1}},
  parameter integer MACROS=INDEX_GROUPS*INDEX_BANKS+COLS,
  parameter integer PIPE=0, MUT=0,
  parameter integer IOG=4, IGRP=4, DOG=2, RS=4, CFGR=4,  // PIPE 2 only
  parameter integer FADV=0                               // PIPE 2: fault reported FADV edges earlier (pgcol leaf: 1)
)(input logic clk, rst_n, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault,
  output logic [15:0] edge_index,
  output logic [LINE_BITS-1:0] command);
  function automatic integer dict_base(input integer c);
    integer v,k;
    begin
      v=INDEX_GROUPS*INDEX_BANKS;
      for(k=0;k<c;k=k+1) v=v+DICT_BANKS[32*k+:32];
      dict_base=v;
    end
  endfunction
  localparam integer TOTAL_BANKS=dict_base(COLS);
  // PIPE 2 third index stage: the registered funnel group (unpacked, IGRP > 0) or, packed (pgcol leaf), the registered
  // 16:1 word select of the packed index row
  localparam integer XSTG=(IGRP>0 || INDEX_PACK>1)?1:0;
  localparam integer XI=(PIPE==2)?(2+XSTG):(PIPE!=0)?2:0; // extra index-path edges (pair/og reg [+ group] + indices_r)
  localparam integer XD=(PIPE!=0)?1:0;          // extra dictionary-path edges (pair register)
  localparam integer XP=XI+XD;
`ifndef SYNTHESIS
  initial if(MACROS!=TOTAL_BANKS) $fatal(1,"programme MACROS capacity mismatch");
  initial if(PIPE==1 && INDEX_PACK!=1) $fatal(1,"programme PIPE 1 requires unpacked indices");
  initial if(FADV<0 || (PIPE!=2 && FADV!=0) || FADV>XP-1) $fatal(1,"programme FADV only with PIPE 2, < XP");
`endif
  logic issue,v1,v2;
  logic [15:0] pc, count, e1,e2;
  logic busy_i, fault_i;
  wire [INDEX_GROUPS*256-1:0] index_rows;
  wire [INDEX_GROUPS*256-1:0] indices;
  localparam integer INDEX_SHIFT=$clog2(INDEX_PACK);
  initial if(INDEX_PACK<1 || INDEX_PACK>16 || (INDEX_PACK & (INDEX_PACK-1))!=0 || (INDEX_PACK!=1 && COLS!=1))
    $fatal(1,"packed programme indices require power-of-two pack<=16 and exactly one dictionary column");
  generate if(INDEX_PACK==1)begin:g_unpacked_index
    assign indices=index_rows;
  end else begin:g_packed_index
    logic [INDEX_SHIFT-1:0] word_slot;
    always_ff @(posedge clk)if(issue)word_slot<=pc[INDEX_SHIFT-1:0];
    assign indices={240'd0,index_rows[16*word_slot+:16]};
  end endgenerate
  // next internal busy (the busy_i register's D; PIPE 1 also forms the registered output busy from it)
  logic nb;
  always_comb begin
    nb=busy_i;
    if(start && !(busy_i || length==0 || length>EDGES || (PIPE==2 && cfg_we))) nb=1;
    if(c_v && c_e==count-1) nb=0;
  end
  // dictionary read issue (d_ren), its edge number and address: PIPE 0 = v1/e1/indices (unchanged)
  logic d_ren; logic [15:0] d_e; logic [INDEX_GROUPS*256-1:0] d_addr;
  logic [COLS-1:0] d_ren_c;                     // PIPE 2: per-column copies of d_ren (dictionary read enables)
  logic [COLS*RS-1:0] c_v_c;                    // PIPE 2: per-column x slice copies of c_v (command valids)
  // command stage valid/edge/data: PIPE 0 = v2/e2/templates
  logic c_v; logic [15:0] c_e;
  wire [COLS*256-1:0] templates;
  wire write_enable=cfg_we && !busy_i && cfg_bank<TOTAL_BANKS;
  genvar g,c;
  generate for(g=0;g<((PIPE==2)?0:INDEX_GROUPS);g=g+1) begin:ix
    ot_hbm_su_programme_mem #(.BANKS(INDEX_BANKS),.BASE(g*INDEX_BANKS),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(index_rows[g*256+:256]));
  end
  for(c=0;c<((PIPE==2)?0:COLS);c=c+1) begin:dt
    ot_hbm_su_programme_mem #(.BANKS(DICT_BANKS[32*c+:32]),.BASE(dict_base(c)),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[32*c+:32]]),.ren(d_ren),.addr(d_addr[c*16+:16]),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(templates[c*256+:256]));
  end
  if(PIPE==2) begin:g_m4
    // replicated configuration write port: per-bank enable, CFGR row/data copies (registered after acceptance)
    logic [TOTAL_BANKS-1:0] wce_r;
    (* keep *) logic [6:0] wrow_r [0:CFGR-1];
    (* keep *) logic [255:0] wdat_r [0:CFGR-1];
    logic [6:0] row_late;
    always_ff @(posedge clk) row_late <= cfg_row;
    integer wb, wk;
    always_ff @(posedge clk) begin
      if(!rst_n) wce_r<='0;
      else for(wb=0;wb<TOTAL_BANKS;wb=wb+1) wce_r[wb] <= write_enable && cfg_bank==wb;
      for(wk=0;wk<CFGR;wk=wk+1) begin
        wrow_r[wk] <= (MUT==3 && wk==CFGR-1) ? row_late : cfg_row;
        wdat_r[wk] <= cfg_data;
      end
    end
    wire [7*TOTAL_BANKS-1:0] w_row; wire [256*TOTAL_BANKS-1:0] w_data;
    for(genvar wbg=0;wbg<TOTAL_BANKS;wbg=wbg+1) begin:wmap
      assign w_row[7*wbg+:7]=wrow_r[(wbg*CFGR)/TOTAL_BANKS];
      assign w_data[256*wbg+:256]=wdat_r[(wbg*CFGR)/TOTAL_BANKS];
    end
    for(g=0;g<INDEX_GROUPS;g=g+1) begin:ix
      ot_hbm_su_programme_mem_r4 #(.BANKS(INDEX_BANKS),.OG(IOG),.GRP((INDEX_PACK>1)?0:IGRP),.RS(RS),.MUT(MUT==1)) mem(
        .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),
        .w_ce(wce_r[g*INDEX_BANKS+:INDEX_BANKS]),.w_row(w_row[7*g*INDEX_BANKS+:7*INDEX_BANKS]),
        .w_data(w_data[256*g*INDEX_BANKS+:256*INDEX_BANKS]),.data(index_rows[g*256+:256]));
    end
    for(c=0;c<COLS;c=c+1) begin:dt
      ot_hbm_su_programme_mem_r4 #(.BANKS(DICT_BANKS[32*c+:32]),.OG(DOG),.GRP(0),.RS(RS),.MUT(MUT==1)) mem(
        .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[32*c+:32]]),.ren(d_ren_c[c]),.addr(d_addr[c*16+:16]),
        .w_ce(wce_r[dict_base(c)+:DICT_BANKS[32*c+:32]]),.w_row(w_row[7*dict_base(c)+:7*DICT_BANKS[32*c+:32]]),
        .w_data(w_data[256*dict_base(c)+:256*DICT_BANKS[32*c+:32]]),.data(templates[c*256+:256]));
    end
  end
  if(PIPE==0) begin:g_p0
    assign d_ren=v1; assign d_e=e1; assign d_addr=indices;
    assign c_v=v2; assign c_e=e2;
    assign busy=busy_i; assign fault=fault_i;
  end else if(PIPE==2) begin:g_p2
    // index path: v1 (index data at the og registers next edge) -> va -> vb (group registers) -> vi (indices_r) = d_ren
    logic va, vb, vi, vd; logic [15:0] ea, eb, ei, ed;
    logic [INDEX_GROUPS*256-1:0] indices_r;
    (* keep *) logic [COLS-1:0] vi_c;
    (* keep *) logic [COLS*RS-1:0] vd_c;
    if(INDEX_PACK>1) begin:g_pk
      // packed (one column): index_rows is the og register AND-OR (aligned with va/ea); the 16-bit word of edge ea is
      // selected and registered (aligned with vb/eb), then indices_r (vi/ei) as the unpacked path
      logic [15:0] ixw;
      always_ff @(posedge clk) begin ixw<=index_rows[16*ea[INDEX_SHIFT-1:0]+:16]; indices_r<={{(INDEX_GROUPS*256-16){1'b0}},ixw}; end
    end else begin:g_upk
      always_ff @(posedge clk) indices_r<=indices;
    end
    always_ff @(posedge clk) begin
      ea<=e1; ei<=(XSTG>0)?eb:ea; eb<=ea; ed<=e2;
    end
    always_ff @(posedge clk) if(!rst_n) begin va<=0; vb<=0; vi<=0; vd<=0; vi_c<='0; vd_c<='0; end
      else begin
        va<=v1; vb<=va; vi<=(XSTG>0)?vb:va; vd<=v2;
        vi_c<={COLS{(XSTG>0)?vb:va}}; vd_c<={(COLS*RS){v2}};
      end
    assign d_ren=vi; assign d_e=ei; assign d_addr=indices_r; assign d_ren_c=vi_c;
    assign c_v=vd; assign c_e=ed; assign c_v_c=vd_c;
    logic [XP-1:0] busy_d, fault_d; logic busy_q;
    always_ff @(posedge clk) if(!rst_n) begin busy_d<='0; fault_d<='0; busy_q<=0; end
      else begin
        busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i};
        busy_q<=(MUT==2)?nb:(nb && busy_d[XP-2]);
      end
    assign busy=busy_q;
    assign fault=fault_d[XP-1-FADV];
  end else begin:g_p1
    // index path: v1 (index macro data at its pair registers next edge) -> va -> vi (indices_r valid) = d_ren
    logic va, vi, vd; logic [15:0] ea, ei, ed;
    logic [INDEX_GROUPS*256-1:0] indices_r;
    always_ff @(posedge clk) begin
      indices_r<=indices; ea<=e1; ei<=ea; ed<=e2;
    end
    always_ff @(posedge clk) if(!rst_n) begin va<=0; vi<=0; vd<=0; end else begin va<=v1; vi<=va; vd<=v2; end
    assign d_ren=vi; assign d_e=ei; assign d_addr=indices_r;
    assign c_v=vd; assign c_e=ed;
    // outputs cycle-identical to a PIPE 0 producer started XP edges later, all register outputs:
    // busy(t+1) = busy_i(t+1) && busy_i(t+1-XP) = nb(t) && busy_d[XP-2](t)
    logic [XP-1:0] busy_d, fault_d; logic busy_q;
    always_ff @(posedge clk) if(!rst_n) begin busy_d<='0; fault_d<='0; busy_q<=0; end
      else begin
        busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i};
        busy_q<=(MUT==2)?nb:(nb && busy_d[XP-2]);
      end
    assign busy=busy_q;
    assign fault=fault_d[XP-1];
  end endgenerate
  // Start sampled at S; first command/valid presented after S+3 (PIPE 1: S+6) and sampled
  // by a downstream sequential consumer at S+4 (PIPE 1: S+7). Subsequent lines every edge.
  always_ff @(posedge clk) begin
    if(!rst_n) begin
      busy_i<=0; issue<=0; valid<=0; done<=0; fault_i<=0;
      v1<=0; v2<=0; edge_index<=0;
      if(PIPE==0) begin pc<=0; count<=0; e1<=0; e2<=0; end
    end else begin
      valid<=c_v; v1<=issue; v2<=d_ren; done<=0;
      if(cfg_we && (busy_i || cfg_bank>=TOTAL_BANKS)) fault_i<=1;
      busy_i<=nb;
      if(start) begin
        if(busy_i || length==0 || length>EDGES || (PIPE==2 && cfg_we)) fault_i<=1;
        else begin issue<=1; pc<=0; count<=length; end
      end
      if(issue) begin
        e1<=pc;
        if(pc==count-1) issue<=0; else pc<=pc+1;
      end
      if(d_ren) e2<=d_e;
      if(c_v) begin
        edge_index<=c_e;
        if(c_e==count-1) done<=1;
      end
    end
  end
  // command register: PIPE 0 synchronous reset (unchanged); PIPE 1 no reset (clears the edge after the valid chain
  // resets)
  generate if(PIPE==0) begin:g_cmd0
    always_ff @(posedge clk) command <= (rst_n && c_v) ? templates[LINE_BITS-1:0] : '0;
  end else if(PIPE==1) begin:g_cmd1
    always_ff @(posedge clk) command <= c_v ? templates[LINE_BITS-1:0] : '0;
  end else begin:g_cmd2
    // per column x slice valid copy (each drives <= 256/RS command bits)
    for(genvar cb=0;cb<LINE_BITS;cb=cb+1) begin:cbit
      always_ff @(posedge clk) command[cb] <= c_v_c[(cb/256)*RS+(cb%256)/(256/RS)] & templates[cb];
    end
  end endgenerate
endmodule
