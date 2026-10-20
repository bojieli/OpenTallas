// r7: opt-in additive successor; 16 independent kept 2-bit read groups replace2 broad16-bit groups. Same ports/edges; no layout admission.
`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SU quarter core successor r5 (HBM-SU3 2026-10-17; coordinator 0dc: "qcore: regional roots, not 66").
// Same ports, edges and function as ot_hbm_su_static_qcore (COLLPORT 1, RF_LOCAL 1 = the d4f die parameters) except:
//  * CLOCK: ONE root clk_ctl instead of 66 (64 per-bank clk_rf + clk_ctl + clk_red). Ports clk_rf and clk_red are gone.
//  * RF STORAGE: one copy of the 64 x 4 x 32-bit words (8,192 flops) instead of six per-reader replicas; the read
//    pipeline registers only the SELECTED word per read class.
//  * PINS FIRST: the RF read commands, the 4 relay writers and the COLL writer are captured raw at the pins at edge k
//    (one rung, decoded after the flop); commit k+1, reads k+3 (rf_bword/rf_dsec), reducer operand and scalar edges
//    unchanged.
// Edges (as the hub): command at pin edge k; storage commit k+1 (a read sampled at k+1 sees the pre-commit word, as the
// hub's raw <= v / v <= wd on one edge); raw_c k+1, rd_c k+2, rf_bword/rf_dsec k+3; class 4 operand rd_4 into rc_x at E+1.
// Don't-care difference: on an edge whose read class was NOT valid 3 edges earlier the hub showed the last word that
// class read from THAT bank, r5 the last word that class read (any bank); no consumer samples an invalid read (the
// compiler issues every consumed class; the pgslices check RF-source addresses against rf_bcmd).
// MUT (bench, must FAIL): 256 = an extra read stage (reads k+4); 16/32/64/128 as the hub.
//
// r6 STRUCTURE (HH-11 2026-10-19; route r5-1a1108053 NEEDS_RTL TT -314.4: per-sector writer copies clumped at the E
// face while each sector's banks were spread over the tile -> 20-level copy->mem D paths; class-5 slot kk read bank kk
// of all 8 sectors through ~470 ps of placement buffers; cmd_p -> fault 18 levels). Same ports, same edges, same function:
//  * ONE kept module per sector (ot_hbm_su_qcore_r7_sec, keep_hierarchy; the kit places each as a placement region):
//    the sector's 8 banks x 4 rows x 32 b, its raw writer copies (wv/wa/wd, rrv/rra and -- new -- its own copy of the
//    256-b COLL write data), the bank-match / priority write decode, its read-address copies and its k+1 read registers.
//  * READS: every class registers at k+1, inside the sector, the addressed word GATED by the sector match (zero when
//    another sector is addressed); k+2 ORs the 8 sector words (rd_c, rd5). Valid reads are identical to the r5 select;
//    on hold edges every sector keeps its last captured word, so the OR equals r5's raw[sec1] too.
//    Class 5 (one sector's full row, 8 banks x 32 b): a per-sector 4:1 row pre-select (local) + the 8-way OR at k+2.
//  * WRITE DECODE: per bank a one-hot priority (last writer wins, as the r5 loop) on the sector-local copies.
//  * FAULT: the per-sector write-conflict term is registered in the sector (k+1) and ORed into fault at k+2, i.e. a
//    write-conflict fault reports two edges after the hub (r5: one); drain / class-5 alignment and reducer faults as r5.
// ---------------------------------------------------------------------------------------------------------------------
// PRETREE (HH-6 / HBM-SURED 2026-10-18; default 0 = unchanged): slice_t = the four pgslices' pre-tree outputs
//   (ot_hbm_su_red_pretree_s); ot_hbm_su_red_pretree_j joins them (pin register + 3 node levels) into the quarter's
//   128-word csum8 subtree. A reducer command with osel=1, red_cmd[5]=1, red_cmd[6]=0 takes that subtree as its external
//   operand (rc_x) -- issued at E+PT_RED for the block whose tree_cmd was at E (PT_RED 69 at LAT 6, bench-measured);
//   ops 0 LOAD / 1 ADD_EXT / 3 MAX_EXT as for a lane operand. FAULT: an operand taken while the subtree is not valid,
//   a join adder error. MUT 512: tree operand taken one edge late; 1024: join pairing (s0+s2),(s1+s3).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hbm_su_qcore_r7_kq #(parameter integer W=1,RST=0)(input wire clk,rst_n,input wire [W-1:0] d,(* keep = 1 *) output reg [W-1:0] q);
 if(RST!=0)begin:g_r always @(posedge clk or negedge rst_n) if(!rst_n) q<={W{1'b0}}; else q<=d; end
 else begin:g_n always @(posedge clk) q<=d; end
endmodule

// One RF sector (banks 8S..8S+7, rows 0..3): storage, writer copies + decode, read copies + gated k+1 read registers.
(* keep_hierarchy *)
module ot_hbm_su_qcore_r7_sec #(parameter integer S=0,MUT=0,COLLPORT=1)(
 input wire clk,rst_n,
 input wire [6*9-1:0] rd_cmd,                  // raw pins (k)
 input wire [3:0] wv, input wire [31:0] wa, input wire [127:0] wd,
 input wire rrv, input wire [4:0] rra, input wire [255:0] rrd,
 output reg [5*32-1:0] raw_o,                  // classes 0..4, k+1, zero unless this sector was addressed
 output reg [255:0] raw5_o,                    // class 5 row, k+1, zero unless this sector was addressed
 output reg conf_o                             // write conflict in this sector (registered)
);
 // ---- writer copies (raw, k)
 wire [31:0] wa_c; wire [127:0] wd_c; wire [4:0] rra_c; wire [3:0] wv_c; wire rrv_c; wire [255:0] rrd_c;
 ot_hbm_su_qcore_r7_kq #(.W(165),.RST(0)) u_wd(.clk(clk),.rst_n(rst_n),.d({wa,wd,rra}),.q({wa_c,wd_c,rra_c}));
 ot_hbm_su_qcore_r7_kq #(.W(5),.RST(1)) u_wv(.clk(clk),.rst_n(rst_n),.d({wv,rrv}),.q({wv_c,rrv_c}));
 ot_hbm_su_qcore_r7_kq #(.W(256),.RST(0)) u_rr(.clk(clk),.rst_n(rst_n),.d(rrd),.q(rrd_c));
 // ---- read address copies (raw 9-b class fields {v,row2,sec3,bank3}), one per (class, 16-bit half); class 5 {row2,sec3}
 wire [8:0] ra_c [0:4][0:15]; wire r5v_c [0:15]; wire [4:0] r5a_c [0:15];
 for(genvar h=0;h<16;h=h+1)begin:g_h
  for(genvar c=0;c<5;c=c+1)begin:g_c
   ot_hbm_su_qcore_r7_kq #(.W(9),.RST(0)) u_ra(.clk(clk),.rst_n(rst_n),.d(rd_cmd[c*9+:9]),.q(ra_c[c][h]));
  end
  ot_hbm_su_qcore_r7_kq #(.W(1),.RST(1)) u_r5v(.clk(clk),.rst_n(rst_n),.d(rd_cmd[5*9+8]),.q(r5v_c[h]));
  ot_hbm_su_qcore_r7_kq #(.W(5),.RST(0)) u_r5a(.clk(clk),.rst_n(rst_n),.d(rd_cmd[5*9+3+:5]),.q(r5a_c[h]));
 end
 // ---- storage: 8 banks x 4 rows, word index {row2, bank3}; writes commit k+1
 reg [31:0] mem [0:31];
 wire [7:0] bconf;
 wire rrb=(COLLPORT!=0)&&rrv_c&&rra_c[2:0]==3'(S);           // the COLL writer fills all 8 banks of one row
 for(genvar b=0;b<8;b=b+1)begin:g_b
  wire [3:0] hit;
  for(genvar w=0;w<4;w=w+1)begin:g_w assign hit[w]=wv_c[w]&&wa_c[w*8+:6]==6'(8*S+b); end
  // last writer wins (as the r5 loop): one-hot priority select
  wire [3:0] sel={hit[3],hit[2]&&!hit[3],hit[1]&&!hit[2]&&!hit[3],hit[0]&&!hit[1]&&!hit[2]&&!hit[3]};
  wire [31:0] wdb=({32{sel[0]}}&wd_c[0+:32])|({32{sel[1]}}&wd_c[32+:32])|({32{sel[2]}}&wd_c[64+:32])|({32{sel[3]}}&wd_c[96+:32]);
  wire [1:0] wab=({2{sel[0]}}&wa_c[6+:2])|({2{sel[1]}}&wa_c[14+:2])|({2{sel[2]}}&wa_c[22+:2])|({2{sel[3]}}&wa_c[30+:2]);
  wire wvb=|hit;
  wire [31:0] rrdb=rrd_c[32*((MUT==128)?7-b:b)+:32];
  wire bwv=wvb||rrb; wire [1:0] bwa=rrb?rra_c[4:3]:wab; wire [31:0] bwd=rrb?rrdb:wdb;
  always @(posedge clk) if(bwv) mem[{bwa,3'(b)}] <= bwd;
  wire multi=(hit[0]&&(hit[1]||hit[2]||hit[3]))||(hit[1]&&(hit[2]||hit[3]))||(hit[2]&&hit[3]);
  assign bconf[b]=multi||(rrb&&wvb);
 end
 always @(posedge clk or negedge rst_n) if(!rst_n) conf_o<=1'b0; else conf_o<=|bconf;
 // ---- reads at k+1: gated by the sector match (the k+2 OR across sectors selects)
 integer c,h,kk;
 always @(posedge clk)begin
  for(c=0;c<5;c=c+1) for(h=0;h<16;h=h+1)
   if(ra_c[c][h][8]) raw_o[c*32+h*2+:2] <= (ra_c[c][h][5:3]==3'(S)) ? mem[{ra_c[c][h][7:6],ra_c[c][h][2:0]}][h*2+:2] : 2'd0;
  for(h=0;h<16;h=h+1) if(r5v_c[h])
   for(kk=0;kk<8;kk=kk+1) raw5_o[kk*32+h*2+:2] <= (r5a_c[h][2:0]==3'(S)) ? mem[{r5a_c[h][4:3],3'(kk)}][h*2+:2] : 2'd0;
 end
endmodule

module ot_hbm_su_static_qcore_r7 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1,PRETREE=0)(
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
 input wire [4*67-1:0] slice_t,        // PRETREE: {max, vB, xB, vA, xA} per slice
 output reg fault
);
 wire rf_drain_now=rf_drain_cmd[1]&&(rf_drain_cmd[0]||MUT==16);
 // ---------------------------------------------------------------- class-5 alignment check rung (raw capture at k)
 reg c5v_p; reg [2:0] c5b_p;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) begin c5v_p<=1'b0; c5b_p<=3'd0; end
  else begin c5v_p<=rf_rd_cmd[5*9+8]; c5b_p<=rf_rd_cmd[5*9+:3]; end
 // ---------------------------------------------------------------- 8 sectors (kept, one placement region each)
 wire [5*32-1:0] raw_s [0:7]; wire [255:0] raw5_s [0:7]; wire [7:0] conf_s;
 for(genvar s=0;s<8;s=s+1)begin:g_sec
  ot_hbm_su_qcore_r7_sec #(.S(s),.MUT(MUT),.COLLPORT(COLLPORT)) u_s(.clk(clk_ctl),.rst_n(rst_n),.rd_cmd(rf_rd_cmd),
   .wv(rf_wv),.wa(rf_wa),.wd(rf_wd),.rrv(rr_wv),.rra(rr_wa),.rrd(rr_wd),.raw_o(raw_s[s]),.raw5_o(raw5_s[s]),.conf_o(conf_s[s]));
 end
 // ---------------------------------------------------------------- k+2: OR of the gated sector words
 reg [5*32-1:0] raw_or; reg [255:0] raw5_or; integer s2;
 always @*begin
  raw_or=0; raw5_or=0;
  for(s2=0;s2<8;s2=s2+1)begin raw_or=raw_or|raw_s[s2]; raw5_or=raw5_or|raw5_s[s2]; end
 end
 reg [31:0] rd [0:4]; reg [31:0] rd_x [0:4]; reg [255:0] rd5;
 integer c;
 always @(posedge clk_ctl)begin
  for(c=0;c<5;c=c+1) rd_x[c] <= raw_or[c*32+:32];
  for(c=0;c<5;c=c+1) rd[c] <= (MUT==256) ? rd_x[c] : raw_or[c*32+:32];
  rd5 <= raw5_or;
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
 wire dbad=(drain_p&&!c5_lead_q)||(c5v_p&&c5b_p!=3'd0);
 reg rc_v; reg [2:0] rc_op; reg [9:0] rc_a,rc_b,rc_d; reg [31:0] rc_tag,rc_x;
 reg [1:0] e_sl; reg e_os,e_sfu,e_tr; reg [72:8] e_f;
 always @(posedge clk_ctl)begin e_sl<=red_cmd[5:4];e_os<=red_cmd[7];e_sfu<=(COLLPORT!=0)&&red_cmd[6]&&(MUT!=64);e_f<=red_cmd[72:8];
  e_tr<=(PRETREE!=0)&&red_cmd[7]&&red_cmd[5]&&!red_cmd[6];end
 // ---------------------------------------------------------------- PRETREE join (quarter 128-word subtree)
 wire pt_v,pt_max,pt_fault; wire [31:0] pt_x;
 if(PRETREE!=0)begin:g_pretree
  wire jv,jm; wire [31:0] jx;
  ot_hbm_su_red_pretree_j #(.LAT(6),.MUT((MUT==1024)?2:0)) u_ptj(.clk(clk_ctl),.rst_n(rst_n),.slice_t(slice_t),.tree_v(jv),.tree_x(jx),
   .tree_max(jm),.fault(pt_fault));
  if(MUT==512)begin:g_mut_late
   reg lv,lm; reg [31:0] lx; always @(posedge clk_ctl)begin lv<=jv;lm<=jm;lx<=jx;end
   assign pt_v=lv; assign pt_max=lm; assign pt_x=lx;
  end else begin:g_on_time
   assign pt_v=jv; assign pt_max=jm; assign pt_x=jx;
  end
 end else begin:g_no_pretree
  assign pt_v=1'b0; assign pt_max=1'b0; assign pt_x=32'd0; assign pt_fault=1'b0;
 end
 reg e_v;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)e_v<=1'b0; else e_v<=red_cmd[73];
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)rc_v<=1'b0; else rc_v<=e_v;
 // tree operand checks (sampled with rc_x): subtree valid, and its mode matches the op (MAX_EXT <-> max tree)
 reg pt_bad; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) pt_bad<=1'b0;
  else pt_bad<=e_v&&e_tr&&(!pt_v||(e_f[72:70]==3'd1&&pt_max)||(e_f[72:70]==3'd3&&!pt_max)||
                (e_f[72:70]!=3'd0&&e_f[72:70]!=3'd1&&e_f[72:70]!=3'd3));
 always @(posedge clk_ctl)begin
  rc_op<=e_f[72:70];rc_a<=e_f[69:60];rc_b<=e_f[59:50];rc_d<=e_f[49:40];rc_tag<=e_f[39:8];
  rc_x<=e_os?(e_tr?pt_x:e_sfu?sfu_x:rf_word[4]):slice_x[e_sl*32+:32];
 end
 wire red_fault;
 ot_hbm_su_reduce_static #(.AW(10)) u_red(.clk(clk_ctl),.rst_n(rst_n),.cmd_valid(rc_v),.cmd_op(rc_op),.cmd_a(rc_a),
  .cmd_b(rc_b),.cmd_dst(rc_d),.operand_fp32(rc_x),.cmd_tag(rc_tag),.scalar_valid(red_sv),.scalar_tag(red_tag),
  .scalar_fp32(red_x),.scalar_bf16(),.fault(red_fault));
 assign red_rf_v=red_sv&&(red_tag[8]||MUT==32);
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0; else if((|conf_s)||dbad||red_fault||pt_fault||pt_bad)fault<=1'b1;
endmodule
`default_nettype wire
