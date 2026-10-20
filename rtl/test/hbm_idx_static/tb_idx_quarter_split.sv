`timescale 1ns/1ps
`default_nettype none
// OWN-IDXSCORE 2026-10-18: lockstep of the wires-only IDX quarter scorer (ot_hbm_idx_score_quarter_wo = W glue tile +
// 8 leaves + E glue tile) against the flat ot_hbm_idx_score_quarter_static, identical stimulus, EVERY edge compared:
// new.score / new.fault == old one edge earlier (the W tile's registered output stage = +1 on every leaf input).
// -DOT_QS_WO2 (L2H-IDXSCORE 2026-10-19): the DUT is the r4 parent ot_hbm_idx_score_quarter_wo2 (W tile r4 with a mid stage:
// +2 edges, row clocks, leaf_c1 leaves, E tile r4 with per-row score registers); compared at +2.
// Two frames (query load of all 32 heads, key beats with partial last beat, keep bitmap, different rank / first_ord),
// strap HALF from -GHALF. Reset defines only score.ev and fault (payload flops have no reset).
// During reset assert those controls; from the FIRST rst_n-high edge compare the ENTIRE score bus,
// including idle cycles and reset-release relay cycles, at +1. No warmup window or valid-only mask.
// PASS requires one score event per beat, finite nonzero scores on both rows, no score-lane faults.
module tb_idx_quarter_split #(parameter integer TP=192, parameter integer HALF=0)();
 localparam integer RANK_W=$clog2(TP);
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0;
 reg [RANK_W-1:0] rank=0; reg [10:0] first_ord=0; reg [11:0] nkeys=0; reg keep_en=0; reg [170:0] keep_bitmap=0;
 reg ql_v=0; reg [7:0] ql_head=0; reg [511:0] ql_codes=0; reg [31:0] ql_sc=0; reg [15:0] ql_w=0;
 reg beat_v=0; reg [7:0] beat_index=0; reg [4395:0] key_lines=0;
 wire [1:0] c2={clk,clk}; wire [7:0] c8={8{clk}}; wire [255:0] c256={256{clk}};
 wire [305:0] so, sn; wire fo, fn;
 ot_hbm_idx_score_quarter_static #(.TP(TP)) u_old(.clk_ctl(clk),.clk_engine(c2),.clk_meta(c2),.clk_tail(c2),.clk_chunk(c8),
  .clk_hslice(c256),.rst_n(rst_n),.half(1'(HALF)),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),
  .keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),
  .beat_index(beat_index),.key_lines(key_lines),.score(so),.fault(fo));
`ifdef OT_QS_WO2
 localparam integer LAT=2;
 ot_hbm_idx_score_quarter_wo2 #(.TP(TP)) u_new(.clk_engine(c2),.clk_tail(c2),.clk_chunk(c8),.rst_n(rst_n),.half(1'(HALF)),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),
  .keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),
  .beat_index(beat_index),.key_lines(key_lines),.score(sn),.fault(fn));
`else
 localparam integer LAT=1;
 ot_hbm_idx_score_quarter_wo #(.TP(TP)) u_new(.clk_ctl(clk),.clk_engine(c2),.clk_meta(c2),.clk_tail(c2),.clk_chunk(c8),
  .clk_hslice(c256),.rst_n(rst_n),.half(1'(HALF)),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),
  .keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),
  .beat_index(beat_index),.key_lines(key_lines),.score(sn),.fault(fn));
`endif
 reg [305:0] so_d1, so_d; reg fo_d1, fo_d; integer cyc=0, errs=0, evs=0, nz=0, oldfault_cyc=-1, newev=0;
 integer nz_row0=0, nz_row1=0, lane_faults=0;
 bit finite_frame=0;
 always @(posedge clk) begin
  so_d1<=so; fo_d1<=fo; cyc<=cyc+1;
  if (LAT==2) begin so_d<=so_d1; fo_d<=fo_d1; end else begin so_d<=so; fo_d<=fo; end
  begin
   if ((!rst_n && ({sn[0],so[0],fn,fo} !== 4'b0)) ||
       (rst_n && (sn!==so_d || fn!==fo_d))) begin
    errs<=errs+1;
    if (errs<8) $display("QSPLIT_BAD cyc%0d new{ev%0d last%0d f%0d idx0 %05h val0 %04h} old_d1{ev%0d last%0d f%0d idx0 %05h val0 %04h}",
      cyc, sn[0], sn[1], fn, sn[305-:20], sn[145-:16], so_d[0], so_d[1], fo_d, so_d[305-:20], so_d[145-:16]);
   end
   if (so[0]) begin
    evs<=evs+1;
    if (finite_frame && so[9:2] != 0) lane_faults<=lane_faults+1;
    for (int l=0;l<8;l++) begin
     if (finite_frame && so[10+l] && so[18+16*l+:16]!=0 && so[18+16*l+:16]!=16'hff80 && so[18+16*l+7+:8]!=8'hff) begin
      nz<=nz+1;
      if(l<4) nz_row0<=nz_row0+1; else nz_row1<=nz_row1+1;
     end
    end
   end
   if (sn[0]) newev<=newev+1;
   if (fo && oldfault_cyc<0) oldfault_cyc<=cyc;
  end
 end
 function automatic [511:0] r512(); for (int i=0;i<16;i++) r512[i*32+:32]=$urandom; endfunction
 task automatic frame(input integer nb, input integer nk, input integer fo_v, input integer rk_v, input bit kep, input bit bounded);
  @(negedge clk); finite_frame=bounded; rank=RANK_W'(rk_v); first_ord=11'(fo_v); nkeys=12'(nk); keep_en=kep;
  for (int i=0;i<6;i++) keep_bitmap[i*32+:32]=$urandom;
  for (int h=0;h<32;h++) begin
   ql_v=1; ql_head=8'(h); ql_codes=r512(); ql_sc=$urandom; ql_w=16'($urandom);
   if(bounded) begin
   // Positive E2M1 codes, UE8M0 scales near unity and bounded BF16 weight.
   // Arbitrary raw scale/weight bits mostly test arithmetic refusal/zeroing.
   for(int q=0;q<128;q++) ql_codes[q*4+:4]=4'(1+($urandom%7));
   for(int q=0;q<4;q++) ql_sc[q*8+:8]=8'(125+($urandom%3));
   ql_w=16'h3e80+16'(h*3);
   end
   @(negedge clk);
  end
  ql_v=0; repeat (8) @(negedge clk);
  for (int b=0;b<nb;b++) begin
   beat_v=1; beat_index=8'(b);
   for (int j=0;j<4;j++) begin
    key_lines[j*1099]=1'b1; key_lines[j*1099+1+:10]=10'((4*HALF+j)*128+b);
    for (int w=0;w<34;w++) key_lines[j*1099+11+w*32+:32]=$urandom;
    if(bounded) for(int k=0;k<2;k++) begin
     for(int q=0;q<128;q++) key_lines[j*1099+11+k*544+q*4+:4]=4'(1+($urandom%7));
     for(int q=0;q<4;q++) key_lines[j*1099+11+k*544+512+q*8+:8]=8'(125+((j+k+b+q)%3));
    end
   end
   @(negedge clk);
  end
  beat_v=0; key_lines=0; repeat (420) @(negedge clk);
 endtask
 // Poison ONLY the deliberately unreset output payload, with different histories.
 // Reset controls remain driven by RTL; normal clock assignments flush poison.
 initial if ($test$plusargs("poison_payload")) begin
  force u_old.score[305:1] = {305{1'b1}};
`ifdef OT_QS_WO2
  force u_new.u_e.score0[153:1] = {153{1'b0}}; force u_new.u_e.score1 = {152{1'b0}};
`else
  force u_new.u_e.score[305:1] = {305{1'b0}};
`endif
  repeat(2) @(negedge clk);
  release u_old.score[305:1];
`ifdef OT_QS_WO2
  release u_new.u_e.score0[153:1]; release u_new.u_e.score1;
`else
  release u_new.u_e.score[305:1];
`endif
  $display("IDX_QUARTER_SPLIT payload_poison_released");
 end
 initial begin
  void'($urandom(32'h1d5c0de + HALF));
  repeat (10) @(negedge clk); rst_n=1; repeat (40) @(negedge clk);
  frame(20, 16*20-5, 3, 7, 0, 0);
  frame(9, 16*9-13, 41, 191 % TP, 1, 0);
  frame(20, 16*20-5, 19, 73 % TP, 0, 1);
  repeat (20) @(negedge clk);
  $display("IDX_QUARTER_SPLIT half%0d errors%0d old_events%0d nonzero%0d new_events%0d old_first_fault_cyc%0d", HALF, errs, evs, nz, newev, oldfault_cyc);
  $display("IDX_QUARTER_SPLIT coverage row0_nonzero_events%0d row1_nonzero_events%0d lane_fault_events%0d",nz_row0,nz_row1,lane_faults);
  // else: Verilator runs the statement after $finish in the same block (qs3/qs4 printed a stray FAIL line after PASS)
  if (errs==0 && evs==49 && nz_row0>0 && nz_row1>0 && lane_faults==0 && newev==evs && oldfault_cyc<0) begin $display("IDX_QUARTER_SPLIT PASS"); $finish; end
  else begin $display("IDX_QUARTER_SPLIT FAIL"); $stop; end
 end
endmodule
`default_nettype wire
