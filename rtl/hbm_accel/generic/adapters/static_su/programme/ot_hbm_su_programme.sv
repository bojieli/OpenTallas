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

// PIPE (HBM-SU 2026-10-17, default 0 = unchanged): 1 = the pipelined producer for the hard per-quarter master.
//   index read -> pair register (OREG) -> 1-of-N pair mux -> index register indices_r -> dictionary read -> pair
//   register (OREG) -> 1-of-N pair mux -> command register. Index path +2 edges, dictionary path +1 edge: command 0
//   is presented 3 edges later than PIPE 0 (start sampled at S -> consumer samples command 0 at S+7). The compiler
//   issues start 3 edges earlier (the same start-advance mechanism as the partition DEPTH), so every command bit
//   reaches its consumer on the same edge as from the PIPE 0 producer.
//   Output busy rises 3 edges after the internal busy (busy & busy delayed 3) and falls with it, so busy/valid/done/
//   edge_index/command are cycle-identical to a PIPE 0 producer started 3 edges later; fault is reported 3 edges
//   later (sticky diagnostic). The command and internal data registers carry no reset (command clears the edge after
//   reset reaches the valid chain; rst_n fans out to the ~30 control flops only).
//   MUT 1 (bench): pair-mux stale select (see the mem module); MUT 2: output busy not rise-delayed.
module ot_hbm_su_programme #(
  parameter integer LINE_BITS=9688, EDGES=7111,
  parameter integer COLS=(LINE_BITS+255)/256,
  parameter integer INDEX_GROUPS=(COLS+15)/16,
  parameter integer INDEX_PACK=1,
  parameter integer INDEX_BANKS=(EDGES+128*INDEX_PACK-1)/(128*INDEX_PACK),
  // Packed little-column vector keeps the production source legal in Yosys.
  parameter [32*COLS-1:0] DICT_BANKS={COLS{32'd1}},
  parameter integer MACROS=INDEX_GROUPS*INDEX_BANKS+COLS,
  parameter integer PIPE=0, MUT=0
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
  localparam integer XI=(PIPE!=0)?2:0;          // extra index-path edges (pair register + indices_r)
  localparam integer XD=(PIPE!=0)?1:0;          // extra dictionary-path edges (pair register)
  localparam integer XP=XI+XD;
  initial if(MACROS!=TOTAL_BANKS) $fatal(1,"programme MACROS capacity mismatch");
  initial if(PIPE!=0 && INDEX_PACK!=1) $fatal(1,"programme PIPE requires unpacked indices");
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
  // dictionary read issue (d_ren), its edge number and address: PIPE 0 = v1/e1/indices (unchanged)
  logic d_ren; logic [15:0] d_e; logic [INDEX_GROUPS*256-1:0] d_addr;
  // command stage valid/edge/data: PIPE 0 = v2/e2/templates
  logic c_v; logic [15:0] c_e;
  wire [COLS*256-1:0] templates;
  wire write_enable=cfg_we && !busy_i && cfg_bank<TOTAL_BANKS;
  genvar g,c;
  generate for(g=0;g<INDEX_GROUPS;g=g+1) begin:ix
    ot_hbm_su_programme_mem #(.BANKS(INDEX_BANKS),.BASE(g*INDEX_BANKS),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(index_rows[g*256+:256]));
  end
  for(c=0;c<COLS;c=c+1) begin:dt
    ot_hbm_su_programme_mem #(.BANKS(DICT_BANKS[32*c+:32]),.BASE(dict_base(c)),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[32*c+:32]]),.ren(d_ren),.addr(d_addr[c*16+:16]),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(templates[c*256+:256]));
  end
  if(PIPE==0) begin:g_p0
    assign d_ren=v1; assign d_e=e1; assign d_addr=indices;
    assign c_v=v2; assign c_e=e2;
    assign busy=busy_i; assign fault=fault_i;
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
    // outputs cycle-identical to a PIPE 0 producer started XP edges later
    logic [XP-1:0] busy_d, fault_d;
    always_ff @(posedge clk) if(!rst_n) begin busy_d<='0; fault_d<='0; end
      else begin busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i}; end
    assign busy=(MUT==2)?busy_i:(busy_i && busy_d[XP-1]);
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
      if(start) begin
        if(busy_i || length==0 || length>EDGES) fault_i<=1;
        else begin busy_i<=1; issue<=1; pc<=0; count<=length; end
      end
      if(issue) begin
        e1<=pc;
        if(pc==count-1) issue<=0; else pc<=pc+1;
      end
      if(d_ren) e2<=d_e;
      if(c_v) begin
        edge_index<=c_e;
        if(c_e==count-1) begin busy_i<=0; done<=1; end
      end
    end
  end
  // command register: PIPE 0 synchronous reset (unchanged); PIPE 1 no reset (clears the edge after the valid chain
  // resets)
  generate if(PIPE==0) begin:g_cmd0
    always_ff @(posedge clk) command <= (rst_n && c_v) ? templates[LINE_BITS-1:0] : '0;
  end else begin:g_cmd1
    always_ff @(posedge clk) command <= c_v ? templates[LINE_BITS-1:0] : '0;
  end endgenerate
endmodule
