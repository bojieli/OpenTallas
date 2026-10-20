`timescale 1ns/1ps
// QW-N59-4 (10-19): service child of the hardened native59 split; edge contract and rationale in qfd_native59_qbank.sv.
// ----------------------------------------------------------------------------------------------------------------------
// Service child: qfd_native59_dv_service (SAFE 2, ROOTS 1, RST_FOREST 1) with the Q-seat section replaced by the bank's
// registered qb_* words.  dd_i / layer_context_v / command_stage are the bank's one-edge relays (so this child's pin
// registers see them one edge later, like every other port of this child: see the file header).
module qfd_native59_svc #(
 parameter integer MUT=0,CODEC_MUT=0,NATIVE_PROFILE=0,LAND_QUALIFIED=0,LAND_EDGES=8,
 parameter integer NU=1,parameter [13:0] MU_SEQ0=14'd0,parameter integer MCTX=0,EMB_RELAY=0
)(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[547:0]dd_i,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 output wire[523:0]x3,output wire[58:0]x3_identity,output wire[1:0]x3_generation,
 input wire qb_v,input wire[4:0]qb_beat,input wire[511:0]qb_row,input wire qb_full,qb_committed,qb_bad,
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
 (* keep = "true" *) reg[199:0]rst_cp_fmt;(* keep = "true" *) reg[23:0]rst_cp_x3;(* keep = "true" *) reg[103:0]rst_cp_svc;
 (* keep = "true" *) reg[79:0]rst_cp_rec;(* keep = "true" *) reg[11:0]rst_cp_ctx;(* keep = "true" *) reg[55:0]rst_cp_land;
 (* keep = "true" *) reg[79:0]rst_cp_pin;(* keep = "true" *) reg[47:0]rst_cp_top;   // QW-N59-4: qseen/qctx moved to the bank (1,599 - ~520 loads)
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
 reg p_ts;reg[3:0]p_tk;reg[4:0]p_tb;reg p_rv;reg[547:0]p_rp;reg p_rs;reg[3:0]p_rk;reg[4:0]p_rb;
 reg[511:0]p_ecq;reg[15:0]p_esq;reg p_vis,p_cs;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin
   p_hev<=0;p_hfc<=0;p_he<=0;p_ht<=0;p_hg<=0;p_lcv<=0;p_stage<=0;p_tok<=0;p_pos<=0;p_cmd<=0;p_dd<=0;
   p_kvs<=0;p_x3s<=0;p_kvi<=0;p_ts<=0;p_tk<=0;p_tb<=0;p_rv<=0;p_rp<=0;p_rs<=0;p_rk<=0;p_rb<=0;
   p_ecq<=0;p_esq<=0;p_vis<=0;p_cs<=0;
  end else begin
   p_hev<=host_epoch_valid;p_hfc<=host_fused_capability;p_he<=host_epoch;p_ht<=host_tag;p_hg<=host_generation;
   p_lcv<=layer_context_v;p_stage<=command_stage;p_tok<=native_token;p_pos<=native_position;p_cmd<=native_cmd;p_dd<=dd_i;
   p_kvs<=kv_word_slot;p_x3s<=kv_x3_slot;p_kvi<=kv_word_index;
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
 // ---------------------------------------------------------------- dd word decode (the bank relays dd_i one edge: see the header)
 wire dd_v=p_dd[547];wire[1:0]dd_kind=p_dd[546:545];wire[7:0]dd_mask=p_dd[544:537];
 wire dd_q=dd_v&&dd_kind==2'd0,dd_kv=dd_v&&(dd_kind==2'd1||dd_kind==2'd2);
 wire dd_form_bad=(!dd_v&&(|p_dd[546:0]))||(dd_v&&((|p_dd[88:0])||dd_mask==8'd0||dd_kind==2'd3));
 // ---------------------------------------------------------------- Q: the hard Q-seat bank child's registered outputs
 // (qfd_native59_qbank; every word is the flat block's combinational value of the previous edge = this child's edge)
 wire vm_q_epoch,vm_q_start;
 wire q_open=(MUT==4)?vm_q_start:request_slot;
 reg qctx,qlock;
 wire q_in_bad=(dd_q&&(!qctx||qlock||begin_slot))||qb_bad;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin qctx<=0;qlock<=0;end
  else if(begin_slot)begin qctx<=1;qlock<=0;end
  else begin if(q_open)qlock<=1;end
 wire q_committed=qb_committed;
 wire[511:0]qrow=qb_row;wire qrow_full=qb_full;
 wire q_emit=qb_v;wire[4:0]q_emit_beat=qb_beat;
 wire q_miss=q_emit&&!qrow_full;
 wire[523:0]q=q_emit?{1'b1,3'd1,3'd0,q_emit_beat,qrow}:524'd0;
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
 .clk(ck),.rst_n(rst_fmt),.epoch_begin(native_context),.epoch_pos(c_pos),
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
  .q_slot(q_emit&&f),.q_slot_beat(q_emit_beat),.q_v(q[523]&&f),.q_beat(q[516:512]),.q_tag(q_frame_tag),.q_data(q[511:0]),
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
 wire g0=vm_write_v;
 reg[58:0]dr_tag;
 wire g1;
 generate if(EMB_RELAY==0)begin:g_emb_direct
  assign g1=e3;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin dr_o<=0;dr_tag<=0;dr_s<=0;end
   else begin
    dr_tag<=vm_write_tag;dr_s<=(NS>1)?s_vm_write_v[NS-1]:1'b0;
    dr_o<=g0?{1'b1,1'b0,1'b0,vm_write_beat,vm_write_data}:
          g1?{1'b1,1'b1,(k3==7'd64)?6'd0:k3[5:0],(k3==7'd64)?{496'd0,p_esq}:p_ecq}:520'd0;
   end
 end else begin:g_emb_relay
  // relay stage (no reset on the data: every use is qualified by the reset e4 copies)
  reg[511:0]ecq_r;reg[15:0]esq_r;
  always @(posedge ck)begin ecq_r<=p_ecq;esq_r<=p_esq;end
  reg e4;reg[5:0]k4b;reg k4s;
  (* keep = "true" *) reg[15:0]e4c;   // one select copy per 32-bit dr_o segment
  (* keep = "true" *) reg[15:0]k4c;   // scale-word select copies (k3 == 64)
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin e4<=0;k4b<=0;k4s<=0;e4c<=0;k4c<=0;end
   else begin e4<=e3;k4b<=k3[5:0];k4s<=(k3==7'd64);e4c<={16{e3}};k4c<={16{k3==7'd64}};end
  assign g1=e4;
  integer sg;
  always @(posedge ck or negedge rst_top)
   if(!rst_top)begin dr_o<=0;dr_tag<=0;dr_s<=0;end
   else begin
    dr_tag<=vm_write_tag;dr_s<=(NS>1)?s_vm_write_v[NS-1]:1'b0;
    dr_o[519:512]<=g0?{1'b1,1'b0,1'b0,vm_write_beat}:e4?{1'b1,1'b1,k4s?6'd0:k4b}:8'd0;
    for(sg=0;sg<16;sg=sg+1)
     dr_o[32*sg+:32]<=g0?vm_write_data[32*sg+:32]:
                      e4c[sg]?(k4c[sg]?((sg==0)?{16'd0,esq_r}:32'd0):ecq_r[32*sg+:32]):32'd0;
   end
 end endgenerate
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
  if(MUT<0||MUT>6||(MUT>=5&&NU<2))$fatal(1,"qfd_native59_svc: MUT undefined");
  if(NU<1||NU>4)$fatal(1,"qfd_native59_dv_service: NU %0d outside 1..4",NU);
  if(MCTX!=0&&MCTX!=1)$fatal(1,"qfd_native59_dv_service: MCTX %0d (0 or 1)",MCTX);
 end
endmodule

