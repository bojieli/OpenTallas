`timescale 1ns/1ps
// Host-configured, fixed-cycle programme producer. Each logical memory is made
// exclusively from target 128x256 SRAM macros. No simulation-only DUT storage.
module ot_hbm_su_programme_mem #(
  parameter integer BANKS=1, BASE=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic ren, input logic [15:0] addr,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data, output logic [255:0] data);
  wire [255:0] q [0:BANKS-1];
  logic [8:0] select_q;
  always_ff @(posedge clk) if (ren) select_q <= addr[15:7];
  always_comb begin
    data='0;
    for(integer k=0;k<BANKS;k=k+1) if(select_q==k) data=q[k];
  end
  for(genvar k=0;k<BANKS;k=k+1) begin:g
    ot_sram_1r1w_128x256_m1_r2c2 mem(
      .clk(clk_macro[k]), .r_ce_in(ren && addr[15:7]==k), .r_addr_in(addr[6:0]), .rd_out(q[k]),
      .w_ce_in(cfg_we && cfg_bank==BASE+k), .w_addr_in(cfg_row),
      .wd_in(cfg_data), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end
endmodule

module ot_hbm_su_programme #(
  parameter integer LINE_BITS=9688, EDGES=7111,
  parameter integer COLS=(LINE_BITS+255)/256,
  parameter integer INDEX_GROUPS=(COLS+15)/16,
  parameter integer INDEX_PACK=1,
  parameter integer INDEX_BANKS=(EDGES+128*INDEX_PACK-1)/(128*INDEX_PACK),
  parameter integer DICT_BANKS [0:COLS-1]='{default:1},
  parameter integer MACROS=INDEX_GROUPS*INDEX_BANKS+COLS
)(input logic clk, rst_n, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault,
  output logic [15:0] edge_index,
  output logic [LINE_BITS-1:0] command);
  function automatic integer dict_base(input integer c);
    integer v;
    begin
      v=INDEX_GROUPS*INDEX_BANKS;
      for(integer k=0;k<c;k=k+1) v=v+DICT_BANKS[k];
      return v;
    end
  endfunction
  localparam integer TOTAL_BANKS=dict_base(COLS);
  initial if(MACROS!=TOTAL_BANKS) $fatal(1,"programme MACROS capacity mismatch");
  logic issue,v1,v2;
  logic [15:0] pc, count, e1,e2;
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
  wire [COLS*256-1:0] templates;
  wire write_enable=cfg_we && !busy && cfg_bank<TOTAL_BANKS;
  for(genvar g=0;g<INDEX_GROUPS;g=g+1) begin:ix
    ot_hbm_su_programme_mem #(.BANKS(INDEX_BANKS),.BASE(g*INDEX_BANKS)) mem(
      .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(index_rows[g*256+:256]));
  end
  for(genvar c=0;c<COLS;c=c+1) begin:dt
    ot_hbm_su_programme_mem #(.BANKS(DICT_BANKS[c]),.BASE(dict_base(c))) mem(
      .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[c]]),.ren(v1),.addr(indices[c*16+:16]),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(templates[c*256+:256]));
  end
  // Start sampled at S; first command/valid presented after S+3 and sampled
  // by a downstream sequential consumer at S+4. Subsequent lines every edge.
  always_ff @(posedge clk) begin
    if(!rst_n) begin
      busy<=0; issue<=0; valid<=0; done<=0; fault<=0;
      v1<=0; v2<=0; pc<=0; count<=0; e1<=0; e2<=0; edge_index<=0; command<='0;
    end else begin
      valid<=v2; v1<=issue; v2<=v1; done<=0;
      if(cfg_we && (busy || cfg_bank>=TOTAL_BANKS)) fault<=1;
      if(start) begin
        if(busy || length==0 || length>EDGES) fault<=1;
        else begin busy<=1; issue<=1; pc<=0; count<=length; end
      end
      if(issue) begin
        e1<=pc;
        if(pc==count-1) issue<=0; else pc<=pc+1;
      end
      if(v1) e2<=e1;
      if(v2) begin
        edge_index<=e2; command<=templates[LINE_BITS-1:0];
        if(e2==count-1) begin busy<=0; done<=1; end
      end else command<='0;
    end
  end
endmodule
