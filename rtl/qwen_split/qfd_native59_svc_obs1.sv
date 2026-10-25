// Explicit STATUS observer ABI v1; legacy source remains unchanged. Payload is meaningful after its real event.
`timescale 1ns/1ps
// QW-N59-4 (10-19): service child of the hardened native59 split; edge contract and rationale in qfd_native59_qbank.sv.
// ----------------------------------------------------------------------------------------------------------------------
// Service child: qfd_native59_dv_service (SAFE 2, ROOTS 1, RST_FOREST 1) with the Q-seat section replaced by the bank's
// registered qb_* words.  dd_i / layer_context_v / command_stage are the bank's three-edge relays (this child runs three edges
// behind the bank ports: see qfd_native59_qbank.sv).  svc2: the record codec captures rx data on every edge (RX_FREE 1);
// svc3: tx payload too (TX_FREE, MCTX 1) and the DV fault as four sticky flops.
module qfd_native59_svc_obs1 #(
 parameter integer MUT=0,CODEC_MUT=0,NATIVE_PROFILE=0,LAND_QUALIFIED=0,LAND_EDGES=8,
 parameter integer RECV_INPUTS=0,RECV_MUT=0,LOCAL32=0,LOCAL_MUT=0,
 parameter integer ROPE=0,USER_BIND=0,HEAD_PREP=0,NU=1,parameter [13:0] MU_SEQ0=14'd0,parameter integer MCTX=0,EMB_RELAY=0
)(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire head_prepare_v,input wire[1:0]head_prepare_user,input wire[17:0]head_prepare_token,head_prepare_position,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[547:0]dd_i,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 output wire[523:0]x3,output wire[58:0]x3_identity,output wire[1:0]x3_generation,
 input wire qb_v,input wire[4:0]qb_beat,input wire[511:0]qb_row,input wire qb_full,qb_committed,qb_bad,
 input wire[1:0]tx_user,rx_user, // scheduled metadata, same age as TX/RX events
 input wire tx_slot,input wire[3:0]tx_slot_kind,input wire[4:0]tx_slot_beat,
 output wire native_tx_v,output wire[547:0]native_tx_payload,
 output reg head_descriptor_v,output reg[58:0]head_descriptor_tag,output reg[1:0]head_descriptor_generation,
 input wire native_rx_v,input wire[547:0]native_rx_payload,
 input wire rx_slot,input wire[3:0]rx_slot_kind,input wire[4:0]rx_slot_beat,
 output reg[519:0]dr_o,
 output reg emb_code_re,output reg[23:0]emb_code_addr,output reg emb_scale_re,output reg[17:0]emb_scale_addr,
 input wire[511:0]emb_code_q,input wire[15:0]emb_scale_q,
 input wire visibility_slot,complete_slot,output wire completed,output wire[58:0] completed_tag,output reg[94:0]native_ret,
 output reg fault
);
 // Opt-in v4: every functional receiving pin lands one edge before the legacy service graph.
 // Uniform input shift preserves field alignment. No reset on payload flops; static reset idle window applies.
 // Default RECV_INPUTS=0 is the original combinational alias, with no added edges.
 wire  bnd_host_epoch_valid;
 wire  bnd_host_fused_capability;
 wire [15:0] bnd_host_epoch;
 wire [58:0] bnd_host_tag;
 wire [1:0] bnd_host_generation;
 wire  bnd_layer_context_v;
 wire [5:0] bnd_command_stage;
 wire [17:0] bnd_native_token;
 wire [17:0] bnd_native_position;
 wire [379:0] bnd_native_cmd;
 wire [547:0] bnd_dd_i;
 wire  bnd_kv_word_slot;
 wire [1:0] bnd_kv_word_index;
 wire  bnd_kv_x3_slot;
 wire  bnd_qb_v;
 wire [4:0] bnd_qb_beat;
 wire [511:0] bnd_qb_row;
 wire  bnd_qb_full;
 wire  bnd_qb_committed;
 wire  bnd_qb_bad;
 wire[1:0]bnd_tx_user,bnd_rx_user;
 wire  bnd_tx_slot;
 wire [3:0] bnd_tx_slot_kind;
 wire [4:0] bnd_tx_slot_beat;
 wire  bnd_native_rx_v;
 wire [547:0] bnd_native_rx_payload;
 wire  bnd_rx_slot;
 wire [3:0] bnd_rx_slot_kind;
 wire [4:0] bnd_rx_slot_beat;
 wire [511:0] bnd_emb_code_q;
 wire [15:0] bnd_emb_scale_q;
 wire  bnd_visibility_slot;
 wire  bnd_complete_slot;
 generate if(RECV_INPUTS!=0)begin:g_recv
  (* keep = "true" *) reg[1:0]tx_user_q,rx_user_q;
  always @(posedge ck)begin tx_user_q<=tx_user;rx_user_q<=rx_user;end
  assign bnd_tx_user=tx_user_q;assign bnd_rx_user=rx_user_q;
  (* keep = "true" *) reg  p_host_epoch_valid;
  always @(posedge ck) p_host_epoch_valid<=host_epoch_valid;
  assign bnd_host_epoch_valid=p_host_epoch_valid;
  (* keep = "true" *) reg  p_host_fused_capability;
  always @(posedge ck) p_host_fused_capability<=host_fused_capability;
  assign bnd_host_fused_capability=p_host_fused_capability;
  (* keep = "true" *) reg [15:0] p_host_epoch;
  always @(posedge ck) p_host_epoch<=host_epoch;
  assign bnd_host_epoch=p_host_epoch;
  (* keep = "true" *) reg [58:0] p_host_tag;
  always @(posedge ck) p_host_tag<=host_tag;
  assign bnd_host_tag=p_host_tag;
  (* keep = "true" *) reg [1:0] p_host_generation;
  always @(posedge ck) p_host_generation<=host_generation;
  assign bnd_host_generation=p_host_generation;
  (* keep = "true" *) reg  p_layer_context_v;
  always @(posedge ck) p_layer_context_v<=layer_context_v;
  assign bnd_layer_context_v=p_layer_context_v;
  (* keep = "true" *) reg [5:0] p_command_stage;
  always @(posedge ck) p_command_stage<=command_stage;
  assign bnd_command_stage=p_command_stage;
  (* keep = "true" *) reg [17:0] p_native_token;
  always @(posedge ck) p_native_token<=native_token;
  assign bnd_native_token=p_native_token;
  (* keep = "true" *) reg [17:0] p_native_position;
  always @(posedge ck) p_native_position<=native_position;
  assign bnd_native_position=p_native_position;
  (* keep = "true" *) reg [379:0] p_native_cmd;
  always @(posedge ck) p_native_cmd<=native_cmd;
  assign bnd_native_cmd=p_native_cmd;
  (* keep = "true" *) reg [547:0] p_dd_i;
  always @(posedge ck) p_dd_i<=dd_i;
  assign bnd_dd_i=p_dd_i;
  (* keep = "true" *) reg  p_kv_word_slot;
  always @(posedge ck) p_kv_word_slot<=kv_word_slot;
  assign bnd_kv_word_slot=p_kv_word_slot;
  (* keep = "true" *) reg [1:0] p_kv_word_index;
  always @(posedge ck) p_kv_word_index<=kv_word_index;
  assign bnd_kv_word_index=p_kv_word_index;
  (* keep = "true" *) reg  p_kv_x3_slot;
  always @(posedge ck) p_kv_x3_slot<=kv_x3_slot;
  assign bnd_kv_x3_slot=p_kv_x3_slot;
  (* keep = "true" *) reg  p_qb_v;
  always @(posedge ck) p_qb_v<=qb_v;
  if(RECV_MUT==2)begin:g_late_qb_v
   (* keep = "true" *) reg  late;
   always @(posedge ck) late<=p_qb_v;
   assign bnd_qb_v=late;
  end else begin:g_main_qb_v
   assign bnd_qb_v=(RECV_MUT==1)?qb_v:p_qb_v;
  end
  (* keep = "true" *) reg [4:0] p_qb_beat;
  always @(posedge ck) p_qb_beat<=qb_beat;
  if(RECV_MUT==2)begin:g_late_qb_beat
   (* keep = "true" *) reg [4:0] late;
   always @(posedge ck) late<=p_qb_beat;
   assign bnd_qb_beat=late;
  end else begin:g_main_qb_beat
   assign bnd_qb_beat=(RECV_MUT==1)?qb_beat:p_qb_beat;
  end
  (* keep = "true" *) reg [511:0] p_qb_row;
  always @(posedge ck) p_qb_row<=qb_row;
  if(RECV_MUT==2)begin:g_late_qb_row
   (* keep = "true" *) reg [511:0] late;
   always @(posedge ck) late<=p_qb_row;
   assign bnd_qb_row=late;
  end else begin:g_main_qb_row
   assign bnd_qb_row=(RECV_MUT==1)?qb_row:p_qb_row;
  end
  (* keep = "true" *) reg  p_qb_full;
  always @(posedge ck) p_qb_full<=qb_full;
  if(RECV_MUT==2)begin:g_late_qb_full
   (* keep = "true" *) reg  late;
   always @(posedge ck) late<=p_qb_full;
   assign bnd_qb_full=late;
  end else begin:g_main_qb_full
   assign bnd_qb_full=(RECV_MUT==1)?qb_full:p_qb_full;
  end
  (* keep = "true" *) reg  p_qb_committed;
  always @(posedge ck) p_qb_committed<=qb_committed;
  if(RECV_MUT==2)begin:g_late_qb_committed
   (* keep = "true" *) reg  late;
   always @(posedge ck) late<=p_qb_committed;
   assign bnd_qb_committed=late;
  end else begin:g_main_qb_committed
   assign bnd_qb_committed=(RECV_MUT==1)?qb_committed:p_qb_committed;
  end
  (* keep = "true" *) reg  p_qb_bad;
  always @(posedge ck) p_qb_bad<=qb_bad;
  if(RECV_MUT==2)begin:g_late_qb_bad
   (* keep = "true" *) reg  late;
   always @(posedge ck) late<=p_qb_bad;
   assign bnd_qb_bad=late;
  end else begin:g_main_qb_bad
   assign bnd_qb_bad=(RECV_MUT==1)?qb_bad:p_qb_bad;
  end
  (* keep = "true" *) reg  p_tx_slot;
  always @(posedge ck) p_tx_slot<=tx_slot;
  assign bnd_tx_slot=p_tx_slot;
  (* keep = "true" *) reg [3:0] p_tx_slot_kind;
  always @(posedge ck) p_tx_slot_kind<=tx_slot_kind;
  assign bnd_tx_slot_kind=p_tx_slot_kind;
  (* keep = "true" *) reg [4:0] p_tx_slot_beat;
  always @(posedge ck) p_tx_slot_beat<=tx_slot_beat;
  assign bnd_tx_slot_beat=p_tx_slot_beat;
  (* keep = "true" *) reg  p_native_rx_v;
  always @(posedge ck) p_native_rx_v<=native_rx_v;
  assign bnd_native_rx_v=p_native_rx_v;
  (* keep = "true" *) reg [547:0] p_native_rx_payload;
  always @(posedge ck) p_native_rx_payload<=native_rx_payload;
  assign bnd_native_rx_payload=p_native_rx_payload;
  (* keep = "true" *) reg  p_rx_slot;
  always @(posedge ck) p_rx_slot<=rx_slot;
  assign bnd_rx_slot=p_rx_slot;
  (* keep = "true" *) reg [3:0] p_rx_slot_kind;
  always @(posedge ck) p_rx_slot_kind<=rx_slot_kind;
  assign bnd_rx_slot_kind=p_rx_slot_kind;
  (* keep = "true" *) reg [4:0] p_rx_slot_beat;
  always @(posedge ck) p_rx_slot_beat<=rx_slot_beat;
  assign bnd_rx_slot_beat=p_rx_slot_beat;
  (* keep = "true" *) reg [511:0] p_emb_code_q;
  always @(posedge ck) p_emb_code_q<=emb_code_q;
  assign bnd_emb_code_q=p_emb_code_q;
  (* keep = "true" *) reg [15:0] p_emb_scale_q;
  always @(posedge ck) p_emb_scale_q<=emb_scale_q;
  assign bnd_emb_scale_q=p_emb_scale_q;
  (* keep = "true" *) reg  p_visibility_slot;
  always @(posedge ck) p_visibility_slot<=visibility_slot;
  assign bnd_visibility_slot=p_visibility_slot;
  (* keep = "true" *) reg  p_complete_slot;
  always @(posedge ck) p_complete_slot<=complete_slot;
  assign bnd_complete_slot=p_complete_slot;
 end else begin:g_recv_off
  assign bnd_tx_user=tx_user;assign bnd_rx_user=rx_user;
  assign bnd_host_epoch_valid=host_epoch_valid;
  assign bnd_host_fused_capability=host_fused_capability;
  assign bnd_host_epoch=host_epoch;
  assign bnd_host_tag=host_tag;
  assign bnd_host_generation=host_generation;
  assign bnd_layer_context_v=layer_context_v;
  assign bnd_command_stage=command_stage;
  assign bnd_native_token=native_token;
  assign bnd_native_position=native_position;
  assign bnd_native_cmd=native_cmd;
  assign bnd_dd_i=dd_i;
  assign bnd_kv_word_slot=kv_word_slot;
  assign bnd_kv_word_index=kv_word_index;
  assign bnd_kv_x3_slot=kv_x3_slot;
  assign bnd_qb_v=qb_v;
  assign bnd_qb_beat=qb_beat;
  assign bnd_qb_row=qb_row;
  assign bnd_qb_full=qb_full;
  assign bnd_qb_committed=qb_committed;
  assign bnd_qb_bad=qb_bad;
  assign bnd_tx_slot=tx_slot;
  assign bnd_tx_slot_kind=tx_slot_kind;
  assign bnd_tx_slot_beat=tx_slot_beat;
  assign bnd_native_rx_v=native_rx_v;
  assign bnd_native_rx_payload=native_rx_payload;
  assign bnd_rx_slot=rx_slot;
  assign bnd_rx_slot_kind=rx_slot_kind;
  assign bnd_rx_slot_beat=rx_slot_beat;
  assign bnd_emb_code_q=emb_code_q;
  assign bnd_emb_scale_q=emb_scale_q;
  assign bnd_visibility_slot=visibility_slot;
  assign bnd_complete_slot=complete_slot;
 end endgenerate
 initial if(RECV_MUT<0||RECV_MUT>2||(RECV_MUT!=0&&RECV_INPUTS==0)) $fatal(1,"N59 RECV_MUT requires opt-in receiver (0 clean, 1 QB bypass, 2 QB extra edge)");

 localparam integer SAFE=2;
 integer l;
 // ---------------------------------------------------------------- reset distribution (ROOT-RST, QW-N59 10-19)
 // The kit lands rst_n at the face in 2 registered stages (ref_tile "reset_landing", ot_pin_regs.tcl OT_RST_LAND); here
 // ONE more registered stage replicates it per region (equal depth: every copy is a kept flop fed by the landed port),
 // so no reset net drives the whole tile (n1-e4ecec634: one rst_n net reached 10,582 flops > 8,000).  Assertion is
 // immediate (async clear of the copies), release is synchronous one edge later; reset release latency is a scheduled
 // constant.  Copies: 0 formatter, 1 x3 transport, 2 static service, 3 record codec, 4 command context + Q export
 // control, 5 dr landing fence, 6 pin registers + native_ret, 7 the remaining top-level state.
wire rst_fmt,rst_x3,rst_svc,rst_rec,rst_ctx,rst_land,rst_pin,rst_top;

 // Family widths = ceil(region reset loads / 28) from the SAFE2 synthesized netlist (textbook 10-19: fmt 5,517,
 // svc 2,830, pin 2,173, rec 2,139, top 1,599, land 1,420 bit loads (safe3 gate), x3 577, ctx < 256); the pass re-points loads,
 // the gate's high_fanout lint on 1_2_yosys.v is the witness.
 (* keep = "true" *) reg[(LOCAL32?288:200)-1:0]rst_cp_fmt;(* keep = "true" *) reg[(LOCAL32?80:24)-1:0]rst_cp_x3;(* keep = "true" *) reg[103:0]rst_cp_svc;
 (* keep = "true" *) reg[79:0]rst_cp_rec;(* keep = "true" *) reg[11:0]rst_cp_ctx;(* keep = "true" *) reg[55:0]rst_cp_land;
 (* keep = "true" *) reg[(LOCAL32?128:80)-1:0]rst_cp_pin;(* keep = "true" *) reg[(LOCAL32?64:48)-1:0]rst_cp_top;   // R3f: LOCAL32 regions grew   // QW-N59-4: qseen/qctx moved to the bank (1,599 - ~520 loads)
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin
   rst_cp_fmt<='0;rst_cp_x3<='0;rst_cp_svc<='0;rst_cp_rec<='0;rst_cp_ctx<='0;rst_cp_land<='0;rst_cp_pin<='0;rst_cp_top<='0;
  end else begin
   rst_cp_fmt<='1;rst_cp_x3<='1;rst_cp_svc<='1;rst_cp_rec<='1;rst_cp_ctx<='1;rst_cp_land<='1;rst_cp_pin<='1;rst_cp_top<='1;
  end
 assign rst_fmt=rst_cp_fmt[0];assign rst_x3=rst_cp_x3[0];assign rst_svc=rst_cp_svc[0];assign rst_rec=rst_cp_rec[0];
 assign rst_ctx=rst_cp_ctx[0];assign rst_land=rst_cp_land[0];assign rst_pin=rst_cp_pin[0];assign rst_top=rst_cp_top[0];
 // ---------------------------------------------------------------- pin registers (every input, flop-first)
 reg p_hev,p_hfc;reg[15:0]p_he;reg[58:0]p_ht;reg[1:0]p_hg;
 reg p_lcv;reg[5:0]p_stage;reg[17:0]p_tok,p_pos;reg[379:0]p_cmd;reg[547:0]p_dd;
 reg p_kvs,p_x3s;reg[1:0]p_kvi;
 wire[9:0]x3_slot_pub;
 wire[9:0]rx_result_pub;
 generate if(LOCAL32)begin:g_rx_result_pub
  (* keep = "true" *) reg[9:0]q;
  always @(posedge ck or negedge rst_pin)
   if(!rst_pin)q<=0;else q<={10{bnd_rx_slot&&(bnd_rx_slot_kind==3)}};
  assign rx_result_pub=q;
 end else begin:g_rx_result_alias
  assign rx_result_pub={10{p_rs&&(p_rk==3)}};
 end endgenerate
 wire[15:0]fmt_index_pub;
 generate if(LOCAL32)begin:g_fmt_index_pub
  (* keep = "true" *) reg[15:0]q;
  always @(posedge ck or negedge rst_pin)
   if(!rst_pin)q<=0;else q<={8{bnd_kv_word_index}};
  assign fmt_index_pub=q;
 end else begin:g_fmt_index_alias
  assign fmt_index_pub={8{p_kvi}};
 end endgenerate
 generate if(LOCAL32)begin:g_x3_slot_pub
  (* keep = "true" *) reg[9:0]q;
  always @(posedge ck or negedge rst_pin)
   if(!rst_pin)q<=0;else q<={10{bnd_kv_x3_slot}};
  assign x3_slot_pub=q;
 end else begin:g_x3_slot_alias
  assign x3_slot_pub={10{p_x3s}};
 end endgenerate
 reg[1:0]p_tu,p_ru;
 reg p_ts;reg[3:0]p_tk;reg[4:0]p_tb;reg p_rv;reg[547:0]p_rp;reg p_rs;reg[3:0]p_rk;reg[4:0]p_rb;
 reg[511:0]p_ecq;reg[15:0]p_esq;reg p_vis,p_cs;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin
   p_hev<=0;p_hfc<=0;p_he<=0;p_ht<=0;p_hg<=0;p_lcv<=0;p_stage<=0;p_tok<=0;p_pos<=0;p_cmd<=0;p_dd<=0;
   p_tu<=0;p_ru<=0;
   p_kvs<=0;p_x3s<=0;p_kvi<=0;p_ts<=0;p_tk<=0;p_tb<=0;p_rv<=0;p_rp<=0;p_rs<=0;p_rk<=0;p_rb<=0;
   p_ecq<=0;p_esq<=0;p_vis<=0;p_cs<=0;
  end else begin
   p_hev<=bnd_host_epoch_valid;p_hfc<=bnd_host_fused_capability;p_he<=bnd_host_epoch;p_ht<=bnd_host_tag;p_hg<=bnd_host_generation;
   p_lcv<=bnd_layer_context_v;p_stage<=bnd_command_stage;p_tok<=bnd_native_token;p_pos<=bnd_native_position;p_cmd<=bnd_native_cmd;p_dd<=bnd_dd_i;
   p_kvs<=bnd_kv_word_slot;p_x3s<=bnd_kv_x3_slot;p_kvi<=bnd_kv_word_index;
   p_tu<=bnd_tx_user;p_ru<=bnd_rx_user;
   p_ts<=bnd_tx_slot;p_tk<=bnd_tx_slot_kind;p_tb<=bnd_tx_slot_beat;p_rv<=bnd_native_rx_v;p_rp<=bnd_native_rx_payload;
   p_rs<=bnd_rx_slot;p_rk<=bnd_rx_slot_kind;p_rb<=bnd_rx_slot_beat;p_ecq<=bnd_emb_code_q;p_esq<=bnd_emb_scale_q;
   p_vis<=bnd_visibility_slot;p_cs<=bnd_complete_slot;
  end
 // R3d (QW-N59-6 10-20, LOCAL32): kept same-D copies of the landed pin registers p_lcv / p_stage (5) and of the dd word's
 // valid / kind / mask field p_dd[547:537] (24 = 3 per lane), same async rst_pin clear and same D as the originals, so
 // every copy equals its original on every edge.  nc_pub[k] == native_context; ddc[k] == p_dd[547:537].  Consumers:
 // nc_pub 0 formatter eb_q, 1/2 formatter eb_r halves, 3/4 formatter_identity low/high + generation; ddc 3l+0 lane l
 // we + waddr (25 loads), 3l+1 / 3l+2 lane l wdata low / high 16 bits.  R3c census: one OR3 per lane drove 57 loads and
 // native_context 281.  0 added edges.  Other parameterisations alias the originals (no added flops).
 // R3e: nc_pub widened to 26 (5/6 command-context context_tag halves, 7/8 context_tag halves + valid, 9/10 the vm_q_epoch
 // copies' D, 11/12 q_epoch_tag select halves, 13 fs_pub enables, 14+6s+k service slot s begin groups); rq_pub = 20 kept
 // copies of p_cmd[0] (== request_slot: 10s+0..3 service, +4..7 landing, +8/9 s_optag halves); pu_c = 2 kept copies of
 // p_pos[17:16] (the MU user: fseq read / write decode).  Same D / reset as the originals: exact.
 // R3f: every copy group sized to <= 16 enable bits (a DFFE enable costs 2 mapped loads per bit).  nc_pub (48): 0 formatter
 // eb_q, 1/2 eb_r halves, 3..6 formatter_identity quarters (+generation on 6), 7..10 command-context context_tag
 // quarters, 11..14 context_tag quarters (+valid on 14), 15..18 vm_q_epoch copies' D, 19/20 q_epoch_tag select halves,
 // 21 fs_pub enables, 22+13s+k service slot s begin groups.  rq_pub (38): 19s+0..3 service request-tag quarters, +4/5
 // base halves, +6 kreq copies, +7..10 landing tag quarters, +11/12 issued halves, +13/14 covered halves, +15..18 s_optag
 // quarters.  Copies 0..24 / 0..18 load the A face register (bnd_*), the rest the B face copy (<= 32 loads per face
 // flop).  ws_pub: 2 kept copies of p_kvs (formatter word_data group halves).  Same D / reset as the originals: exact.
 localparam integer NNC=50,NRQ=43;   // R3h: nc 48/49 = q_epoch_tag select quarters 2/3   // R3g: rq 38..42 = q_open (q_frame_tag quarters, q_window/q_count)
 wire[NNC-1:0]nc_pub;wire[10:0]ddc[0:23];wire[NRQ-1:0]rq_pub;wire[1:0]pu_pub[0:5];wire[1:0]ws_pub;
 wire lcv_fb,cmd0_fb;wire[5:0]stage_fb;
 generate if(LOCAL32&&RECV_INPUTS)begin:g_face_b
  (* keep = "true" *) reg lcv_b,cmd0_b;(* keep = "true" *) reg[5:0]stage_b;
  always @(posedge ck)begin lcv_b<=layer_context_v;stage_b<=command_stage;cmd0_b<=native_cmd[0];end   // == g_recv p_*
  assign lcv_fb=lcv_b;assign stage_fb=stage_b;assign cmd0_fb=cmd0_b;
 end else begin:g_face_b_alias
  assign lcv_fb=bnd_layer_context_v;assign stage_fb=bnd_command_stage;assign cmd0_fb=bnd_native_cmd[0];
 end endgenerate
 generate if(LOCAL32)begin:g_pin_pub
  (* keep = "true" *) reg[NNC-1:0]lcv_c;(* keep = "true" *) reg[5:0]stage_c[0:NNC-1];(* keep = "true" *) reg[10:0]dd_c[0:23];
  (* keep = "true" *) reg[NRQ-1:0]rq_c;(* keep = "true" *) reg[1:0]pu_c[0:5];(* keep = "true" *) reg[1:0]ws_c;
  integer pk;
  always @(posedge ck or negedge rst_pin)
   if(!rst_pin)begin lcv_c<=0;for(pk=0;pk<NNC;pk=pk+1)stage_c[pk]<=0;for(pk=0;pk<24;pk=pk+1)dd_c[pk]<=0;rq_c<=0;pu_c[0]<=0;pu_c[1]<=0;pu_c[2]<=0;pu_c[3]<=0;pu_c[4]<=0;pu_c[5]<=0;ws_c<=0;end
   else begin
    for(pk=0;pk<NNC;pk=pk+1)begin lcv_c[pk]<=(pk<25)?bnd_layer_context_v:lcv_fb;stage_c[pk]<=(pk<25)?bnd_command_stage:stage_fb;end
    for(pk=0;pk<24;pk=pk+1)dd_c[pk]<=bnd_dd_i[547:537];
    for(pk=0;pk<NRQ;pk=pk+1)rq_c[pk]<=(pk<19||(pk>=38&&pk<41))?bnd_native_cmd[0]:cmd0_fb;
    pu_c[0]<=bnd_native_position[17:16];pu_c[1]<=bnd_native_position[17:16];pu_c[2]<=bnd_native_position[17:16];pu_c[3]<=bnd_native_position[17:16];pu_c[4]<=bnd_native_position[17:16];pu_c[5]<=bnd_native_position[17:16];ws_c<={2{bnd_kv_word_slot}};
   end
  for(genvar k=0;k<NNC;k=k+1)begin:g_nc
   assign nc_pub[k]=lcv_c[k]&&stage_c[k]>=1&&stage_c[k]<=36;
  end
  for(genvar k=0;k<24;k=k+1)begin:g_ddc
   assign ddc[k]=dd_c[k];
  end
  assign rq_pub=rq_c;assign pu_pub[0]=pu_c[0];assign pu_pub[1]=pu_c[1];assign pu_pub[2]=pu_c[2];assign pu_pub[3]=pu_c[3];assign pu_pub[4]=pu_c[4];assign pu_pub[5]=pu_c[5];assign ws_pub=ws_c;
 end else begin:g_pin_alias
  assign nc_pub={NNC{p_lcv&&p_stage>=1&&p_stage<=36}};
  for(genvar k=0;k<24;k=k+1)begin:g_ddc
   assign ddc[k]=p_dd[547:537];
  end
  assign rq_pub={NRQ{p_cmd[0]}};assign pu_pub[0]=p_pos[17:16];assign pu_pub[1]=p_pos[17:16];assign pu_pub[2]=p_pos[17:16];assign pu_pub[3]=p_pos[17:16];assign pu_pub[4]=p_pos[17:16];assign pu_pub[5]=p_pos[17:16];assign ws_pub={2{p_kvs}};
 end endgenerate
 wire[4:0]emit_beat_pub[0:5];   // R3e/g/i: kept copies of dr_o[516:512], 3 per landing slot (check low / pipe, decode, check high)
 // Recurring filler context comes from the actual CTLM c_emb bank sample, before embedding HBM fetch.
 // A dedicated two-edge input pipeline keeps valid/user/token/position at one age. HEAD_PREP=0 retains
 // the legacy stage-1 epoch advance. HEAD_PREP=1 advances that SAME fseq bank here; stage 1 reuses it.
 reg[1:0]hp_v;reg[1:0]hp_u0,hp_u1;reg[17:0]hp_t0,hp_t1,hp_p0,hp_p1;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin hp_v<=0;hp_u0<=0;hp_u1<=0;hp_t0<=0;hp_t1<=0;hp_p0<=0;hp_p1<=0;end
  else begin
   hp_v<={hp_v[0],head_prepare_v};hp_u0<=head_prepare_user;hp_u1<=hp_u0;
   hp_t0<=head_prepare_token;hp_t1<=hp_t0;hp_p0<=head_prepare_position;hp_p1<=hp_p0;
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
 // R3e/g: == c_user; read select split low (fseq[6:0] + fstart) / high (fseq[13:7]), write decode its own copy.
 wire[1:0]c_user_r=MU?pu_pub[0]:2'd0,c_user_h=MU?pu_pub[2]:2'd0,c_user_w=MU?pu_pub[1]:2'd0;
 wire[13:0]fseq_rd={fseq[c_user_h][13:7],fseq[c_user_r][6:0]};
 wire[1:0]c_user_f=MU?pu_pub[4]:2'd0;   // R3i: == c_user (fstart read)
 wire[13:0]c_seq=(HEAD_PREP==0&&fstart[c_user_f]&&c_l0&&MUT!=6)?fseq_rd+14'd1:fseq_rd;
 wire hp_fill=HEAD_PREP!=0&&MU!=0&&hp_v[1]&&hp_u1!=2'd0;
 wire hp_host=HEAD_PREP!=0&&hp_v[1]&&hp_u1==2'd0;
 reg hp_host_pending,hp_host_fault;reg[17:0]hp_host_token,hp_host_position;
 wire hp_host_match=hp_host_pending&&p_hev&&p_hfc&&p_ht[58:43]==p_he&&
    p_ht[36:19]==hp_host_token&&p_ht[18:6]==hp_host_position[12:0]&&p_ht[42:37]==0&&p_ht[5:0]==0;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin hp_host_pending<=0;hp_host_fault<=0;hp_host_token<=0;hp_host_position<=0;end
  else begin
   if(hp_host)begin
    if(hp_host_pending||hp_t1>=151936||hp_p1>=8192)hp_host_fault<=1;
    hp_host_pending<=1;hp_host_token<=hp_t1;hp_host_position<=hp_p1;
   end else if(hp_host_match&&!hp_fill)hp_host_pending<=0;
  end
 wire[13:0]hp_seq=fstart[hp_u1]?fseq[hp_u1]+14'd1:fseq[hp_u1];
 wire[1:0]c_tag=(MUT==5&&c_user==2'd3)?2'd0:c_user;
 wire[1:0]c_user_e=MU?pu_pub[3]:2'd0,c_user_e2=MU?pu_pub[5]:2'd0;   // R3h/j: == c_user (begin_tag epoch select low / high)
 wire[15:0]c_epoch_f={c_seq,c_tag};
 wire[15:0]c_epoch={(MU==0||c_user_e2==2'd0)?p_he[15:8]:c_epoch_f[15:8],(MU==0||c_user_e==2'd0)?p_he[7:0]:c_epoch_f[7:0]};
 integer fu;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin for(fu=0;fu<4;fu=fu+1)fseq[fu]<=MU_SEQ0;fstart<=0;mu_fault<=0;end
  else begin
   if(hp_fill)begin
    fseq[hp_u1]<=hp_seq;fstart[hp_u1]<=1'b1;
    if({1'b0,hp_u1}>=3'(NU)||hp_t1>=18'd151936||hp_p1>=18'd8192)mu_fault<=1'b1;
   end
   if(MU!=0&&native_context&&c_user_w!=2'd0)begin   // R3h: c_user_w == c_user
    if(HEAD_PREP==0)begin fseq[c_user_w]<=c_seq;if(c_l0)fstart[c_user_w]<=1'b1;end
    if({1'b0,c_user}>=3'(NU)||(!fstart[c_user]&&(HEAD_PREP!=0||!c_l0)))mu_fault<=1'b1;
   end
  end
 generate if(MU==0)begin:g_ctx1
  qfd_native59_command_context u_context(
  .ck(ck),.rst_n(rst_ctx),.host_epoch_valid(p_hev),.host_fused_capability(p_hfc),.host_epoch(p_he),.host_tag(p_ht),.host_generation(p_hg),
  .context_v(native_context),.context_stage(p_stage),.context_token(p_tok),.context_position(p_pos),
  .native_cmd(p_cmd),.command_stage(p_stage),.command_token(p_tok),.command_position(p_pos),
  .service_active(active),.begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),.fault(context_fault));
 end else begin:g_ctxmu
  qfd_native59_command_context_mu_local32 #(.NU(NU),.LOCAL32(LOCAL32)) u_context(
  .ck(ck),.rst_n(rst_ctx),.host_epoch_valid(p_hev),.host_fused_capability(p_hfc),.host_epoch(p_he),.host_tag(p_ht),.host_generation(p_hg),
  .context_v(native_context),.context_stage(p_stage),.context_token(p_tok),.context_position(c_pos),
  .native_cmd(p_cmd),.command_stage(p_stage),.command_token(p_tok),.command_position(c_pos),
  .service_active(active),.ctx_user(c_user),.ctx_epoch(c_epoch),
  .begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),.fault(context_fault),
  .context_v_pub(nc_pub[10:7]));
 end endgenerate
 // Actual stage-1 head authority, independent of terminal RESULT ownership.  Kind-12 CONTEXT uses
 // stage zero on the wire; epoch/user, token, position and generation come from this exact begin.
 // Available one service edge after begin_slot; the sole paired calendar must price this output age
 // and its physical landing before reserving a C->K CONTEXT slot ahead of the matching HBM fetch.
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin head_descriptor_v<=0;head_descriptor_tag<=0;head_descriptor_generation<=0;end
  else begin
   head_descriptor_v<=HEAD_PREP!=0?(hp_fill||hp_host_match):(begin_slot&&(begin_tag[42:37]==6'd1));
   if(hp_fill)begin
    head_descriptor_tag<={hp_seq,hp_u1,6'd0,hp_t1,hp_p1[12:0],6'd0};
    head_descriptor_generation<=p_hg;
   end else if(HEAD_PREP!=0&&hp_host_match)begin
    head_descriptor_tag<={p_ht[58:43],6'd0,p_ht[36:0]};
    head_descriptor_generation<=p_hg;
   end else if(HEAD_PREP==0&&begin_slot&&(begin_tag[42:37]==6'd1))begin
    head_descriptor_tag<={begin_tag[58:43],6'd0,begin_tag[36:0]};
    head_descriptor_generation<=p_hg;
   end
  end
 // ---------------------------------------------------------------- dd word decode (the bank relays bnd_dd_i one edge: see the header)
 wire dd_v=p_dd[547];wire[1:0]dd_kind=p_dd[546:545];wire[7:0]dd_mask=p_dd[544:537];
 wire dd_q=dd_v&&dd_kind==2'd0,dd_kv=dd_v&&(dd_kind==2'd1||dd_kind==2'd2);
 wire dd_form_bad=(!dd_v&&(|p_dd[546:0]))||(dd_v&&((|p_dd[88:0])||dd_mask==8'd0||dd_kind==2'd3));
 // ---------------------------------------------------------------- Q: the hard Q-seat bank child's registered outputs
 // (qfd_native59_qbank; every word is the flat block's combinational value of the previous edge = this child's edge)
 wire vm_q_epoch,vm_q_start;
 wire q_open=(MUT==4)?vm_q_start:request_slot;
 wire[4:0]qo=(MUT==4)?{5{vm_q_start}}:rq_pub[42:38];
 reg qctx,qlock;
 wire q_in_bad=(dd_q&&(!qctx||qlock||begin_slot))||bnd_qb_bad;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin qctx<=0;qlock<=0;end
  else if(begin_slot)begin qctx<=1;qlock<=0;end
  else begin if(q_open)qlock<=1;end
 wire q_committed=bnd_qb_committed;
 wire[511:0]qrow=bnd_qb_row;wire qrow_full=bnd_qb_full;
 wire q_emit=bnd_qb_v;wire[4:0]q_emit_beat=bnd_qb_beat;
 wire q_miss=q_emit&&!qrow_full;
 wire[523:0]q=q_emit?{1'b1,3'd1,3'd0,q_emit_beat,qrow}:524'd0;
 wire export_control_fault;
 qfd_native59_q_export_control u_qexport_control(
 .ck(ck),.rst_n(rst_ctx),.begin_slot(begin_slot),.request_slot(request_slot),.q_committed(q_committed),
 .vm_q_epoch(vm_q_epoch),.vm_q_start(vm_q_start),.fault(export_control_fault));
 // R3e: two kept copies of vm_q_epoch (u_qexport_control: vm_q_epoch <= begin_slot under rst_ctx), one per q_epoch_tag half.
 wire[3:0]vq_pub;
 generate if(LOCAL32)begin:g_vq_pub
  (* keep = "true" *) reg[3:0]q;
  always @(posedge ck or negedge rst_ctx)if(!rst_ctx)q<=0;else q<=nc_pub[18:15];
  assign vq_pub=q;
 end else begin:g_vq_alias
  assign vq_pub={4{vm_q_epoch}};
 end endgenerate
 reg[58:0]context_tag,q_epoch_tag,q_frame_tag;
 reg context_valid,q_window,qtag_fault;reg[5:0]q_count;
 always @(posedge ck or negedge rst_top)begin
  if(!rst_top)begin context_tag<=0;q_epoch_tag<=0;q_frame_tag<=0;context_valid<=0;q_window<=0;qtag_fault<=0;q_count<=0;end
  else begin
   if(nc_pub[11])context_tag[14:0]<=begin_tag[14:0];
   if(nc_pub[12])context_tag[29:15]<=begin_tag[29:15];
   if(nc_pub[13])context_tag[44:30]<=begin_tag[44:30];
   if(nc_pub[14])begin context_tag[58:45]<=begin_tag[58:45];context_valid<=1;end
   if(vm_q_epoch)begin
    if(q_window||(!context_valid&&!begin_slot))qtag_fault<=1;
   end
   if(vq_pub[0])q_epoch_tag[14:0]<=nc_pub[19]?begin_tag[14:0]:context_tag[14:0];
   if(vq_pub[1])q_epoch_tag[29:15]<=nc_pub[20]?begin_tag[29:15]:context_tag[29:15];   // R3j: own select copy
   if(vq_pub[2])q_epoch_tag[44:30]<=nc_pub[48]?begin_tag[44:30]:context_tag[44:30];
   if(vq_pub[3])q_epoch_tag[58:45]<=nc_pub[49]?begin_tag[58:45]:context_tag[58:45];
   // R3g: q_open (== request_slot) captures in <= 16-bit groups on kept p_cmd[0] copies (qo[k] == q_open); same order.
   if(q_open&&(q_window||!q_committed))qtag_fault<=1;
   if(qo[4])begin q_window<=1;q_count<=0;end
   if(qo[0])q_frame_tag[14:0]<=q_epoch_tag[14:0];
   if(qo[1])q_frame_tag[29:15]<=q_epoch_tag[29:15];
   if(qo[2])q_frame_tag[44:30]<=q_epoch_tag[44:30];
   if(qo[3])q_frame_tag[58:45]<=q_epoch_tag[58:45];
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
  end
  // R3d: each lane's we / waddr / wdata halves are gated by that lane's own kept field copies (== dd_kv && dd_mask[l]).
  for(l=0;l<8;l=l+1)begin
   if(ddc[3*l][10]&&(ddc[3*l][9:8]==2'd1||ddc[3*l][9:8]==2'd2)&&ddc[3*l][l])begin
    kv_we[l]=1'b1;kv_waddr[24*l+:24]=p_dd[345+24*l+:24]^((MUT==2)?24'd1:24'd0);
   end
   if(ddc[3*l+1][10]&&(ddc[3*l+1][9:8]==2'd1||ddc[3*l+1][9:8]==2'd2)&&ddc[3*l+1][l])kv_wdata[32*l+:16]=p_dd[89+32*l+:16];
   if(ddc[3*l+2][10]&&(ddc[3*l+2][9:8]==2'd1||ddc[3*l+2][9:8]==2'd2)&&ddc[3*l+2][l])kv_wdata[32*l+16+:16]=p_dd[89+32*l+16+:16];
  end
 end
 reg[2:0]iss;
 always @(posedge ck or negedge rst_top)if(!rst_top)iss<=0;else iss<={iss[1:0],native_context};
 wire kv_issue=|iss;
 wire[1:0]kv_kind=iss[0]?2'd0:iss[1]?2'd1:2'd2;
 wire[17:0]kv_nin=iss[0]?18'd128:18'd64;
 wire formatter_fault,formatter_idle,formatter_drained,kvn_v;wire[7:0]formatter_fault_code;
 wire[10:0]kvn_tag;wire[511:0]kvn_data;wire[39:0]kvn_ctl_pub;
 ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1),.SAFE(SAFE),.LOCAL_CTL(LOCAL32))u_formatter(
 .clk(ck),.rst_n(rst_fmt),.epoch_begin(LOCAL32?nc_pub[0]:native_context),.epoch_begin_pub(nc_pub[2:1]),.word_slot_pub(ws_pub),.epoch_pos(c_pos),
 .issue_v(kv_issue),.issue_kind(kv_kind),.issue_nout(18'd1),.issue_nin(kv_nin),
 .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.epoch_idle(formatter_idle),.drained(formatter_drained),
 .word_v(kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),.word_ctl_pub(kvn_ctl_pub),.word_index_pub(fmt_index_pub),.word_slot(p_kvs),.word_index(p_kvi),
 .fault(formatter_fault),.fault_code(formatter_fault_code));
 reg[58:0]formatter_identity;reg[1:0]formatter_generation;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin formatter_identity<=0;formatter_generation<=0;end
  else begin
   if(nc_pub[3])formatter_identity[14:0]<=begin_tag[14:0];
   if(nc_pub[4])formatter_identity[29:15]<=begin_tag[29:15];
   if(nc_pub[5])formatter_identity[44:30]<=begin_tag[44:30];
   if(nc_pub[6])begin formatter_identity[58:45]<=begin_tag[58:45];formatter_generation<=p_hg;end
  end
 wire x3_fault;
 qfd_kvn_static_transport #(.LOCAL32(LOCAL32),.LOCAL_MUT(LOCAL_MUT)) u_kvn(.ck(ck),.rst_n(rst_x3),.word_v(LOCAL32?kvn_ctl_pub[39]:kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),
 .word_identity(formatter_identity),.word_generation(formatter_generation),.slot_v(LOCAL32?x3_slot_pub[9]:p_x3s),.word_ctl_pub(kvn_ctl_pub),.slot_pub(x3_slot_pub),
 .x3(x3),.x3_identity(x3_identity),.x3_generation(x3_generation),.fault(x3_fault));
 // ---------------------------------------------------------------- operation context slots (MU-D2D-OVL; NS = 1: as built)
 localparam integer NS=(MCTX!=0)?2:1;
 reg nf,fs,bs;                       // slot of the next begin, the front (latest begun) slot, the back (oldest active) slot
 wire[NS-1:0]s_active,s_completed,s_svc_fault,s_rec_fault,s_land_fault,s_commit_complete,s_tx_v,s_tx_vb,s_tx_vc,s_tx_vd;   // R3h/j/k: s_tx_vb/c/d == s_tx_v
 wire[NS-1:0]s_req_v,s_kq_v,s_vm_write_v;wire[58:0]s_vm_write_tag[0:NS-1];wire[19:0]s_vm_write_word[0:NS-1];
 wire[4:0]s_vm_write_beat[0:NS-1];wire[511:0]s_vm_write_data[0:NS-1];wire[24:0]s_vm_pub[0:NS-1];wire[547:0]s_tx_payload[0:NS-1];wire[94:0]s_ret[0:NS-1];
 reg[58:0]s_optag[0:NS-1];reg[NS-1:0]s_vis_seen;
 wire svc_fault=|s_svc_fault,record_fault=|s_rec_fault,land_fault=|s_land_fault;
 wire[9:0]back_slot_pub;
 generate if(LOCAL32)begin:g_back_slot_pub
  (* keep = "true" *) reg[9:0]q;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)q<=0;
   else if(MCTX!=0&&(|(s_completed&sel_b)))q<=~q;
  assign back_slot_pub=q;
 end else begin:g_back_slot_alias
  assign back_slot_pub={10{bs}};
 end endgenerate
 wire[NS-1:0]sel_nf=NS'(1)<<(MCTX!=0?nf:1'b0),sel_f=NS'(1)<<(MCTX!=0?fs:1'b0),sel_b=NS'(1)<<(MCTX!=0?bs:1'b0);
 assign active=|(s_active&sel_nf);   // the command context faults a begin into a slot that is still active
 assign completed=|s_completed;
 wire[NS-1:0] s_completing;
 wire[58:0] s_completed_tag[0:NS-1];
 generate if(MCTX!=0)begin:g_obs_last_slot
  for(genvar oc=0;oc<4;oc=oc+1)begin:g_copy
   localparam integer LO=15*oc,W=(oc==3)?14:15;
   (* keep = "true" *) reg last_slot;
   always @(posedge ck or negedge rst_top)
    if(!rst_top)last_slot<=0;
    else if(s_completing[0])last_slot<=0;
    else if(s_completing[1])last_slot<=1;
   assign completed_tag[LO+:W]=last_slot?s_completed_tag[1][LO+:W]:s_completed_tag[0][LO+:W];
  end
 end else begin:g_obs_one_slot
  assign completed_tag=s_completed_tag[0];
 end endgenerate
 // R3e: kept copy of bs (same statement) for the 95-bit native_ret select.
 wire bs_ret;
 generate if(LOCAL32)begin:g_bs_pub
  (* keep = "true" *) reg q;
  always @(posedge ck or negedge rst_top)if(!rst_top)q<=0;else if(MCTX!=0&&(|(s_completed&sel_b)))q<=~q;
  assign bs_ret=q;
 end else begin:g_bs_alias
  assign bs_ret=bs;
 end endgenerate
 assign service_ret_raw={s_ret[MCTX!=0?bs_ret:1'b0][94:2],{2{!(|(s_active&sel_nf))&&!svc_fault}}};
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin nf<=0;fs<=0;bs<=0;end
  else if(MCTX!=0)begin
   if(begin_slot)begin fs<=nf;nf<=~nf;end
   if(|(s_completed&sel_b))bs<=~bs;
  end
 // R3c (QW-CB16A0 10-20): 16 kept same-D copies of the received Q valid (g_recv.p_qb_v: D qb_v, no reset) and of the
 // front-slot register fs (async rst_top, D nf on begin_slot); each copy pair serves <= 5 of the 76 per-slot Q hold
 // enables (64 data bytes, 8 tag bytes, beat, q_seen low/high, count/checks).  Exact: every copy equals its original on
 // every edge, so q_slot_pub[b] == q_emit && f.  Other parameterisations alias the original nets (no added flops).
 localparam integer QPUB=(LOCAL32!=0&&RECV_INPUTS!=0&&RECV_MUT==0)?1:0;
 wire[15:0]qv_pub,fs_pub;
 generate if(QPUB)begin:g_qv_pub
  for(genvar k=0;k<16;k=k+1)begin:g_c
   (* keep = "true" *) reg v;
   (* keep = "true" *) reg s;
   always @(posedge ck) v<=qb_v;
   always @(posedge ck or negedge rst_top)
    if(!rst_top)s<=0;
    else if(MCTX!=0&&nc_pub[21])s<=nf;   // R3e: nc_pub[21] == begin_slot
   assign qv_pub[k]=v;assign fs_pub[k]=s;
  end
 end else begin:g_qv_alias
  assign qv_pub={16{q_emit}};assign fs_pub={16{fs}};
 end endgenerate
 // R3e: 4 kept same-D copies of the received Q beat (g_recv.p_qb_beat: D qb_beat, no reset), 2 per slot (service
 // q_slot_beat and its q_seen decode).
 wire[4:0]qbeat_pub[0:7];   // R3g/i: 4 per slot (check mux low / high, q_seen decode, kernel_q_beat)
 generate if(QPUB)begin:g_qbeat_pub
  for(genvar k=0;k<8;k=k+1)begin:g_c
   (* keep = "true" *) reg[4:0]b;
   always @(posedge ck) b<=qb_beat;
   assign qbeat_pub[k]=b;
  end
 end else begin:g_qbeat_alias
  for(genvar k=0;k<8;k=k+1)begin:g_c
   assign qbeat_pub[k]=q_emit_beat;
  end
 end endgenerate
 // the merged VM write (only the back slot writes; two at once is a slot collision)
 integer si,vb;
 reg vmw_v;reg[19:0]vmw_word;reg[4:0]vmw_beat;reg[58:0]vmw_tag;reg[511:0]vmw_data;reg vmw_two;
 reg ntx_v;reg[547:0]ntx_p;
 always @*begin
  vmw_v=0;vmw_word=0;vmw_beat=0;vmw_tag=0;vmw_data=0;vmw_two=0;ntx_v=0;ntx_p=0;
  for(si=0;si<NS;si=si+1)begin
   // R3c: each merged field is gated by its own kept vm_write_v copy ([21:0] 24-bit data segments, [22]/[23] tag
   // low/high, [24] word+beat); s_vm_pub[si][c] == s_vm_write_v[si] on every edge, so the merge is unchanged.
   if(s_vm_write_v[si])begin vmw_two=vmw_two|vmw_v;vmw_v=1;end
   if(s_vm_pub[si][24])begin vmw_word=vmw_word|s_vm_write_word[si];vmw_beat=vmw_beat|s_vm_write_beat[si];end
   if(s_vm_pub[si][22])vmw_tag[29:0]=vmw_tag[29:0]|s_vm_write_tag[si][29:0];
   if(s_vm_pub[si][23])vmw_tag[58:30]=vmw_tag[58:30]|s_vm_write_tag[si][58:30];
   for(vb=0;vb<512;vb=vb+1)if(s_vm_pub[si][vb/24])vmw_data[vb]=vmw_data[vb]|s_vm_write_data[si][vb];
   ntx_v=ntx_v|s_tx_v[si];   // NS 1: the codec register as built; R3h: each payload half under its own valid copy
   if(NS==1||s_tx_v[si])ntx_p[273:0]=ntx_p[273:0]|s_tx_payload[si][273:0];
   if(NS==1||s_tx_vb[si])ntx_p[410:274]=ntx_p[410:274]|s_tx_payload[si][410:274];
   if(NS==1||s_tx_vc[si])ntx_p[511:411]=ntx_p[511:411]|s_tx_payload[si][511:411];
   if(NS==1||s_tx_vd[si])ntx_p[547:512]=ntx_p[547:512]|s_tx_payload[si][547:512];
  end
 end
 assign vm_write_v=vmw_v;assign vm_write_word=vmw_word;assign vm_write_beat=vmw_beat;assign vm_write_tag=vmw_tag;assign vm_write_data=vmw_data;
 assign native_tx_v=ntx_v;assign native_tx_payload=ntx_p;
 wire user_bind_fault=(USER_BIND!=0)&&
  ((p_ts&&(p_tu!=s_optag[MCTX!=0?fs:1'b0][44:43]))||
   (p_rs&&(p_ru!=s_optag[MCTX!=0?bs:1'b0][44:43]))||
   (p_rv&&((p_ru!=s_optag[MCTX!=0?bs:1'b0][44:43])||(p_ru!=p_rp[520:519]))));
 wire visibility_fault=p_cs&&!(|(s_vis_seen&sel_b));
 // svc3 (QW-N59-4): the sticky DV fault as four sticky flops, each beside its own cone (v2 placed STA: one flop for all
 // terms, -149 ps); dv_fault = their OR on the same edge (exact).
 reg[3:0]dvf;wire dv_fault=|dvf;
 wire src_fault=context_fault|qtag_fault|export_control_fault|dv_fault|formatter_fault|x3_fault|record_fault|land_fault|visibility_fault|vm_address_fault|mu_fault|hp_host_fault;
 reg dr_s;                            // slot whose VM write is in dr_o (the landing fence of that slot checks it)
 reg[58:0]dr_tag;                     // declared before g_slot (u_land.emit_tag59 reads it; a later declaration made it a 1-bit implicit net)
 genvar gs;
 generate for(gs=0;gs<NS;gs=gs+1)begin:g_slot
  wire f=sel_f[gs],b=sel_b[gs];
  // Metadata binds the existing FRONT/BACK operation, never the newest c_user.
  // Wrong TX metadata removes its expected event; wrong RX metadata removes
  // its accepted event. The existing codec faults rather than consuming data.
  wire tx_user_match=(USER_BIND==0)||(p_tu==s_optag[gs][44:43]);
  wire rx_user_match=(USER_BIND==0)||((p_ru==s_optag[gs][44:43])&&(p_ru==p_rp[520:519]));
  wire req_s=request_slot&&f;
  // R3f: the slot's request publications, each gated by its own fs_pub copy (fs_pub[k] == fs): rq_s[k] == req_s.
  wire[18:0]rq_s;
  for(genvar k=0;k<19;k=k+1)begin:g_rqs
   assign rq_s[k]=rq_pub[19*gs+k]&&((MCTX==0)?1'b1:(fs_pub[k%16]==1'(gs)));
  end
  wire[75:0]result_slot_pub;
  wire[75:0]q_slot_pub;wire[23:0]kreq_pub;
  for(genvar qb=0;qb<76;qb=qb+1)begin:g_qsp
   localparam integer K=(qb<64)?qb/4:qb-64;
   assign q_slot_pub[qb]=qv_pub[K]&&((MCTX==0)?1'b1:(fs_pub[K]==1'(gs)));
  end
  wire[9:0]slot_back_pub=(MCTX==0)?10'h3ff:(gs==0?~back_slot_pub:back_slot_pub);
  wire result_v,result_slot,kernel_done;wire[4:0]result_beat,result_slot_beat;wire[58:0]result_tag,kernel_done_tag;wire[511:0]result_data;
  wire[58:0]req_tag,kq_tag;wire[4:0]kq_beat;wire[511:0]kq_data;
  wire vm_commit_v;wire[4:0]vm_commit_beat;wire[58:0]vm_commit_tag;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin s_optag[gs]<=0;s_vis_seen[gs]<=0;end
   else begin
    if(req_s)s_vis_seen[gs]<=0;
    else if(p_vis&&b)s_vis_seen[gs]<=s_commit_complete[gs]&&!s_land_fault[gs];
    if(rq_s[15])s_optag[gs][14:0]<=request_tag[14:0];     // R3e/f: rq_s[k] == req_s
    if(rq_s[16])s_optag[gs][29:15]<=request_tag[29:15];
    if(rq_s[17])s_optag[gs][44:30]<=request_tag[44:30];
    if(rq_s[18])s_optag[gs][58:45]<=request_tag[58:45];
   end
  // R3e: result_slot_beat kept copies (record: result_slot_beat <= rx_slot_beat = p_rb under rst_rec), 2 per slot.
  wire[4:0]rsb_a,rsb_b,rsb_c,rsb_d;
  if(LOCAL32)begin:g_rsb_pub
   (* keep = "true" *) reg[4:0]a,c,d,e;
   always @(posedge ck or negedge rst_rec)if(!rst_rec)begin a<=0;c<=0;d<=0;e<=0;end else begin a<=p_rb;c<=p_rb;d<=p_rb;e<=p_rb;end
   assign rsb_a=a;assign rsb_b=c;assign rsb_c=d;assign rsb_d=e;
  end else begin:g_rsb_alias
   assign rsb_a=result_slot_beat;assign rsb_b=result_slot_beat;assign rsb_c=result_slot_beat;assign rsb_d=result_slot_beat;
  end
  wire[12:0]svc_begin_pub;
  for(genvar k=0;k<13;k=k+1)begin:g_sbp
   assign svc_begin_pub[k]=nc_pub[22+13*gs+k]&&sel_nf[gs];
  end
  wire[4:0]vm_commit_beat_pub,vm_commit_beat_pub2,vm_commit_beat_pub3,vm_commit_beat_pub4;
  qfd_native59_static_service_obs1 #(.LOCAL32(LOCAL32)) u_service(
  .ck(ck),.rst_n(rst_svc),.source_fault(src_fault),
  .begin_slot(begin_slot&&sel_nf[gs]),.begin_tag(begin_tag),.request_slot(req_s),.request_tag(request_tag),.result_base_word(base),
  .qr_committed(q_committed),.qr_tag(q_epoch_tag),.kernel_request_v(s_req_v[gs]),.kernel_request_pub(kreq_pub),.vm_write_pub(s_vm_pub[gs]),.kernel_request_tag(req_tag),
  .q_slot(q_emit&&f),.q_slot_pub(q_slot_pub),.q_slot_beat(qbeat_pub[4*gs]),.q_v(q[523]&&f),.q_beat(q[516:512]),.q_tag(q_frame_tag),.q_data(QPUB?qrow:q[511:0]),
  .kernel_q_v(s_kq_v[gs]),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
  .result_slot(result_slot),.result_slot_pub(result_slot_pub),.result_slot_beat(rsb_a),.result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),
  .vm_write_v(s_vm_write_v[gs]),.vm_write_word(s_vm_write_word[gs]),.vm_write_beat(s_vm_write_beat[gs]),.vm_write_tag(s_vm_write_tag[gs]),.vm_write_data(s_vm_write_data[gs]),
  .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag(vm_commit_tag),.kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),
  .complete_slot(p_cs&&b),.completed(s_completed[gs]),.completing(s_completing[gs]),.completed_tag(s_completed_tag[gs]),.active(s_active[gs]),.fault(s_svc_fault[gs]),.native_ret(s_ret[gs]),
  .begin_pub(svc_begin_pub),.request_pub(rq_s[6:0]),.q_slot_beat_pub(qbeat_pub[4*gs+1]),.q_slot_beat_pub2(qbeat_pub[4*gs+2]),.q_slot_beat_pub3(qbeat_pub[4*gs+3]),
  .result_slot_beat_pub(rsb_b),.vm_commit_beat_pub(vm_commit_beat_pub),.result_slot_beat_pub2(rsb_c),.vm_commit_beat_pub2(vm_commit_beat_pub2),
  .result_slot_beat_pub3(rsb_d),.vm_commit_beat_pub3(vm_commit_beat_pub3),.vm_commit_beat_pub4(vm_commit_beat_pub4));
  qfd_native59_record_endpoint #(.CODEC_MUT(CODEC_MUT),.RX_FREE(1),.TX_FREE(MCTX!=0),.LOCAL32(LOCAL32))u_record(   // QW-N59-4: free rx (svc2) / tx (svc3, MCTX 1: payload merged under tx_v) capture, output-exact
  .ck(ck),.rst_n(rst_rec),.operation_tag(s_optag[gs]),.kernel_request_v(s_req_v[gs]),.kernel_request_pub(kreq_pub),.kernel_request_tag(req_tag),
  .kernel_q_v(s_kq_v[gs]),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
  .tx_slot(p_ts&&f&&tx_user_match),.tx_slot_kind(p_tk),.tx_slot_beat(p_tb),.tx_valid(s_tx_v[gs]),.tx_payload(s_tx_payload[gs]),.tx_valid_pub(s_tx_vb[gs]),.tx_valid_pub2(s_tx_vc[gs]),.tx_valid_pub3(s_tx_vd[gs]),
  .rx_result_pub(rx_result_pub),.slot_back_pub(slot_back_pub),.rx_event(p_rv&&b&&rx_user_match),.rx_payload(p_rp),.rx_slot(p_rs&&b),.rx_slot_kind(p_rk),.rx_slot_beat(p_rb),
  .result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),.result_slot(result_slot),.result_slot_pub(result_slot_pub),.result_slot_beat(result_slot_beat),
  .kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),.fault(s_rec_fault[gs]));
  qfd_native59_dr_landing_local32 #(.LAND_EDGES(LAND_EDGES),.LOCAL32(LOCAL32))u_land(
  .ck(ck),.rst_n(rst_land),.request_slot(req_s),.request_tag59(request_tag),
  .emit_v(dr_o[519]&&!dr_o[518]&&(NS==1||dr_s==1'(gs))),.emit_beat(emit_beat_pub[3*gs]),.emit_tag59(dr_tag),.visibility_slot(p_vis&&b),
  .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag59(vm_commit_tag),.complete(s_commit_complete[gs]),.fault(s_land_fault[gs]),
  .request_pub(rq_s[14:7]),.emit_beat_pub(emit_beat_pub[3*gs+1]),.vm_commit_beat_pub(vm_commit_beat_pub),.vm_commit_beat_pub2(vm_commit_beat_pub2),
  .emit_beat_pub2(emit_beat_pub[3*gs+2]),.vm_commit_beat_pub3(vm_commit_beat_pub3),.vm_commit_beat_pub4(vm_commit_beat_pub4));
 end endgenerate
 // ---------------------------------------------------------------- embedding row read (G9), 65 EMB + optional ARM/RoPE tail
 wire emb_go=!p_cmd[0]&&p_cmd[379:376]==4'hE;
 wire cmd_bad=(emb_go&&((|p_cmd[357:1])||p_cmd[375:358]>=18'd151936))||(!p_cmd[0]&&(|p_cmd)&&!emb_go);
 // Twelve invalid positions let RP1 arm after the 65 EMB words. The same
 // e1/e2/e3 (and optional e4) pipeline carries valid, beat, and payload ages.
 localparam integer ROPE_FIRST=77;
 reg emb_act;reg[6:0]emb_k;reg[17:0]emb_tok;
 wire emb_read=emb_act&&(emb_k<=7'd64||(ROPE!=0&&emb_k>=7'(ROPE_FIRST)));
 wire[23:0]rope_addr=24'd9723904+{3'd0,emb_tok,3'd0}+24'(emb_k-7'(ROPE_FIRST));
 reg e1,e2,e3;reg[6:0]k1,k2,k3;
 (* keep = "true" *) reg e3b;(* keep = "true" *) reg[6:0]k3b;   // R3g: == e3 / k3 (half of the e4c / k4c copies)
 // R3e: 3 kept copies of emb_act (the same set / clear statements, so ea_c[k] == emb_act on every edge): [0] code
 // address / re, [1] scale address / re, [2] emb_tok start.  LOCAL32 0: the original.
 // R3f: 6 copies: [0]/[1] code address halves (+re on 0), [2]/[3] scale address halves (+re on 2), [4]/[5] emb_tok halves.
 (* keep = "true" *) reg[5:0]ea_c;
 wire[5:0]ea=LOCAL32?ea_c:{6{emb_act}};
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin emb_act<=0;emb_k<=0;emb_tok<=0;emb_code_re<=0;emb_code_addr<=0;emb_scale_re<=0;emb_scale_addr<=0;
                  e1<=0;e2<=0;e3<=0;k1<=0;k2<=0;k3<=0;ea_c<=0;e3b<=0;k3b<=0;end
  else begin
   emb_code_re<=0;emb_scale_re<=0;
   if(emb_go&&!emb_act&&!cmd_bad)begin emb_act<=1;ea_c<=6'b111111;emb_k<=0;end
   if(emb_go&&!ea[4]&&!cmd_bad)emb_tok[8:0]<=p_cmd[366:358];
   if(emb_go&&!ea[5]&&!cmd_bad)emb_tok[17:9]<=p_cmd[375:367];
   if(ea[0]&&emb_k<7'd64)begin emb_code_re<=1;emb_code_addr[11:0]<={emb_tok[5:0],emb_k[5:0]^((MUT==3)?6'd1:6'd0)};end
   if(ea[1]&&emb_k<7'd64)emb_code_addr[23:12]<=emb_tok[17:6];
   if(ea[0]&&ROPE!=0&&emb_k>=7'(ROPE_FIRST))begin emb_code_re<=1;emb_code_addr[11:0]<=rope_addr[11:0];end
   if(ea[1]&&ROPE!=0&&emb_k>=7'(ROPE_FIRST))emb_code_addr[23:12]<=rope_addr[23:12];
   if(ea[2]&&emb_k==7'd64)begin emb_scale_re<=1;emb_scale_addr[8:0]<=emb_tok[8:0];end
   if(ea[3]&&emb_k==7'd64)emb_scale_addr[17:9]<=emb_tok[17:9];
   if(emb_act)begin
    emb_k<=emb_k+7'd1;if(emb_k==(ROPE?7'(ROPE_FIRST+7):7'd64))begin emb_act<=0;ea_c<=0;end
   end
   // read edge (e1: the re flop is at the pin), provider answer (e2), answer in the pin register (e3)
   e1<=emb_read;k1<=emb_k;e2<=e1;k2<=k1;e3<=e2;k3<=k2;e3b<=e2;k3b<=k2;
  end
 // ---------------------------------------------------------------- dr_o: group 0 attention result / group 1 embedding row
 wire g0=vm_write_v;
 wire g1;
 generate if(EMB_RELAY==0)begin:g_emb_direct
  assign g1=e3;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin dr_o<=0;dr_tag<=0;dr_s<=0;end
   else begin
    dr_tag<=vm_write_tag;dr_s<=(NS>1)?s_vm_write_v[NS-1]:1'b0;
    dr_o<=g0?{1'b1,1'b0,1'b0,vm_write_beat,vm_write_data}:
          g1?{1'b1,1'b1,(k3==7'd64)?6'd0:((k3>7'd64)?6'(k3-7'(ROPE_FIRST)):k3[5:0]),(k3==7'd64)?{496'd0,p_esq}:p_ecq}:520'd0;
   end
 for(genvar k=0;k<6;k=k+1)begin:g_emd
  assign emit_beat_pub[k]=dr_o[516:512];
 end
 end else begin:g_emb_relay
  // relay stage (no reset on the data: every use is qualified by the reset e4 copies)
  reg[511:0]ecq_r;reg[15:0]esq_r;
  always @(posedge ck)begin ecq_r<=p_ecq;esq_r<=p_esq;end
  reg e4;reg[5:0]k4b;reg k4s;
  localparam integer EC=LOCAL32?32:16,ES=512/EC;   // R3e: 32 copies (16-bit segments) under LOCAL32
  (* keep = "true" *) reg[EC-1:0]e4c;   // one select copy per ES-bit dr_o segment
  (* keep = "true" *) reg[EC-1:0]k4c;   // scale-word select copies (k3 == 64)
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin e4<=0;k4b<=0;k4s<=0;e4c<=0;k4c<=0;end
   else begin e4<=e3;k4b<=(k3>7'd64)?6'(k3-7'(ROPE_FIRST)):k3[5:0];k4s<=(k3==7'd64);e4c<={{(EC/2){e3b}},{(EC/2){e3}}};k4c<={{(EC/2){k3b==7'd64}},{(EC/2){k3==7'd64}}};end
  assign g1=e4;
  integer sb,gi;
  reg[21:0]g0s;
  wire[7:0]dr_hi_n=g0?{1'b1,1'b0,1'b0,vm_write_beat}:e4?{1'b1,1'b1,k4s?6'd0:k4b}:8'd0;
  // R3e: per landing slot a kept copy of dr_o[516:512] (same D, same reset) for its issued-bit decode.
  (* keep = "true" *) reg[4:0]em_c[0:5];
  integer ek;
  always @(posedge ck or negedge rst_top)if(!rst_top)for(ek=0;ek<6;ek=ek+1)em_c[ek]<=0;else for(ek=0;ek<6;ek=ek+1)em_c[ek]<=dr_hi_n[4:0];
  for(genvar k=0;k<6;k=k+1)begin:g_emp
   assign emit_beat_pub[k]=LOCAL32?em_c[k]:dr_o[516:512];
  end
  always @*begin g0s=0;for(gi=0;gi<NS;gi=gi+1)g0s=g0s|s_vm_pub[gi][21:0];end
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin dr_o<=0;dr_tag<=0;dr_s<=0;end
   else begin
    dr_tag<=vm_write_tag;dr_s<=(NS>1)?s_vm_write_v[NS-1]:1'b0;
    dr_o[519:512]<=dr_hi_n;
    // R3c: the attention-result select per 24-bit segment is the OR of that segment's kept slot copies (== g0).
    for(sb=0;sb<512;sb=sb+1)
     dr_o[sb]<=g0s[sb/24]?vm_write_data[sb]:
               e4c[sb/ES]?(k4c[sb/ES]?((sb<16)?esq_r[sb]:1'b0):ecq_r[sb]):1'b0;
   end
 end endgenerate
 // ---------------------------------------------------------------- sticky DV boundary faults and the fault pin
 always @(posedge ck or negedge rst_top)
  if(!rst_top)dvf<=0;
  else begin
   if(dd_form_bad||kv_in_bad)dvf[0]<=1;
   if(q_in_bad||q_miss)dvf[1]<=1;
   if((g0&&g1)||(emb_go&&emb_act)||cmd_bad||user_bind_fault)dvf[2]<=1;
   if(vmw_two)dvf[3]<=1;
  end
 always @(posedge ck or negedge rst_top)
  if(!rst_top)fault<=0;
  else fault<=svc_fault|context_fault|qtag_fault|export_control_fault|dv_fault|formatter_fault|x3_fault|record_fault|land_fault|visibility_fault|vm_address_fault|mu_fault|hp_host_fault;
 initial begin
  if(NATIVE_PROFILE!=0&&LAND_QUALIFIED!=1)$fatal(1,"native service requires the measured dr landing edge contract");
  if(LAND_EDGES<2)$fatal(1,"LAND_EDGES must include the slice pin register and VM write");
  if(MUT<0||MUT>6||(MUT>=5&&NU<2))$fatal(1,"qfd_native59_svc: MUT undefined");
  if(NU<1||NU>4)$fatal(1,"qfd_native59_dv_service: NU %0d outside 1..4",NU);
  if(MCTX!=0&&MCTX!=1)$fatal(1,"qfd_native59_dv_service: MCTX %0d (0 or 1)",MCTX);
 end
endmodule
