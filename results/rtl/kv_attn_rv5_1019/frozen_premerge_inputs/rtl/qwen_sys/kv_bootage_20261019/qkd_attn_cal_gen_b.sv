`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): qkd_attn_cal_gen
// with BOOT-PROGRAMMABLE die ages.  Identical to rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv (kept byte-identical for the
// closed qkd_kvs_attn / qkd_kvs_attn_fl views) except that the STRETCH=1 die ages are a configuration word, not parameters:
//   cfg_cal = {F_DLY[7:0], D_RL[7:0], D_QK[7:0]}, a static configuration net from the KV die cfg (qkd_kv_die_cfg_a, pre-boot
//   image target 10, sealed, POR-held; no handshake / credit / ready):
//     D_QK  = QK_ISSUE_AGE - 34 (the ECTL kiss children's issue age; the closed tile bound 28 while the rt80 ECTL has 91 -> 57)
//     D_RL  = RL - 19 (RL = the pair FIRST_INPUT_AGE - 1, the die's derived V word latency)
//     F_DLY = the result face's stream delay (1 + D(ks_pvfst) - PV_LEAD + D(ks_pvfin) [+ face landing]): R is stretched to
//             SERVICE_END - 48 - F_DLY - PV_START (was - 49, i.e. F_DLY = 1) so the face's RESULT_AGE
//             PV_START + R + 16 + F_DLY stays on the link's fixed RESULT slot (SERVICE_END - 32) for every F_DLY, and the
//             service root ends on SERVICE_END (qkd_attn_service_root_b END = PV_START + LAST + 48 + F_DLY).
//   Every former constant becomes a registered constant from the pinned word (k_*), so each stage keeps one add.
//   F_DLY < 1 or D_QK / D_RL / F_DLY above their bound parameters (now upper bounds) set the sticky fault on go.
// Edge for edge this is qkd_attn_cal_gen #(.D_QK(q), .D_RL(r)) when cfg_cal = {1, r, q} (lockstep bench
// rtl/test/kv_bootage_1019/tb_kvba_calgen.sv); with F_DLY = f, R is (f - 1) smaller and every other output identical.
// MUT: 1-5 as qkd_attn_cal_gen; 6 = F_DLY ignored in R (the - 49 law); 7 = D_RL taken from the D_QK field.
// KVJ-B 2026-10-17: qkd_attn_cal_gen -- the attention calendar generator (kv_static_join_plan.md N1), one per KV die.
// Context length in, the 176-bit service calendar plus the programme's link ages out, computed once per token.
//
// Function: tools/qwen_attention_native/attn_calendar.calendar_w16(T, head_g3s2=G3S2) and
// tools/qwen_kv_die/compile_native_endpoint.compile_programme (compiled_tx_first / compiled_end at compiled_rx_cmd =
// RX_CMD), in closed form (equal over T = 1..8192, both G3S2 values; bench tb_qkd_attn_cal_gen against those
// generators):
//   scan(T)  = last ECTL QK scan of stack 0 (static_qk_calendar: consume age 34): ns = 128 (T>>9) + min(128, T&511),
//              m = ns-1;  ns <= 1024: m>>3;  else mm = m-64: 128 + 8 mm[10:7] + (min(63, mm[6:0]) >> 3)
//   zwalk(T) = max over stacks s (T > 128 s) of, with x = T-1-128 s, q = x>>9, r = x&511:
//              x < 127: x>>3;  else 15 (q+1) - max(0, 15 - (r>>3)) + [r < 120]
//   LMAX = scan + 151 + 5 G3S2, EXP = LMAX + 15, Z = EXP + 250 + zwalk, HUB_LMAX = LMAX + 7,
//   HUB_Z = Z + 261, HUB_RECIP = Z + 342, HUB_PUB = Z + 415,
//   P0 = R = 137 + 16 (((T+255)>>8)+1), P1 = T > 128 ? 137 + 16 (((T+127)>>8)+1) : 137,
//   PV_START = Z - 64 + max(0, 481 - P0)   (= max(EXP + zwalk + 186, HUB_PUB + 2 - P0); then R = P0 exactly),
//   tx_first = RX_CMD + 2 + (PV_START + P0 + 49) - 31,  end = tx_first + 34.
// Calendar field order MSB..LSB {R, P1, P0, PV_START, HUB_PUB, HUB_RECIP, HUB_Z, HUB_LMAX, Z, LMAX, EXP} (16 b each).
// Timing: a 10-edge feed-forward pipeline, initiation interval 1; every stage is at most one <=16-bit add/subtract or
// compare (plus wiring / a 2:1 select), no multiplier, no wide combinational arithmetic (833 ps).  go -> done = LAT
// edges; the result is held in the output registers until the next done (ctx_t is constant over the token's 36 layers).
// fault (sticky): a go with T outside 1..8192.  Static schedule: no ready/credit; the compiler places go >= LAT edges
// before the attention programme's issue.
// STRETCH=1 (KVJ-SMALL 10-17, coordinator decision 4; the static die's production setting, the KV static programme
// compiler law kv_static_programme.attention_calendar(T, profile, service_end)): the die ages shift the chain and the
// pair outputs before the PV_START max, and R stretches so the service ends on the link's fixed RESULT slot:
//   LMAX..HUB_PUB += D_QK (= QK_ISSUE_AGE - 34),  P0 / P1 += D_RL (= RL - 19),  PV_START = Z - 64 + max(0, 481 - P0)
//   on the shifted fields,  R = SERVICE_END - 49 - PV_START,  tx_first = RX_CMD + 2 + SERVICE_END - 31 (constant),
//   end = tx_first + 34 (constant).  fault also rises (sticky) when the context does not fit the slot (R < P0, i.e.
//   PV_START + P0 + 49 > SERVICE_END): the compiler refuses such a die image, so this is a configuration check only.
// STRETCH=0 keeps the minimal-R / per-T link-age generator (bench-feeding calendars; D_QK / D_RL / SERVICE_END unused).
// MUT (diagnostic, bench only): 1 = zwalk [r <= 120], 2 = scan without min(63, .), 3 = P1 always the non-empty law,
// 4 = R stretched one edge short, 5 = D_RL left out of the PV_START max.
module qkd_attn_cal_gen_b #(
 parameter integer G3S2=1,
 parameter integer RX_CMD=2,
 parameter integer STRETCH=0,
 parameter integer D_QK=255,   // bound
 parameter integer D_RL=255,   // bound
 parameter integer F_DLY=127,  // bound
 parameter integer SERVICE_END=1777,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire [23:0] cfg_cal,          // {F_DLY, D_RL, D_QK} boot-loaded (static after the seal)
 input wire go,
 input wire [13:0] ctx_t,
 input wire [15:0] epoch,
 output reg [175:0] cal,
 output reg [15:0] rx_cmd,tx_first,end_age,
 output reg [15:0] cal_epoch,
 output reg done,valid,
 output reg fault
);
 localparam integer LAT=10;
 localparam integer TXF=RX_CMD+2+SERVICE_END-31;
 reg [23:0] cfg_q;reg [11:0] k_dr,k_po0,k_po1;reg [15:0] k_lm,k_rl;reg cfg_bad;
 wire [7:0] c_dq=cfg_q[7:0],c_dr=(MUT==7)?cfg_q[7:0]:cfg_q[15:8],c_fd=cfg_q[23:16];
 always @(posedge ck)begin
  cfg_q<=cfg_cal;
  k_dr<=STRETCH?12'(c_dr):12'd0;                                     // DR
  k_po0<=12'd153+(STRETCH?12'(c_dr):12'd0);                          // 153 + DR
  k_po1<=12'd137+(STRETCH?12'(c_dr):12'd0);                          // 137 + DR
  k_lm<=16'(151+5*G3S2)+(STRETCH?16'(c_dq):16'd0);                   // 151 + 5 G3S2 + DQ
  k_rl<=16'(SERVICE_END-48)-((MUT==6)?16'd1:16'(c_fd));              // RLINK = SERVICE_END - 48 - F_DLY
  cfg_bad<=(c_dq>8'(D_QK))||(c_dr>8'(D_RL))||(c_fd<8'd1)||(c_fd>8'(F_DLY));
 end
 // ---- S1: capture ----
 reg v1;reg [13:0] t1;reg [15:0] e1;
 always @(posedge ck or negedge rst_n)if(!rst_n)v1<=0;else v1<=go;
 always @(posedge ck)if(go)begin t1<=ctx_t;e1<=epoch;end
 // ---- S2: per-stack offsets, stack-0 row count, P.V issue rounds ----
 reg v2,f2,big1;reg [15:0] e2;reg [12:0] x2[0:3];reg [3:0] p2;reg [11:0] ns2;reg [5:0] c0_2,c1_2;
 wire [8:0] tl=t1[8:0];
 always @(posedge ck or negedge rst_n)if(!rst_n)v2<=0;else v2<=v1;
 always @(posedge ck)if(v1)begin
  f2<=(t1==14'd0)||(t1>14'd8192);e2<=e1;
  for(integer s=0;s<4;s=s+1)begin x2[s]<=13'(t1-14'd1-14'(128*s));p2[s]<=t1>14'(128*s);end
  ns2<=12'({t1[13:9],7'd0}+((tl>=9'd128)?14'd128:14'(tl)));
  c0_2<=6'((t1+14'd255)>>8);c1_2<=6'((t1+14'd127)>>8);big1<=t1>14'd128;
 end
 // ---- S3: zwalk lane terms, scan operands, pair output ages ----
 reg v3,f3;reg [15:0] e3;reg [3:0] p3,sm3,b3;reg [7:0] a3[0:3];reg [3:0] cnt3[0:3];reg [9:0] xs3[0:3];
 reg [10:0] m3,mm3;reg nbig3;reg [11:0] po0_3,po1_3;
 always @(posedge ck or negedge rst_n)if(!rst_n)v3<=0;else v3<=v2;
 always @(posedge ck)if(v2)begin
  f3<=f2;e3<=e2;p3<=p2;
  for(integer s=0;s<4;s=s+1)begin
   sm3[s]<=x2[s]<13'd127;
   xs3[s]<=x2[s][12:3];
   a3[s]<=8'({x2[s][12:9],4'd0}-{4'd0,x2[s][12:9]}+8'd15);            // 15 (q+1)
   cnt3[s]<=(x2[s][8:3]>=6'd15)?4'd0:4'(4'd15-x2[s][6:3]);            // max(0, 15 - (r>>3))
   b3[s]<=(MUT==1)?(x2[s][8:0]<=9'd120):(x2[s][8:0]<9'd120);
  end
  m3<=11'(ns2-12'd1);mm3<=11'(ns2-12'd65);nbig3<=ns2<=12'd1024;
  po0_3<=12'(k_po0+{c0_2,4'd0});                               // 137 + 16 (c0 + 1) (+ D_RL)
  po1_3<=(big1||MUT==3)?12'(k_po0+{c1_2,4'd0}):k_po1;
 end
 // ---- S4: lane values, scan, P.V adjust ----
 reg v4,f4;reg [15:0] e4;reg [9:0] zv4[0:3];reg [7:0] scan4;reg [11:0] po0_4,po1_4;reg [8:0] adj4;
 wire [6:0] lo7=mm3[6:0];
 always @(posedge ck or negedge rst_n)if(!rst_n)v4<=0;else v4<=v3;
 always @(posedge ck)if(v3)begin
  f4<=f3;e4<=e3;po0_4<=po0_3;po1_4<=po1_3;
  for(integer s=0;s<4;s=s+1)zv4[s]<=!p3[s]?10'd0:sm3[s]?xs3[s]:10'(a3[s]-{4'd0,cnt3[s]}+{7'd0,b3[s]});
  scan4<=nbig3?8'(m3>>3):8'(8'd128+{1'b0,mm3[10:7],3'd0}+((MUT==2)?{5'd0,lo7[5:3]}|{4'd0,lo7[6],3'd0}:((lo7>=7'd63)?8'd7:{5'd0,lo7[5:3]})));
  if(MUT==5)adj4<=(po0_3-k_dr<=12'd480)?9'(12'd481-(po0_3-k_dr)):9'd0;
  else adj4<=(po0_3<=12'd480)?9'(12'd481-po0_3):9'd0;
 end
 // ---- S5: zwalk max level 1, LMAX ----
 reg v5,f5;reg [15:0] e5;reg [9:0] za5,zb5;reg [15:0] lmax5;reg [11:0] po0_5,po1_5;reg [8:0] adj5;
 always @(posedge ck or negedge rst_n)if(!rst_n)v5<=0;else v5<=v4;
 always @(posedge ck)if(v4)begin
  f5<=f4;e5<=e4;po0_5<=po0_4;po1_5<=po1_4;adj5<=adj4;
  za5<=(zv4[0]>zv4[1])?zv4[0]:zv4[1];zb5<=(zv4[2]>zv4[3])?zv4[2]:zv4[3];
  lmax5<=16'(scan4)+k_lm;
 end
 // ---- S6: zwalk max, EXP, Z base, HUB_LMAX ----
 reg v6,f6;reg [15:0] e6;reg [9:0] zw6;reg [15:0] lmax6,exp6,zb6,hl6;reg [11:0] po0_6,po1_6;reg [8:0] adj6;
 always @(posedge ck or negedge rst_n)if(!rst_n)v6<=0;else v6<=v5;
 always @(posedge ck)if(v5)begin
  f6<=f5;e6<=e5;po0_6<=po0_5;po1_6<=po1_5;adj6<=adj5;lmax6<=lmax5;
  zw6<=(za5>zb5)?za5:zb5;exp6<=lmax5+16'd15;zb6<=lmax5+16'd265;hl6<=lmax5+16'd7;
 end
 // ---- S7: Z; link-age base ----
 reg v7,f7;reg [15:0] e7;reg [15:0] lmax7,exp7,z7,hl7,pvo7,lk7,le7;reg [11:0] po0_7,po1_7;
 always @(posedge ck or negedge rst_n)if(!rst_n)v7<=0;else v7<=v6;
 always @(posedge ck)if(v6)begin
  f7<=f6;e7<=e6;lmax7<=lmax6;exp7<=exp6;hl7<=hl6;po0_7<=po0_6;po1_7<=po1_6;
  z7<=zb6+16'(zw6);
  pvo7<=16'(adj6)-16'd64;                                              // PV_START - Z (mod 2^16)
  lk7<=16'(po0_6)+16'(RX_CMD+20);                                      // tx_first - PV_START
  le7<=16'(po0_6)+16'(RX_CMD+54);                                      // end - PV_START
 end
 // ---- S8: hub ages, PV_START ----
 reg v8,f8;reg [15:0] e8;reg [15:0] lmax8,exp8,z8,hl8,hz8,hr8,hp8,pv8,lk8,le8;reg [11:0] po0_8,po1_8;
 always @(posedge ck or negedge rst_n)if(!rst_n)v8<=0;else v8<=v7;
 always @(posedge ck)if(v7)begin
  f8<=f7;e8<=e7;lmax8<=lmax7;exp8<=exp7;z8<=z7;hl8<=hl7;po0_8<=po0_7;po1_8<=po1_7;lk8<=lk7;le8<=le7;
  hz8<=z7+16'd261;hr8<=z7+16'd342;hp8<=z7+16'd415;pv8<=z7+pvo7;
 end
 // ---- S9: link ages ----
 reg v9,f9;reg [15:0] e9;reg [175:0] cal9;reg [15:0] tx9,en9,p09;reg [16:0] r9;
 always @(posedge ck or negedge rst_n)if(!rst_n)v9<=0;else v9<=v8;
 always @(posedge ck)if(v8)begin
  f9<=f8;e9<=e8;
  r9<={1'b0,k_rl-((MUT==4)?16'd1:16'd0)}-{1'b0,pv8};                          // stretched R (bit 16: does not fit)
  p09<=16'(po0_8);
  cal9<={STRETCH?k_rl-((MUT==4)?16'd1:16'd0)-pv8:16'(po0_8),16'(po1_8),16'(po0_8),pv8,hp8,hr8,hz8,hl8,z8,lmax8,exp8};
  tx9<=STRETCH?16'(TXF):pv8+lk8;en9<=STRETCH?16'(TXF+34):pv8+le8;
 end
 // ---- S10: held result ----
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin done<=0;valid<=0;fault<=0;cal<=0;rx_cmd<=16'(RX_CMD);tx_first<=0;end_age<=0;cal_epoch<=0;end
  else begin
   done<=v9;
   if(v9)valid<=1;else if(go)valid<=0;     // a result landing on a go edge (II = 1) stays valid
   if(v9)begin
    cal<=cal9;tx_first<=tx9;end_age<=en9;cal_epoch<=e9;rx_cmd<=16'(RX_CMD);
    if(f9||(STRETCH!=0&&(r9[16]||r9[15:0]<p09))||(STRETCH!=0&&cfg_bad))fault<=1;
   end
  end
 end
endmodule
