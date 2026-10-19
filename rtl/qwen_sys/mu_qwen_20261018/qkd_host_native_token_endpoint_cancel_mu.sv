`timescale 1ns/1ps
// MU-ADOPT-HROOT 10-19 (Qwen ROM 4 users, RELEASE_TREE K.STA.MU): drop-in successor of
// qkd_host_native_token_endpoint_cancel (host-root guard core, u_rank__u_native) with the SAME ports.
//   MU 0: instantiates the unchanged original (behaviour-identical by construction; original file untouched).
//   MU 1: four step contexts, one per user.  The host (ot_qfd_pkgctl MU + qkd_host_ctl MU) puts the step's user on
//         hc pos[17:16]; this endpoint strips it (positions < 8192 per user: hc pos[15:13] must be 0) and binds the
//         step to the shared epoch whose low 2 bits are that user (allocator convention epoch = {seq14, user2},
//         ot_qwen_tp8_token_epoch_allocator_mu).  A start for a user whose context is still owned, a wrong epoch user,
//         or pos[15:13] != 0 is a sticky protocol_fault (fail closed, as the original; never a stall).
//   Static order: requests issue in acceptance order (one request credit, as the original); results are matched to
//         their context by the result TAG's epoch user (rtag[44:43]) with the full TAG59 + generation; steps RETIRE in
//         acceptance order (the head), one per edge.  The retire report on local_tk (TK93) is the pkgctl MU form:
//         [92] done (sticky after the first retire), [91:90] = generation of the LAST retired step (pkgctl counts a
//         die report when the generation changes with done && drained), [89] = drained.
//   Drains: the four die drain flags are global.  With one step owned (a single user) retire waits for all four
//         drains exactly as the original.  With other users' steps in flight the die is never globally drained, so
//         the step's terminal result -- emitted by the static calendar after that step's last scheduled KV/VM/collective
//         work -- retires it without the global drains (OWNER/die-lane audit point, lanes/MU-QWEN-ADOPT.md ## HROOT).
//         Recovery clear, a cancel release of a LIVE step and the allocator wrap fence still require the true global
//         drains.  MU-KV-PEER 10-19: the terminal barrier release (class5) of an already-RETIRED step follows the
//         retire rule (drains, or other users' contexts still owned), and a pending release blocks only the request
//         issue of its own user (with one global drain per release, 4 pipelined users would drain the die every step).
// TAG59 = {epoch16, stage6, token18, position13, segment6}; terminal stage 37 / segment 0 (unchanged).
module qkd_host_native_token_endpoint_cancel_mu #(parameter integer ENABLE_NATIVE=0,MUT=0,MU=1)(
 input wire ck,por_n,rst_n,input wire[181:0]hc,input wire[92:0]legacy_tk,
 input wire image_ready,input wire shared_epoch_valid,input wire[15:0]shared_epoch,
 output reg request_v,output reg[58:0]request_tag,output reg[31:0]request_trace,output reg[1:0]request_gen,
 output reg[17:0]request_token,request_pos,input wire request_cr,
 output reg[142:0]native_pr,
 input wire result_v,input wire[58:0]result_tag,input wire[1:0]result_gen,
 input wire result_done,result_fault,input wire[3:0]result_cause,
 input wire[17:0]result_token,input wire[31:0]result_value,result_cycles,
 output reg result_cr,
 input wire kv_drained,vm_drained,collective_drained,host_drained,collective_busy,kv_flush,
 input wire recovery_clear,input wire cancel_release_v,input wire[58:0]cancel_release_tag,input wire[1:0]cancel_release_gen,
 output wire context_owned,output reg cancel_released,output reg[92:0]local_tk,output reg protocol_fault
);
generate if(MU==0)begin:g_plain
 wire w_request_v,w_result_cr,w_cancel_released,w_protocol_fault;wire[58:0]w_request_tag;wire[31:0]w_request_trace;
 wire[1:0]w_request_gen;wire[17:0]w_request_token,w_request_pos;wire[142:0]w_native_pr;wire[92:0]w_local_tk;
 qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(ENABLE_NATIVE),.MUT(MUT))u_plain(
  .ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(legacy_tk),.image_ready(image_ready),
  .shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(w_request_v),.request_tag(w_request_tag),.request_trace(w_request_trace),.request_gen(w_request_gen),
  .request_token(w_request_token),.request_pos(w_request_pos),.request_cr(request_cr),.native_pr(w_native_pr),
  .result_v(result_v),.result_tag(result_tag),.result_gen(result_gen),.result_done(result_done),.result_fault(result_fault),
  .result_cause(result_cause),.result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),
  .result_cr(w_result_cr),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),
  .host_drained(host_drained),.collective_busy(collective_busy),.kv_flush(kv_flush),.recovery_clear(recovery_clear),
  .cancel_release_v(cancel_release_v),.cancel_release_tag(cancel_release_tag),.cancel_release_gen(cancel_release_gen),
  .context_owned(context_owned),.cancel_released(w_cancel_released),.local_tk(w_local_tk),.protocol_fault(w_protocol_fault));
 always @*begin
  request_v=w_request_v;request_tag=w_request_tag;request_trace=w_request_trace;request_gen=w_request_gen;
  request_token=w_request_token;request_pos=w_request_pos;native_pr=w_native_pr;result_cr=w_result_cr;
  cancel_released=w_cancel_released;local_tk=w_local_tk;protocol_fault=w_protocol_fault;
 end
end else begin:g_mu
 reg[181:0]hc_q;reg[92:0]legacy_q;reg image_ready_q;
 reg cr_q,rv,rdone,rfault,kq,cq,cbq,kfq,vq,hq,epoch_valid_q;reg[15:0]epoch_q;reg[58:0]rtag;
 reg[31:0]rvv,rcy;reg[1:0]rg;reg[3:0]rcause;reg[17:0]rt;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
  image_ready_q<=0;hc_q<=0;legacy_q<=0;cr_q<=0;rv<=0;rdone<=0;rfault<=0;kq<=0;cq<=0;cbq<=0;kfq<=0;vq<=0;hq<=0;
  epoch_valid_q<=0;epoch_q<=0;rtag<=0;rvv<=0;rcy<=0;rg<=0;rcause<=0;rt<=0;
 end else begin
  image_ready_q<=image_ready;hc_q<=hc;legacy_q<=legacy_tk;cr_q<=request_cr;
  epoch_valid_q<=shared_epoch_valid;epoch_q<=shared_epoch;
  rv<=result_v;rtag<=result_tag;rg<=result_gen;rdone<=result_done;rfault<=result_fault;
  rcause<=result_cause;rt<=result_token;rvv<=result_value;rcy<=result_cycles;
  kq<=kv_drained;vq<=vm_drained;hq<=host_drained;cq<=collective_drained;cbq<=collective_busy;kfq<=kv_flush;
 end
 // per-user contexts
 reg[3:0]c_act,c_pend,c_iss,c_seen,c_done;
 reg[15:0]c_epoch[0:3];reg[31:0]c_trace[0:3];reg[17:0]c_next[0:3];reg[31:0]c_val[0:3],c_cyc[0:3];reg[1:0]c_gen[0:3];reg[17:0]c_tok[0:3];reg[12:0]c_pos[0:3];
 // acceptance-order queue of users: issue pointer ip, retire pointer rp, write pointer wp (2-bit slots, count 0..4)
 reg[1:0]q_u[0:3];reg[1:0]wp,ip,rp;reg[2:0]n_q,n_i;     // n_q owned entries, n_i entries not yet issued/skipped
 reg credit,fault_q,skip_drained;reg[3:0]cause_q;reg[31:0]trace_counter;
 reg released_valid;reg[58:0]released_tag;reg[1:0]released_gen;
 reg release_pending;reg[58:0]release_tag;reg[1:0]release_gen;
 wire drains=kq&&vq&&cq&&hq;
 wire[1:0]u_in=hc_q[17:16];
 function automatic [58:0]term(input[15:0]e,input[17:0]t,input[12:0]p);term={e,6'd37,t,p,6'd0};endfunction
 wire[58:0]in_term=term(epoch_q,hc_q[35:18],hc_q[12:0]);
 wire previously_retired=released_valid&&released_tag==in_term&&released_gen==hc_q[37:36];
 assign context_owned=|c_act;
 wire start=ENABLE_NATIVE&&hc_q[38]&&!protocol_fault&&!fault_q;
 wire accept=start&&(image_ready_q||MUT==5)&&(MUT==6||!previously_retired)&&!c_act[u_in]&&epoch_valid_q&&
             hc_q[15:13]==0&&epoch_q[1:0]==u_in;
 // issue: the oldest not-yet-issued owned step (acceptance order)
 wire[1:0]ui=q_u[ip];
 wire skip_i=n_i!=0&&!c_pend[ui];                       // a released step that never issued
 // results: context by the epoch user of the result TAG
 wire[1:0]ur=rtag[44:43];
 wire[58:0]r_term=term(c_epoch[ur],c_tok[ur],c_pos[ur]);
 wire result_ok=rv&&c_act[ur]&&c_iss[ur]&&!c_seen[ur]&&(MUT==2||(rtag==r_term&&rg==c_gen[ur]));
 // retire: the head of the acceptance queue only
 wire[1:0]uh=q_u[rp];
 wire head_iss=n_q!=n_i;                                // head already issued (or skipped)
 wire alone=n_q==1;
 wire retire=n_q!=0&&head_iss&&c_act[uh]&&c_seen[uh]&&c_done[uh]&&(MUT==1||drains||!alone)&&!protocol_fault;
 wire pop_dead=n_q!=0&&head_iss&&!c_act[uh];            // a released step leaves the queue head without a report
 // cancel release (exceptional): the context named by the release TAG's epoch user
 wire[1:0]uc=release_tag[44:43];
 wire release_matches=release_tag==term(c_epoch[uc],c_tok[uc],c_pos[uc])&&release_gen==c_gen[uc];
 wire release_fire=release_pending&&c_act[uc]&&release_matches&&(MUT==4||drains)&&credit;
 wire[1:0]ucv=cancel_release_tag[44:43];
 wire issue=ENABLE_NATIVE&&n_i!=0&&c_pend[ui]&&(credit||MUT==3)&&!protocol_fault&&!fault_q&&!(release_pending&&uc==ui)&&!(cancel_release_v&&ucv==ui);
 always @(posedge ck or negedge por_n)if(!por_n)trace_counter<=0;
 else if(rst_n&&accept)trace_counter<=trace_counter+1'b1;
 integer k;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
  c_act<=0;c_pend<=0;c_iss<=0;c_seen<=0;c_done<=0;
  for(k=0;k<4;k=k+1)begin c_next[k]<=0;c_val[k]<=0;c_cyc[k]<=0;c_epoch[k]<=0;c_trace[k]<=0;c_gen[k]<=0;c_tok[k]<=0;c_pos[k]<=0;q_u[k]<=0;end
  wp<=0;ip<=0;rp<=0;n_q<=0;n_i<=0;credit<=1;fault_q<=0;skip_drained<=0;cause_q<=0;
  request_v<=0;request_tag<=0;request_trace<=0;request_gen<=0;request_token<=0;request_pos<=0;
  native_pr<=0;result_cr<=0;local_tk<=0;protocol_fault<=0;released_valid<=0;released_tag<=0;released_gen<=0;
  release_pending<=0;release_tag<=0;release_gen<=0;cancel_released<=0;
 end else begin
  native_pr<=hc_q[181:39];request_v<=0;result_cr<=0;cancel_released<=0;
  if(recovery_clear)begin
   if((|c_act)||release_pending||!credit||!drains)protocol_fault<=1;
   else begin released_valid<=0;protocol_fault<=0;fault_q<=0;c_seen<=0;c_done<=0;cause_q<=0;end
  end
  if(cancel_release_v)begin
   if(release_pending||(c_act[ucv]&&(cancel_release_tag!=term(c_epoch[ucv],c_tok[ucv],c_pos[ucv])||cancel_release_gen!=c_gen[ucv])))protocol_fault<=1;
   else begin release_pending<=1;release_tag<=cancel_release_tag;release_gen<=cancel_release_gen;end
  end
  if(!ENABLE_NATIVE)local_tk<=legacy_q;
  else begin
   // live status fields (as the original); [92:89] change only at a retire (pkgctl MU report)
   local_tk[88]<=fault_q||protocol_fault;local_tk[87:84]<=protocol_fault?4'hf:cause_q;local_tk[83]<=cbq;local_tk[82]<=kfq;
   local_tk[89]<=drains||skip_drained;
   if(start&&!accept)protocol_fault<=1;
   if(accept)begin
    c_act[u_in]<=1;c_pend[u_in]<=1;c_iss[u_in]<=0;c_seen[u_in]<=0;c_done[u_in]<=0;
    c_epoch[u_in]<=epoch_q;c_trace[u_in]<=trace_counter+1'b1;c_gen[u_in]<=hc_q[37:36];c_tok[u_in]<=hc_q[35:18];
    c_pos[u_in]<=hc_q[12:0];q_u[wp]<=u_in;wp<=wp+1'b1;
   end
   if(cr_q&&credit&&!issue)protocol_fault<=1;
   else credit<=credit+1'(cr_q)-1'(issue);
   if(issue)begin
    request_v<=1;request_tag<={c_epoch[ui],6'd0,c_tok[ui],c_pos[ui],6'd0};request_trace<=c_trace[ui];request_gen<=c_gen[ui];
    request_token<=c_tok[ui];request_pos<={5'd0,c_pos[ui]};c_pend[ui]<=0;c_iss[ui]<=1;
   end
   if(issue||skip_i)ip<=ip+1'b1;
   if(rv)begin
    if(!result_ok||(!rdone&&!rfault))protocol_fault<=1;
    else begin
     if(rfault)begin fault_q<=1;cause_q<=rcause;end
     if(rdone)begin c_seen[ur]<=1;c_done[ur]<=1;c_next[ur]<=rt;c_val[ur]<=rvv;c_cyc[ur]<=rcy;end
     else result_cr<=1; // nonterminal genuine fault alert occupies no result slot
    end
   end
   if(retire)begin
    c_act[uh]<=0;result_cr<=1;
    local_tk[92]<=1;local_tk[91:90]<=c_gen[uh];local_tk[89]<=1;skip_drained<=!drains;
    local_tk[81:64]<=c_next[uh];local_tk[63:32]<=c_val[uh];local_tk[31:0]<=c_cyc[uh];
   end
   if(retire||pop_dead)rp<=rp+1'b1;
   if(release_fire)begin
    c_act[uc]<=0;c_pend[uc]<=0;c_iss[uc]<=0;release_pending<=0;cancel_released<=1;released_valid<=1;
    released_tag<=release_tag;released_gen<=release_gen;
    if(c_seen[uc]&&c_done[uc]&&!(retire&&uh==uc))result_cr<=1;
   end
   if(release_pending&&!c_act[uc]&&credit&&(drains||(|c_act))&&!start&&!hc_q[38]&&!hc[38]&&!request_v)begin
    release_pending<=0;cancel_released<=1;released_valid<=1;released_tag<=release_tag;released_gen<=release_gen;
   end
  end
  // queue occupancy
  n_q<=n_q+3'(accept&&ENABLE_NATIVE)-3'((retire||pop_dead)&&ENABLE_NATIVE);
  n_i<=n_i+3'(accept&&ENABLE_NATIVE)-3'((issue||skip_i)&&ENABLE_NATIVE);
 end
end endgenerate
endmodule
