`timescale 1ns/1ps
// redesign-hbm 2026-10-09 (owner: no cycle / area limit; structural alternatives): SYSTOLIC successor of
// ot_hgi_idx_topk.sv (same module name, parameters and ports; a route / bench uses ONE of the two files).
// hgi-idx-topk-b-d52820055-tc-cx-wv2 PREROUTE reg2reg -1,079 ps with 153,117 endpoints below -750: the parallel
// insertion sorter broadcasts the incoming 53-bit key to all MAX_K cells every cycle (2,048 comparators + neighbour muxes
// on one net) and its FILL / EMIT / clear enables fan out to ~174k flops.
// Borrowed ideas (TPU MXU / systolic priority queue; Tensix-style hardened abutted cells):
//   * nearest-neighbour dataflow: a key enters cell 0 and TRAVELS one cell per edge in its own register (t_*); each cell
//     compares the arriving key with its resident key, keeps the larger and passes the smaller on.  Keys enter in
//     order and never overtake, so every cell sees the stream in input order and the final array is the insertion
//     sort's (keys are unique: score | ~index), i.e. bit-identical cells[0..k-1];
//   * a CLEAR TOKEN travels one cell ahead of the first key of a row (no global clear);
//   * emission is the existing head shift, but the shift enable is issued from a credit counter and distributed by a
//     REGISTERED, REPLICATED fanout tree (latency EL edges, every leaf the same depth), and the head lands in an output
//     FIFO (depth EF >= EL + 2: full rate) instead of answering out_ready combinationally;
//   * no signal reaches more than one cell (plus its leaf of the enable tree) combinationally.
// TS (cells per systolic stage): 1 = one compare a cell per edge; 2 = a key crosses two cells per edge (two chained
// compare / mux steps, ~460 ps) and the travelling registers exist every second cell (~1.5x instead of ~2x the flops).
// Cost per row vs ot_hgi_idx_topk: + k + 1 drain edges (the last key's wave passes cell k-1) + EL + 2 (enable tree,
// clear-token injection) ; area ~2x cells (travelling registers): MAX_K x 86 flops + tree + FIFO.
module ot_hgi_idx_topk #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048,
 parameter bit MUTANT_TIE=0,
 parameter integer EL=3, parameter integer EF=8, parameter integer NT=64,   // enable-tree depth, FIFO depth, cells per leaf
 parameter integer TS=`ifdef OT_TOPK_SYS_TS2 2 `else 1 `endif,              // cells a key crosses per edge (travelling regs every TS cells)
 parameter integer MUT_SYS=`ifdef OT_TOPK_SYS_MUT_DRAIN 1 `else 0 `endif   // 1: no drain (shifts start while the last waves are in flight: bench mutant)
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [31:0] in_score,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 localparam IDLE=0,FILL=1,DRAIN=2,EMIT=3,WAITE=4,FINISH=5;
 localparam integer NL=(MAX_K+NT-1)/NT;            // enable-tree leaves
 localparam integer N1=(NL+15)/16;                  // first tree level copies
 reg [2:0] state;
 reg [31:0] n,m,row,cursor;
 reg [11:0] k,ecnt,dcnt;
 reg values_enabled;
 // ---- the systolic array: resident (c_*) and travelling (t_*) registers; t_*[i] enters cell i at the next edge
 reg [52:0] c_key[0:MAX_K-1]; reg [31:0] c_val[0:MAX_K-1];
 localparam integer NS=(MAX_K+TS-1)/TS;           // systolic stages
 reg [52:0] t_key[0:NS];   reg [31:0] t_val[0:NS];  // t_*[s] enters stage s at the next edge
 reg        t_clr[0:NS];
 wire [31:0] canon=(in_score[30:0]==0)?32'd0:in_score;
 wire [31:0] monotone=canon[31]?~canon:(canon|32'h80000000);
 wire [19:0] index_key=MUTANT_TIE?cursor[19:0]:~cursor[19:0];
 wire [52:0] key={1'b1,monotone,index_key};
 wire nan=(in_score[30:23]==8'hff)&&(in_score[22:0]!=0);
 // ---- shift enable: issue (from flops) -> se0 -> se1[N1] -> se2[NL] (keep, fanout <= 16 / NT cells)
 reg se0; (* keep *) reg se1[0:N1-1]; (* keep *) reg se2[0:NL-1];
 reg [3:0] credit; reg [3:0] inflight;
 wire issue=(state==EMIT)&&ecnt<k&&credit!=0;
 // ---- output FIFO (head capture at the shift edge)
 reg [52:0] fq_key[0:EF-1]; reg [31:0] fq_val[0:EF-1]; reg [31:0] fq_row[0:EF-1]; reg fq_last[0:EF-1]; reg fq_vals[0:EF-1];
 reg [3:0] fw,fr,fn;
 reg [31:0] prow[0:EL]; reg [11:0] pidx[0:EL];     // row / index of each in-flight shift (aligned with the tree)
 wire push=se2[0];
 wire pop=out_valid&&out_ready;
 assign cmd_ready=ENABLE&&state==IDLE;
 assign in_ready=ENABLE&&state==FILL;
 assign out_valid=ENABLE&&fn!=0;
 assign out_id={{12{1'b0}},MUTANT_TIE?fq_key[fr][19:0]:~fq_key[fr][19:0]};
 assign out_score=fq_val[fr];
 assign out_row=fq_row[fr];
 assign out_last=fq_last[fr];
 assign out_values_valid=out_valid&&fq_vals[fr];
 integer i;
 genvar g;
 // ---- cells: stage s = cells s*TS .. s*TS+TS-1; one local compare per cell, its own leaf of the shift-enable tree
 wire [52:0] xi_key[0:MAX_K-1]; wire [31:0] xi_val[0:MAX_K-1];    // key arriving at cell g this edge
 wire [52:0] xo_key[0:MAX_K-1]; wire [31:0] xo_val[0:MAX_K-1];    // key cell g passes on
 generate for(g=0;g<MAX_K;g=g+1) begin:g_cell
  localparam integer S=g/TS;
  wire sh=se2[g/NT];
  if(g%TS==0) begin:g_in assign xi_key[g]=t_key[S]; assign xi_val[g]=t_val[S]; end
  else begin:g_ch assign xi_key[g]=xo_key[g-1]; assign xi_val[g]=xo_val[g-1]; end
  wire gt=xi_key[g]>c_key[g];
  assign xo_key[g]=gt?c_key[g]:xi_key[g]; assign xo_val[g]=gt?c_val[g]:xi_val[g];
  always @(posedge clk) begin
   if(t_clr[S]) begin c_key[g]<=0; c_val[g]<=0; end
   else if(sh) begin
    c_key[g]<=(g==MAX_K-1)?53'd0:c_key[(g==MAX_K-1)?g:g+1]; c_val[g]<=(g==MAX_K-1)?32'd0:c_val[(g==MAX_K-1)?g:g+1];
   end else if(gt) begin c_key[g]<=xi_key[g]; c_val[g]<=xi_val[g]; end
  end
  if(g%TS==TS-1 || g==MAX_K-1) begin:g_out          // the stage's travelling register
   always @(posedge clk) begin
    if(t_clr[S]) begin t_key[S+1]<=0; t_val[S+1]<=0; end
    else if(sh) begin t_key[S+1]<=t_key[S]; t_val[S+1]<=t_val[S]; end
    else begin t_key[S+1]<=xo_key[g]; t_val[S+1]<=xo_val[g]; end
   end
   always @(posedge clk or negedge rst_n) if(!rst_n) t_clr[S+1]<=1'b0; else t_clr[S+1]<=t_clr[S];
  end
 end endgenerate
 // ---- control (state, entry at cell 0, credits, tree, FIFO)
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE; values_enabled<=0; done<=0;error<=0;n<=0;m<=0;k<=0;row<=0;cursor<=0;ecnt<=0;dcnt<=0;
   t_clr[0]<=1'b0; t_key[0]<=0; t_val[0]<=0; se0<=0; credit<=EF; inflight<=0; fw<=0; fr<=0; fn<=0;
   for(i=0;i<N1;i=i+1) se1[i]<=0;
   for(i=0;i<NL;i=i+1) se2[i]<=0;
  end else begin
   done<=0; t_clr[0]<=1'b0; t_key[0]<=0; t_val[0]<=0;
   se0<=issue; for(i=0;i<N1;i=i+1) se1[i]<=se0; for(i=0;i<NL;i=i+1) se2[i]<=se1[i/16];
   credit<=credit-(issue?4'd1:4'd0)+(pop?4'd1:4'd0);
   inflight<=inflight+(issue?4'd1:4'd0)-(push?4'd1:4'd0);
   if(push) begin fw<=(fw==EF-1)?4'd0:fw+4'd1; end
   if(pop) begin fr<=(fr==EF-1)?4'd0:fr+4'd1; end
   fn<=fn+(push?4'd1:4'd0)-(pop?4'd1:4'd0);
   case(state)
    IDLE: if(cmd_valid) begin
     error<=0;
     if(!ENABLE||cmd_unit!=9||cmd_op!=2) begin error<=1;done<=1;end
     else if(cmd_param[24:12]!=0||cmd_param[11:0]==0||cmd_param[11:0]>MAX_K||
       cmd_param[11:0]>cmd_n||cmd_n==0||cmd_n>1048576||cmd_m==0) begin error<=2;done<=1;end
     else begin
      values_enabled<=cmd_values;n<=cmd_n;m<=cmd_m;k<=cmd_param[11:0];row<=0;cursor<=0;state<=FILL;
      t_clr[0]<=1'b1;                                   // the clear token leads the row's keys
     end
    end
    FILL: if(in_valid) begin
     if(nan) begin error<=3;done<=1;state<=IDLE;end
     else begin
      t_key[0]<=key; t_val[0]<=in_score;
      cursor<=cursor+1;
      if(cursor+1==n) begin state<=DRAIN; dcnt<=(MUT_SYS==1)?12'd1:k+12'd1; end
     end
    end
    DRAIN: if(dcnt<=1) begin state<=EMIT; ecnt<=0; end else dcnt<=dcnt-1;
    EMIT: if(issue) begin
     ecnt<=ecnt+1;
     if(ecnt+1==k) begin state<=WAITE; dcnt<=EL+2; end
    end
    WAITE: if(dcnt<=1&&inflight==0) begin           // every issued shift has landed: the array may be cleared
     if(row+1==m) state<=FINISH;
     else begin row<=row+1;cursor<=0;state<=FILL;t_clr[0]<=1'b1; end
    end else if(dcnt>1) dcnt<=dcnt-1;
    FINISH: if(fn==0&&!push&&inflight==0) begin done<=1;state<=IDLE;end
    default:state<=IDLE;
   endcase
  end
 end
 // in-flight shift tags (row / index), aligned with the enable tree
 always @(posedge clk) begin
  prow[0]<=row; pidx[0]<=ecnt;
  for(i=1;i<=EL;i=i+1) begin prow[i]<=prow[i-1]; pidx[i]<=pidx[i-1]; end
  if(push) begin
   fq_key[fw]<=c_key[0]; fq_val[fw]<=c_val[0]; fq_row[fw]<=prow[EL-1]; fq_last[fw]<=(pidx[EL-1]+1==k); fq_vals[fw]<=values_enabled;
  end
 end
endmodule
