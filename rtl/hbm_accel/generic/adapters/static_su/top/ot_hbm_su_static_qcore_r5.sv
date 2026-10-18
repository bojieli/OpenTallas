`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SU quarter core successor r5 (HBM-SU3 2026-10-17; coordinator 0dc: "qcore: regional roots, not 66").
// Same ports, edges and function as ot_hbm_su_static_qcore (COLLPORT 1, RF_LOCAL 1 = the d4f die parameters) except:
//  * CLOCK: ONE root clk_ctl (~11.4k sinks + the reducer's 2 SRAMs) instead of 66 (64 per-bank clk_rf + clk_ctl +
//    clk_red). Ports clk_rf and clk_red are gone (the die drives one serial entry per quarter core).
//  * READ PIPELINE per class: k+1 registers the addressed word of EVERY sector (8 x 32 b, a 32:1 mux per sector driven by
//    a per-sector copy of the pin-rung address), k+2 selects the sector -- the same k+1/k+2 edges as one 256:1 mux,
//    without an 8,192-load address net (r5 gate g1: cmd_p[*] 8,192 loads).
//  * RF STORAGE: one copy of the 64 x 4 x 32-bit words (8,192 flops) instead of six per-reader replicas, and the read
//    pipeline registers only the SELECTED word per read class (raw_c at k+1, rd_c at k+2) instead of a raw/read_data
//    register per (bank, reader) followed by a bank-select mux (64 x 6 x 32 x 2 = 24,576 flops). ~77k -> ~10k flops.
//  * PINS FIRST: the RF read commands, the 4 relay writers and the COLL writer are captured raw at the pins at edge k
//    (one rung, decoded after the flop) -- the hub's per-bank post-decode rung moved to the pin; commit k+1, reads k+3
//    (rf_bword/rf_dsec), reducer operand and scalar edges unchanged.
// Edges (as the hub): command at pin edge k; storage commit k+1 (a read sampled at k+1 sees the pre-commit word, as the
// hub's raw <= v / v <= wd on one edge); raw_c k+1, rd_c k+2, rf_bword/rf_dsec k+3; class 4 operand rd_4 into rc_x at E+1.
// Don't-care difference: on an edge whose read class was NOT valid 3 edges earlier the hub showed the last word that
// class read from THAT bank, r5 the last word that class read (any bank); no consumer samples an invalid read (the
// compiler issues every consumed class; the pgslices check RF-source addresses against rf_bcmd).
// FAULT: write-conflict and drain-check faults report one edge later (computed on registered inputs); reducer unchanged.
// MUT (bench, must FAIL): 256 = an extra read stage (reads k+4); 16/32/64/128 as the hub.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_qcore_r5 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1)(
 input wire clk_ctl,rst_n,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire [1:0] rf_drain_cmd,
 input wire [4*32-1:0] slice_x,
 input wire [3:0] rf_wv, input wire [4*8-1:0] rf_wa, input wire [4*32-1:0] rf_wd,
 output reg [4*32-1:0] rf_bword,
 output reg [4*9-1:0] rf_bcmd,
 output reg [255:0] rf_dsec,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x,
 output wire red_rf_v,
 input wire rr_wv,
 input wire [4:0] rr_wa,
 input wire [255:0] rr_wd,
 input wire [31:0] sfu_x,
 output reg fault
);
 wire rf_drain_now=rf_drain_cmd[1]&&(rf_drain_cmd[0]||MUT==16);
 // ---------------------------------------------------------------- pin rung (raw capture at k)
 reg [53:0] cmd_p; reg [3:0] wv_p; reg [31:0] wa_p; reg [127:0] wd_p; reg rrv_p; reg [4:0] rra_p; reg [255:0] rrd_p;
 always @(posedge clk_ctl)begin wa_p<=rf_wa;wd_p<=rf_wd;rra_p<=rr_wa;rrd_p<=rr_wd;end
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)begin cmd_p<=54'd0;wv_p<=4'd0;rrv_p<=1'b0;end
  else begin cmd_p<=rf_rd_cmd;wv_p<=rf_wv;rrv_p<=rr_wv;end
 // read address copies, one per sector (classes 0..4: {v, row2, bank3-in-sector}); class 5 row per sector
 reg [5:0] ra_s [0:7][0:4]; reg [1:0] r5_s [0:7]; integer s1,c1;
 always @(posedge clk_ctl) for(s1=0;s1<8;s1=s1+1) begin
  for(c1=0;c1<5;c1=c1+1) ra_s[s1][c1] <= {rf_rd_cmd[c1*9+8], rf_rd_cmd[c1*9+6+:2], rf_rd_cmd[c1*9+:3]};
  r5_s[s1] <= rf_rd_cmd[5*9+6+:2];
 end
 // ---------------------------------------------------------------- storage: one copy, writes commit k+1
 reg [31:0] mem [0:255];               // word index {row2, bank6}
 wire [63:0] rf_wconf;
 for(genvar bb=0;bb<64;bb=bb+1)begin:g_rfb
  reg wv; reg [1:0] wa; reg [31:0] wd; reg [2:0] nw; integer w;
  always @*begin
   wv=0;wa=0;wd=0;nw=0;
   for(w=0;w<4;w=w+1)if(wv_p[w]&&wa_p[w*8+:6]==6'(bb))begin wv=1;wa=wa_p[w*8+6+:2];wd=wd_p[w*32+:32];nw=nw+3'd1;end
  end
  wire rrb=(COLLPORT!=0)&&rrv_p&&rra_p[2:0]==3'(bb/8);
  wire [31:0] rrd=rrd_p[32*((MUT==128)?7-(bb%8):(bb%8))+:32];
  wire bwv=wv||rrb; wire [1:0] bwa=rrb?rra_p[4:3]:wa; wire [31:0] bwd=rrb?rrd:wd;
  always @(posedge clk_ctl) if(bwv) mem[{bwa,6'(bb)}] <= bwd;
  assign rf_wconf[bb]=(nw>3'd1)||(rrb&&wv);
 end
 // ---------------------------------------------------------------- read pipeline: per-sector word k+1, sector select k+2
 reg [31:0] raw [0:4][0:7]; reg [2:0] sec1 [0:4]; reg [31:0] rd [0:4]; reg [31:0] rd_x [0:4];
 reg [255:0] raw5, rd5;
 integer c,kk,ss;
 always @(posedge clk_ctl)begin
  for(c=0;c<5;c=c+1)begin
   for(ss=0;ss<8;ss=ss+1) if(ra_s[ss][c][5]) raw[c][ss] <= mem[{ra_s[ss][c][4:3],3'(ss),ra_s[ss][c][2:0]}];
   if(cmd_p[c*9+8]) sec1[c] <= cmd_p[c*9+3+:3];
  end
  if(cmd_p[5*9+8]) for(kk=0;kk<8;kk=kk+1) raw5[kk*32+:32] <= mem[{cmd_p[5*9+6+:2],cmd_p[5*9+3+:3],3'(kk)}];
  for(c=0;c<5;c=c+1) rd_x[c] <= raw[c][sec1[c]];
  for(c=0;c<5;c=c+1) rd[c] <= (MUT==256) ? rd_x[c] : raw[c][sec1[c]];
  rd5 <= raw5;
 end
 wire [31:0] rf_word [0:4];
 for(genvar c2=0;c2<5;c2=c2+1)begin:g_rfw assign rf_word[c2]=rd[c2]; end
 always @(posedge clk_ctl)begin
  rf_bword<={rf_word[3],rf_word[2],rf_word[1],rf_word[0]};
  rf_bcmd<=rf_rd_cmd[0+:36];
  rf_dsec<=rd5;
 end
 // ---------------------------------------------------------------- checks + reducer staging (as the hub)
 reg c5_d1,c5_d2;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)begin c5_d1<=1'b0;c5_d2<=1'b0;end
  else begin c5_d1<=rf_rd_cmd[5*9+8];c5_d2<=c5_d1;end
 wire c5_lead=RF_LOCAL?c5_d2:c5_d1;
 // drain checks on registered inputs (fault +1 edge, status only): class-5 alignment from the pin rung, drain from a pin flop
 reg drain_p; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) drain_p<=1'b0; else drain_p<=rf_drain_now;
 reg c5_lead_q; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) c5_lead_q<=1'b0; else c5_lead_q<=c5_lead;
 wire dbad=(drain_p&&!c5_lead_q)||(cmd_p[5*9+8]&&cmd_p[5*9+:3]!=3'd0);
 reg rc_v; reg [2:0] rc_op; reg [9:0] rc_a,rc_b,rc_d; reg [31:0] rc_tag,rc_x;
 reg [1:0] e_sl; reg e_os,e_sfu; reg [72:8] e_f;
 always @(posedge clk_ctl)begin e_sl<=red_cmd[5:4];e_os<=red_cmd[7];e_sfu<=(COLLPORT!=0)&&red_cmd[6]&&(MUT!=64);e_f<=red_cmd[72:8];end
 reg e_v;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)e_v<=1'b0; else e_v<=red_cmd[73];
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)rc_v<=1'b0; else rc_v<=e_v;
 always @(posedge clk_ctl)begin
  rc_op<=e_f[72:70];rc_a<=e_f[69:60];rc_b<=e_f[59:50];rc_d<=e_f[49:40];rc_tag<=e_f[39:8];
  rc_x<=e_os?(e_sfu?sfu_x:rf_word[4]):slice_x[e_sl*32+:32];
 end
 wire red_fault;
 ot_hbm_su_reduce_static #(.AW(10)) u_red(.clk(clk_ctl),.rst_n(rst_n),.cmd_valid(rc_v),.cmd_op(rc_op),.cmd_a(rc_a),
  .cmd_b(rc_b),.cmd_dst(rc_d),.operand_fp32(rc_x),.cmd_tag(rc_tag),.scalar_valid(red_sv),.scalar_tag(red_tag),
  .scalar_fp32(red_x),.scalar_bf16(),.fault(red_fault));
 assign red_rf_v=red_sv&&(red_tag[8]||MUT==32);
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0; else if((|rf_wconf)||dbad||red_fault)fault<=1'b1;
endmodule
`default_nettype wire
