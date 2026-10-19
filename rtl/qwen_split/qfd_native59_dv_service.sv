`timescale 1ns/1ps
// qfd_native59_dv_service -- native59 compute service re-ported to the distributed-vector die (dv2f7, lane Q-N59,
// 10-17).  The central VM and SU64 are gone: Q and K/V arrive as the W5 slice D2D word dd_i (W5_CONTRACT.md,
// claude/qslice-1017 be28f313b) and the attention result / embedding row leave as dr_o into the W5 return chain.
// The link-side children are the SAME RTL as qfd_native59_compute_service (no re-implemented arithmetic):
//   qfd_native59_command_context, qfd_native59_q_export_control, ot_qfd_su_kv_static_posted (FP8 KV formatter),
//   qfd_kvn_static_transport (x3), qfd_native59_static_service, qfd_native59_record_endpoint (native548 codec).
// What is new is only the boundary packing:
//   * dd_i {v, kind 2, mask 8, 8 x addr 24, 8 x FP32, 89 x 0}.  kind 1 (K) / 2 (V): lane l (mask[l]) becomes formatter
//     lane l of the 64-lane write face (lanes 8..63 never written); the lane address IS the formatter's KV address
//     (K < 2^20, V in [2^20, 2^21), HEADS=1) and must agree with kind.  kind 0 (Q): element e = addr[8:0] (addr[23:9]
//     = 0) lands in the 512-element Q seat bank at beat e[8:4], lane e[3:0]; the seat bank replaces the VM's Q rows.
//     q_committed = all 512 seats written in this epoch; at q_slot the bank emits the old 524-b q word
//     {v, 3'd1, 3'd0, beat 5, data 512} to the unchanged tag / static-service / codec path.
//   * The formatter issue permit (V, Klo, Khi; nout 1, nin 128/64/64) is the fixed native program shape: it is raised
//     on the three edges after the epoch begin (the SU instruction is no longer visible at native59); every lane is
//     still checked for position, kind, duplicate and coverage by the formatter itself.
//   * write_commit_* are DERIVED (the VM is now in the slices): a group-0 dr word is visible in every slice VM exactly
//     LAND_EDGES edges after its dr_o edge (W5..E5 return-chain hops + slice pin register + w16 VM write; compiler
//     constant).  Landing collisions are slice port faults (W5 ss/ag -> tt_ctlm), not an acknowledgement.
//   * Embedding (G9): native_cmd with [0]=0 and [379:376]=4'hE (EMB), token [375:358], all of [357:1] zero, starts a
//     fixed 65-edge read: emb_code_re words 0..63 then emb_scale_re; each answer leaves as a group-1 dr word 3 edges
//     after its read edge (k = 0..63: beat k, the code word; k = 64: beat 0, {496'd0, BF16 scale}).  The slice lands
//     group-1 words at em_base + 16*k (its own counter), so the scale lands at em_base + 1024.
// Static schedule only: every input lands in a pin register, every output is a flop, no ready/credit; any schedule
// violation (missing/duplicate/late Q seat, malformed dd word, dr group collision, EMB while busy, unknown command)
// is a sticky fault.  All internal slots are one edge later than at qfd_native59_compute_service's pins.
// MUT (bench mutants, must FAIL): 1 Q lane packing e^1, 2 KV lane address ^1, 3 EMB code word k^1,
// 4 legacy Q window from vm_q_start (Q beat 0 one link slot late against the compiled calendar, F1),
// 5 (MU, = MU-TOK-KV m7) user 3's records carry user tag 0, 6 (MU) the filler epoch sequence never advances.
// D2D USER (MU-DQ-D2DUSER 10-19, NU > 1; NU = 1 is the block above on every edge): the user of a native context /
//   request is native_position[17:16] (qfd_tt_ctlm_dv: the user of the latest head start; positions are < 8192).  The
//   operation's epoch -- carried by the D2D CMD / Q records out and checked on the RESULT / STATUS records back (the
//   unchanged record endpoint compares the full epoch) and by the KVN x3 identity -- is
//     user 0: the HOST epoch (the face's single context; must be a user-0 MU epoch, [1:0] = 0) -> user 0 is
//             bit-identical to NU = 1;
//     user u > 0: {seq14[u], u}, seq14[u] = MU_SEQ0 at the user's first L0 context, +1 at each later L0 context (stage
//             1): the mirror of the HOST allocator's per-user sequence (ot_qwen_tp8_token_epoch_allocator_mu, INITIAL
//             _EPOCH[15:2] = MU_SEQ0).  A filler context of a layer > 0 before the user's first L0 is a fault.
//   The KV die serves user epoch[1:0] (MU-ADOPT-KV, HBM row 64 + l + 256 u).  Context checks: qfd_native59_command_
//   context_mu (HOST token / position match for user 0 only).  No port, no edge: the stamp is on the context edge.
// MULTI-CONTEXT (MU-D2D-OVL 10-19, MCTX = 1; MCTX = 0 is the single-context block on every edge): with the D2D link's
//   overlapping request / response segments (ot_qwen_d2d_static_end OVL = 1) user k+1's operation FRONT (context begin,
//   Q seats, K/V formatter, CMD + Q records, KVN words) runs while user k's BACK (RESULT / STATUS records, VM writes,
//   dr landing, visibility, completion) is still in flight.  The per-operation state is held in NS = 2 static context
//   slots: static service, record endpoint (codec), dr landing fence, visibility, operation tag.  Slots are taken in
//   operation order: the FRONT slot is the one the latest context begin took (begins alternate 0, 1, 0, ...), the BACK
//   slot is the oldest operation not yet completed (it advances on its completion).  Front events (begin, request,
//   Q, TX slots, KV/x3) drive the front slot; back events (RX records, result slots, VM commits, kernel done,
//   visibility, complete) drive the back slot.  The front children (Q seat bank, export control, formatter, KVN
//   transport, command context) hold one operation (they finish at the CMD / KVN edge).  Static schedule: a begin into
//   a slot whose operation is still active (a third operation in flight) is the context's service_active fault, an RX
//   record of another operation fails the back slot's codec epoch / layer check (the user is in epoch[1:0]): collision
//   = fault, never a wait.  native_ret: the back slot's word with ready = the next begin's slot is free.
// RESET (S-QWCOL QW-N59 94d19372e, merged 10-19): see rst_q below.
module qfd_native59_dv_service #(
 parameter integer MUT=0,CODEC_MUT=0,
 // LAND_EDGES=0 profile is not allowed: production must supply the measured W5..E5 return-chain landing edge count.
 parameter integer NATIVE_PROFILE=0,LAND_QUALIFIED=0,LAND_EDGES=8,
 // MU-DQ-D2DUSER: users (1 = single user, the as-built block) and the HOST allocator's initial sequence (INITIAL_EPOCH[15:2])
 parameter integer NU=1,parameter [13:0] MU_SEQ0=14'd0,
 // MU-D2D-OVL: 1 = two operation context slots (overlapping D2D request / response; see the header)
 parameter integer MCTX=0, SAFE=0
)(
 input wire ck,rst_n,
 // SAFE regional roots, fixed-phase siblings of ck; unused in the legacy path.
 input wire ck_fmt,ck_qbuf,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[547:0]dd_i,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 output wire[523:0]x3,output wire[58:0]x3_identity,output wire[1:0]x3_generation,
 input wire q_slot,input wire[4:0]q_slot_beat,
 input wire tx_slot,input wire[3:0]tx_slot_kind,input wire[4:0]tx_slot_beat,
 output wire native_tx_v,output wire[547:0]native_tx_payload,
 input wire native_rx_v,input wire[547:0]native_rx_payload,
 input wire rx_slot,input wire[3:0]rx_slot_kind,input wire[4:0]rx_slot_beat,
 output reg[519:0]dr_o,
 output reg emb_code_re,output reg[23:0]emb_code_addr,output reg emb_scale_re,output reg[17:0]emb_scale_addr,
 input wire[511:0]emb_code_q,input wire[15:0]emb_scale_q,
 input wire visibility_slot,complete_slot,output wire completed,output reg[94:0]native_ret,
 output reg fault
);
 integer l;
 // ---------------------------------------------------------------- reset distribution (ROOT-RST, QW-N59 10-19)
 // The kit lands rst_n at the face in 2 registered stages (ref_tile "reset_landing", ot_pin_regs.tcl OT_RST_LAND); here
 // ONE more registered stage replicates it per region (equal depth: every copy is a kept flop fed by the landed port),
 // so no reset net drives the whole tile (n1-e4ecec634: one rst_n net reached 10,582 flops > 8,000).  Assertion is
 // immediate (async clear of the copies), release is synchronous one edge later; reset release latency is a scheduled
 // constant.  Copies: 0 formatter, 1 x3 transport, 2 static service, 3 record codec, 4 command context + Q export
 // control, 5 dr landing fence, 6 pin registers + native_ret, 7 the remaining top-level state.
 (* keep = "true" *) reg[7:0]rst_q;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)rst_q<=8'd0;
  else rst_q<=8'hFF;
 wire rst_fmt=rst_q[0],rst_x3=rst_q[1],rst_svc=rst_q[2],rst_rec=rst_q[3],rst_ctx=rst_q[4],rst_land=rst_q[5],
      rst_pin=rst_q[6],rst_top=rst_q[7];
 // ---------------------------------------------------------------- pin registers (every input, flop-first)
 reg p_hev,p_hfc;reg[15:0]p_he;reg[58:0]p_ht;reg[1:0]p_hg;
 reg p_lcv;reg[5:0]p_stage;reg[17:0]p_tok,p_pos;reg[379:0]p_cmd;reg[547:0]p_dd;
 reg p_kvs,p_x3s;reg[1:0]p_kvi;reg p_qs;reg[4:0]p_qb;
 reg p_ts;reg[3:0]p_tk;reg[4:0]p_tb;reg p_rv;reg[547:0]p_rp;reg p_rs;reg[3:0]p_rk;reg[4:0]p_rb;
 reg[511:0]p_ecq;reg[15:0]p_esq;reg p_vis,p_cs;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin
   p_hev<=0;p_hfc<=0;p_he<=0;p_ht<=0;p_hg<=0;p_lcv<=0;p_stage<=0;p_tok<=0;p_pos<=0;p_cmd<=0;p_dd<=0;
   p_kvs<=0;p_x3s<=0;p_kvi<=0;p_qs<=0;p_qb<=0;p_ts<=0;p_tk<=0;p_tb<=0;p_rv<=0;p_rp<=0;p_rs<=0;p_rk<=0;p_rb<=0;
   p_ecq<=0;p_esq<=0;p_vis<=0;p_cs<=0;
  end else begin
   p_hev<=host_epoch_valid;p_hfc<=host_fused_capability;p_he<=host_epoch;p_ht<=host_tag;p_hg<=host_generation;
   p_lcv<=layer_context_v;p_stage<=command_stage;p_tok<=native_token;p_pos<=native_position;p_cmd<=native_cmd;p_dd<=dd_i;
   p_kvs<=kv_word_slot;p_x3s<=kv_x3_slot;p_kvi<=kv_word_index;p_qs<=q_slot;p_qb<=q_slot_beat;
   p_ts<=tx_slot;p_tk<=tx_slot_kind;p_tb<=tx_slot_beat;p_rv<=native_rx_v;p_rp<=native_rx_payload;
   p_rs<=rx_slot;p_rk<=rx_slot_kind;p_rb<=rx_slot_beat;p_ecq<=emb_code_q;p_esq<=emb_scale_q;
   p_vis<=visibility_slot;p_cs<=complete_slot;
  end
 // ---------------------------------------------------------------- command context (unchanged child)
 wire[94:0]service_ret_raw;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)native_ret<=95'd0;
  else native_ret<=service_ret_raw;
 wire vm_write_v;wire[19:0]vm_write_word;wire[4:0]vm_write_beat;wire[58:0]vm_write_tag;wire[511:0]vm_write_data;
 wire vm_address_fault=vm_write_v&&(vm_write_word!=(20'd3167+{15'd0,vm_write_beat}));
 wire native_context=p_lcv&&p_stage>=1&&p_stage<=36;
 wire begin_slot,request_slot,context_fault,active;
 wire[58:0]begin_tag,request_tag;wire[19:0]base;
 // ---------------------------------------------------------------- D2D user (MU-DQ-D2DUSER, NU > 1; see the header)
 localparam integer MU=(NU>1)?1:0;
 wire[1:0]c_user=MU?p_pos[17:16]:2'd0;
 wire[17:0]c_pos=MU?{2'b00,p_pos[15:0]}:p_pos;
 reg[13:0]fseq[0:3];reg[3:0]fstart;reg mu_fault;
 wire c_l0=p_stage==6'd1;
 wire[13:0]c_seq=(fstart[c_user]&&c_l0&&MUT!=6)?fseq[c_user]+14'd1:fseq[c_user];
 wire[1:0]c_tag=(MUT==5&&c_user==2'd3)?2'd0:c_user;
 wire[15:0]c_epoch=(MU==0||c_user==2'd0)?p_he:{c_seq,c_tag};
 integer fu;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin for(fu=0;fu<4;fu=fu+1)fseq[fu]<=MU_SEQ0;fstart<=0;mu_fault<=0;end
  else if(MU!=0&&native_context&&c_user!=2'd0)begin
   fseq[c_user]<=c_seq;if(c_l0)fstart[c_user]<=1'b1;
   if({1'b0,c_user}>=3'(NU)||(!c_l0&&!fstart[c_user]))mu_fault<=1'b1;
  end
 generate if(MU==0)begin:g_ctx1
  qfd_native59_command_context u_context(
  .ck(ck),.rst_n(rst_ctx),.host_epoch_valid(p_hev),.host_fused_capability(p_hfc),.host_epoch(p_he),.host_tag(p_ht),.host_generation(p_hg),
  .context_v(native_context),.context_stage(p_stage),.context_token(p_tok),.context_position(p_pos),
  .native_cmd(p_cmd),.command_stage(p_stage),.command_token(p_tok),.command_position(p_pos),
  .service_active(active),.begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),.fault(context_fault));
 end else begin:g_ctxmu
  qfd_native59_command_context_mu #(.NU(NU)) u_context(
  .ck(ck),.rst_n(rst_ctx),.host_epoch_valid(p_hev),.host_fused_capability(p_hfc),.host_epoch(p_he),.host_tag(p_ht),.host_generation(p_hg),
  .context_v(native_context),.context_stage(p_stage),.context_token(p_tok),.context_position(c_pos),
  .native_cmd(p_cmd),.command_stage(p_stage),.command_token(p_tok),.command_position(c_pos),
  .service_active(active),.ctx_user(c_user),.ctx_epoch(c_epoch),
  .begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),.fault(context_fault));
 end endgenerate
 // ---------------------------------------------------------------- dd word decode
 wire dd_v=p_dd[547];wire[1:0]dd_kind=p_dd[546:545];wire[7:0]dd_mask=p_dd[544:537];
 wire dd_q=dd_v&&dd_kind==2'd0,dd_kv=dd_v&&(dd_kind==2'd1||dd_kind==2'd2);
 wire dd_form_bad=(!dd_v&&(|p_dd[546:0]))||(dd_v&&((|p_dd[88:0])||dd_mask==8'd0||dd_kind==2'd3));
 // ---------------------------------------------------------------- Q seat bank (replaces the VM Q rows)
 // Q export window (QXF-LINK 2026-10-18, TOKEN-XDIE-QWEN F1): the compiler's D2D calendar sends Q beat 0 in the slot
 // right after the CMD (tools/qwen_split/d2d_link_calendar.py layer_msgs: Q beat b at q0 + 1 + b; the KV
 // qkd_native_attention_static_ctl expects Q at RX_CMD+1..+32).  The Q words come from the local seat bank (no VM read),
 // so the window opens on the accepted request edge itself: q_slot may be the edge after request_slot, and the Q record
 // follows the CMD record on consecutive codec edges.  MUT 4 (bench): the legacy window from the registered vm_q_start
 // (Q beat 0 >= 2 edges after the CMD, i.e. one idle link slot), which the compiled calendar does not reserve.
 wire vm_q_epoch,vm_q_start;
 wire q_open=(MUT==4)?vm_q_start:request_slot;
 // Decoded constant-index form (S-QWCOL 10-18): the n1c gate's synthesis smoke timed out (2700 s, yosys SHARE on the
 // 8 x 16384-b runtime $shift writes + the 512-b $shiftx read).  Same function as the per-lane loop it replaces: each
 // lane l decodes its element qe_l once; seat e takes the data of the HIGHEST hitting lane (the old loop's last write
 // wins); q_in_bad = a hit on a seat already seen this epoch, or two lanes of one word on the same seat.
 wire[16383:0]qbuf;reg[511:0]qseen;reg qctx,qlock;   // MU-DQ-D2DUSER: restored (lost in the e28fa950f merge: the file did not elaborate)
 wire[16383:0]qbuf_n;wire[511:0]qseen_n,qdup;
 wire[71:0]qe_all;wire[7:0]qhit_any,qhi_bad;
 // Kept replicas capture the raw face on the SAME edge as p_dd/p_lcv.
 // Each address/valid replica serves only32 seats; no extra data edge.
 (* keep = "true" *) reg[71:0]qe_rep[0:15];
 (* keep = "true" *) reg[7:0]qh_rep[0:15];
 (* keep = "true" *) reg[15:0]qb_rep;
 genvar gr;
 generate if(SAFE!=0)begin:g_scatter_rep
  for(gr=0;gr<16;gr=gr+1)begin:g_seg
   always @(posedge ck)begin
    qb_rep[gr]<=layer_context_v&&command_stage>=1&&command_stage<=36;
    qh_rep[gr]<={8{dd_i[547]&&dd_i[546:545]==0&&!(layer_context_v&&command_stage>=1&&command_stage<=36)}}&dd_i[544:537];
    for(integer lane=0;lane<8;lane=lane+1)
     qe_rep[gr][9*lane+:9]<=dd_i[345+24*lane+:9]^9'(MUT==1);
   end
   always @(posedge ck or negedge rst_top)
    if(!rst_top)qseen[32*gr+:32]<=0;
    else if(qb_rep[gr])qseen[32*gr+:32]<=0;
    else qseen[32*gr+:32]<=qseen_n[32*gr+:32];
  end
 end else begin:g_seen_legacy
  always @(posedge ck or negedge rst_top)
   if(!rst_top)qseen<=0;else if(begin_slot)qseen<=0;else qseen<=qseen_n;
 end endgenerate
 wire[1151:0]qe_copies;wire[127:0]qh_copies;
 generate for(gr=0;gr<16;gr=gr+1)begin:g_scatter_bus
  assign qe_copies[72*gr+:72]=qe_rep[gr];assign qh_copies[8*gr+:8]=qh_rep[gr];
 end endgenerate
 genvar gl,ge;
 generate
  for(gl=0;gl<8;gl=gl+1)begin:g_qlane
   assign qe_all[9*gl+:9]=p_dd[345+24*gl+:9]^((MUT==1)?9'd1:9'd0);
   assign qhit_any[gl]=dd_q&&dd_mask[gl];
   assign qhi_bad[gl]=qhit_any[gl]&&(|p_dd[345+24*gl+9+:15]);
  end
  for(ge=0;ge<512;ge=ge+1)begin:g_qseat
   wire[7:0]hit;
   for(gl=0;gl<8;gl=gl+1)begin:g_h
    assign hit[gl]=(SAFE!=0)?(qh_rep[ge/32][gl]&&(qe_rep[ge/32][9*gl+:9]==9'(ge))):(qhit_any[gl]&&(qe_all[9*gl+:9]==ge));
   end
   assign qbuf_n[32*ge+:32]=hit[7]?p_dd[89+32*7+:32]:hit[6]?p_dd[89+32*6+:32]:hit[5]?p_dd[89+32*5+:32]:
                             hit[4]?p_dd[89+32*4+:32]:hit[3]?p_dd[89+32*3+:32]:hit[2]?p_dd[89+32*2+:32]:
                             hit[1]?p_dd[89+32*1+:32]:hit[0]?p_dd[89+32*0+:32]:qbuf[32*ge+:32];
   assign qseen_n[ge]=qseen[ge]|(|hit);
   assign qdup[ge]=(qseen[ge]&&(|hit))||(|(hit&(hit-8'd1)));
  end
 endgenerate
 wire q_in_bad=(dd_q&&(!qctx||qlock||begin_slot))||(|qhi_bad)||(|qdup);
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin qctx<=0;qlock<=0;end
  else if(begin_slot)begin qctx<=1;qlock<=0;end
  else begin if(q_open)qlock<=1;end
 generate if(SAFE==0)begin:g_qlegacy
  reg[16383:0]qb;
  always @(posedge ck)if(!begin_slot)qb<=qbuf_n;
  assign qbuf=qb;
 end else begin:g_qsafe
  assign qbuf=16384'd0;
 end endgenerate
 wire q_committed=qctx&&(&qseen);
 // beat read as a decoded AND-OR over the 32 constant beats (no runtime part-select)
 wire[511:0]qrow_t[0:32];wire[32:0]qfull_t;
 assign qrow_t[0]=512'd0;assign qfull_t[0]=1'b0;
 genvar gb;
 generate for(gb=0;gb<32;gb=gb+1)begin:g_qbeat
  wire sel=(p_qb==gb);
  assign qrow_t[gb+1]=qrow_t[gb]|({512{sel}}&qbuf[512*gb+:512]);
  assign qfull_t[gb+1]=qfull_t[gb]|(sel&&(&qseen[16*gb+:16]));
 end endgenerate
 wire[511:0]qrow;wire qrow_full;
 generate if(SAFE==0)begin:g_qread_legacy
  assign qrow=qrow_t[32];assign qrow_full=qfull_t[32];
 end else begin:g_qread_safe
  // 8 independent masked writers preserve the full scatter interface. Read and
  // owner select land at the existing pin edge; SRAM read-before-write is exact.
  qfd_native59_qseat_sram #(.MUT(MUT),.REGIONAL(1),.REPLICATE(1)) u_qseat(
   .ck(ck),.ck_mem(ck_qbuf),.rst_n(rst_top),.clear(begin_slot),.write_v(qhit_any),
   .write_element(qe_all),.write_data(p_dd[344:89]),
   .element_copies(qe_copies),.valid_copies(qh_copies),
   .read_v(q_slot),.read_beat(q_slot_beat),.read_data(qrow));
  reg full_q;
  always @(posedge ck)full_q<=!begin_slot&&(&qseen_n[16*q_slot_beat+:16]);
  assign qrow_full=full_q;
 end endgenerate
 wire q_miss=p_qs&&!qrow_full;
 wire[523:0]q=p_qs?{1'b1,3'd1,3'd0,p_qb,qrow}:524'd0;
 wire export_control_fault;
 qfd_native59_q_export_control u_qexport_control(
 .ck(ck),.rst_n(rst_ctx),.begin_slot(begin_slot),.request_slot(request_slot),.q_committed(q_committed),
 .vm_q_epoch(vm_q_epoch),.vm_q_start(vm_q_start),.fault(export_control_fault));
 reg[58:0]context_tag,q_epoch_tag,q_frame_tag;
 reg context_valid,q_window,qtag_fault;reg[5:0]q_count;
 always @(posedge ck or negedge rst_top)begin
  if(!rst_top)begin context_tag<=0;q_epoch_tag<=0;q_frame_tag<=0;context_valid<=0;q_window<=0;qtag_fault<=0;q_count<=0;end
  else begin
   if(begin_slot)begin context_tag<=begin_tag;context_valid<=1;end
   if(vm_q_epoch)begin
    if(q_window||(!context_valid&&!begin_slot))qtag_fault<=1;
    q_epoch_tag<=begin_slot?begin_tag:context_tag;
   end
   if(q_open)begin
    if(q_window||!q_committed)qtag_fault<=1;
    q_window<=1;q_count<=0;q_frame_tag<=q_epoch_tag;
   end
   if(q[523])begin
    if(!q_window||q[522:520]!=1||q[519:517]!=0||q_count!={1'b0,q[516:512]})qtag_fault<=1;
    q_count<=q_count+1'b1;
    if(q_count==31)q_window<=0;
   end
  end
 end
 // ---------------------------------------------------------------- K/V: dd lanes -> the formatter's 64-lane face
 reg[63:0]kv_we;reg[1535:0]kv_waddr;reg[2047:0]kv_wdata;reg kv_in_bad;reg[23:0]ka;
 always @*begin
  kv_we=0;kv_waddr=0;kv_wdata=0;kv_in_bad=0;ka=0;
  if(dd_kv)for(l=0;l<8;l=l+1)if(dd_mask[l])begin
   ka=p_dd[345+24*l+:24];
   if((dd_kind==2'd1)?(|ka[23:20]):((|ka[23:21])||!ka[20]))kv_in_bad=1;
   kv_we[l]=1'b1;kv_waddr[24*l+:24]=ka^((MUT==2)?24'd1:24'd0);kv_wdata[32*l+:32]=p_dd[89+32*l+:32];
  end
 end
 reg[2:0]iss;
 always @(posedge ck or negedge rst_top)if(!rst_top)iss<=0;else iss<={iss[1:0],native_context};
 wire kv_issue=|iss;
 wire[1:0]kv_kind=iss[0]?2'd0:iss[1]?2'd1:2'd2;
 wire[17:0]kv_nin=iss[0]?18'd128:18'd64;
 wire formatter_fault,formatter_idle,formatter_drained,kvn_v;wire[7:0]formatter_fault_code;
 wire[10:0]kvn_tag;wire[511:0]kvn_data;
 ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1),.SAFE(SAFE))u_formatter(
 .clk(SAFE?ck_fmt:ck),.rst_n(rst_fmt),.epoch_begin(native_context),.epoch_pos(c_pos),
 .issue_v(kv_issue),.issue_kind(kv_kind),.issue_nout(18'd1),.issue_nin(kv_nin),
 .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.epoch_idle(formatter_idle),.drained(formatter_drained),
 .word_v(kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),.word_slot(p_kvs),.word_index(p_kvi),
 .fault(formatter_fault),.fault_code(formatter_fault_code));
 reg[58:0]formatter_identity;reg[1:0]formatter_generation;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin formatter_identity<=0;formatter_generation<=0;end
  else if(native_context)begin formatter_identity<=begin_tag;formatter_generation<=p_hg;end
 wire x3_fault;
 qfd_kvn_static_transport u_kvn(.ck(ck),.rst_n(rst_x3),.word_v(kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),
 .word_identity(formatter_identity),.word_generation(formatter_generation),.slot_v(p_x3s),
 .x3(x3),.x3_identity(x3_identity),.x3_generation(x3_generation),.fault(x3_fault));
 // ---------------------------------------------------------------- operation context slots (MU-D2D-OVL; NS = 1: as built)
 localparam integer NS=(MCTX!=0)?2:1;
 reg nf,fs,bs;                       // slot of the next begin, the front (latest begun) slot, the back (oldest active) slot
 wire[NS-1:0]s_active,s_completed,s_svc_fault,s_rec_fault,s_land_fault,s_commit_complete,s_tx_v;
 wire[NS-1:0]s_req_v,s_kq_v,s_vm_write_v;wire[58:0]s_vm_write_tag[0:NS-1];wire[19:0]s_vm_write_word[0:NS-1];
 wire[4:0]s_vm_write_beat[0:NS-1];wire[511:0]s_vm_write_data[0:NS-1];wire[547:0]s_tx_payload[0:NS-1];wire[94:0]s_ret[0:NS-1];
 reg[58:0]s_optag[0:NS-1];reg[NS-1:0]s_vis_seen;
 wire svc_fault=|s_svc_fault,record_fault=|s_rec_fault,land_fault=|s_land_fault;
 wire[NS-1:0]sel_nf=NS'(1)<<(MCTX!=0?nf:1'b0),sel_f=NS'(1)<<(MCTX!=0?fs:1'b0),sel_b=NS'(1)<<(MCTX!=0?bs:1'b0);
 assign active=|(s_active&sel_nf);   // the command context faults a begin into a slot that is still active
 assign completed=|s_completed;
 assign service_ret_raw={s_ret[MCTX!=0?bs:1'b0][94:2],{2{!(|(s_active&sel_nf))&&!svc_fault}}};
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin nf<=0;fs<=0;bs<=0;end
  else if(MCTX!=0)begin
   if(begin_slot)begin fs<=nf;nf<=~nf;end
   if(|(s_completed&sel_b))bs<=~bs;
  end
 // the merged VM write (only the back slot writes; two at once is a slot collision)
 integer si;
 reg vmw_v;reg[19:0]vmw_word;reg[4:0]vmw_beat;reg[58:0]vmw_tag;reg[511:0]vmw_data;reg vmw_two;
 reg ntx_v;reg[547:0]ntx_p;
 always @*begin
  vmw_v=0;vmw_word=0;vmw_beat=0;vmw_tag=0;vmw_data=0;vmw_two=0;ntx_v=0;ntx_p=0;
  for(si=0;si<NS;si=si+1)begin
   if(s_vm_write_v[si])begin vmw_two=vmw_two|vmw_v;vmw_v=1;vmw_word=vmw_word|s_vm_write_word[si];vmw_beat=vmw_beat|s_vm_write_beat[si];
    vmw_tag=vmw_tag|s_vm_write_tag[si];vmw_data=vmw_data|s_vm_write_data[si];end
   ntx_v=ntx_v|s_tx_v[si];if(NS==1||s_tx_v[si])ntx_p=ntx_p|s_tx_payload[si];   // NS 1: the codec register as built
  end
 end
 assign vm_write_v=vmw_v;assign vm_write_word=vmw_word;assign vm_write_beat=vmw_beat;assign vm_write_tag=vmw_tag;assign vm_write_data=vmw_data;
 assign native_tx_v=ntx_v;assign native_tx_payload=ntx_p;
 wire visibility_fault=p_cs&&!(|(s_vis_seen&sel_b));
 reg dv_fault;
 wire src_fault=context_fault|qtag_fault|export_control_fault|dv_fault|formatter_fault|x3_fault|record_fault|land_fault|visibility_fault|vm_address_fault|mu_fault;
 reg dr_s;                            // slot whose VM write is in dr_o (the landing fence of that slot checks it)
 genvar gs;
 generate for(gs=0;gs<NS;gs=gs+1)begin:g_slot
  wire f=sel_f[gs],b=sel_b[gs];
  wire req_s=request_slot&&f;
  wire result_v,result_slot,kernel_done;wire[4:0]result_beat,result_slot_beat;wire[58:0]result_tag,kernel_done_tag;wire[511:0]result_data;
  wire[58:0]req_tag,kq_tag;wire[4:0]kq_beat;wire[511:0]kq_data;
  wire vm_commit_v;wire[4:0]vm_commit_beat;wire[58:0]vm_commit_tag;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin s_optag[gs]<=0;s_vis_seen[gs]<=0;end
   else begin
    if(req_s)begin s_optag[gs]<=request_tag;s_vis_seen[gs]<=0;end
    else if(p_vis&&b)s_vis_seen[gs]<=s_commit_complete[gs]&&!s_land_fault[gs];
   end
  qfd_native59_static_service u_service(
  .ck(ck),.rst_n(rst_svc),.source_fault(src_fault),
  .begin_slot(begin_slot&&sel_nf[gs]),.begin_tag(begin_tag),.request_slot(req_s),.request_tag(request_tag),.result_base_word(base),
  .qr_committed(q_committed),.qr_tag(q_epoch_tag),.kernel_request_v(s_req_v[gs]),.kernel_request_tag(req_tag),
  .q_slot(p_qs&&f),.q_slot_beat(p_qb),.q_v(q[523]&&f),.q_beat(q[516:512]),.q_tag(q_frame_tag),.q_data(q[511:0]),
  .kernel_q_v(s_kq_v[gs]),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
  .result_slot(result_slot),.result_slot_beat(result_slot_beat),.result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),
  .vm_write_v(s_vm_write_v[gs]),.vm_write_word(s_vm_write_word[gs]),.vm_write_beat(s_vm_write_beat[gs]),.vm_write_tag(s_vm_write_tag[gs]),.vm_write_data(s_vm_write_data[gs]),
  .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag(vm_commit_tag),.kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),
  .complete_slot(p_cs&&b),.completed(s_completed[gs]),.active(s_active[gs]),.fault(s_svc_fault[gs]),.native_ret(s_ret[gs]));
  qfd_native59_record_endpoint #(.CODEC_MUT(CODEC_MUT))u_record(
  .ck(ck),.rst_n(rst_rec),.operation_tag(s_optag[gs]),.kernel_request_v(s_req_v[gs]),.kernel_request_tag(req_tag),
  .kernel_q_v(s_kq_v[gs]),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
  .tx_slot(p_ts&&f),.tx_slot_kind(p_tk),.tx_slot_beat(p_tb),.tx_valid(s_tx_v[gs]),.tx_payload(s_tx_payload[gs]),
  .rx_event(p_rv&&b),.rx_payload(p_rp),.rx_slot(p_rs&&b),.rx_slot_kind(p_rk),.rx_slot_beat(p_rb),
  .result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),.result_slot(result_slot),.result_slot_beat(result_slot_beat),
  .kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),.fault(s_rec_fault[gs]));
  qfd_native59_dr_landing #(.LAND_EDGES(LAND_EDGES))u_land(
  .ck(ck),.rst_n(rst_land),.request_slot(req_s),.request_tag59(request_tag),
  .emit_v(dr_o[519]&&!dr_o[518]&&(NS==1||dr_s==1'(gs))),.emit_beat(dr_o[516:512]),.emit_tag59(dr_tag),.visibility_slot(p_vis&&b),
  .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag59(vm_commit_tag),.complete(s_commit_complete[gs]),.fault(s_land_fault[gs]));
 end endgenerate
 // ---------------------------------------------------------------- embedding row read (G9), fixed 65-edge sequence
 wire emb_go=!p_cmd[0]&&p_cmd[379:376]==4'hE;
 wire cmd_bad=(emb_go&&((|p_cmd[357:1])||p_cmd[375:358]>=18'd151936))||(!p_cmd[0]&&(|p_cmd)&&!emb_go);
 reg emb_act;reg[6:0]emb_k;reg[17:0]emb_tok;
 reg e1,e2,e3;reg[6:0]k1,k2,k3;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin emb_act<=0;emb_k<=0;emb_tok<=0;emb_code_re<=0;emb_code_addr<=0;emb_scale_re<=0;emb_scale_addr<=0;
                  e1<=0;e2<=0;e3<=0;k1<=0;k2<=0;k3<=0;end
  else begin
   emb_code_re<=0;emb_scale_re<=0;
   if(emb_go&&!emb_act&&!cmd_bad)begin emb_act<=1;emb_k<=0;emb_tok<=p_cmd[375:358];end
   if(emb_act)begin
    if(emb_k<7'd64)begin emb_code_re<=1;emb_code_addr<={emb_tok,emb_k[5:0]^((MUT==3)?6'd1:6'd0)};end
    else begin emb_scale_re<=1;emb_scale_addr<=emb_tok;end
    emb_k<=emb_k+7'd1;if(emb_k==7'd64)emb_act<=0;
   end
   // read edge (e1: the re flop is at the pin), provider answer (e2), answer in the pin register (e3)
   e1<=emb_act;k1<=emb_k;e2<=e1;k2<=k1;e3<=e2;k3<=k2;
  end
 // ---------------------------------------------------------------- dr_o: group 0 attention result / group 1 embedding row
 wire g0=vm_write_v,g1=e3;
 reg[58:0]dr_tag;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin dr_o<=0;dr_tag<=0;dr_s<=0;end
  else begin
   dr_tag<=vm_write_tag;dr_s<=(NS>1)?s_vm_write_v[NS-1]:1'b0;
   dr_o<=g0?{1'b1,1'b0,1'b0,vm_write_beat,vm_write_data}:
         g1?{1'b1,1'b1,(k3==7'd64)?6'd0:k3[5:0],(k3==7'd64)?{496'd0,p_esq}:p_ecq}:520'd0;
  end
 // ---------------------------------------------------------------- sticky DV boundary faults and the fault pin
 always @(posedge ck or negedge rst_top)
  if(!rst_top)dv_fault<=0;
  else if(dd_form_bad||q_in_bad||kv_in_bad||q_miss||(g0&&g1)||(emb_go&&emb_act)||cmd_bad||vmw_two)dv_fault<=1;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)fault<=0;
  else fault<=svc_fault|context_fault|qtag_fault|export_control_fault|dv_fault|formatter_fault|x3_fault|record_fault|land_fault|visibility_fault|vm_address_fault|mu_fault;
 initial begin
  if(NATIVE_PROFILE!=0&&LAND_QUALIFIED!=1)$fatal(1,"native service requires the measured dr landing edge contract");
  if(LAND_EDGES<2)$fatal(1,"LAND_EDGES must include the slice pin register and VM write");
  if(MUT<0||MUT>6||(MUT>=5&&NU<2))$fatal(1,"qfd_native59_dv_service: MUT undefined");
  if(NU<1||NU>4)$fatal(1,"qfd_native59_dv_service: NU %0d outside 1..4",NU);
  if(MCTX!=0&&MCTX!=1)$fatal(1,"qfd_native59_dv_service: MCTX %0d (0 or 1)",MCTX);
 end
endmodule

// Static landing fence for the group-0 dr words: the compiler owns LAND_EDGES (dr_o edge -> last slice VM write).
// Nothing here gates an issue or acknowledges a write; a missing / duplicate / foreign word or an early visibility
// slot is a fault.
module qfd_native59_dr_landing #(parameter integer LAND_EDGES=8)(
 input wire ck,rst_n,
 input wire request_slot,input wire[58:0]request_tag59,
 input wire emit_v,input wire[4:0]emit_beat,input wire[58:0]emit_tag59,
 input wire visibility_slot,
 output reg vm_commit_v,output reg[4:0]vm_commit_beat,output reg[58:0]vm_commit_tag59,
 output wire complete,output reg fault
);
 reg active;reg[58:0]tag;reg[31:0]issued,covered;
 reg[LAND_EDGES-1:0]pending;reg[4:0]beat_pipe[0:LAND_EDGES-1];reg[58:0]tag_pipe[0:LAND_EDGES-1];
 integer i;
 wire[4:0]lb=beat_pipe[LAND_EDGES-1];
 assign complete=active&&(&covered)&&!fault;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin
   active<=0;tag<=0;issued<=0;covered<=0;pending<=0;vm_commit_v<=0;vm_commit_beat<=0;vm_commit_tag59<=0;fault<=0;
   for(i=0;i<LAND_EDGES;i=i+1)begin beat_pipe[i]<=0;tag_pipe[i]<=0;end
  end else begin
   vm_commit_v<=0;
   pending<={pending[LAND_EDGES-2:0],emit_v};
   beat_pipe[0]<=emit_beat;tag_pipe[0]<=emit_tag59;
   for(i=1;i<LAND_EDGES;i=i+1)begin beat_pipe[i]<=beat_pipe[i-1];tag_pipe[i]<=tag_pipe[i-1];end
   if(request_slot)begin
    if((active&&!(&covered))||(|pending)||emit_v)fault<=1;
    active<=1;tag<=request_tag59;issued<=0;covered<=0;
   end
   if(emit_v)begin
    if(!active||request_slot||emit_tag59!=tag||issued[emit_beat])fault<=1;
    issued[emit_beat]<=1;
   end
   if(pending[LAND_EDGES-1])begin
    if(!active||request_slot||tag_pipe[LAND_EDGES-1]!=tag||covered[lb])fault<=1;
    else begin covered[lb]<=1;if(!fault)begin vm_commit_v<=1;vm_commit_beat<=lb;vm_commit_tag59<=tag_pipe[LAND_EDGES-1];end end
   end
   if(visibility_slot&&(!active||!(&issued)||!(&covered)||(|pending)))fault<=1;
  end
endmodule

// qfd_native59_command_context_mu (in this file so every native59 source list stays valid) -- MU-DQ-D2DUSER (10-19, Qwen ROM 4 users): drop-in successor of
// qfd_native59_command_context for qfd_native59_dv_service at NU > 1 (the original file is untouched and still binds
// at NU = 1).  Same ports plus ctx_user / ctx_epoch.
//   ctx_user  = the user of the head segment that drives the native context / request (qfd_tt_ctlm_dv native_pos[17:16],
//               the head-start user: 0 on the face's dh start, the calendar's cmd_user on a LOCAL SEG start).
//   ctx_epoch = the epoch this user's records carry: user 0 = the HOST epoch (the face's single context, unchanged);
//               filler u = {seq14[u], u} (the service's per-user mirror of the HOST allocator's sequence,
//               ot_qwen_tp8_token_epoch_allocator_mu).  The D2D attention records (CMD / Q out, RESULT / STATUS back)
//               carry it, so the KV die reads the user from epoch[1:0] (MU-ADOPT-KV convention, KV row 64+l+256u).
// Differences from the single-user block (NU > 1 only):
//   * begin_tag epoch = ctx_epoch (user 0: host_epoch, so user 0 is bit-identical to the single-user block);
//   * the HOST-tag token / position match (host_tag[36:19] / [18:6] vs the context) and host_epoch == context epoch are
//     checked for user 0 only: the closed face carries the latency user's HOST context only (MU OPEN item "filler
//     initial context"); a filler's identity is the head's per-user bank (qfd_tt_ctlm_dv tok_b / pos_b) -- compiled;
//   * NEW: user 0's HOST epoch must be a user-0 MU epoch (host_epoch[1:0] == 0), and the request's user must be the
//     context's user (the head segment that asks for attention is the one whose context opened the operation).
// Every other check of the original is kept unchanged.  Static schedule: checks only fault, never stall.
module qfd_native59_command_context_mu #(parameter integer NU=4)(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire [15:0] host_epoch,
 input wire [58:0] host_tag,input wire [1:0] host_generation,
 input wire context_v,input wire [5:0] context_stage,
 input wire [17:0] context_token,context_position,
 input wire [379:0] native_cmd,input wire [5:0] command_stage,
 input wire [17:0] command_token,command_position,
 input wire service_active,
 input wire [1:0] ctx_user,input wire [15:0] ctx_epoch,
 output wire begin_slot,output wire [58:0] begin_tag,
 output wire request_slot,output wire [58:0] request_tag,
 output wire [19:0] result_base_word,output reg fault
);
 localparam [379:0] TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg valid,cap;reg [1:0] generation;reg [58:0] context_tag;reg [1:0] ctx_u;
 wire host0=ctx_user==2'd0;
 assign begin_slot=context_v;
 assign begin_tag={ctx_epoch,context_stage,context_token,context_position[12:0],6'd0};
 assign request_slot=native_cmd[0];
 assign request_tag={context_tag[58:43],command_stage,command_token,command_position[12:0],6'd0};
 assign result_base_word=native_cmd[299:280];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin valid<=0;cap<=0;generation<=0;context_tag<=0;ctx_u<=0;fault<=0;end
  else begin
   if(context_v)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||
       (host0&&(host_tag[36:19]!=context_token||host_tag[18:6]!=context_position||host_epoch[1:0]!=2'd0))||
       service_active||!host_epoch_valid||!host_fused_capability||(valid&&begin_tag==context_tag)||context_stage<1||context_stage>36||context_token>=151936||context_position>=8192)fault<=1;
    valid<=1;cap<=host_fused_capability;generation<=host_generation;context_tag<=begin_tag;ctx_u<=ctx_user;
   end
   if(request_slot)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||
       (ctx_u==2'd0&&(host_tag[36:19]!=context_tag[36:19]||host_tag[18:6]!=context_tag[18:6]||host_epoch!=context_tag[58:43]))||
       ctx_user!=ctx_u||host_generation!=generation||!valid||context_v||!host_epoch_valid||!cap||!host_fused_capability||request_tag!=context_tag||command_position>=8192||native_cmd!=TEMPLATE)fault<=1;
   end
  end
 end
 initial if(NU<2||NU>4)$fatal(1,"qfd_native59_command_context_mu: NU %0d outside 2..4 (NU 1 binds qfd_native59_command_context)",NU);
endmodule
