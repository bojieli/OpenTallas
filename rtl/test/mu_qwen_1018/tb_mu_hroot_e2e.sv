`timescale 1ns/1ps
// MU-ADOPT-HROOT 10-19: 4-user steps end to end on the KV die host root, MU 1.
//   allocator  ot_qwen_tp8_token_epoch_allocator_mu   (epoch = {seq14[user], user2}, one allocation per user)
//   endpoint   qkd_host_native_token_endpoint_cancel_mu (hc user on pos[17:16], 4 contexts, in-order retire)
//   KV         qkd_static_kv_layer_programme_mu        (4 contexts, compiled per-user stage GAP table)
//   KV row     qkd_kv_mu_wrow (MU 1) on every writer_start: row = 64 + layer + 256*user, user = programme epoch[1:0]
// Per round the host admits 4 steps (users 0..3, one in flight per user, generation +1 per step as ot_qfd_pkgctl MU),
// the endpoint issues each request (position stripped to 13 b), the KV programme runs the 4 users interleaved (user u
// shifted 16u in the 64-cycle stage frame; user 3 also has a compiled 64-cycle gap before stage 5), each done becomes
// the endpoint result, the endpoint retires in acceptance order with the pkgctl-MU report, then the allocator terminal.
// Die drains are high only when no KV context is active (so retire/terminal of non-last users take the !alone path).
// +COLLIDE: user 1 is started on user 0's frame slot -> the programme must raise the collision fault (fault_code[4]).
module tb_mu_hroot_e2e;
 reg ck=0;always #0.5 ck=~ck;
 reg por_n=0,rst_n=0;
 integer cyc=0;always @(posedge ck)cyc<=cyc+1;
 // ---------------- allocator ----------------
 reg a_req=0;wire a_rdy;reg[17:0]a_tok=0,a_pos=0;reg[1:0]a_gen=0;wire a_gv;reg a_gr=0;
 wire[15:0]g_ep;wire[17:0]g_tok,g_pos;wire[1:0]g_gen;wire[58:0]g_tag;wire a_av,a_ad,a_busy,a_wl,a_idf,a_tacc;
 reg t_v=0;reg[58:0]t_tag=0;reg[1:0]t_gen=0;
 wire drn;
 ot_qwen_tp8_token_epoch_allocator_mu #(.INITIAL_EPOCH(16'h0010),.MU(1)) alloc(
  .clk(ck),.por_n(por_n),.warm_ready(1'b1),.request_valid(a_req),.request_ready(a_rdy),.request_token(a_tok),
  .request_position(a_pos),.request_generation(a_gen),.grant_valid(a_gv),.grant_ready(a_gr),.grant_epoch(g_ep),
  .grant_token(g_tok),.grant_position(g_pos),.grant_generation(g_gen),.grant_tag(g_tag),.allocated_valid(a_av),
  .allocated_delivered(a_ad),.terminal_valid(t_v),.terminal_tag(t_tag),.terminal_generation(t_gen),.terminal_done(1'b1),
  .terminal_fault(1'b0),.terminal_kv_drained(drn),.terminal_vm_drained(drn),.terminal_collective_drained(drn),
  .terminal_host_drained(drn),.wrap_fence_valid(1'b0),.wrap_links_drained(1'b0),.wrap_link_reset_seen(1'b0),
  .wrap_retraining_done(1'b0),.busy(a_busy),.wrap_locked(a_wl),.identity_fault(a_idf),.terminal_accepted(a_tacc));
 // ---------------- endpoint ----------------
 reg[181:0]hc=0;reg sev=0;reg[15:0]sep=0;
 wire rq_v;wire[58:0]rq_tag;wire[31:0]rq_trace;wire[1:0]rq_gen;wire[17:0]rq_tok,rq_pos;reg rq_cr=0;wire[142:0]npr;
 reg rs_v=0;reg[58:0]rs_tag=0;reg[1:0]rs_gen=0;reg[17:0]rs_tok=0;reg[31:0]rs_val=0,rs_cyc=0;wire rs_cr;
 wire owned,crel,pfault;wire[92:0]ltk;
 qkd_host_native_token_endpoint_cancel_mu #(.ENABLE_NATIVE(1),.MU(1)) ep(
  .ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(sev),
  .shared_epoch(sep),.request_v(rq_v),.request_tag(rq_tag),.request_trace(rq_trace),.request_gen(rq_gen),
  .request_token(rq_tok),.request_pos(rq_pos),.request_cr(rq_cr),.native_pr(npr),.result_v(rs_v),.result_tag(rs_tag),
  .result_gen(rs_gen),.result_done(1'b1),.result_fault(1'b0),.result_cause(4'd0),.result_token(rs_tok),
  .result_value(rs_val),.result_cycles(rs_cyc),.result_cr(rs_cr),.kv_drained(drn),.vm_drained(drn),
  .collective_drained(drn),.host_drained(drn),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(1'b0),
  .cancel_release_v(1'b0),.cancel_release_tag(59'd0),.cancel_release_gen(2'd0),.context_owned(owned),
  .cancel_released(crel),.local_tk(ltk),.protocol_fault(pfault));
 // ---------------- KV layer programme ----------------
 reg we=0;reg[8:0]ad=0;reg[63:0]da=0;reg kst=0;reg[15:0]kep=0;reg[17:0]ktok=0,kpos=0;reg[1:0]kgen=0;
 wire cg,kg,vg,ai,ar,ws,ls,ss,sd,qq,cf,kac,kdn,kft;wire[5:0]cs,kstg,klay;wire[15:0]kepo;wire[17:0]ktko,kpso;
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
 // KV row of every writer_start through the MU write-row leaf (row field {row19, bank5, column5}: row at [28:10])
 wire[28:0]xa_o;wire rf;wire[287:0]es_o;
 qkd_kv_mu_wrow #(.MU(1),.NL(1)) wrow(.user(kepo[1:0]),.es_i(288'd0),.xa_i({19'(64+klay),10'd0}),.es_o(es_o),.xa_o(xa_o),.range_fault(rf));
 // ---------------- checks ----------------
 integer ROUNDS=3,r,u,k,kt,ti=0,ntacc=0,uw,uq,ud,urr,fails=0,nws=0,nret=0,nreq=0;
 reg[15:0]ep_of[0:3];reg[17:0]tok_of[0:3];reg[12:0]pos_of[0:3];reg[1:0]gen_of[0:3];
 reg[35:0]layer_seen[0:3];integer wr_of[0:3];reg[5:0]last_layer[0:3];
 reg[1023:0]rowmap;                                  // (user, layer) -> written once per round
 integer done_cyc[0:3],ret_cyc[0:3];reg[1:0]ret_order[0:15];integer ret_n=0;reg[1:0]acc_order[0:15];integer acc_n=0;
 reg[1:0]last_gen_rep=0;reg collide_mode=0;
 task fail(input[1023:0]m);begin fails=fails+1;if(fails<8)$display("ERR cyc %0d %0s",cyc,m);end endtask
 always @(negedge ck)if(rst_n)begin
  if(ws)begin
   nws=nws+1;uw=kepo[1:0];
   if(kepo!==ep_of[uw])fail("writer epoch is not the user's allocated epoch");
   if(xa_o[28:10]!==19'(64+klay+256*uw))fail("KV row != 64+layer+256*user");
   if(rf)fail("row range fault");
   if(layer_seen[uw][klay])fail("layer written twice for a user in one token");
   layer_seen[uw][klay]=1;wr_of[uw]=wr_of[uw]+1;
   if(klay!=0&&klay!=last_layer[uw]+1)fail("user layers out of order");
   last_layer[uw]=klay;
  end
  if(pfault)fail("endpoint protocol_fault");
  if(a_idf)fail("allocator identity_fault");
  if(kft&&!collide_mode)fail("KV programme fault");
 end
 // endpoint request: credit back 2 edges later; check stripped position + epoch user
 always @(posedge ck)if(rq_v)begin
  nreq=nreq+1;uq=rq_tag[44:43];
  if(rq_pos!=={5'd0,pos_of[uq]})begin fail("request position not stripped");end
  if(rq_tag!=={ep_of[uq],6'd0,tok_of[uq],pos_of[uq],6'd0}||rq_gen!==gen_of[uq])fail("request TAG/gen");
  if(acc_order[nreq-1]!==2'(uq))fail("request not in acceptance order");
  fork begin repeat(2)@(negedge ck);rq_cr=1;@(negedge ck);rq_cr=0;end join_none
 end
 // KV done -> endpoint result (1 edge later)
 always @(posedge ck)if(kdn&&!collide_mode)begin
  ud=kepo[1:0];done_cyc[ud]=cyc;
  if(wr_of[ud]!=36)fail("user token without 36 writer stages");
  fork begin @(negedge ck);rs_v=1;rs_tag={ep_of[kepo[1:0]],6'd37,tok_of[kepo[1:0]],pos_of[kepo[1:0]],6'd0};rs_gen=gen_of[kepo[1:0]];
   rs_tok=18'h100+kepo[1:0];rs_val=32'hc0de0000+kepo[1:0];rs_cyc=32'd77;@(negedge ck);rs_v=0;end join_none
 end
 // endpoint retire report (pkgctl MU form): generation change with done && drained
 reg[92:0]ltk_q=0;
 always @(posedge ck)begin
  ltk_q<=ltk;
  if(ltk[92]&&ltk[91:90]!==ltk_q[91:90]&&rst_n)begin
   if(!ltk[89])fail("retire report without drained");
   urr=ltk[81:64]-18'h100;ret_order[ret_n]=2'(urr);ret_n=ret_n+1;nret=nret+1;ret_cyc[urr]=cyc;
   if(ltk[91:90]!==gen_of[urr])fail("retire report generation");
   if(ltk[63:32]!==32'hc0de0000+urr)fail("retire report value of another user");
   if(2'(urr)!==acc_order[ret_n-1])fail("retire not in acceptance order");
   if(cyc-done_cyc[urr]>12)fail("retire late (waited for global drains while other users in flight)");
  end
 end
 // allocator terminal for every retired step, right after its retire report (in retire order)
 initial begin
  forever begin
   @(negedge ck);
   if(ti<ret_n)begin
    t_v=1;t_gen=gen_of[ret_order[ti]];
    t_tag={ep_of[ret_order[ti]],6'd37,tok_of[ret_order[ti]],pos_of[ret_order[ti]],6'd0};
    if(ti%4!=3&&drn)fail("terminal test lost its !alone case (drains already high)");
    kt=0;while(!a_tacc&&kt<100)begin @(negedge ck);kt=kt+1;end
    if(kt>=100)fail("allocator terminal not accepted");
    ntacc=ntacc+1;ti=ti+1;t_v=0;
   end
  end
 end
 task host_step(input integer uu,input integer rr);reg[17:0]p;begin
  p={2'(uu),3'd0,13'(100*rr+17*uu+1)};
  @(negedge ck);a_req=1;a_tok=18'(1000+10*rr+uu);a_pos=p;a_gen=2'(4*rr+uu+1);
  #0.1;k=0;while(!a_rdy&&k<2000)begin @(negedge ck);#0.1;k=k+1;end   // sample after the combinational ready settles
  if(k>=2000)begin fail("allocator never ready for this user");
   $display("  dbg u%0d pos %h ubusy %b gp %b tc %b wl %b idf %b tv %b",uu,a_pos,alloc.g_mu.ubusy,alloc.g_mu.grant_pending,alloc.g_mu.terminal_consumed,a_wl,a_idf,t_v);end
  @(negedge ck);a_req=0;
  k=0;while(!a_gv&&k<50)begin @(negedge ck);k=k+1;end
  if(g_ep!=={14'(16'h0010>>2)+14'(rr),2'(uu)})fail("allocator epoch != {seq14[user], user}");
  ep_of[uu]=g_ep;tok_of[uu]=a_tok;pos_of[uu]=p[12:0];gen_of[uu]=a_gen;
  a_gr=1;@(negedge ck);a_gr=0;
  // host step on hc (user on pos[17:16]) with the shared epoch
  acc_order[acc_n]=2'(uu);acc_n=acc_n+1;
  hc[38]=1;hc[37:36]=a_gen;hc[35:18]=a_tok;hc[17:0]=p;sev=1;sep=ep_of[uu];
  @(negedge ck);hc[38]=0;sev=0;
 end endtask
 task kv_start(input integer uu);begin
  while((cyc%64)!=16*uu)@(posedge ck);
  @(negedge ck);kst=1;kep=ep_of[uu];ktok=tok_of[uu];kpos={5'd0,pos_of[uu]};kgen=gen_of[uu];
  @(negedge ck);kst=0;
 end endtask
 initial begin
  if($test$plusargs("COLLIDE"))collide_mode=1;
  repeat(3)@(negedge ck);por_n=1;rst_n=1;repeat(3)@(negedge ck);
  // boot the KV programme: stage_end 64, roots 3..11 (quiet 11 greatest), GAP 0 except user 3 before stage 5 (+64)
  for(k=0;k<36;k=k+1)begin
   @(negedge ck);we=1;ad=9*k+0;da=3;@(negedge ck);ad=9*k+1;da=4;@(negedge ck);ad=9*k+2;da=5;@(negedge ck);ad=9*k+3;da=6;
   @(negedge ck);ad=9*k+4;da=10;@(negedge ck);ad=9*k+5;da=7;@(negedge ck);ad=9*k+6;da=8;@(negedge ck);ad=9*k+7;da=11;
   @(negedge ck);ad=9*k+8;da=64;
  end
  @(negedge ck);ad=324;da=64'hfeedfacecafebeef;@(negedge ck);ad=325;da=64'h00a5;
  for(k=0;k<144;k=k+1)begin @(negedge ck);ad=326+k;da=(k==3*36+4)?64:0;end
  @(negedge ck);ad=470;da=64'h514b564c59523336;@(negedge ck);we=0;
  repeat(4)@(negedge ck);
  if(!cf||kft)begin $display("FAIL MU_HROOT_E2E KV boot cf=%b fault=%b code=%h",cf,kft,kfc);$finish;end
  for(k=0;k<4;k=k+1)begin wr_of[k]=0;layer_seen[k]=0;last_layer[k]=0;end
  if(collide_mode)begin
   host_step(0,0);host_step(1,0);
   kv_start(0);repeat(63)@(negedge ck);@(negedge ck);kst=1;kep=ep_of[1];ktok=tok_of[1];kpos={5'd0,pos_of[1]};kgen=gen_of[1];
   @(negedge ck);kst=0;repeat(200)@(negedge ck);
   if(kft&&kfc[4])$display("PASS MU_HROOT_COLLIDE: user 1 on user 0's frame slot -> KV programme collision fault code %h",kfc);
   else $display("FAIL MU_HROOT_COLLIDE: no collision fault (fault=%b code=%h)",kft,kfc);
   $finish;
  end
  for(r=0;r<ROUNDS;r=r+1)begin
   for(k=0;k<4;k=k+1)begin wr_of[k]=0;layer_seen[k]=0;end
   for(u=0;u<4;u=u+1)host_step(u,r);
   repeat(3)@(negedge ck);   // the last hc start reaches the endpoint context 2 edges later (input + accept registers)
   if(!(owned&&a_busy&&ep.g_mu.n_q==4&&alloc.g_mu.ubusy==4'hf))fail("4 steps not all in flight (ep/alloc)");
   for(u=0;u<4;u=u+1)kv_start(u);
   // wait for the 4 retires of this round, then the 4 allocator terminals in the same order
   k=0;while(ret_n<4*(r+1)&&k<20000)begin @(negedge ck);k=k+1;end
   if(k>=20000)fail("round did not retire 4 steps");
   k=0;while(ntacc<4*(r+1)&&k<2000)begin @(negedge ck);k=k+1;end
   if(k>=2000)fail("allocator terminals not all accepted");
   for(u=0;u<4;u=u+1)if(wr_of[u]!=36)fail("user missing writer stages");
   if(a_busy||owned)fail("allocations/contexts left after the round");
  end
  repeat(20)@(negedge ck);
  if(fails==0&&nret==4*ROUNDS&&nreq==4*ROUNDS&&nws==36*4*ROUNDS)
   $display("PASS MU_HROOT_E2E rounds=%0d steps=%0d writer_stages=%0d rows=64+l+256u epochs={seq14,user2} retire=acceptance order",ROUNDS,nret,nws);
  else $display("FAIL MU_HROOT_E2E fails=%0d retires=%0d requests=%0d writer_stages=%0d",fails,nret,nreq,nws);
  $finish;
 end
 initial begin #2000000;$display("FAIL MU_HROOT_E2E timeout retires=%0d fails=%0d",nret,fails);$finish;end
endmodule
