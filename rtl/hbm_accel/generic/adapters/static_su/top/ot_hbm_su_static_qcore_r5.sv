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
// g3 (HBM-SU6 2026-10-17, r5 g2 gate: rf_bcmd[*] 8,193 loads = synthesis merged the 8 per-sector address copies with the
// rf_bcmd output flop; placement reg->reg -178.7 ps into mem[*] D): every replicated pin-rung copy is a KEPT instance
// (ot_hbm_su_qcore_r5_kq, keep_hierarchy, never merged). Read address: one copy per (sector, class, 16-bit half)
// (<= ~256 mux loads); class 5: one copy per (word slot, half). Writers: per-sector copies of wv/wa/wd/rrv/rra so each
// copy feeds 8 banks. Same edges (all copies capture at k from the pins), same function.
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hbm_su_qcore_r5_kq #(parameter integer W=1,RST=0)(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
 if(RST!=0)begin:g_r always @(posedge clk or negedge rst_n) if(!rst_n) q<={W{1'b0}}; else q<=d; end
 else begin:g_n always @(posedge clk) q<=d; end
endmodule

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
 reg [53:0] cmd_p; reg [255:0] rrd_p;
 always @(posedge clk_ctl) rrd_p<=rr_wd;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) cmd_p<=54'd0; else cmd_p<=rf_rd_cmd;
 // per-sector writer copies (kept): {wa 32, wd 128, rra 5} no reset; {wv 4, rrv 1} reset
 wire [3:0] wv_s [0:7]; wire [31:0] wa_s [0:7]; wire [127:0] wd_s [0:7]; wire rrv_s [0:7]; wire [4:0] rra_s [0:7];
 // read address copies (kept): classes 0..4 per (sector, half) {v, row2, bank3-in-sector}; class 5 per (word slot, half)
 wire [5:0] ra_s [0:7][0:4][0:1]; wire r5v_s [0:7][0:1]; wire [4:0] r5a_s [0:7][0:1];
 for(genvar s=0;s<8;s=s+1)begin:g_sec
  ot_hbm_su_qcore_r5_kq #(.W(165),.RST(0)) u_wd(.clk(clk_ctl),.rst_n(rst_n),.d({rf_wa,rf_wd,rr_wa}),.q({wa_s[s],wd_s[s],rra_s[s]}));
  ot_hbm_su_qcore_r5_kq #(.W(5),.RST(1)) u_wv(.clk(clk_ctl),.rst_n(rst_n),.d({rf_wv,rr_wv}),.q({wv_s[s],rrv_s[s]}));
  for(genvar h=0;h<2;h=h+1)begin:g_h
   for(genvar c=0;c<5;c=c+1)begin:g_c
    ot_hbm_su_qcore_r5_kq #(.W(6),.RST(0)) u_ra(.clk(clk_ctl),.rst_n(rst_n),
     .d({rf_rd_cmd[c*9+8],rf_rd_cmd[c*9+6+:2],rf_rd_cmd[c*9+:3]}),.q(ra_s[s][c][h]));
   end
   ot_hbm_su_qcore_r5_kq #(.W(1),.RST(1)) u_r5v(.clk(clk_ctl),.rst_n(rst_n),.d(rf_rd_cmd[5*9+8]),.q(r5v_s[s][h]));
   ot_hbm_su_qcore_r5_kq #(.W(5),.RST(0)) u_r5a(.clk(clk_ctl),.rst_n(rst_n),.d({rf_rd_cmd[5*9+6+:2],rf_rd_cmd[5*9+3+:3]}),.q(r5a_s[s][h]));
  end
 end
 // ---------------------------------------------------------------- storage: one copy, writes commit k+1
 reg [31:0] mem [0:255];               // word index {row2, bank6}
 wire [63:0] rf_wconf;
 for(genvar bb=0;bb<64;bb=bb+1)begin:g_rfb
  localparam integer S=bb/8;
  reg wv; reg [1:0] wa; reg [31:0] wd; reg [2:0] nw; integer w;
  always @*begin
   wv=0;wa=0;wd=0;nw=0;
   for(w=0;w<4;w=w+1)if(wv_s[S][w]&&wa_s[S][w*8+:6]==6'(bb))begin wv=1;wa=wa_s[S][w*8+6+:2];wd=wd_s[S][w*32+:32];nw=nw+3'd1;end
  end
  wire rrb=(COLLPORT!=0)&&rrv_s[S]&&rra_s[S][2:0]==3'(bb/8);
  wire [31:0] rrd=rrd_p[32*((MUT==128)?7-(bb%8):(bb%8))+:32];
  wire bwv=wv||rrb; wire [1:0] bwa=rrb?rra_s[S][4:3]:wa; wire [31:0] bwd=rrb?rrd:wd;
  always @(posedge clk_ctl) if(bwv) mem[{bwa,6'(bb)}] <= bwd;
  assign rf_wconf[bb]=(nw>3'd1)||(rrb&&wv);
 end
 // ---------------------------------------------------------------- read pipeline: per-sector word k+1, sector select k+2
 reg [31:0] raw [0:4][0:7]; reg [2:0] sec1 [0:4]; reg [31:0] rd [0:4]; reg [31:0] rd_x [0:4];
 reg [255:0] raw5, rd5;
 integer c,kk,ss,hh;
 always @(posedge clk_ctl)begin
  for(c=0;c<5;c=c+1)begin
   for(ss=0;ss<8;ss=ss+1) for(hh=0;hh<2;hh=hh+1)
    if(ra_s[ss][c][hh][5]) raw[c][ss][hh*16+:16] <= mem[{ra_s[ss][c][hh][4:3],3'(ss),ra_s[ss][c][hh][2:0]}][hh*16+:16];
   if(cmd_p[c*9+8]) sec1[c] <= cmd_p[c*9+3+:3];
  end
  for(kk=0;kk<8;kk=kk+1) for(hh=0;hh<2;hh=hh+1)
   if(r5v_s[kk][hh]) raw5[kk*32+hh*16+:16] <= mem[{r5a_s[kk][hh],3'(kk)}][hh*16+:16];
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
