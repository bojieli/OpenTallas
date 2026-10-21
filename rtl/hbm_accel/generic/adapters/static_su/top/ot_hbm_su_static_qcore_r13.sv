// r13 (HBM-QCORE9 2026-10-20 23:00): r12 + (a) FP adders = Codex FP6 ot_hdc_fp32_add_n32 (d73bee5f7: native max 32 standalone,
// LAT 6 DRST 0 bit-exact to ot_hdc_fp32_add_lat; kit synthesis runs its copy-alias + splitter canonicalize step) in the
// pre-tree (ot_hbm_su_red_pretree_j_r13) and reducer (ot_hbm_su_reduce_static_r13); (b) per-writer bank hit compare
// (r12 hit_b 44-46 loads); (c) reset landing 24 copies (kit). Same ports, edges, function.
// r12 (HBM-QCORE8 2026-10-20 22:40): r11 census (max 281): ABC pushed the bank hits into the 16-bit data AND-OR (hit_b
// 52-78 loads) -> the one-hot select is now a kept submodule (selq) so only sel drives the data; reducer r12 writes
// replicated data under two per-SRAM kept mask decodes (r10/r11: 8 x 96-load pd decodes); reset via kit landing copies.
// r11 (HBM-QCORE8 2026-10-20 22:20): r10 gate census (max 273) showed loads are counted THROUGH kept hierarchy: duplicated
// consumers need duplicated DRIVER flops.  Sector: per-writer sector match + bank predecode once (hit per bank), row/COLL
// fields in 2 kept copies (4 banks each); pretree: per-node-byte kept copies of mode / valid, per-byte comparators.
// r10 (HBM-QCORE8 2026-10-20): r9 + native-32 writer / operand / pretree / reducer fixes. Same ports, edges, function.
//  * WRITES: per (bank, 16-bit half) kept module ot_hbm_su_qcore_r13_wb computes the priority select, row enables and data
//    from the sector writer copies (r9: one decode per bank drove 32-bit data muxes and 32 row flops: 437 loads).
//  * OPERAND rc_x: one-hot source selects registered at the e_ edge in 4 kept per-byte copies (r9 e_sl 128 loads).
//  * PRETREE: ot_hbm_su_red_pretree_j_r13 (per-byte kept operand selects); REDUCER: ot_hbm_su_reduce_static_r10
//    (kept per-half write-data select pipeline). FP adders stay ot_hdc_fp32_add_lat.
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
//  * ONE kept module per sector (ot_hbm_su_qcore_r13_sec, keep_hierarchy; the kit places each as a placement region):
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
module ot_hbm_su_qcore_r13_kq #(parameter integer W=1,RST=0)(input wire clk,rst_n,input wire [W-1:0] d,(* keep = 1 *) output reg [W-1:0] q);
 if(RST!=0)begin:g_r always @(posedge clk or negedge rst_n) if(!rst_n) q<={W{1'b0}}; else q<=d; end
 else begin:g_n always @(posedge clk) q<=d; end
endmodule

// One RF sector (banks 8S..8S+7, rows 0..3): storage, writer copies + decode, read copies + gated k+1 read registers.
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_sec #(parameter integer S=0,MUT=0,COLLPORT=1)(
 input wire clk,rst_n,
 input wire [5*32-1:0] rd_oh, input wire [3:0] r5_oh,
 input wire [39:0] rd_ve,rd_key, input wire [7:0] r5_ve,r5_key,
 input wire [3:0] wv, input wire [31:0] wa, input wire [127:0] wd,
 input wire rrv, input wire [4:0] rra, input wire [255:0] rrd,
 output reg [5*32-1:0] raw_o,                  // classes 0..4, k+1, zero unless this sector was addressed
 output reg [255:0] raw5_o,                    // class 5 row, k+1, zero unless this sector was addressed
 output reg conf_o                             // write conflict in this sector (registered)
);
 // ---- writer copies (raw, k).  r11: data / address / valid copies; row + COLL fields in 2 copies (banks 0-3, 4-7)
 wire [31:0] wa_c; wire [127:0] wd_c; wire [3:0] wv_c; wire [255:0] rrd_c;
 ot_hbm_su_qcore_r13_kq #(.W(128),.RST(0)) u_wd(.clk(clk),.rst_n(rst_n),.d(wd),.q(wd_c));
 ot_hbm_su_qcore_r13_kq #(.W(32),.RST(0)) u_wa(.clk(clk),.rst_n(rst_n),.d(wa),.q(wa_c));
 ot_hbm_su_qcore_r13_kq #(.W(4),.RST(1)) u_wv(.clk(clk),.rst_n(rst_n),.d(wv),.q(wv_c));
 ot_hbm_su_qcore_r13_kq #(.W(256),.RST(0)) u_rr(.clk(clk),.rst_n(rst_n),.d(rrd),.q(rrd_c));
 wire [7:0] row_g [0:1]; wire [4:0] rra_g [0:1]; wire rrv_g [0:1];
 for(genvar g=0;g<2;g=g+1)begin:g_rw
  ot_hbm_su_qcore_r13_kq #(.W(13),.RST(0)) u_rw(.clk(clk),.rst_n(rst_n),.d({wa[30+:2],wa[22+:2],wa[14+:2],wa[6+:2],rra}),
   .q({row_g[g],rra_g[g]}));
  ot_hbm_su_qcore_r13_kq #(.W(1),.RST(1)) u_rv(.clk(clk),.rst_n(rst_n),.d(rrv),.q(rrv_g[g]));
 end
 // bank hit predecode (wa[w*8+:6] == 8*S+b): sector match once per writer, 3-bit bank decode
 // r13: the 3-bit bank compare is done INSIDE each (bank, half) writer (r12 census: hit_b[b][3] = sel[3] fanned into both
 // halves' data AND-OR, 44-46 loads); smatch / bank bits now drive 16 writer copies each.
 wire [3:0] smatch; wire [11:0] wbk;
 for(genvar w=0;w<4;w=w+1)begin:g_sm assign smatch[w]=wv_c[w]&&wa_c[w*8+3+:3]==3'(S); assign wbk[w*3+:3]=wa_c[w*8+:3]; end
 // ---- registered onehot selectors. Global predecode is before the old command-capture edge.
 (* keep = 1 *) reg [31:0] rq[0:4][0:1];
 (* keep = 1 *) reg [3:0] r5q[0:15];
 wire cv[0:4][0:7]; wire c5v[0:7][0:3];
 for(genvar h=0;h<16;h=h+1)begin:g_rq
  if(h<2)begin:g_ncap
   for(genvar c=0;c<5;c=c+1)begin:g_c
    always @(posedge clk) rq[c][h]<=rd_oh[c*32+:32];
   end
  end
  always @(posedge clk) r5q[h]<=r5_oh;
 end
 for(genvar c=0;c<5;c=c+1)begin:g_cv
  for(genvar g=0;g<8;g=g+1)begin:g_g
   ot_hbm_su_qcore_r13_xor u_v(.a(rd_ve[c*8+g]),.b(rd_key[c*8+g]),.y(cv[c][g]));
  end
 end
 for(genvar g=0;g<8;g=g+1)begin:g_c5v
  for(genvar bp=0;bp<4;bp=bp+1)begin:g_bp
   ot_hbm_su_qcore_r13_xor u_v(.a(r5_ve[g]),.b(r5_key[g]),.y(c5v[g][bp]));
  end
 end
 // ---- storage: 8 banks x 4 rows x 2 halves, word index {row2, bank3}; writes commit k+1 (r10: per (bank, half) kept writer)
 wire [1023:0] memf;                                    // word n = memf[n*32+:32]
 wire [7:0] bconf;
 for(genvar b=0;b<8;b=b+1)begin:g_b
  wire [1:0] cf;
  for(genvar hf=0;hf<2;hf=hf+1)begin:g_h
   wire [3:0] en; wire [15:0] d; wire [63:0] wd16;
   for(genvar w=0;w<4;w=w+1)begin:g_w assign wd16[w*16+:16]=wd_c[w*32+hf*16+:16]; end
   ot_hbm_su_qcore_r13_wb #(.S(S),.B(b),.COLLPORT(COLLPORT)) u_wb(.sm(smatch),.wbk(wbk),.row(row_g[b/4]),.wd16(wd16),.rrv(rrv_g[b/4]),.rra(rra_g[b/4]),
    .rrd16(rrd_c[32*((MUT==128)?7-b:b)+hf*16+:16]),.en(en),.d(d),.conf(cf[hf]));
   for(genvar r=0;r<4;r=r+1)begin:g_r
    reg [15:0] q;
    always @(posedge clk) if(en[r]) q<=d;
    assign memf[(r*8+b)*32+hf*16+:16]=q;
   end
  end
  assign bconf[b]=cf[0];
 end
 always @(posedge clk or negedge rst_n) if(!rst_n) conf_o<=1'b0; else conf_o<=|bconf;
 // ---- exact old valid/hold edges, with onehot selected data.
 wire [1:0] read_word[0:4][0:15]; wire [1:0] read5_word[0:15][0:7];
 for(genvar h=0;h<16;h=h+1)begin:g_read
  for(genvar c=0;c<5;c=c+1)begin:g_c
   reg [1:0] val; integer n;
   always @*begin val=0; for(n=0;n<32;n=n+1) val=val|({2{rq[c][h/8][n]}}&memf[n*32+h*2+:2]); end
   assign read_word[c][h]=val;
   always @(posedge clk) if(cv[c][h/2]) raw_o[c*32+h*2+:2]<=read_word[c][h];
  end
  for(genvar k=0;k<8;k=k+1)begin:g_k
   reg [1:0] val; integer n;
   always @*begin val=0; for(n=0;n<4;n=n+1) val=val|({2{r5q[h][n]}}&memf[(n*8+k)*32+h*2+:2]); end
   assign read5_word[h][k]=val;
   always @(posedge clk) if(c5v[h/2][k/2]) raw5_o[k*32+h*2+:2]<=read5_word[h][k];
  end
 end

endmodule

module ot_hbm_su_static_qcore_r13 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1,PRETREE=0)(
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
 // Factored decode: every native predecode bit has at most16word terms;
 // every final word select reaches16capturebits. Encodedvalid retains the old every-edge hold semantics.
 wire [1279:0] rd_all; wire [31:0] r5_all; wire [39:0] rd_ve,rd_key; wire [7:0] r5_ve,r5_key;
 for(genvar c=0;c<5;c=c+1)begin:g_dec
  ot_hbm_su_qcore_r13_dec9 u_d(.a(rf_rd_cmd[c*9+:9]),.y(rd_all[c*256+:256]));
  for(genvar g=0;g<8;g=g+1)begin:g_g
   ot_hbm_su_qcore_r13_kq #(.W(2),.RST(0)) u_v(.clk(clk_ctl),.rst_n(rst_n),
    .d({rf_rd_cmd[c*9+8]^rf_rd_cmd[c*9],rf_rd_cmd[c*9]}),.q({rd_ve[c*8+g],rd_key[c*8+g]}));
  end
 end
 ot_hbm_su_qcore_r13_dec6 u_d5(.a(rf_rd_cmd[48+:6]),.y(r5_all));
 for(genvar g=0;g<8;g=g+1)begin:g_v5
  ot_hbm_su_qcore_r13_kq #(.W(2),.RST(0)) u_v(.clk(clk_ctl),.rst_n(rst_n),
   .d({rf_rd_cmd[53]^rf_rd_cmd[51],rf_rd_cmd[51]}),.q({r5_ve[g],r5_key[g]}));
 end
 // ---------------------------------------------------------------- 8 sectors (kept, one placement region each)
 wire [5*32-1:0] raw_s [0:7]; wire [255:0] raw5_s [0:7]; wire [7:0] conf_s;
 for(genvar s=0;s<8;s=s+1)begin:g_sec
  wire [159:0] local_oh; wire [3:0] local_5;
  for(genvar c=0;c<5;c=c+1)begin:g_c
   for(genvar n=0;n<32;n=n+1)begin:g_n
    assign local_oh[c*32+n]=rd_all[c*256+(n/8)*64+s*8+n%8];
   end
  end
  for(genvar n=0;n<4;n=n+1)begin:g_n5 assign local_5[n]=r5_all[n*8+s]; end
  ot_hbm_su_qcore_r13_sec #(.S(s),.MUT(MUT),.COLLPORT(COLLPORT)) u_s(.clk(clk_ctl),.rst_n(rst_n),.rd_oh(local_oh),.r5_oh(local_5),.rd_ve(rd_ve),.rd_key(rd_key),.r5_ve(r5_ve),.r5_key(r5_key),
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
  ot_hbm_su_red_pretree_j_r13 #(.LAT(6),.MUT((MUT==1024)?2:0)) u_ptj(.clk(clk_ctl),.rst_n(rst_n),.slice_t(slice_t),.tree_v(jv),.tree_x(jx),
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
  end

 // r10: rc_x source as 4 kept per-byte one-hot copies, registered on the e_ edge (same decode as e_os/e_tr/e_sfu/e_sl)
 wire [6:0] oh_d={(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd3,(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd2,
                  (red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd1,(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd0,
                  red_cmd[7]&&!((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])&&!((COLLPORT!=0)&&red_cmd[6]&&(MUT!=64)),
                  red_cmd[7]&&!((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])&&((COLLPORT!=0)&&red_cmd[6]&&(MUT!=64)),
                  red_cmd[7]&&((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])};   // {sl3,sl2,sl1,sl0,rf,sfu,pt}
 wire [31:0] rcx_d;
 for(genvar y=0;y<4;y=y+1)begin:g_osel
  wire [6:0] oh;
  ot_hbm_su_qcore_r13_kq #(.W(7),.RST(0)) u_oh(.clk(clk_ctl),.rst_n(rst_n),.d(oh_d),.q(oh));
  ot_hbm_su_qcore_r13_xsel8 u_x(.oh(oh),.pt(pt_x[y*8+:8]),.sfu(sfu_x[y*8+:8]),.rf(rf_word[4][y*8+:8]),
   .s0(slice_x[0*32+y*8+:8]),.s1(slice_x[1*32+y*8+:8]),.s2(slice_x[2*32+y*8+:8]),.s3(slice_x[3*32+y*8+:8]),.y(rcx_d[y*8+:8]));
 end
 always @(posedge clk_ctl) rc_x<=rcx_d;
 wire red_fault;
 ot_hbm_su_reduce_static_r13 #(.AW(10)) u_red(.clk(clk_ctl),.rst_n(rst_n),.cmd_valid(rc_v),.cmd_op(rc_op),.cmd_a(rc_a),
  .cmd_b(rc_b),.cmd_dst(rc_d),.operand_fp32(rc_x),.cmd_tag(rc_tag),.scalar_valid(red_sv),.scalar_tag(red_tag),
  .scalar_fp32(red_x),.scalar_bf16(),.fault(red_fault));
 assign red_rf_v=red_sv&&(red_tag[8]||MUT==32);
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0; else if((|conf_s)||dbad||red_fault||pt_fault||pt_bad)fault<=1'b1;
endmodule

// r13: bank hit compare per writer copy. r11 writer for one (bank, 16-bit half) of sector S: last-writer-wins one-hot select (as r5) on the predecoded bank hits,
// COLL row writer, row enables.
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_wb #(parameter integer S=0,B=0,COLLPORT=1)(
 input wire [3:0] sm, input wire [11:0] wbk, input wire [7:0] row, input wire [63:0] wd16,
 input wire rrv, input wire [4:0] rra, input wire [15:0] rrd16,
 output wire [3:0] en, output wire [15:0] d, output wire conf
);
 wire [3:0] hit, sel; wire wvb, multi;
 for(genvar w=0;w<4;w=w+1)begin:g_hit assign hit[w]=sm[w]&&wbk[w*3+:3]==3'(B); end
 ot_hbm_su_qcore_r13_selq u_q(.hit(hit),.sel(sel),.any(wvb),.multi(multi));
 wire [15:0] wdb=({16{sel[0]}}&wd16[0+:16])|({16{sel[1]}}&wd16[16+:16])|({16{sel[2]}}&wd16[32+:16])|({16{sel[3]}}&wd16[48+:16]);
 wire [1:0] wab=({2{sel[0]}}&row[0+:2])|({2{sel[1]}}&row[2+:2])|({2{sel[2]}}&row[4+:2])|({2{sel[3]}}&row[6+:2]);
 wire rrb=(COLLPORT!=0)&&rrv&&rra[2:0]==3'(S);
 wire bwv=wvb||rrb; wire [1:0] bwa=rrb?rra[4:3]:wab;
 assign d=rrb?rrd16:wdb;
 for(genvar r=0;r<4;r=r+1)begin:g_en assign en[r]=bwv&&bwa==2'(r); end
 assign conf=multi||(rrb&&wvb);
endmodule

// r10 operand byte select: one-hot {sl3,sl2,sl1,sl0,rf,sfu,pt}
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_xsel8(input wire [6:0] oh, input wire [7:0] pt,sfu,rf,s0,s1,s2,s3, output wire [7:0] y);
 assign y=({8{oh[0]}}&pt)|({8{oh[1]}}&sfu)|({8{oh[2]}}&rf)|({8{oh[3]}}&s0)|({8{oh[4]}}&s1)|({8{oh[5]}}&s2)|({8{oh[6]}}&s3);
endmodule

// r12: last-writer-wins one-hot select of the predecoded bank hits, kept so the hits never fan into the data AND-OR
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_selq(input wire [3:0] hit, output wire [3:0] sel, output wire any, multi);
 assign sel={hit[3],hit[2]&&!hit[3],hit[1]&&!hit[2]&&!hit[3],hit[0]&&!hit[1]&&!hit[2]&&!hit[3]};
 assign any=|hit;
 assign multi=(hit[0]&&(hit[1]||hit[2]||hit[3]))||(hit[1]&&(hit[2]||hit[3]))||(hit[2]&&hit[3]);
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_xor(input wire a,b,output wire y);assign y=a^b;endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec4(input wire[3:0]a,output wire[15:0]y);
 for(genvar i=0;i<16;i=i+1)begin:g assign y[i]=(a==4'(i));end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec5v(input wire[4:0]a,output wire[15:0]y);
 for(genvar i=0;i<16;i=i+1)begin:g assign y[i]=(a=={1'b1,4'(i)});end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec9(input wire[8:0]a,output wire[255:0]y);
 wire[15:0]lo,hi;ot_hbm_su_qcore_r13_dec4 u_l(.a(a[3:0]),.y(lo));ot_hbm_su_qcore_r13_dec5v u_h(.a(a[8:4]),.y(hi));
 for(genvar i=0;i<256;i=i+1)begin:g assign y[i]=lo[i%16]&hi[i/16];end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec3(input wire[2:0]a,output wire[7:0]y);
 for(genvar i=0;i<8;i=i+1)begin:g assign y[i]=(a==3'(i));end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec3v(input wire[2:0]a,output wire[3:0]y);
 for(genvar i=0;i<4;i=i+1)begin:g assign y[i]=(a=={1'b1,2'(i)});end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec6(input wire[5:0]a,output wire[31:0]y);
 wire[7:0]lo;wire[3:0]hi;ot_hbm_su_qcore_r13_dec3 u_l(.a(a[2:0]),.y(lo));ot_hbm_su_qcore_r13_dec3v u_h(.a(a[5:3]),.y(hi));
 for(genvar i=0;i<32;i=i+1)begin:g assign y[i]=lo[i%8]&hi[i/8];end
endmodule

`default_nettype wire
