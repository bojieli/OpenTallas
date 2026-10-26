`timescale 1ns/1ps
// KV-FLOOR2 2026-10-20 r2 STRUCTURAL SAFE REBUILD (same ports, same parameters, same scheduled token/data edges as r1):
//   r1 gate 1 failed the pre-gate native census (rst_q 277, start_r 70, IDLE&start load decode 79, 33, pid 36, age[1] 33).
//   * reset: control / valid bits only (owner 10-20 09:05); datapath unreset (lim, nq, phase counters, request walker
//     q/nq/lim, pin data words); reset via ot_rst_relay_bounded32 (16 kept leaves, <= 18 clears each). Boot-only:
//     reset release reaches the control flops 3 edges later than r1 (relay root/second/leaf); assertion stays async.
//   * start / pair_id / fia_bad / IDLE: kept registered copies (start_k, pid_k, fbad_k, idle_k = state_n==IDLE one-hot
//     copies), one (start, idle, fia_bad) triple per load group (ep, nq_end, lim, nq, pa_c, pa_n; walker active/q, lim, nq).
//   * age -> two kept pa counters (pa = age + 1: pa_c check side, pa_n next/cmd side), same value every edge.
//   * cv_r all-equal check as and/or trees (cv_r[0] no longer drives 32 compares).
//   MUT 3 (bench negative control of the replica structure): the pa_n copy loads 2 at start (one edge early).
// KV-BIND8 2026-10-20: PAIR END FLOOR successor of ot_qwen_tp8_pv_wide_ctl_tb (boot-age pair control).  Identical except:
//   END_FLOOR=1: the FEED phase ends, and out_age is published, on the issue count of PAIR 0 (nq_end = w16_nq(T, 0)) for
//   both pair straps.  Pair 1 issues exactly its own rows (requests, arrival checks and column takes use nq, unchanged);
//   it only stays in FEED for nq_end - nq extra edges with no row in flight, then drains / reduces / joins as before.
//   So both pairs' results leave at the SAME static age P0 = P1 for every context (attn_calendar w16_pair_out(T, 0)):
//   qkd_pv_fin_s |P0 - P1| <= SKEW holds with SKEW 1 at every context (was 0 / 16 / 32 when T <= 128 or T mod 256 in
//   1..128: KV_STATIC_PARAMS ATTN_CALENDAR PVFIN_PAIR_SKEW, 4096 of 8192 contexts on gen9d11r).  Token cost 0: the pvfin
//   join already waits for max(P0, P1) = P0.  No stall, no handshake: a fixed, compiler-known age per context.
//   END_FLOOR=0 reproduces ot_qwen_tp8_pv_wide_ctl_tb edge for edge (negative control of the floor bench).
// Bench: tools/qwen_kv_die/pv_floor_bench.sh (tb_qkd_pvw_die_t on the trunked pair, golden bit-exact, both pairs).
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): the PV pair control
// tile ot_qwen_tp8_pv_wide_ctl_t with a BOOT-PROGRAMMABLE FIRST_INPUT_AGE.  Identical to
// rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_t.sv (kept byte-identical for its closed kit) except:
//   cfg_fia[7:0] = FIRST_INPUT_AGE as a static configuration net from the KV die cfg (qkd_kv_die_cfg_a, pre-boot image target
//   10, sealed before the first token; POR-held; no handshake / credit / ready).  The die derives it from its relay plan /
//   netlist (pair FIRST_INPUT_AGE = 4 + W + DQ + RT + 1, kv_static_params) and the generator FAILS when the boot image
//   value differs.  The parameter FIRST_INPUT_AGE is the upper bound; 1 <= cfg_fia <= bound, else a start faults.
//   Every compile-time use of FIRSTI (= FIRST_INPUT_AGE + 1) becomes a registered constant derived from the pinned word
//   (k_* below, static after the seal), so the per-edge logic keeps its depth (one add / compare as before).
// Edge for edge this is ot_qwen_tp8_pv_wide_ctl_t #(.FIRST_INPUT_AGE(a)) when cfg_fia = a (lockstep bench
// rtl/test/kv_bootage_1019/tb_kvba_pvctl.sv).
// MUT (bench negative controls): 1 = arrival check slot one edge late (k_qc + 1); 2 = range check off.
// KVPLAN 1815 (2026-10-16, COORDINATOR STANDARD item 1): the PV pair control tile for the TRUNKED pair successor
// (ot_qwen_tp8_pv_wide_pair_t).  Identical to ot_qwen_tp8_pv_wide_ctl (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv, unchanged,
// its closed kits stay valid) except two static parameters of the die distribution:
//   TRUNK_D  registered station stages between this tile's cmd pin register and every tile's command pin (the V / e words
//            take the same TRUNK_D stages from the pair face, so command and data meet exactly as in the original pair);
//   FLAG_D   registered stages from every column's y_valid / fault pins back to col_valid / col_fault here.
// The column output check slot moves by TRUNK_D + FLAG_D (COL_CHK), the static output age by TRUNK_D; wage widens 6 -> 8 b.
// Defaults TRUNK_D = FLAG_D = 0 reproduce the original tile cycle for cycle (pinned by the pair_t bench at D = 0).
// Pair control tile: calendar walk, V requests, arrival identity per port, the column command word, output check.
// Every port is registered at the pin: inputs (start/context/epoch, arrival identities, column flags) one edge in,
// outputs (V requests, command word, flags, out_age) one edge out. Internal age 'pa' counts from the registered start.
module ot_qwen_tp8_pv_wide_ctl_tbf #(parameter integer FIRST_INPUT_AGE=255,parameter integer END_FLOOR=1,parameter integer RESET_PIN=0,parameter integer MUT=0,
 parameter integer TRUNK_D=0,   // registered stages ctl cmd pin -> every tile's command pin (balanced, KVPLAN trunk)
 parameter integer FLAG_D=0     // registered stages every column flag pin -> this tile's col_valid / col_fault pins (balanced)
)(
 input wire clk,rst_n,
 input wire[7:0] cfg_fia,                       // boot-loaded FIRST_INPUT_AGE (static after the seal)
 input wire pair_id,                            // die strap: one master serves both pairs
 input wire start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output reg[7:0] req_valid,output reg[111:0] req_t,
 output reg[59:0] cmd,input wire[31:0] col_valid,input wire[31:0] col_fault,
 output reg[15:0] out_epoch,output reg fault,output reg busy,output reg[15:0] out_age
);
 // ---- reset: pin flop (RESET_PIN) -> ot_rst_relay_bounded32 kept leaves; every leaf clears <= 18 control flops ----
 // Boot-only change vs r1: reset RELEASE reaches the control flops 3 edges later (relay root, second, leaf).
 // Assertion stays asynchronous. No scheduled data / token edge moves (the first start follows boot by >> 3 edges).
 wire root_rst_n;
 generate if(RESET_PIN)begin:g_reset_pin
  (* keep *)reg rst_q;
  always @(posedge clk)rst_q<=rst_n;
  assign root_rst_n=rst_q;
 end else begin:g_reset_legacy
  assign root_rst_n=rst_n;
 end endgenerate
 localparam integer NRL=16;
 localparam integer R_FSM=0,R_IDLE=1,R_ST=2,R_IV=3,R_CV0=4,R_CV1=5,R_CF0=6,R_CF1=7,R_CMD0=8,R_CMD1=9,R_OA=10,R_OE=11,
                    R_EP=12,R_NQE=13,R_PAC=14,R_PAN=15;
 wire[NRL-1:0] rl;
 ot_rst_relay_bounded32 #(.REGIONS(NRL)) u_rst(.clk(clk),.rst_n_in(root_rst_n),.rst_n(rl));

 localparam IDLE=0,FEED=1,DRAIN=2,TRA=3,TRB=4,TRADD=5,TRDRAIN=6,JOIN=7;
 localparam integer JGO=2;                       // join_go 2 edges into JOIN: bank tree sums cross the bank out + join in pin regs
 localparam integer COL_LAT=JGO+3+3*7+3+1;      // JOIN -> column y_valid: + cmd reg, join pin reg, jrun start, J_OUT 24, y reg
 localparam integer COL_CHK=COL_LAT+TRUNK_D+FLAG_D;   // KVPLAN trunk: the column flags reach this tile TRUNK_D + FLAG_D later
 // kept replica groups (census <= 32 loads per driver): go group g = start_k[g] & idle_k[g] & ~fbad_k[g]
 localparam integer G_EP=0,G_NQE=1,G_LIM=2,G_NQ=3,G_PAC=4,G_PAN=5,NG=6;
 localparam integer S_VQ=6,S_VL=7,S_VN=8,NS=9;   // vrow start copies: active/q, lim, nq
 localparam integer I_CHK=6,I_BAD=7,NI=8;        // idle copies for the arrival-check window and the cbad gating
 // FIRSTI = cfg_fia + 1 (+ the request pin register: arrival pa of q = 0): registered constants, static after the seal
 reg[7:0] fia_q;reg[15:0] k_fi,k_fi1,k_qc,k_qn,k_fe,k_oa;reg fia_bad;
 (* keep="true",dont_touch="true" *) reg[NG-1:0] fbad_k;
 wire fia_bad_d=(MUT==2)?1'b0:(fia_q<8'd1||fia_q>8'(FIRST_INPUT_AGE));
 always @(posedge clk)begin
  fia_q<=cfg_fia;
  k_fi<=16'(fia_q)+16'd1;                         // FIRSTI
  k_fi1<=16'(fia_q)+16'd2;                        // FIRSTI + 1
  k_qc<=16'(fia_q)+16'd2+((MUT==1)?16'd1:16'd0);  // qc = pa - 1 - FIRSTI
  k_qn<=16'(fia_q);                               // qn = pa + 1 - FIRSTI
  k_fe<=16'(fia_q);                               // FEED end: pa >= FIRSTI + nq - 1
  k_oa<=16'(fia_q)+16'd1+16'd13+16'd73+16'(COL_LAT)+16'(TRUNK_D);   // 1 + FIRSTI - 1 + 13 + 73 + COL_LAT + TRUNK_D
  fia_bad<=fia_bad_d;
  fbad_k<={NG{fia_bad_d}};
 end
 // ---- input pin registers (valid / flag bits reset, data unreset) ----
 reg start_r;reg[13:0] ctx_r;reg[15:0] epoch_r;reg[7:0] iv_r;reg[111:0] it_r;reg[127:0] ie_r;reg[31:0] cv_r,cf_r;
 (* keep="true",dont_touch="true" *) reg[NS-1:0] start_k;   // kept copies of the start pin register
 (* keep="true",dont_touch="true" *) reg[3:0] pid_k;        // pair_id strap, registered, kept copies (constant)
 always @(posedge clk)pid_k<={4{pair_id}};
 always @(posedge clk or negedge rl[R_ST])if(!rl[R_ST])start_k<=0;else start_k<={NS{start}};
 always @(posedge clk or negedge rl[R_IV])if(!rl[R_IV])iv_r<=0;else iv_r<=in_valid;
 always @(posedge clk or negedge rl[R_CV0])if(!rl[R_CV0])cv_r[15:0]<=0;else cv_r[15:0]<=col_valid[15:0];
 always @(posedge clk or negedge rl[R_CV1])if(!rl[R_CV1])cv_r[31:16]<=0;else cv_r[31:16]<=col_valid[31:16];
 always @(posedge clk or negedge rl[R_CF0])if(!rl[R_CF0])cf_r[15:0]<=0;else cf_r[15:0]<=col_fault[15:0];
 always @(posedge clk or negedge rl[R_CF1])if(!rl[R_CF1])cf_r[31:16]<=0;else cf_r[31:16]<=col_fault[31:16];
 always @(posedge clk)begin ctx_r<=context_len;epoch_r<=epoch;it_r<=in_t;ie_r<=in_epoch;end
 reg[3:0] state;reg[15:0] ep;reg[13:0] lim;reg[15:0] nq;reg[15:0] nq_end;reg flt;
 reg[4:0] nodes;reg[2:0] ti;reg[3:0] drain_left,reduce_left;reg[7:0] wage;
 // pa = cycles since the registered start (r1: age + 1), held as two kept counters (check side / next+cmd side)
 (* keep="true",dont_touch="true" *) reg[15:0] pa_c,pa_n;
 (* keep="true",dont_touch="true" *) reg[NI-1:0] idle_k;   // registered one-hot IDLE decode copies (from state_n)
 wire idle=(state==IDLE);
 // checks: the registered arrival seen at pa arrived at pa-1, i.e. q = pa - 1 - FIRSTI
 wire[15:0] qc=pa_c-k_qc;
 wire chk_window=!idle_k[I_CHK]&&pa_c>=k_fi1&&qc<nq;
 wire[11:0] rc=qc[15:4];wire[3:0] ac=qc[3:0];
 // slice takes: the command word for the arrival at pa+1 (cmd reg + column pin reg = 2 edges, payload 1 edge)
 wire[15:0] qn=pa_n-k_qn;
 wire next_window=(state==FEED)&&pa_n+16'd1>=k_fi&&qn<nq;
 wire[11:0] rn=qn[15:4];wire[3:0] an=qn[3:0];
 reg[7:0] exp_take,pexp_v;reg[13:0] pexp_t[0:7];
 integer l,wn,wt,wp;                          // loop temporaries (blocking, combinational only; no automatic decls for yosys)
 always @*begin
  exp_take=0;pexp_v=0;wn=0;wt=0;wp=0;
  for(l=0;l<8;l=l+1)pexp_t[l]=0;
  // per PORT (constant index): port wp carries bank l = (wp&3) + 4h of step n = rc - h with n&1 == wp>>2, i.e.
  // h = (rc ^ (wp>>2)) & 1 -- the same (bank, step) -> port map as before, without a runtime-indexed write
  for(wp=0;wp<8;wp=wp+1)begin
   l=(wp&3)+4*((int'(rc)^(wp>>2))&1);
   wn=int'(rc)-(l>>2);
   wt=256*wn+128*int'(pid_k[0])+16*l+int'(ac);
   if(chk_window&&wn>=0&&wt<int'(lim))begin pexp_v[wp]=1'b1;pexp_t[wp]=14'(wt);end
  end
  for(l=0;l<8;l=l+1)begin
   wn=int'(rn)-(l>>2);
   wt=256*wn+128*int'(pid_k[1])+16*l+int'(an);
   if(next_window&&wn>=0&&wt<int'(lim))exp_take[l]=1'b1;
  end
 end
 wire[7:0] rq;wire[111:0] rqt;
 ot_qwen_tp8_pv_wide_ctl_tbf_vrow u_req(.clk(clk),.rst_n(rl[R_NQE]),.pair_id(pid_k[3]),.start_q(start_k[S_VQ]),
  .start_l(start_k[S_VL]),.start_n(start_k[S_VN]),.context_len(ctx_r),.req_valid(rq),.req_t(rqt));
 always @(posedge clk)req_t<=rqt;
 reg cbad;integer k;
 wire out_slot=(state==JOIN)&&wage==8'(COL_CHK+1);
 always @*begin
  cbad=0;
  if(!idle_k[I_BAD]&&iv_r!=pexp_v)cbad=1;
  for(k=0;k<8;k=k+1)if(iv_r[k]&&(it_r[14*k+:14]!=pexp_t[k]||ie_r[16*k+:16]!=ep))cbad=1;
  if(|cf_r)cbad=1;
  if(!((&cv_r)||!(|cv_r)))cbad=1;                 // = cv_r != {32{cv_r[0]}} (and/or trees: 2 loads per bit)
  if(!idle_k[I_BAD]&&cv_r[0]!=out_slot)cbad=1;
 end
 // ---- control FSM: next state once, registered state + kept one-hot IDLE copies ----
 wire abort=(start_r&&!idle)||(!idle&&cbad);
 wire badgo=start_r&&idle&&fia_bad;
 wire feed_end=pa_n>=k_fe+nq_end&&pa_n>=16'd16;
 reg[3:0] state_n;reg flt_n;reg[4:0] nodes_n;reg[2:0] ti_n;
 always @*begin
  state_n=state;flt_n=flt;nodes_n=nodes;ti_n=ti;
  if(abort)begin state_n=IDLE;flt_n=1;end
  else if(badgo)flt_n=1;                         // an invalid boot age: the command never starts
  else case(state)
   IDLE:if(start_r)begin if(ctx_r==0||ctx_r>8192)flt_n=1;else state_n=FEED;end
   FEED:if(feed_end)state_n=DRAIN;
   DRAIN:if(drain_left<=1)begin nodes_n=16;ti_n=0;state_n=TRA;end
   TRA:state_n=TRB;
   TRB:state_n=TRADD;
   TRADD:if(5'(ti)+1==nodes/2)state_n=TRDRAIN;else begin ti_n=ti+1'b1;state_n=TRA;end
   TRDRAIN:if(reduce_left==1)begin if(nodes==2)state_n=JOIN;else begin nodes_n=nodes/2;ti_n=0;state_n=TRA;end end
   JOIN:if(wage==8'(COL_CHK+1))state_n=IDLE;
   default:;
  endcase
 end
 always @(posedge clk or negedge rl[R_FSM])
  if(!rl[R_FSM])begin start_r<=0;state<=IDLE;flt<=0;nodes<=0;ti<=0;end
  else begin start_r<=start;state<=state_n;flt<=flt_n;nodes<=nodes_n;ti<=ti_n;end
 always @(posedge clk or negedge rl[R_IDLE])if(!rl[R_IDLE])idle_k<={NI{1'b1}};else idle_k<={NI{state_n==IDLE}};
 // phase counters: unreset datapath (each is loaded before it is read in its own state)
 always @(posedge clk)if(!abort)case(state)
   FEED:if(feed_end)drain_left<=12;
   DRAIN:drain_left<=drain_left-1'b1;
   TRADD:reduce_left<=7;
   TRDRAIN:begin reduce_left<=reduce_left-1'b1;if(reduce_left==1&&nodes==2)wage<=0;end
   JOIN:wage<=wage+1'b1;
   default:;
  endcase
 // command load groups (IDLE & start & valid boot age), one kept (start, idle, fia_bad) triple per group
 wire[NG-1:0] go=start_k[NG-1:0]&idle_k[NG-1:0]&~fbad_k;
 wire inc_c=!idle_k[G_PAC]&&!start_k[G_PAC]&&!cbad;   // r1: age<=age+1 when running and not aborted
 wire inc_n=!idle_k[G_PAN]&&!start_k[G_PAN]&&!cbad;
 always @(posedge clk or negedge rl[R_EP])if(!rl[R_EP])ep<=0;else if(go[G_EP])ep<=epoch_r;
 always @(posedge clk or negedge rl[R_NQE])if(!rl[R_NQE])nq_end<=0;else if(go[G_NQE])
   nq_end<=(END_FLOOR!=0)?((ctx_r>14'd0)?16'(16*(((int'(ctx_r)+255)>>8)+1)):16'd0)
                         :((ctx_r>14'(128*int'(pid_k[2])))?16'(16*(((int'(ctx_r)-128*int'(pid_k[2])+255)>>8)+1)):16'd0);
 always @(posedge clk)if(go[G_LIM])lim<=ctx_r;
 always @(posedge clk)if(go[G_NQ])
   nq<=(ctx_r>14'(128*int'(pid_k[2])))?16'(16*(((int'(ctx_r)-128*int'(pid_k[2])+255)>>8)+1)):16'd0;
 always @(posedge clk or negedge rl[R_PAC])if(!rl[R_PAC])pa_c<=16'd1;else if(go[G_PAC])pa_c<=16'd1;else if(inc_c)pa_c<=pa_c+1'b1;
 always @(posedge clk or negedge rl[R_PAN])if(!rl[R_PAN])pa_n<=16'd1;
  else if(go[G_PAN])pa_n<=(MUT==3)?16'd2:16'd1;else if(inc_n)pa_n<=pa_n+1'b1;   // MUT 3: next-side copy one edge early
 // column command word, registered at this tile's output pin (the column registers it again at its input pin)
 wire n0_lo=(rn==0),n0_hi=(rn==1);
 reg[31:0] cmd_n;reg[15:0] cmd_q0,cmd_q1;
 always @*begin
  cmd_n=0;
  cmd_n[0]=rn[0];cmd_n[8:1]=exp_take&{8{!flt}};cmd_n[9]=n0_lo;cmd_n[10]=n0_hi;cmd_n[14:11]=an;
  cmd_n[15]=(state==FEED)&&pa_n>=1&&pa_n<=16;cmd_n[19:16]=4'(pa_n-1);
  cmd_n[20]=(state==TRA)||(state==TRB);cmd_n[24:21]={ti,1'b0}+4'(state==TRB);
  cmd_n[25]=state==TRADD;cmd_n[26]=state==TRB;cmd_n[27]=nodes==2;cmd_n[30:28]=ti;
  cmd_n[31]=(state==JOIN)&&wage==8'(JGO);
 end
 always @(posedge clk or negedge rl[R_CMD0])if(!rl[R_CMD0])cmd_q0<=0;else cmd_q0<=cmd_n[15:0];
 always @(posedge clk or negedge rl[R_CMD1])if(!rl[R_CMD1])cmd_q1<=0;else cmd_q1<=cmd_n[31:16];
 always @*cmd={28'd0,cmd_q1,cmd_q0};             // cmd[59:32] reserved zero
 // output pin registers: flags and the static output age (service cycles after start_pv: + the start pin register)
 always @(posedge clk or negedge rl[R_IV])
  if(!rl[R_IV])begin fault<=0;busy<=0;req_valid<=0;end
  else begin fault<=flt;busy<=state!=IDLE;req_valid<=rq;end
 always @(posedge clk or negedge rl[R_OE])if(!rl[R_OE])out_epoch<=0;else out_epoch<=ep;
 always @(posedge clk or negedge rl[R_OA])if(!rl[R_OA])out_age<=0;else out_age<=k_oa+nq_end;
endmodule

// r2 request walker (= ot_qwen_tp8_vrow_wide edge for edge, unconnected fault dropped): valid bit reset, data unreset,
// the start load split over three kept start copies (<= 16 enable loads each)
module ot_qwen_tp8_pv_wide_ctl_tbf_vrow (
 input wire clk,rst_n,pair_id,start_q,start_l,start_n,input wire[13:0] context_len,
 output reg[7:0] req_valid,output reg[111:0] req_t
);
 reg active;reg[15:0] q;reg[15:0] nq;reg[13:0] lim;
 integer l,wn,wt,wp;
 always @*begin
  req_valid=0;req_t=0;wn=0;wt=0;wp=0;
  if(active&&q<nq)for(wp=0;wp<8;wp=wp+1)begin
   l=(wp&3)+4*((int'(q>>4)^(wp>>2))&1);
   wn=int'(q>>4)-(l>>2);
   wt=256*wn+128*int'(pair_id)+16*l+int'(q&15);
   if(wn>=0&&wt<int'(lim))begin req_valid[wp]=1'b1;req_t[14*wp+:14]=14'(wt);end
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)active<=0;else if(start_q)active<=1;else if(active&&!(q<nq))active<=0;
 always @(posedge clk)if(start_q)q<=0;else if(active&&q<nq)q<=q+1'b1;
 always @(posedge clk)if(start_l)lim<=context_len;
 always @(posedge clk)if(start_n)
   nq<=(context_len>14'(128*int'(pair_id)))?16'(16*(((int'(context_len)-128*int'(pair_id)+255)>>8)+1)):16'd0;
endmodule
