`timescale 1ns/1ps
// Actual CEXT2 ctl + RPS1/SPLIT1 children, all25 logical child clocks coherent.
module xcache_actual_tile #(parameter integer XLOCAL=0)(
 input wire cc,input wire rst_n,input wire [15:0] tid,input wire go,
 input wire [378:0] ib,input wire [127:0] xl,output wire [3:0] xr,
 output wire [95:0] xa,output wire [20:0] epoch,output wire [511:0] tout,
 output wire tv,output wire fault
);
 wire [69:0] req;wire [2047:0] rqr;wire [3127:0] ld;wire [583:0] lq;
 wire [71:0] le;wire vd,nf;wire [129:0] rm;reg [2659:0] rd=0;
 genvar i;generate for(i=0;i<8;i=i+1) begin assign le[9*i+:9]=lq[73*i+64+:9];end endgenerate
`ifdef XCACHE_TP8
 generate if(XLOCAL==0) begin:choice_ref
 ot_qwen_tile_ctl_tp8_ref ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end else begin:choice
 ot_qwen_tile_ctl_tp8 ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end endgenerate
`else
 ot_qwen_tile_ctl #(.XLOCAL(XLOCAL)) ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
`endif
 ot_qwen_tile_kids #(.CODE_BANKS(5),.RPS(0),.MCLK(1),.SPLIT(1)) kids(.clk(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),.rst_n(rst_n),.cx_rreq(req),.cx_rq(),.cx_rqr(rqr),.cx_ld(ld),.cx_lq(lq),.cx_td(512'd0),.cx_tvd(vd),.cx_nfault(nf),.n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(tout),.t_vout(tv),.rom_req_m(rm),.rom_rd(rd));
 integer p,l;always @(posedge cc) for(p=0;p<10;p=p+1) if(rm[13*p+12]) begin
  rd[266*p+:266]<=0;
  for(l=0;l<32;l=l+1) rd[266*p+8*l+:8]<=8'(rm[13*p+:12]+32*(p/5)+l+3*tid+1);
 end
endmodule
module tb_qwen_numeric_merged_boundary;
 parameter integer MUT=0,ALL_SPLITS=0,QUEUE_DEPTH=8,FULL_STALLS=0,BOUNDARY_BYPASS=0;
`ifdef XCACHE_TP8
 localparam integer TARGET_GT=3072;
 `define REF_ME ref_tile.choice_ref.ctl.u_logic.u_me
`else
 localparam integer TARGET_GT=6144;
 `define REF_ME ref_tile.ctl.u_logic.u_me
`endif
 reg [378:0] native_ib[0:3];
 reg incoming=0,expected_mode=0;reg [15:0] current_ctx=0,expected_ctx=0,offered_ctx=0;reg [31:0] expected_ver=0;wire read_mode;wire [15:0] read_ctx;wire [31:0] read_ver;wire op_accept,core_idle;wire [15:0] accepted_ctx;wire [31:0] accepted_ver;wire [378:0] accepted_ib;reg [378:0] expected_accepted_ib=0;reg accepted_valid=0;integer accepts=0,metadata_checks=0,descriptor_checks=0;reg [95:0] load_key=0;reg [15:0] load_ctx=0;reg [31:0] load_ver=0;integer mode_checks=0,resident_checks=0;
 reg clk=0;always #5 clk=~clk;
 wire [88:0] numeric_tuple;wire [47:0] numeric_identity=numeric_tuple[87:40];wire numeric_has_query=numeric_tuple[88];wire [39:0] numeric_query_seq=numeric_tuple[39:0];wire query_output_toggle=0;wire [87:0] query_output_tuple={numeric_identity,numeric_query_seq};wire query_output_ack=0;reg old_query_output=0;reg [88:0] output_oracle[0:45];integer consumed_outputs=0,typed_consumed=0,held_output_bases=0;
 wire output_queue_credit,output_queue_v,output_queue_has_query,output_queue_fault;wire [511:0] output_queue_word;wire [87:0] output_queue_tag;reg sink_ready=1,actual_produced_step=0;integer posted_outputs=0,expected_head=0,expected_tail=0;reg [511:0] expected_words[0:2047];reg expected_types[0:2047];reg [87:0] expected_tags[0:2047];
 ot_qwen_numeric_stream_queue #(.ENABLE(1),.DEPTH(QUEUE_DEPTH)) output_queue(.base_clk(clk),.rst_n(rst_n),.core_output_step(gate),.numeric_v(cv),.numeric_word(ct),.numeric_identity(numeric_identity),.numeric_has_query(numeric_has_query),.numeric_query_seq(numeric_query_seq),.core_credit(output_queue_credit),.consume_ready(actual_sink_ready),.consume_v(output_queue_v),.consume_word(output_queue_word),.consume_has_query(output_queue_has_query),.consume_query_tuple(output_queue_tag),.fault(output_queue_fault));
 wire query_issue_v;wire issue_last;wire [3:0] drain_toggle;wire [191:0] drain_tuple;reg [3:0] drain_ack=0,old_drain=0;integer issue_edge=0,final_output_edge=0,drain_events=0,outstanding=0,peak_outstanding=0;reg [47:0] last_identity;
 reg [39:0] load_seq=40'h8abcdef123;wire load_ready,read_credit,fill_toggle,response_toggle;wire [246:0] fill_tuple,response_tuple;reg fill_ack=0,response_ack=0;integer fill_events=0,response_events=0;reg [246:0] expected_fill,expected_response;reg expected_fill_v,expected_response_v,old_fill=0,old_response=0;
 wire [39:0] query_seq;wire query_toggle,query_credit,query_fault,accept_toggle,admission_fault;reg query_ack=0,accept_ack=0;integer query_callbacks=0,base_edges=0,query_held=0;reg [39:0] next_query=0;reg last_query_toggle=0;
 always @(negedge clk)begin
 sink_ready<=!(next_offer&&base_edges<offer_base+40)&&(base_edges%17!=5&&base_edges%17!=6&&base_edges%17!=7);
 allow<=base_edges%19!=7&&base_edges%19!=8;
 end
 always @(posedge clk)begin
  base_edges=base_edges+1;
  if(!rst_n)begin query_ack<=0;accept_ack<=0;fill_ack<=0;response_ack<=0;drain_ack<=0;actual_produced_step<=0;end
  else begin
   actual_produced_step<=gate;
   accept_ack<=accept_toggle;fill_ack<=fill_toggle;drain_ack<=drain_toggle;
   if(base_edges%13!=2&&base_edges%13!=3)response_ack<=response_toggle;
   if(query_toggle!=query_ack)begin query_held=query_held+1;if(ledger_issue_ready[recipient_index])begin query_callbacks=query_callbacks+1;query_ack<=query_toggle;end end
   if(output_queue_v&&actual_sink_ready)begin
    if(expected_head==expected_tail||output_queue_word!==expected_words[expected_head])$fatal(1,"actual posted numeric word mismatch");
    if(output_queue_has_query!==expected_types[expected_head]||output_queue_tag!==expected_tags[expected_head])$fatal(1,"actual posted output mask/tag mismatch");
    consumed_outputs=consumed_outputs+1;if(output_queue_has_query)typed_consumed=typed_consumed+1;expected_head=expected_head+1;
   end
   if(actual_produced_step&&rv)begin
    expected_words[expected_tail]=rt;expected_types[expected_tail]=output_oracle[45][88];expected_tags[expected_tail]=output_oracle[45][88]?output_oracle[45][87:0]:{output_oracle[45][87:40],40'd0};expected_tail=expected_tail+1;posted_outputs=posted_outputs+1;if(next_offer&&!local_granted&&output_oracle[45][87:72]==1)held_offer_old_posts=held_offer_old_posts+1;
   end
   if(query_output_toggle!=query_output_ack)held_output_bases=held_output_bases+1;
  end
  #1;if(rst_n&&output_queue_fault)$fatal(1,"actual numeric output queue reservation/event fault");
 end
 reg bank_reset=0;reg [1:0] begin_bank=0;reg selected_bank=0;
 integer issued_total=0,retired_total=0,ledger_peak=0,queue_peak=0;
 wire [5:0] recipient_index=tid%48;
 wire [47:0] bank_issue_ready[0:1],bank_retire_ready[0:1];wire [1:0] bank_fault,bank_drained,bank_active;
 wire [335:0] bank_outstanding[0:1];
 wire [47:0] ledger_issue_ready=bank_issue_ready[selected_bank],ledger_retire_ready=bank_retire_ready[selected_bank];
 wire [47:0] ledger_issue_v=(48'd1<<recipient_index)&{48{query_toggle!=query_ack}};
 wire [47:0] ledger_retire_v=(48'd1<<recipient_index)&{48{output_queue_v&&sink_ready&&output_queue_has_query}};
 wire actual_sink_ready=sink_ready&&(!output_queue_has_query||ledger_retire_ready[recipient_index]);
 wire [1919:0] issue_sequences,retire_sequences;wire [767:0] issue_contexts,retire_contexts;wire [1535:0] issue_versions,retire_versions;
 wire [335:0] outstanding_observed=bank_outstanding[selected_bank];
 for(genvar li=0;li<48;li=li+1)begin:ledger_tuple
  assign issue_sequences[40*li+:40]=query_seq;assign issue_contexts[16*li+:16]=read_ctx;assign issue_versions[32*li+:32]=read_ver;
  assign retire_sequences[40*li+:40]=output_queue_tag[39:0];assign retire_contexts[16*li+:16]=output_queue_tag[87:72];assign retire_versions[32*li+:32]=output_queue_tag[71:40];
 end
 for(genvar bi=0;bi<2;bi=bi+1)begin:banks
  ot_qwen_xdelivery_ack_vector #(.ENABLE(1),.N(48),.SEQ_W(40),.COUNT_W(7)) ledger(
   .clk(clk),.rst_n(rst_n&&bank_reset),.begin_v(begin_bank[bi]),.fenced_clear(1'b0),.begin_context(16'(bi+1)),.begin_version(32'(32'hC1230001+bi)),.participant_mask({48{1'b1}}),
   .issue_v(ledger_issue_v&{48{selected_bank==bi}}),.issue_ready(bank_issue_ready[bi]),.issue_seq(issue_sequences),.issue_context(issue_contexts),.issue_version(issue_versions),
   .retire_v(ledger_retire_v&{48{selected_bank==bi}}),.retire_ready(bank_retire_ready[bi]),.retire_seq(retire_sequences),.retire_context(retire_contexts),.retire_version(retire_versions),
   .seal_v(48'd0),.seal_context(768'd0),.seal_version(1536'd0),.drained(bank_drained[bi]),.fault(bank_fault[bi]));
  assign bank_active[bi]=ledger.active;
  for(genvar oi=0;oi<48;oi=oi+1)assign bank_outstanding[bi][7*oi+:7]=ledger.recipient[oi].outstanding;
 end
 always @(posedge clk)begin
  if(rst_n&&bank_reset)begin
   if((|begin_bank)&&(|ledger_issue_v||(|ledger_retire_v))||(|ledger_issue_v)&&!bank_active[selected_bank])$fatal(1,"boundary BEGIN precedes all actual events");
   if(ledger_issue_v[recipient_index]&&ledger_issue_ready[recipient_index])issued_total=issued_total+1;
   if(ledger_retire_v[recipient_index]&&ledger_retire_ready[recipient_index])retired_total=retired_total+1;
   #1;if(|bank_fault)begin
    if(BOUNDARY_BYPASS&&early_accept_old_live==0)$fatal(1,"boundary negative lacked actual old outstanding acceptance");
    $fatal(1,"boundary actual new query mismatched old active ledger");
   end
   if(outstanding_observed[7*recipient_index+:7]>ledger_peak)ledger_peak=outstanding_observed[7*recipient_index+:7];
   if(output_queue.count>queue_peak)queue_peak=output_queue.count;
   if(|bank_drained)$fatal(1,"boundary fabricated peer seals");
  end
 end
 reg allow=1,gate=1;wire hit;always @(negedge clk) gate<=allow&&hit&&query_credit&&read_credit&&output_queue_credit;
 wire cc=clk&&gate;
 reg rst_n=0,clear=0,lv=0,j_repeat=1;
 reg offer_go=0,next_offer=0,local_granted=0,old_drain_seen=0; reg [378:0] held_next_ib;
 integer offer_base=0,held_offer_old_posts=0,early_accept_old_live=0,second_accept_base=0;
 wire go=offer_go&&(!next_offer||local_granted||BOUNDARY_BYPASS);
 wire local_candidate=old_drain_seen&&!output_queue_v&&!output_queue.pending_post&&!cv&&bank_outstanding[0][7*recipient_index+:7]==0&&query_credit&&read_credit;

 reg [15:0] tid=0;reg [378:0] ib=0;reg [20:0] load_epoch=0;
 reg [127:0] lx=0;wire [127:0] cache_x;reg [127:0] stale_x=0;always @(posedge cc) stale_x<=cache_x;
 wire [3:0] cr,unused_r;wire [95:0] ca,unused_a;wire [20:0] ep,unused_e;
 wire [511:0] rt,ct;wire rv,cv,rf,cf,cachefault;
 reg [95:0] oracle_addr=0;reg [3:0] oracle_req=0;reg [20:0] oracle_epoch=0;
 reg [127:0] held_ref=0;reg [127:0] raw_ref;
 function automatic [31:0] xv(input [23:0] a);
  xv=32'h3f800000 | (((a*24'd7919)^24'h123456)&23'h7fffff);
 endfunction
 integer l;always @* begin
  raw_ref=held_ref;
  if(|oracle_req) for(integer z=0;z<4;z=z+1) raw_ref[32*z+:32]=xv(oracle_addr[24*z+:24]);
 end
 xcache_actual_tile #(.XLOCAL(0)) ref_tile(cc,rst_n,tid,go,ib,raw_ref,unused_r,unused_a,unused_e,rt,rv,rf);
 ot_qwen_tile_tp8_numeric_stream_merged dut_cached(
 .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx_group(cc),.clk_rqr({2{cc}}),
 .clk_cache_response(cc),.clk_cache_load(clk),.clk_local_drain(cc),.clk_node_lifetime(cc),
 .numeric_tuple(numeric_tuple),
 .drain_ack_toggle(drain_ack),.drain_toggle(drain_toggle),.drain_tuple(drain_tuple),
 .node_context(16'd0),.node_version(32'd0),.node_sequence(40'd0),.producer_seal_v(1'b0),.producer_seal_context(16'd0),.producer_seal_version(32'd0),
 .node_clear_context(1'b0),.node_retire_ack_toggle(1'b0),.node_accept_ack_toggle(1'b0),.node_credit(),.node_accept_credit(),.node_produced_toggle(),.node_accept_toggle(),.node_drained(),.node_produced_tuple(),.node_accept_tuple(),.node_output_tuple(),.node_output_valid(),.node_active_identity(),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),
 .op_context(offered_ctx),.vm_version(32'(32'hC1230000+offered_ctx)),.cache_clear(clear),.load_v(lv),.load_j_repeat(xjs==0),
 .load_epoch(load_epoch),.load_addr(load_key),.load_context(load_ctx),.load_version(load_ver),.load_x(lx),
 .load_token(load_ctx^load_epoch[18:3]),.load_root(load_epoch[7:3]),.load_phase(load_epoch[6:3]),.load_recipient(tid),.load_query_seq(load_seq),
 .fill_ack_toggle(fill_ack),.response_ack_toggle(response_ack),.load_ready(load_ready),.read_credit(read_credit),.cache_hit(hit),
 .fill_toggle(fill_toggle),.response_toggle(response_toggle),.fill_tuple(fill_tuple),.response_tuple(response_tuple),
 .cx_xre(cr),.cx_xaddr(ca),.cx_xepoch(ep),.cx_xjrepeat(read_mode),.cx_xcontext(read_ctx),.cx_xversion(read_ver),
 .query_ack_toggle(query_ack),.cx_query_seq(query_seq),.cx_query_toggle(query_toggle),.cx_query_credit(query_credit),.cx_query_fault(query_fault),.cx_query_issue_v(query_issue_v),
 .accept_ack_toggle(accept_ack),.accept_transport_fence(1'b0),.cx_accept_toggle(accept_toggle),.cx_admission_fault(admission_fault),
 .cx_op_accept(op_accept),.cx_issue_last(issue_last),.cx_accepted_context(accepted_ctx),.cx_accepted_version(accepted_ver),.cx_accepted_ib(accepted_ib),.cx_core_idle(core_idle),
 .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(ct),.t_vout(cv),.fault(cf));
 assign cachefault=0;
 // Accepted fill and response-produced events retain full provenance until ACK.
 always @(posedge clk)begin
  expected_fill_v=rst_n&&!clear&&lv&&load_ready;
  expected_fill={load_ctx,load_ver,(xjs==0),load_epoch,load_key,(load_ctx^load_epoch[18:3]),load_epoch[7:3],load_epoch[6:3],tid,load_seq};
  #1;if(rst_n)begin
   if(expected_fill_v)begin fill_events=fill_events+1;if(fill_toggle===old_fill||fill_tuple!==expected_fill)$fatal(1,"actual event fill provenance mismatch");end
   else if(fill_toggle!==old_fill)$fatal(1,"fill event without accepted load");
   old_fill=fill_toggle;
  end else old_fill=0;
 end
 always @(posedge cc)begin
  expected_response_v=rst_n&&(|cr)&&hit&&read_credit;
  expected_response={read_ctx,read_ver,read_mode,ep,ca,(read_ctx^ep[18:3]),ep[7:3],ep[6:3],tid,query_seq};
  #1;if(rst_n)begin
   if(expected_response_v)begin response_events=response_events+1;if(response_toggle===old_response||response_tuple!==expected_response)$fatal(1,"actual event current-query response provenance mismatch");end
   else if(response_toggle!==old_response)$fatal(1,"response event without capture");
   old_response=response_toggle;
  end else old_response=0;
 end

 // Independent generated query mask/context/sequence through46 coherent edges.
 always @(posedge cc)begin
  if(!rst_n)begin for(integer oi=0;oi<46;oi=oi+1)output_oracle[oi]<=0;end
  else begin
   output_oracle[0]<={|oracle_req,expected_ctx,expected_ver,(next_query-40'd1)};
   for(integer oi=1;oi<46;oi=oi+1)output_oracle[oi]<=output_oracle[oi-1];
  end
  #1;if(!rst_n)old_query_output=0;else begin
   if(rv&&numeric_identity!==output_oracle[45][87:40])$fatal(1,"actual every-math numeric context mismatch");
   if(rv&&(numeric_has_query!==output_oracle[45][88] || numeric_has_query&&numeric_query_seq!==output_oracle[45][39:0]))$fatal(1,"actual streaming mask/query sequence mismatch");
   old_query_output=query_output_toggle;
  end
 end
 integer checks=0,requests=0,misses=0,edges=0,ops=0;
 always @(posedge cc) begin
  edges=edges+1;
  if(!rst_n) begin accepted_valid<=0;oracle_req<=0;next_query=0;last_query_toggle=0;expected_mode<=0;expected_ctx<=0;expected_ver<=0;end
  else begin
   if(`REF_ME.go && `REF_ME.ready)begin
    expected_accepted_ib<=ref_tile.choice_ref.ctl.u_logic.ib_i;accepted_valid<=1;
   end
   // Capture pre-update request mode/context on the same actual address edge.
   expected_mode<=(`REF_ME.xjs_r==0);expected_ctx<=current_ctx;expected_ver<=32'(32'hC1230000+current_ctx);
   // Independent production reference state, not candidate request reuse.
   for(l=0;l<4;l=l+1) begin
    oracle_req[l]<=`REF_ME.active && (((`REF_ME.gb+l)>>`REF_ME.split_r)<(TARGET_GT>>`REF_ME.split_r));
    oracle_addr[24*l+:24]<=`REF_ME.xc+((`REF_ME.gb+l)&((1<<`REF_ME.split_r)-1))*`REF_ME.xcs_r;
   end
   oracle_epoch<={`REF_ME.k,`REF_ME.j};
  end
  if(|oracle_req) held_ref<=raw_ref;
  #1;
  if(!rst_n)old_drain=0;
  if(rst_n) begin
   if(issue_last)begin issue_edge=edges;last_identity={read_ctx,read_ver};end
   if(rv)final_output_edge=edges;
   for(integer di=0;di<4;di=di+1)if(drain_toggle[di]!=old_drain[di])begin drain_events=drain_events+1;if(edges-issue_edge!=49||drain_tuple[48*di+:48]!==last_identity)$fatal(1,"actual arithmetic drain identity/timing mismatch delta=%0d",edges-issue_edge);end
   for(integer di=0;di<4;di=di+1)if(drain_toggle[di]!=old_drain[di]&&drain_tuple[48*di+:48]=={16'd1,32'hC1230001})old_drain_seen=1;
   old_drain=drain_toggle;
   if(ops<4)begin if(|cr)outstanding=outstanding+1;if(rv)outstanding=outstanding-1;if(outstanding>peak_outstanding)peak_outstanding=outstanding;if(outstanding<0)$fatal(1,"native output before query obligation");end
   if(next_offer&&!local_granted&&!BOUNDARY_BYPASS&&(ib!==native_ib[0]||offered_ctx!=1))$fatal(1,"boundary dispatch changed physical IB/context before real local drain");
 if(op_accept)begin
 next_query=0;current_ctx=accepted_ctx;
 if(accepted_ctx==2)begin
 second_accept_base=base_edges;
 if(!local_granted)begin early_accept_old_live=bank_outstanding[0][7*recipient_index+:7];$display("BOUNDARY_EARLY old_outstanding=%0d old_numeric_v=%0b queue=%0d",early_accept_old_live,cv,output_queue.count);end
 if(!BOUNDARY_BYPASS&&!local_granted)$fatal(1,"boundary next actualaccept before local drain");
 end
 end
   if(|cr)begin if(query_seq!==next_query||query_toggle===last_query_toggle)$fatal(1,"actual production query40 monotonic/toggle mismatch");next_query=next_query+1;end
   else if(query_toggle!==last_query_toggle)$fatal(1,"query40 callback without request");
   last_query_toggle=query_toggle;
   if(query_issue_v!==(|cr))$fatal(1,"actual allocated query valid mismatch");
   if(query_fault||admission_fault)$fatal(1,"actual query40 credit/admission violation");
   if(cr!==oracle_req || (|cr) && (ca!==oracle_addr || ep!==oracle_epoch)) $fatal(1,"actual tile request/epoch mismatch op=%0d cr=%h oracle=%h ca=%h expectaddr=%h epoch=%h oracleepoch=%h active=%b",ops,cr,oracle_req,ca,oracle_addr,ep,oracle_epoch,`REF_ME.active);
   if(MUT!=1 && accepted_valid && (MUT!=4 || incoming))begin
    descriptor_checks=descriptor_checks+1;
    if(accepted_ib!==expected_accepted_ib)$fatal(1,"production acceptedIB lifetime mismatch");
   end
   if(|cr) begin
    requests=requests+1;
    if(MUT!=1 && (read_mode!==expected_mode || read_ctx!==expected_ctx || read_ver!==expected_ver))$fatal(1,"production request metadata mismatch");
    if(MUT!=1)metadata_checks=metadata_checks+1;
   end
   if(MUT!=1 && op_accept)begin
    accepts=accepts+1;
    if(accepted_ctx!==current_ctx || accepted_ver!==32'(32'hC1230000+current_ctx))$fatal(1,"production accepted context mismatch");
   end
   if(rv!==cv || rv && rt!==ct) $fatal(1,"actual CEXT2 arithmetic mismatch op=%0d edge=%0d",ops,edges);
   if(rf!==cf || cachefault) $fatal(1,"actual tile/cache fault op=%0d",ops);
   if(rv) checks=checks+1;
  end
 end
 integer op=0,t,k,j,a,kc=8,tiles=1,sp=9,xjs=0,xb=4096,nout=768,xks=1,xcs=8;
 task preload(input integer ctx,input integer base,input integer count,input integer split,input integer stride);
  for(integer kk=0;kk<count;kk=kk+1)begin
   @(negedge clk);load_ctx=16'(ctx);load_ver=32'(32'hC1230000+ctx);load_epoch={18'(kk),3'd0};
   for(integer ll=0;ll<4;ll=ll+1)begin
    load_key[24*ll+:24]=24'(base+((4*tid+ll)&((1<<split)-1))*stride+kk);
    lx[32*ll+:32]=xv(load_key[24*ll+:24]);
   end
   while(!load_ready)@(negedge clk);lv=1;@(negedge clk);lv=0;@(negedge clk);
  end
 endtask
 initial begin
  $readmemh("native_profiles.hex",native_ib);
  repeat(4)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
  current_ctx=1;offered_ctx=1;tid=0;ib=native_ib[0];
  preload(1,4096,8,9,8);
  @(negedge clk);bank_reset=1;begin_bank[0]=1;@(negedge clk);begin_bank[0]=0;
  repeat(3)@(negedge clk);offer_go=1;wait(op_accept);@(negedge clk);offer_go=0;
  wait(issue_last);@(negedge clk);
  if(bank_outstanding[0][7*recipient_index+:7]==0)$fatal(1,"boundary missing actual old live obligations");
  next_offer=1;offer_base=base_edges;held_next_ib=native_ib[1];offer_go=1;
  if(BOUNDARY_BYPASS)begin offered_ctx=2;ib=held_next_ib;end
  $display("BOUNDARY_OFFER base=%0d old_outstanding=%0d numeric_delivered=%0d",base_edges,bank_outstanding[0][7*recipient_index+:7],consumed_outputs);
  preload(2,50672,2,8,2);
  wait(local_candidate);@(negedge clk);
  if(accepts!=1||consumed_outputs!=64||held_offer_old_posts==0||queue_peak!=8)$fatal(1,"boundary old drain/held-offer coverage accepts=%0d oldconsumed=%0d heldposts=%0d queuepeak=%0d",accepts,consumed_outputs,held_offer_old_posts,queue_peak);
  begin_bank[1]=1;@(negedge clk);begin_bank[1]=0;selected_bank=1;ib=held_next_ib;offered_ctx=2;local_granted=1;
  $display("BOUNDARY_GRANT base=%0d old_outstanding=0 queueempty=1 source49=1 oldbank_unsealed=1",base_edges);
  wait(accepts==2);@(negedge clk);offer_go=0;ops=1;
  wait(consumed_outputs==112);while(cv||output_queue.pending_post||output_queue_v||bank_outstanding[1][7*recipient_index+:7]!=0||edges<issue_edge+49)@(negedge clk);
  if(checks!=112||requests!=112||issued_total!=112||retired_total!=112||typed_consumed!=112||accepts!=2||drain_events!=2)$fatal(1,"boundary arithmetic/lifetime totals wrong");
  if(|bank_fault||(|bank_drained)||early_accept_old_live!=0)$fatal(1,"boundary fault/fabricated release");
  $display("PASS boundary actual2accept112words112queryretire old49_queueempty_ledgerzero=1 held_offer_old_posts=%0d peakqueue=%0d ledgerpeak=%0d base=%0d secondaccept=%0d seals=0",held_offer_old_posts,queue_peak,ledger_peak,base_edges,second_accept_base);$finish;
 end
 initial begin #500000;$fatal(1,"boundary timeout");end

endmodule

// Bench-only synchronous hash model for the actual RPS0 hard-ROM interfaces.
// Both reference and candidate instantiate the real rpair leaf and this model.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk) if(ce_in) begin
  rd_out<=0;
  for(l=0;l<32;l=l+1) rd_out[8*l+:8]<=8'(addr_in+l+1);
 end
endmodule
