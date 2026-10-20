`timescale 1ns/1ps
// MU-KV-PEER 10-19: 4 users x ROUNDS steps end to end through the die-0 coordinator chain at MU 1, users PIPELINED
// (each user starts its next step as soon as its previous step POSTs; user 3 is held back in round 1 so the other
// users overtake it and the per-user epochs reach the peers out of global order).
//   host cmd (hc, user on pos[17:16]) -> die-0 token service _mu -> qkd_host_tp8_coordinator_mu (allocator_mu, epoch
//   {seq14,user2}) -> grant -> local hc + 7 peer token frames (peer token services _mu, per-user epoch freshness) ->
//   8 endpoints _mu (4 contexts) -> 8 rank codecs (class9) -> coordinator codec _mu -> cohort _mu (dispatch in begin
//   order) -> engine dispatch -> KV layer programme _mu (4 contexts, 36 writer stages, KV row 64+l+256u) -> KV done ->
//   engine result -> class9 result to 8 ranks -> endpoint retire -> lifecycle _mu terminal queue -> allocator/cohort
//   terminal -> codec _mu terminal queue (class5 barrier, class8 releases) -> HOST step retire + CQ (rank-0 class 6/7)
//   -> POST collector _mu -> POST queue -> the user's next step.
// Die drains (every endpoint / rank status) are high only when no KV context runs, so with users pipelined every
// terminal, release and POST but the last ones takes the "other users in flight" path; each POST must follow its
// step's KV done within POST_LIM cycles (a global-drain wait would take a whole other user's step).
module tb_mu_peer_e2e;
 reg ck=0;always #0.5 ck=~ck;
 reg por_n=0,rst_n=0;
 integer cyc=0;always @(posedge ck)cyc<=cyc+1;
 localparam integer ROUNDS=3,POST_LIM=400,DELAY3=3000;
 integer fails=0;reg trace=0;initial trace=$test$plusargs("TRACE");
 task fail(input[1023:0]m);begin fails=fails+1;if(fails<12)$display("ERR cyc %0d %0s",cyc,m);end endtask
 // ---------------- die drains (KV model) ----------------
 wire kac,kst_w;wire drn;
 // ---------------- token services (die 0 = coordinator side, dies 1..7 peers) ----------------
 reg ts_rx_v[0:7];reg[511:0]ts_rx_d[0:7];reg ts_tx_cr[0:7];
 wire ts_tx_v[0:7];wire[511:0]ts_tx_d[0:7];wire[181:0]ts_hc[0:7];wire ts_fault[0:7];wire ts_tev[0:7];wire[15:0]ts_te[0:7];
 wire ts_cv[0:7];wire[58:0]ts_ct[0:7];wire[1:0]ts_cg[0:7];wire ts_cd[0:7],ts_cf[0:7];wire[3:0]ts_cdr[0:7];
 reg cmd_v=0;reg[181:0]cmd_hc=0;wire cmd_cr;reg pkg_abort=0;reg abort_mode=0;integer ncancel=0;
 wire ts_trv[0:7],ts_tgr[0:7],ts_ccr[0:7];wire[17:0]ts_trt[0:7],ts_trp[0:7];wire[1:0]ts_trg[0:7];
 // coordinator <-> die-0 token service
 wire t_req_v,t_req_r;wire[17:0]t_req_tok,t_req_pos;wire[1:0]t_req_gen;
 wire t_gv,t_gr;wire[15:0]t_gep;wire[17:0]t_gtok,t_gpos;wire[1:0]t_ggen;wire[58:0]t_gtag;wire a_v,a_d;
 wire co_idf,co_wl,co_rc;
 // rank side
 wire[7:0]peer_rx_valid,peer_rx_ready,peer_tx_valid,peer_tx_ready;wire[4095:0]peer_rx_data,peer_tx_data;
 wire[7:0]rq_v,rq_cr,rs_v,rs_done,rs_fault,rs_cr,owned,crel,rel_v,ep_fault,rc_fault,c_acc;
 wire[471:0]rq_tag,rs_tag,rel_tag;wire[15:0]rq_gen,rs_gen,rel_gen;wire[255:0]rq_trace,rs_val,rs_cyc;wire[143:0]rq_tok,rq_pos,rs_tok;wire[31:0]rs_cause;
 wire[743:0]ltk;
 reg cert_v=0;
 reg st_issue=0,st_retire=0,st_cq=0,st_rcq=0;reg[15:0]st_client=0;reg[7:0]st_slot=0;reg[17:0]st_pos=0,st_tok=0;
 for(genvar d=0;d<8;d=d+1)begin:g_ts
  qkd_host_ctrl_token_service_packet_collected_mu #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1))ts(
   .ck(ck),.rst_n(rst_n),.die_id(3'(d)),.rx_v(ts_rx_v[d]),.rx_d(ts_rx_d[d]),.rx_cr(),.tx_v(ts_tx_v[d]),.tx_d(ts_tx_d[d]),.tx_cr(ts_tx_cr[d]),
   .local_tk(ltk[d*93+:93]),.local_kst(10'd0),.local_boot(2'b11),.cmd_v(d==0?cmd_v:1'b0),.cmd_hc(d==0?cmd_hc:182'd0),.cmd_cr(ts_ccr[d]),
   .hc(ts_hc[d]),.tk8(),.kst8(),.boot8(),.seen(),.fault(ts_fault[d]),.startup_allowed(1'b1),.local_service_ready(1'b1),
   .local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),.begin_cr(),.begin_available(),.service_begin_v(),
   .service_begin_epoch(),.pending_advertised(),.pending_epoch(),.service_ready8(),.pending_ack8(),.service_epoch8(),
   .ingest_permission(),.por_n(por_n),.token_wrap_fence_valid(d==0?co_rc:1'b0),.token_wrap_drained(d==0?co_rc:1'b0),
   .token_wrap_link_reset_seen(d==0?co_rc:1'b0),.token_wrap_retraining_done(d==0?co_rc:1'b0),
   .token_allocator_fault(d==0?co_idf:1'b0),.package_abort(d==0?pkg_abort:1'b0),.abort_drained(d==0?{4{drn}}:4'd0),
   .token_request_valid(ts_trv[d]),.token_request_ready(d==0?t_req_r:1'b0),.token_request_token(ts_trt[d]),.token_request_position(ts_trp[d]),
   .token_request_generation(ts_trg[d]),.token_grant_valid(d==0?t_gv:1'b0),.token_grant_ready(ts_tgr[d]),
   .token_grant_epoch(d==0?t_gep:16'd0),.token_grant_token(d==0?t_gtok:18'd0),.token_grant_position(d==0?t_gpos:18'd0),
   .token_grant_generation(d==0?t_ggen:2'd0),.token_grant_tag(d==0?t_gtag:59'd0),.allocated_valid(d==0?a_v:1'b0),
   .allocated_delivered(d==0?a_d:1'b0),.allocated_epoch(d==0?t_gep:16'd0),.allocated_token(d==0?t_gtok:18'd0),
   .allocated_position(d==0?t_gpos:18'd0),.allocated_generation(d==0?t_ggen:2'd0),.token_epoch_valid(ts_tev[d]),
   .token_epoch(ts_te[d]),.cancel_valid(ts_cv[d]),.cancel_tag(ts_ct[d]),.cancel_generation(ts_cg[d]),.cancel_done(ts_cd[d]),
   .cancel_fault(ts_cf[d]),.cancel_drained(ts_cdr[d]),.terminal_accepted(c_acc[d]));
 end
 assign t_req_v=ts_trv[0];assign t_req_tok=ts_trt[0];assign t_req_pos=ts_trp[0];assign t_req_gen=ts_trg[0];
 assign t_gr=ts_tgr[0];assign cmd_cr=ts_ccr[0];
 // ---------------- coordinator (MU 1) ----------------
 wire dispatch_valid,dispatched,co_fault,post_pending,consensus;wire[58:0]cohort_tag;wire[1:0]cohort_gen;wire[7:0]acc_ranks;
 reg er_v=0;reg[58:0]er_tag=0;reg[1:0]er_gen=0;reg[17:0]er_tok=0;reg[31:0]er_val=0;wire er_cr;
 qkd_host_tp8_coordinator_mu #(.MU(1)) co(.ck_codec(ck),.ck_lifecycle(ck),.ck_post(ck),.por_n(por_n),
  .peer_rx_valid(peer_rx_valid),.peer_rx_data(peer_rx_data),.peer_rx_ready(peer_rx_ready),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.peer_tx_ready(peer_tx_ready),
  .token_request_valid(t_req_v),.token_request_token(t_req_tok),.token_request_position(t_req_pos),.token_request_gen(t_req_gen),.token_request_ready(t_req_r),
  .token_grant_valid(t_gv),.token_grant_ready(t_gr),.token_grant_epoch(t_gep),.token_grant_token(t_gtok),.token_grant_position(t_gpos),.token_grant_gen(t_ggen),.token_grant_tag(t_gtag),
  .allocated_valid(a_v),.allocated_delivered(a_d),.engine_admit_ready(1'b1),.dispatch_valid(dispatch_valid),.dispatched(dispatched),.cohort_tag(cohort_tag),.cohort_gen(cohort_gen),
  .accepted_ranks(acc_ranks),.participant_trace(),.participant_token(),.participant_pos(),
  .engine_result_v(er_v),.engine_result_tag(er_tag),.engine_result_gen(er_gen),.engine_result_done(1'b1),.engine_result_fault(1'b0),.engine_result_cause(4'd0),
  .engine_result_token(er_tok),.engine_result_value(er_val),.engine_result_cycles(32'd77),.engine_result_cr(er_cr),
  .program_consensus(consensus),.program_epoch(),.program_digest(),.certificate_valid(),.certificate(),.certificate_prefix(),
  .wrap_locked(co_wl),.identity_fault(co_idf),.recovery_complete(co_rc),.post_pending(post_pending),.fault(co_fault));
 // ---------------- 8 ranks: class9 rank codec + endpoint _mu ----------------
 for(genvar d=0;d<8;d=d+1)begin:g_rk
  qkd_host_peer_rank_codec #(.RANK(d))rc(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[d]),.tx_data(peer_rx_data[d*512+:512]),.tx_ready(peer_rx_ready[d]),.rx_valid(peer_tx_valid[d]),.rx_data(peer_tx_data[d*512+:512]),.rx_ready(peer_tx_ready[d]),
   .request_v(rq_v[d]),.request_tag(rq_tag[d*59+:59]),.request_gen(rq_gen[d*2+:2]),.request_trace(rq_trace[d*32+:32]),.request_token(rq_tok[d*18+:18]),.request_pos(rq_pos[d*18+:18]),.request_cr(rq_cr[d]),.request_aborted(),
   .cancel_valid(ts_cv[d]),.cancel_tag(ts_ct[d]),.cancel_gen(ts_cg[d]),.cancel_done(ts_cd[d]),.cancel_fault(ts_cf[d]),.cancel_drained(ts_cdr[d]),.cancel_accepted(c_acc[d]),
   .cancel_release_v(rel_v[d]),.cancel_release_tag(rel_tag[d*59+:59]),.cancel_release_gen(rel_gen[d*2+:2]),.cancel_released(crel[d]),
   .result_v(rs_v[d]),.result_tag(rs_tag[d*59+:59]),.result_gen(rs_gen[d*2+:2]),.result_done(rs_done[d]),.result_fault(rs_fault[d]),.result_cause(rs_cause[d*4+:4]),.result_token(rs_tok[d*18+:18]),.result_value(rs_val[d*32+:32]),.result_cycles(rs_cyc[d*32+:32]),.result_cr(rs_cr[d]),
   .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drn}}),.context_owned(owned[d]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
   .step_issue_v(d==0&&st_issue),.step_client_tag(st_client),.step_slot(st_slot),.step_pos(st_pos),.step_retire_v(d==0&&st_retire),.step_retire_cq(st_rcq),.step_retire_client_tag(st_client),.step_retire_slot(st_slot),.step_retire_pos(st_pos),.step_retire_token(st_tok),
   .cq_commit_v(d==0&&st_cq),.cq_client_tag(st_client),.cq_slot(st_slot),.cq_pos(st_pos),.cq_token(st_tok),.certificate_v(cert_v),.certificate(66'h1234),.certificate_prefix(32'd0),
   .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(),.retrain_request(),.recovery_clear(),.fault(rc_fault[d]));
  qkd_host_native_token_endpoint_cancel_mu #(.ENABLE_NATIVE(1),.MU(1))ep(.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(ts_hc[d]),.legacy_tk(93'd0),.image_ready(1'b1),
   .shared_epoch_valid(ts_tev[d]),.shared_epoch(ts_te[d]),
   .request_v(rq_v[d]),.request_tag(rq_tag[d*59+:59]),.request_trace(rq_trace[d*32+:32]),.request_gen(rq_gen[d*2+:2]),.request_token(rq_tok[d*18+:18]),.request_pos(rq_pos[d*18+:18]),.request_cr(rq_cr[d]),.native_pr(),
   .result_v(rs_v[d]),.result_tag(rs_tag[d*59+:59]),.result_gen(rs_gen[d*2+:2]),.result_done(rs_done[d]),.result_fault(rs_fault[d]),.result_cause(rs_cause[d*4+:4]),.result_token(rs_tok[d*18+:18]),.result_value(rs_val[d*32+:32]),.result_cycles(rs_cyc[d*32+:32]),.result_cr(rs_cr[d]),
   .kv_drained(drn),.vm_drained(drn),.collective_drained(drn),.host_drained(drn),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(1'b0),
   .cancel_release_v(rel_v[d]),.cancel_release_tag(rel_tag[d*59+:59]),.cancel_release_gen(rel_gen[d*2+:2]),.context_owned(owned[d]),.cancel_released(crel[d]),.local_tk(ltk[d*93+:93]),.protocol_fault(ep_fault[d]));
 end
 // ---------------- KV layer programme _mu + KV row ----------------
 reg we=0;reg[8:0]ad=0;reg[63:0]da=0;reg kst=0;reg[15:0]kep=0;reg[17:0]ktok=0,kpos=0;reg[1:0]kgen=0;
 wire cg,kg,vg,ai,ar,ws,ls,ss,sd,qq,cf,kdn,kft;wire[5:0]cs,kstg,klay;wire[15:0]kepo;wire[17:0]ktko,kpso;
 wire[13:0]kct;wire[1:0]kgno;wire[7:0]kfc;wire[31:0]kage,ktc;
 qkd_static_kv_layer_programme_mu #(.MU(1)) kv(
  .ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(ad),.cfg_data(da),.start(kst),.authority_valid(1'b1),
  .programme_authorized(1'b1),.programme_epoch(16'h00a5),.programme_digest(64'hfeedfacecafebeef),.authority_epoch(kep),
  .authority_token(ktok),.authority_position(kpos),.authority_generation(kgen),.ctrl_go(cg),.kgo(kg),.vgo(vg),
  .attention_issue(ai),.attention_run(ar),.writer_start(ws),.link_start(ls),.stage_start(ss),.stage_done(sd),
  .expected_upstream_quiet(qq),.completed_stage(cs),.stage(kstg),.layer(klay),.epoch(kepo),.token(ktko),.position(kpso),
  .ctx_t(kct),.generation(kgno),.configured(cf),.active(kac),.done(kdn),.fault(kft),.fault_code(kfc),.age(kage),
  .token_cycles(ktc));
 assign drn=!kac&&!kst;
 wire[28:0]xa_o;wire rf;wire[287:0]es_o;
 qkd_kv_mu_wrow #(.MU(1),.NL(1)) wrow(.user(kepo[1:0]),.es_i(288'd0),.xa_i({19'(64+klay),10'd0}),.es_o(es_o),.xa_o(xa_o),.range_fault(rf));
 // ---------------- token-service frame router (die d -> target die, one frame per 2 edges per target) ----------------
 reg[511:0]rq[0:7][0:63];integer rqw[0:7],rqr[0:7],rgap[0:7],crp[0:7];integer i,t,ri,fi,bi;
 initial for(i=0;i<8;i=i+1)begin rqw[i]=0;rqr[i]=0;rgap[i]=0;crp[i]=0;ts_rx_v[i]=0;ts_rx_d[i]=0;ts_tx_cr[i]=0;end
 always @(negedge ck)begin
  for(ri=0;ri<8;ri=ri+1)begin
   ts_rx_v[ri]=0;ts_tx_cr[ri]=0;
   if(ts_tx_v[ri])begin
    t=-1;for(integer b=0;b<8;b=b+1)if(ts_tx_d[ri][24+b])t=b;
    if(t<0||ts_tx_d[ri][31:24]!=(8'd1<<t))fail("router: frame without one target");
    else begin rq[t][rqw[t]%64]=ts_tx_d[ri];rqw[t]=rqw[t]+1;end
    crp[ri]=crp[ri]+1;
   end
  end
  for(ri=0;ri<8;ri=ri+1)begin
   if(crp[ri]>0)begin ts_tx_cr[ri]=1;crp[ri]=crp[ri]-1;end
   if(rgap[ri]>0)rgap[ri]=rgap[ri]-1;
   else if(rqr[ri]<rqw[ri])begin ts_rx_v[ri]=1;ts_rx_d[ri]=rq[ri][rqr[ri]%64];rqr[ri]=rqr[ri]+1;rgap[ri]=1;end
  end
 end
 // ---------------- per-user bookkeeping ----------------
 reg[15:0]ep_of[0:3];reg[17:0]tok_of[0:3],pos_of[0:3];reg[1:0]gen_of[0:3];
 integer grants[0:3],disp_n[0:3],kdone_n[0:3],ret_n[0:3],post_n[0:3],done_cyc[0:3],kvbusy[0:3],wr_of[0:3];
 reg[35:0]layer_seen[0:3];reg[5:0]last_layer[0:3];
 integer nreq=0,nws=0,nres=0,npost=0,overlap_disp=0,overlap_post=0,maxlat=0,cmd_credit=4,peer_starts=0,epoch_out_of_order=0;
 reg[15:0]last_grant_ep=0;reg any_grant=0;
 initial for(i=0;i<4;i=i+1)begin grants[i]=0;disp_n[i]=0;kdone_n[i]=0;ret_n[i]=0;post_n[i]=0;kvbusy[i]=0;wr_of[i]=0;layer_seen[i]=0;last_layer[i]=0;ep_of[i]=0;tok_of[i]=0;pos_of[i]=0;gen_of[i]=0;end
 function automatic integer others_busy(input integer u);integer k;begin others_busy=0;for(k=0;k<4;k=k+1)if(k!=u&&kvbusy[k])others_busy=1;end endfunction
 // grants (allocator epochs {seq14[user], user2}, one per user per round)
 always @(posedge ck)if(t_gv&&t_gr)begin:grant_mon
  integer u;u=t_gep[1:0];
  if(t_gpos[17:16]!==2'(u))fail("grant epoch user != position user");
  if(t_gep[15:2]!==14'(grants[u]))fail("allocator epoch != {seq14[user], user}");
  if(any_grant&&t_gep<last_grant_ep)epoch_out_of_order=epoch_out_of_order+1;
  any_grant=1;last_grant_ep=t_gep;
  ep_of[u]=t_gep;grants[u]=grants[u]+1;
  if(trace)$display("T %0d grant u%0d ep %h",cyc,u,t_gep);
 end
 // starts at every die: shared epoch = the user's allocated epoch, user consistent
 always @(negedge ck)for(integer d=0;d<8;d=d+1)if(ts_hc[d][38])begin
  if(!ts_tev[d]||ts_te[d]!==((t_gv&&t_gr&&t_gep[1:0]==ts_hc[d][17:16])?t_gep:ep_of[ts_hc[d][17:16]])||ts_te[d][1:0]!==ts_hc[d][17:16])fail("die start without the user's shared epoch");
  if(d!=0)peer_starts=peer_starts+1;
 end
 // rank requests: stripped position + the user's TAG
 always @(posedge ck)for(integer d=0;d<8;d=d+1)if(rq_v[d])begin:req_mon
  integer u;u=rq_tag[d*59+43+:2];nreq=nreq+1;
  if(rq_pos[d*18+:18]!=={5'd0,pos_of[u][12:0]})fail("request position not stripped");
  if(rq_tag[d*59+:59]!=={ep_of[u],6'd0,tok_of[u],pos_of[u][12:0],6'd0}||rq_gen[d*2+:2]!==gen_of[u])fail("request TAG/gen");
 end
 // cohort dispatch: all 8 ranks, the user's TAG -> start the user's KV token at its frame slot
 always @(posedge ck)if(dispatch_valid)begin:disp_mon
  integer u;u=cohort_tag[44:43];
  if(acc_ranks!==8'hff)fail("partial cohort dispatch");
  if(cohort_tag!=={ep_of[u],6'd0,tok_of[u],pos_of[u][12:0],6'd0}||cohort_gen!==gen_of[u])fail("cohort TAG/gen");
  if(others_busy(u))overlap_disp=overlap_disp+1;
  disp_n[u]=disp_n[u]+1;
  if(trace)$display("T %0d dispatch u%0d",cyc,u);
 end
 // writer stages
 always @(negedge ck)if(rst_n&&ws)begin:ws_mon
  integer u;u=kepo[1:0];nws=nws+1;
  if(kepo!==ep_of[u])fail("writer epoch is not the user's allocated epoch");
  if(xa_o[28:10]!==19'(64+klay+256*u))fail("KV row != 64+layer+256*user");
  if(rf)fail("row range fault");
  if(layer_seen[u][klay])fail("layer written twice for a user in one token");
  layer_seen[u][klay]=1;wr_of[u]=wr_of[u]+1;
  if(klay!=0&&klay!=last_layer[u]+1)fail("user layers out of order");
  last_layer[u]=klay;
 end
 // KV done -> engine result queue
 reg[1:0]resq[0:63];integer resw=0,resr=0,er_busy=0;
 always @(posedge ck)if(kdn)begin:kdone_mon
  integer u;u=kepo[1:0];
  if(wr_of[u]!=36)fail("user token without 36 writer stages");
  if(trace)$display("T %0d kvdone u%0d",cyc,u);
  kvbusy[u]=0;done_cyc[u]=cyc;kdone_n[u]=kdone_n[u]+1;resq[resw%64]=2'(u);resw=resw+1;
 end
 always @(negedge ck)begin
  er_v=0;
  if(er_cr)begin er_busy=0;nres=nres+1;end
  if(!er_busy&&resr<resw&&rst_n)begin:er_send
   integer u;u=resq[resr%64];resr=resr+1;er_busy=1;
   er_v=1;er_tag={ep_of[u],6'd37,tok_of[u],pos_of[u][12:0],6'd0};er_gen=gen_of[u];er_tok=18'h100+18'(u);er_val=32'hc0de0000+u;
  end
 end
 // die-0 endpoint retire report (pkgctl MU form) -> HOST step retire for that user
 reg[92:0]ltk0_q=0;
 always @(posedge ck)begin
  ltk0_q<=ltk[92:0];
  if(rst_n&&ltk[92]&&ltk[91:90]!==ltk0_q[91:90])begin:ret_mon
   integer u;u=ltk[81:64]-18'h100;
   if(u<0||u>3)fail("retire report token");
   else begin
    if(ltk[91:90]!==gen_of[u])fail("retire report generation");
    if(ltk[63:32]!==32'hc0de0000+u)fail("retire report value of another user");
    ret_n[u]=ret_n[u]+1;
    if(trace)$display("T %0d retire0 u%0d",cyc,u);
   end
  end
 end
 // POSTs (coordinator POST collector _mu): in order per user, within POST_LIM of the user's KV done
 always @(posedge ck)if(co.g_mu.u_lifecycle.post_retired)begin:post_mon
  integer u,lat;u=co.g_mu.u_lifecycle.post_tag[44:43];
  if(co.g_mu.u_lifecycle.post_tag!=={ep_of[u],6'd37,tok_of[u],pos_of[u][12:0],6'd0})fail("POST identity");
  lat=cyc-done_cyc[u];if(lat>maxlat)maxlat=lat;
  if(lat>POST_LIM&&!abort_mode)begin fail("POST late (waited for a global die drain while other users in flight)");$display("  u%0d lat %0d",u,lat);end
  if(others_busy(u))overlap_post=overlap_post+1;
  post_n[u]=post_n[u]+1;npost=npost+1;
  if(trace)$display("T %0d post u%0d lat %0d",cyc,u,lat);
 end
 // faults
 always @(negedge ck)if(por_n&&rst_n)begin
  for(fi=0;fi<8;fi=fi+1)if(ts_fault[fi])begin fail("token service fault");$display("  die %0d",fi);end
  if(co_fault)begin fail("coordinator fault");$display("  codec %b post %b identity %b lifecycle %b alloc %b cohort %b",co.g_mu.codec_fault,co.g_mu.post_fault,co.identity_fault,co.g_mu.lifecycle_fault,co.g_mu.u_lifecycle.g_mu.u_lifecycle.g_mu.allocator_fault,co.g_mu.u_lifecycle.g_mu.u_lifecycle.g_mu.cohort_fault);end
  if(co_idf)fail("coordinator identity_fault");
  if(|rc_fault)fail("rank codec fault");
  if(|ep_fault)fail("endpoint protocol_fault");
  if(kft)begin fail("KV programme fault");$display("  code %h cf %b",kfc,cf);end
  if(fails>=12)begin $display("FAIL MU_PEER_E2E fails=%0d (stopped)",fails);$finish;end
 end
 always @(posedge ck)if(ts_cv[0]&&c_acc[0])ncancel<=ncancel+1;
 // ---------------- host ----------------
 reg host_busy=0,step_busy=0;integer host_steps=0;
 always @(posedge ck)if(cmd_cr)cmd_credit<=cmd_credit+1;
 task automatic lock_host;begin while(host_busy)@(negedge ck);host_busy=1;end endtask
 task automatic step_frame(input integer kind,input integer u,input bit rcq);begin
  while(step_busy||g_rk[0].rc.step_pending||g_rk[0].rc.retire_pending||g_rk[0].rc.cq_pending)@(negedge ck);
  step_busy=1;
  @(negedge ck);st_client=16'h7261+16'(u);st_slot=8'(u);st_pos=pos_of[u];st_tok=18'h100+18'(u);st_rcq=rcq;
  if(kind==5)st_issue=1;if(kind==6)st_retire=1;if(kind==7)st_cq=1;
  @(negedge ck);st_issue=0;st_retire=0;st_cq=0;repeat(2)@(negedge ck);step_busy=0;
 end endtask
 task automatic kv_start(input integer u);begin
  while((cyc%64)!=16*u||kst)@(posedge ck);
  @(negedge ck);kst=1;kep=ep_of[u];ktok=tok_of[u];kpos={5'd0,pos_of[u][12:0]};kgen=gen_of[u];kvbusy[u]=1;wr_of[u]=0;layer_seen[u]=0;last_layer[u]=0;
  @(negedge ck);kst=0;
 end endtask
 task automatic host_cmd(input integer u,input integer r);reg[17:0]p;begin
  p={2'(u),3'd0,13'(100*r+17*u+1)};
  lock_host;
  while(cmd_credit==0)@(negedge ck);
  pos_of[u]=p;tok_of[u]=18'(1000+10*r+u);gen_of[u]=2'(host_steps+1);host_steps=host_steps+1;   // pkgctl MU: generation +1 per host step
  @(negedge ck);cmd_v=1;cmd_hc=0;cmd_hc[38]=1;cmd_hc[37:36]=gen_of[u];cmd_hc[35:18]=tok_of[u];cmd_hc[17:0]=p;cmd_credit=cmd_credit-1;
  @(negedge ck);cmd_v=0;host_busy=0;
  step_frame(5,u,0);
 end endtask
 task automatic wait_cnt(input integer which,input integer u,input integer n,input[1023:0]m);integer k;begin
  k=0;while((which==0?disp_n[u]:which==1?ret_n[u]:post_n[u])<n&&k<20000)begin @(negedge ck);k=k+1;end
  if(k>=20000)begin fail(m);$display("  u%0d n%0d",u,n);end
 end endtask
 task automatic user_thread(input integer u);integer r,k;begin
  for(r=0;r<ROUNDS;r=r+1)begin
   if(u==3&&r==1)repeat(DELAY3)@(negedge ck);
   host_cmd(u,r);
   k=0;while(disp_n[u]<=r&&k<20000)begin @(negedge ck);k=k+1;end
   if(k>=20000)begin fail("user step never dispatched");$display("  u%0d r%0d",u,r);end
   kv_start(u);
   k=0;while(ret_n[u]<=r&&k<20000)begin @(negedge ck);k=k+1;end
   if(k>=20000)begin fail("user step never retired at die 0");$display("  u%0d r%0d",u,r);dump;end
   step_frame(6,u,r>0);
   if(r>0)step_frame(7,u,0);
   k=0;while(post_n[u]<=r&&k<20000)begin @(negedge ck);k=k+1;end
   if(k>=20000)begin fail("user step never POSTed");$display("  u%0d r%0d post_pending %b",u,r,post_pending);end
  end
 end endtask
 task dump;begin
  $display("  ep0 n_q %0d n_i %0d act %b pend %b iss %b seen %b done %b qu %0d %0d %0d %0d rp %0d ip %0d credit %b relp %b relu %0d",
   g_rk[0].ep.g_mu.n_q,g_rk[0].ep.g_mu.n_i,g_rk[0].ep.g_mu.c_act,g_rk[0].ep.g_mu.c_pend,g_rk[0].ep.g_mu.c_iss,g_rk[0].ep.g_mu.c_seen,g_rk[0].ep.g_mu.c_done,
   g_rk[0].ep.g_mu.q_u[0],g_rk[0].ep.g_mu.q_u[1],g_rk[0].ep.g_mu.q_u[2],g_rk[0].ep.g_mu.q_u[3],g_rk[0].ep.g_mu.rp,g_rk[0].ep.g_mu.ip,g_rk[0].ep.g_mu.credit,g_rk[0].ep.g_mu.release_pending,g_rk[0].ep.g_mu.uc);
  $display("  er_busy %0d resr %0d resw %0d codec result_busy %b send %h ret %h tq_n %0d tsend %h trel %h rq_queued %h rq_ack %h",er_busy,resr,resw,
   co.g_mu.u_peer.g_mu.result_busy,co.g_mu.u_peer.g_mu.result_send,co.g_mu.u_peer.g_mu.result_return,co.g_mu.u_peer.g_mu.tq_n,co.g_mu.u_peer.g_mu.terminal_send,co.g_mu.u_peer.terminal_released,co.g_mu.u_peer.g_mu.request_queued,co.g_mu.u_peer.g_mu.request_ack);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",0,
   g_rk[0].rc.result_busy,g_rk[0].rc.credit_pending,g_rk[0].rc.req_pending,g_rk[0].rc.barrier_wait,g_rk[0].rc.release_pending,g_rk[0].ep.g_mu.c_act,g_rk[0].ep.g_mu.c_seen,g_rk[0].ep.g_mu.n_q,g_rk[0].ep.g_mu.release_pending,g_rk[0].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",1,
   g_rk[1].rc.result_busy,g_rk[1].rc.credit_pending,g_rk[1].rc.req_pending,g_rk[1].rc.barrier_wait,g_rk[1].rc.release_pending,g_rk[1].ep.g_mu.c_act,g_rk[1].ep.g_mu.c_seen,g_rk[1].ep.g_mu.n_q,g_rk[1].ep.g_mu.release_pending,g_rk[1].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",2,
   g_rk[2].rc.result_busy,g_rk[2].rc.credit_pending,g_rk[2].rc.req_pending,g_rk[2].rc.barrier_wait,g_rk[2].rc.release_pending,g_rk[2].ep.g_mu.c_act,g_rk[2].ep.g_mu.c_seen,g_rk[2].ep.g_mu.n_q,g_rk[2].ep.g_mu.release_pending,g_rk[2].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",3,
   g_rk[3].rc.result_busy,g_rk[3].rc.credit_pending,g_rk[3].rc.req_pending,g_rk[3].rc.barrier_wait,g_rk[3].rc.release_pending,g_rk[3].ep.g_mu.c_act,g_rk[3].ep.g_mu.c_seen,g_rk[3].ep.g_mu.n_q,g_rk[3].ep.g_mu.release_pending,g_rk[3].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",4,
   g_rk[4].rc.result_busy,g_rk[4].rc.credit_pending,g_rk[4].rc.req_pending,g_rk[4].rc.barrier_wait,g_rk[4].rc.release_pending,g_rk[4].ep.g_mu.c_act,g_rk[4].ep.g_mu.c_seen,g_rk[4].ep.g_mu.n_q,g_rk[4].ep.g_mu.release_pending,g_rk[4].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",5,
   g_rk[5].rc.result_busy,g_rk[5].rc.credit_pending,g_rk[5].rc.req_pending,g_rk[5].rc.barrier_wait,g_rk[5].rc.release_pending,g_rk[5].ep.g_mu.c_act,g_rk[5].ep.g_mu.c_seen,g_rk[5].ep.g_mu.n_q,g_rk[5].ep.g_mu.release_pending,g_rk[5].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",6,
   g_rk[6].rc.result_busy,g_rk[6].rc.credit_pending,g_rk[6].rc.req_pending,g_rk[6].rc.barrier_wait,g_rk[6].rc.release_pending,g_rk[6].ep.g_mu.c_act,g_rk[6].ep.g_mu.c_seen,g_rk[6].ep.g_mu.n_q,g_rk[6].ep.g_mu.release_pending,g_rk[6].ep.protocol_fault);
  $display("  rank %0d rc result_busy %b credit_pending %b req_pending %b barrier %b relp %b | ep act %b seen %b n_q %0d relp %b fault %b",7,
   g_rk[7].rc.result_busy,g_rk[7].rc.credit_pending,g_rk[7].rc.req_pending,g_rk[7].rc.barrier_wait,g_rk[7].rc.release_pending,g_rk[7].ep.g_mu.c_act,g_rk[7].ep.g_mu.c_seen,g_rk[7].ep.g_mu.n_q,g_rk[7].ep.g_mu.release_pending,g_rk[7].ep.protocol_fault);
 end endtask
 integer udone=0;
 initial begin
  repeat(3)@(negedge ck);por_n=1;rst_n=1;repeat(6)@(negedge ck);
  // KV programme boot: stage_end 64, roots 3..11, GAP 0 except user 3 before stage 5 (+64)
  for(bi=0;bi<36;bi=bi+1)begin
   @(negedge ck);we=1;ad=9*bi+0;da=3;@(negedge ck);ad=9*bi+1;da=4;@(negedge ck);ad=9*bi+2;da=5;@(negedge ck);ad=9*bi+3;da=6;
   @(negedge ck);ad=9*bi+4;da=10;@(negedge ck);ad=9*bi+5;da=7;@(negedge ck);ad=9*bi+6;da=8;@(negedge ck);ad=9*bi+7;da=11;
   @(negedge ck);ad=9*bi+8;da=64;
  end
  @(negedge ck);ad=324;da=64'hfeedfacecafebeef;@(negedge ck);ad=325;da=64'h00a5;
  for(bi=0;bi<144;bi=bi+1)begin @(negedge ck);ad=326+bi;da=(bi==3*36+4)?64:0;end
  @(negedge ck);ad=470;da=64'h514b564c59523336;@(negedge ck);we=0;
  repeat(4)@(negedge ck);
  if(!cf||kft)begin $display("FAIL MU_PEER_E2E KV boot cf=%b fault=%b",cf,kft);$finish;end
  @(negedge ck);cert_v=1;@(negedge ck);cert_v=0;
  bi=0;while(!consensus&&bi<2000)begin @(negedge ck);bi=bi+1;end
  if(!consensus)fail("no program consensus");
  repeat(50)@(negedge ck);
  fork
   begin user_thread(0);udone=udone+1;end
   begin user_thread(1);udone=udone+1;end
   begin user_thread(2);udone=udone+1;end
   begin user_thread(3);udone=udone+1;end
  join_none
  bi=0;while(udone<4&&bi<200000)begin @(negedge ck);bi=bi+1;end
  repeat(50)@(negedge ck);
  if(post_pending||(|owned)||a_v)fail("allocations/contexts/POSTs left at the end");
  if(npost!=4*ROUNDS)fail("POST count");
  if(nreq!=8*4*ROUNDS)fail("rank request count");
  if(nws!=36*4*ROUNDS)fail("writer stage count");
  if(peer_starts!=7*4*ROUNDS)fail("peer start count");
  if(overlap_disp<4*ROUNDS-4)fail("users not pipelined (dispatch overlap)");
  if(overlap_post<2*ROUNDS)fail("POSTs not overlapped with other users' KV work");
  if(epoch_out_of_order==0)fail("bench lost its out-of-order epoch case");
  if($test$plusargs("ABORT"))begin
   // abort with three retained users: u0 has completed and POSTed (its retained request names a TERMINATED identity),
   // u1 and u2 are dispatched and never run (live allocations).  The die-0 token service must cancel all three in
   // turn; the lifecycle acknowledges u0's cancel against its last retired identity and turns u1/u2 into fault
   // terminals; every endpoint releases them, the HOST retires both with a fault CQ, and both POST.
   abort_mode=1;
   host_cmd(0,ROUNDS);wait_cnt(0,0,ROUNDS+1,"abort phase: u0 never dispatched");
   host_cmd(1,ROUNDS);wait_cnt(0,1,ROUNDS+1,"abort phase: u1 never dispatched");
   host_cmd(2,ROUNDS);wait_cnt(0,2,ROUNDS+1,"abort phase: u2 never dispatched");
   kv_start(0);wait_cnt(1,0,ROUNDS+1,"abort phase: u0 never retired");
   step_frame(6,0,1);step_frame(7,0,0);wait_cnt(2,0,ROUNDS+1,"abort phase: u0 never POSTed");
   repeat(20)@(negedge ck);
   if(!a_v||g_ts[0].ts.g_mu.rr!==4'b0111)begin fail("abort fixture: retained users != {u0,u1,u2}");$display("  rr %b",g_ts[0].ts.g_mu.rr);end
   @(negedge ck);pkg_abort=1;
   bi=0;while(ncancel<3&&bi<5000)begin @(negedge ck);bi=bi+1;end
   if(ncancel!=3)begin fail("abort: not all three retained users cancelled and acknowledged");$display("  cancels %0d rr %b",ncancel,g_ts[0].ts.g_mu.rr);end
   repeat(100)@(negedge ck);
   step_frame(6,1,1);step_frame(7,1,0);step_frame(6,2,1);step_frame(7,2,0);
   wait_cnt(2,1,ROUNDS+1,"abort phase: cancelled u1 never POSTed");wait_cnt(2,2,ROUNDS+1,"abort phase: cancelled u2 never POSTed");
   repeat(50)@(negedge ck);
   if(post_pending||(|owned)||a_v||g_ts[0].ts.g_mu.rr!=0)fail("abort: allocations/contexts/POSTs/retained left");
   if(fails==0)$display("PASS MU_PEER_ABORT cancels=%0d (u0 terminated identity, u1+u2 live) posts=%0d after %0d normal steps",ncancel,npost,4*ROUNDS);
   else $display("FAIL MU_PEER_ABORT fails=%0d cancels=%0d posts=%0d",fails,ncancel,npost);
   $finish;
  end
  if(abort_mode);
  else if(fails==0)
   $display("PASS MU_PEER_E2E users=4 rounds=%0d steps=%0d posts=%0d rank_requests=%0d peer_starts=%0d writer_stages=%0d overlap_dispatch=%0d overlap_post=%0d epochs_out_of_global_order=%0d max_post_after_kv_done=%0d cycles=%0d",
     ROUNDS,4*ROUNDS,npost,nreq,peer_starts,nws,overlap_disp,overlap_post,epoch_out_of_order,maxlat,cyc);
  else $display("FAIL MU_PEER_E2E fails=%0d posts=%0d requests=%0d writer_stages=%0d",fails,npost,nreq,nws);
  $finish;
 end
 initial begin #3000000;$display("FAIL MU_PEER_E2E timeout posts=%0d fails=%0d",npost,fails);$finish;end
endmodule
