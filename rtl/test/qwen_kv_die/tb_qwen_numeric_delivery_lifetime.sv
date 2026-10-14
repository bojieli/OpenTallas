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
module tb_qwen_numeric_delivery_lifetime;
 parameter integer MUT=0,ALL_SPLITS=0,QUEUE_DEPTH=2;
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
 wire [47:0] numeric_identity;wire query_output_credit,query_output_toggle;wire [87:0] query_output_tuple;wire query_output_ack;reg old_query_output=0;reg [88:0] output_oracle[0:45];integer consumed_outputs=0,typed_consumed=0,held_output_bases=0;
 wire output_queue_credit,output_queue_v,output_queue_has_query,output_queue_fault;wire [511:0] output_queue_word;wire [87:0] output_queue_tag;reg sink_ready=1,actual_produced_step=0;integer posted_outputs=0,expected_head=0,expected_tail=0;reg [511:0] expected_words[0:2047];reg expected_types[0:2047];reg [87:0] expected_tags[0:2047];
 ot_qwen_numeric_output_queue #(.ENABLE(1),.DEPTH(QUEUE_DEPTH)) output_queue(.base_clk(clk),.rst_n(rst_n),.core_output_step(gate),.numeric_v(cv),.numeric_word(ct),.numeric_identity(numeric_identity),.query_output_toggle(query_output_toggle),.query_output_tuple(query_output_tuple),.query_output_ack_toggle(query_output_ack),.core_credit(output_queue_credit),.consume_ready(actual_sink_ready),.consume_v(output_queue_v),.consume_word(output_queue_word),.consume_has_query(output_queue_has_query),.consume_query_tuple(output_queue_tag),.fault(output_queue_fault));
 wire query_issue_v;wire issue_last;wire [3:0] drain_toggle;wire [191:0] drain_tuple;reg [3:0] drain_ack=0,old_drain=0;integer issue_edge=0,final_output_edge=0,drain_events=0,outstanding=0,peak_outstanding=0;reg [47:0] last_identity;
 reg [39:0] load_seq=40'h8abcdef123;wire load_ready,read_credit,fill_toggle,response_toggle;wire [246:0] fill_tuple,response_tuple;reg fill_ack=0,response_ack=0;integer fill_events=0,response_events=0;reg [246:0] expected_fill,expected_response;reg expected_fill_v,expected_response_v,old_fill=0,old_response=0;
 wire [39:0] query_seq;wire query_toggle,query_credit,query_fault,accept_toggle,admission_fault;reg query_ack=0,accept_ack=0;integer query_callbacks=0,base_edges=0,query_held=0;reg [39:0] next_query=0;reg last_query_toggle=0;
 always @(negedge clk)sink_ready<=(base_edges%17!=5&&base_edges%17!=6&&base_edges%17!=7);
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
    expected_words[expected_tail]=rt;expected_types[expected_tail]=output_oracle[45][88];expected_tags[expected_tail]=output_oracle[45][88]?output_oracle[45][87:0]:{output_oracle[45][87:40],40'd0};expected_tail=expected_tail+1;posted_outputs=posted_outputs+1;
   end
   if(query_output_toggle!=query_output_ack)held_output_bases=held_output_bases+1;
  end
  #1;if(rst_n&&output_queue_fault)$fatal(1,"actual numeric output queue reservation/event fault");
 end
 reg bank_begin=0,bank_reset=0;integer issued_total=0,retired_total=0,ledger_peak=0,queue_peak=0;wire [5:0] recipient_index=tid%48;
 wire [47:0] ledger_issue_ready,ledger_retire_ready;wire ledger_fault,ledger_drained;
 wire [47:0] ledger_issue_v=(48'd1<<recipient_index)&{48{query_toggle!=query_ack}};
 wire [47:0] ledger_retire_v=(48'd1<<recipient_index)&{48{output_queue_v&&sink_ready&&output_queue_has_query}};
 wire actual_sink_ready=sink_ready&&(!output_queue_has_query||ledger_retire_ready[recipient_index]);
 wire [1919:0] issue_sequences,retire_sequences;wire [767:0] issue_contexts,retire_contexts;wire [1535:0] issue_versions,retire_versions;
 wire [335:0] outstanding_observed;
 for(genvar li=0;li<48;li=li+1)begin:ledger_tuple
  assign issue_sequences[40*li+:40]=query_seq;assign issue_contexts[16*li+:16]=read_ctx;assign issue_versions[32*li+:32]=read_ver;
  assign retire_sequences[40*li+:40]=output_queue_tag[39:0];assign retire_contexts[16*li+:16]=output_queue_tag[87:72];assign retire_versions[32*li+:32]=output_queue_tag[71:40];
  assign outstanding_observed[7*li+:7]=ledger.recipient[li].outstanding;
 end
 wire begin_to_bank=(MUT==5)?(!ledger.active&&|ledger_issue_v):bank_begin;
 ot_qwen_xdelivery_ack_vector #(.ENABLE(1),.N(48),.SEQ_W(40),.COUNT_W(7)) ledger(
 .clk(clk),.rst_n(rst_n&&bank_reset),.begin_v(begin_to_bank),.fenced_clear(1'b0),.begin_context(current_ctx),.begin_version(32'(32'hC1230000+current_ctx)),.participant_mask({48{1'b1}}),
 .issue_v(ledger_issue_v),.issue_ready(ledger_issue_ready),.issue_seq(issue_sequences),.issue_context(issue_contexts),.issue_version(issue_versions),
 .retire_v(ledger_retire_v),.retire_ready(ledger_retire_ready),.retire_seq(retire_sequences),.retire_context(retire_contexts),.retire_version(retire_versions),
 .seal_v(48'd0),.seal_context(768'd0),.seal_version(1536'd0),.drained(ledger_drained),.fault(ledger_fault));
 always @(posedge clk)begin
  if(rst_n&&bank_reset)begin
   if(MUT!=5 && (begin_to_bank&&(|ledger_issue_v||(|ledger_retire_v))||(|ledger_issue_v)&&!ledger.active))$fatal(1,"actual bank startup not complete before event");
   if(ledger_issue_v[recipient_index]&&ledger_issue_ready[recipient_index])issued_total=issued_total+1;
   if(ledger_retire_v[recipient_index]&&ledger_retire_ready[recipient_index])retired_total=retired_total+1;
   #1;if(ledger_fault)$fatal(1,"actual delivery ledger startup or event fault");
   if(outstanding_observed[7*recipient_index+:7]>ledger_peak)ledger_peak=outstanding_observed[7*recipient_index+:7];
   if(output_queue.count>queue_peak)queue_peak=output_queue.count;
   if(ledger_drained)$fatal(1,"unbound recipient seals fabricated");
  end
 end
 reg allow=1,gate=1;wire hit;always @(negedge clk) gate<=allow&&hit&&query_credit&&read_credit&&query_output_credit&&output_queue_credit;
 wire cc=clk&&gate;
 reg rst_n=0,go=0,clear=0,lv=0,j_repeat=1;
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
 ot_qwen_tile_tp8_numeric_identity dut_cached(
 .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx_group(cc),.clk_rqr({2{cc}}),
 .clk_cache_response(cc),.clk_cache_load(clk),.clk_local_drain(cc),.clk_node_lifetime(cc),.clk_query_output_identity(cc),
 .query_output_ack_toggle(query_output_ack),.query_output_credit(query_output_credit),.query_output_toggle(query_output_toggle),.query_output_tuple(query_output_tuple),.numeric_identity(numeric_identity),
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
   if(output_oracle[45][88])begin
    if(!cv||query_output_toggle===old_query_output||query_output_tuple!==output_oracle[45][87:0])$fatal(1,"actual output40 mask/identity/arithmetic edge mismatch");
   end else if(query_output_toggle!==old_query_output)$fatal(1,"output40 event without allocated query");
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
   old_drain=drain_toggle;
   if(ops<4)begin if(|cr)outstanding=outstanding+1;if(rv)outstanding=outstanding-1;if(outstanding>peak_outstanding)peak_outstanding=outstanding;if(outstanding<0)$fatal(1,"native output before query obligation");end
   if(op_accept)next_query=0;
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
 integer op,t,k,j,a,kc,tiles,sp,xjs,xb,nout,xks,xcs;
 initial begin
`ifdef XCACHE_TP8
  $readmemh("native_profiles.hex",native_ib);
`endif
  repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
  for(op=0;op<6+(ALL_SPLITS?16:0);op=op+1) begin
   allow=1;
   while(op>0&&(expected_head!=expected_tail||cv||output_queue.pending_post||outstanding_observed[7*recipient_index+:7]!=0||edges<issue_edge+49))@(negedge clk);
   bank_reset=0;rst_n=0;repeat(16)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
   if(op>=6) begin allow=1;rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);end
   current_ctx=16'(op+1);offered_ctx=current_ctx;incoming=0;allow=0;repeat(2) @(negedge clk);clear=1;@(negedge clk);clear=0;
   case(op)
    0:begin tid=0;sp=9;kc=8;tiles=1;nout=768;xjs=0;end
    1:begin tid=127;sp=8;kc=2;tiles=3;nout=4096;xjs=0;end
    2:begin tid=(TARGET_GT==3072)?512:768;sp=7;kc=32;tiles=1;nout=3072;xjs=0;end
    3:begin tid=(TARGET_GT==3072)?767:1535;sp=8;kc=6;tiles=3;nout=4096;xjs=0;end
    4:begin tid=511;sp=11;kc=3;tiles=1;nout=16;xjs=17;end
    5:begin tid=(TARGET_GT==3072)?703:1023;sp=7;kc=9;tiles=2;nout=4096;xjs=29;end
    default:begin tid=0;sp=op-6;kc=2;tiles=1;nout=128;xjs=5;end
   endcase
   xb=4096+op*10000;xks=1;xcs=kc;
   if(op==5 || op>=6) begin
    xb=24'hFED123;xks=24'hC7D8E9;xjs=24'hABCDE7;xcs=24'hFACE91;
   end
   j_repeat=(xjs==0);
   ib={18'(nout),18'(tiles),18'(kc),1'b0,24'd0,24'(kc*8),24'd8,24'd1,24'(xb),24'(xks),24'(xjs),24'(xcs),3'd0,4'(sp),24'd0,1'b1,24'd0,24'd8,24'd1,1'b0,1'b1,1'b0,1'b0,24'd0};
`ifdef XCACHE_TP8
   if(op<4) begin
    ib=native_ib[op];
    case(op) 0:xb=4096;1:xb=50672;2:xb=4096;3:xb=55280;endcase
   end
`endif
   for(k=0;k<kc;k=k+1) for(j=0;j<(j_repeat?1:8);j=j+1) begin
    load_ctx=current_ctx;load_ver=32'(32'hC1230000+current_ctx);load_epoch={18'(k),3'(j)};
    for(l=0;l<4;l=l+1) begin a=xb+((4*tid+l)&((1<<sp)-1))*xcs+k*xks+j*xjs;lx[32*l+:32]=xv(24'(a));load_key[24*l+:24]=24'(a);end
    while(!load_ready)@(negedge clk);lv=1;@(negedge clk);lv=0;@(negedge clk);
   end
   lv=0;bank_reset=1;bank_begin=1;@(negedge clk);bank_begin=0;allow=1;repeat(8) @(negedge clk);go=1;wait(op_accept);@(negedge clk);go=0;
   for(t=0;t<3*kc*tiles*8+300;t=t+1) begin
    if(op==5 && t==20) begin clear=1;@(negedge clk);clear=0;end
    if(!hit) begin
     misses=misses+1;load_epoch=ep;
     for(l=0;l<4;l=l+1) lx[32*l+:32]=xv(ca[24*l+:24]);
     load_ctx=read_ctx;load_ver=read_ver;load_key=ca;load_seq=query_seq;while(!load_ready)@(negedge clk);lv=1;@(negedge clk);lv=0;repeat(2)@(negedge clk);
    end
    if(op==5 && !incoming && |cr && ep[2:0]==6 && ep[20:3]==0)begin
     // Offer a next descriptor with xjs0 while its GO is held externally.
     // Old actual request j6 remains pending; only latest external mode changes.
     incoming=1;j_repeat=1;ib=native_ib[0];offered_ctx=current_ctx+16'h4000;mode_checks=mode_checks+1;
     if(MUT!=1)begin
      allow=0;repeat(2)@(negedge clk);
      load_ctx=current_ctx+16'h4000;load_ver=read_ver+1;load_key=ca;load_epoch=ep;
      lx=128'h40000000400000004000000040000000;while(!load_ready)@(negedge clk);lv=1;@(negedge clk);lv=0;@(negedge clk);lv=0;
      #1;if(MUT!=2 && hit)$fatal(1,"resident context/version reused for old request");
      resident_checks=resident_checks+1;
      load_ctx=read_ctx;load_ver=read_ver;
      for(l=0;l<4;l=l+1)lx[32*l+:32]=xv(ca[24*l+:24]);
      while(!load_ready)@(negedge clk);lv=1;@(negedge clk);lv=0;@(negedge clk);lv=0;
     end
    end
    if(MUT==2 && incoming && |cr && !hit)$fatal(1,"live mode lost old pending request");
    allow=(t%13!=7 && t%13!=8);@(negedge clk);
   end
   allow=1;repeat(8) @(negedge clk);if(final_output_edge>=issue_edge+49)$fatal(1,"actual output not drained before local certificate delta=%0d",final_output_edge-issue_edge);
   $display("DRAINTRACE op=%0d tid=%0d last_issue_cc=%0d final_output_cc=%0d latency=%0d outstanding=%0d peak=%0d",op,tid,issue_edge,final_output_edge,final_output_edge-issue_edge,outstanding,peak_outstanding);ops=ops+1;
   
  end
  if(MUT==0 && (metadata_checks<600 || accepts<6 || descriptor_checks<600))$fatal(1,"production metadata coverage missing");
  if(MUT==0 && resident_checks!=1)$fatal(1,"missing resident context/version overlap coverage");
  if(mode_checks!=1)$fatal(1,"missing actual j6 mode-overlap coverage");
  if(requests<600 || checks!=680+(ALL_SPLITS?256:0) || misses<4) $fatal(1,"coverage actualrequests=%0d arithmetic=%0d misses=%0d",requests,checks,misses);
  allow=1;while(expected_head!=expected_tail||cv||output_queue.pending_post||outstanding_observed[7*recipient_index+:7]!=0||edges<issue_edge+49)@(negedge clk);
  if(retired_total!=requests||issued_total!=requests)$fatal(1,"actual ledger query retire count mismatch issued=%0d retired=%0d requests=%0d",issued_total,retired_total,requests);
  if(consumed_outputs!=checks||posted_outputs!=checks||typed_consumed!=requests||expected_head!=expected_tail)$fatal(1,"actual numeric/query delivery missing or fabricated words=%0d queries=%0d checks=%0d requests=%0d",consumed_outputs,typed_consumed,checks,requests);
  $display("DELIVERY_LEDGER depth=%0d issued=%0d retired=%0d outstanding=0 seals=0 ledger_peak=%0d queue_peak=%0d startup_before_events=1",QUEUE_DEPTH,issued_total,retired_total,ledger_peak,queue_peak);
  $display("OUTPUT40 numeric_consumed=%0d typed_consumed=%0d held_output_base_edges=%0d",consumed_outputs,typed_consumed,held_output_bases);
  $display("LOCAL_DRAIN events=%0d native_peak_outstanding=%0d",drain_events,peak_outstanding);
  $display("EVENT40 fills=%0d responses=%0d",fill_events,response_events);
  $display("QUERY40 durable_callbacks=%0d observed_pending_base_edges=%0d base_edges=%0d max_pending_queries=1",query_callbacks,query_held,base_edges);
  $display("PASS production acceptedIB and request ports GT%0d NW18 ops=%0d arithmetic=%0d requests=%0d misses=%0d XLOCAL=1 IREG_XL_bypass_only=1 ME_EXTRA=8 indexed_entries=32 coherent26roots=1 raw_split_fault_diagnostics=%0d",TARGET_GT,ops,checks,requests,misses,ALL_SPLITS);$finish;
 end
endmodule

// Bench-only synchronous hash model for the actual RPS0 hard-ROM interfaces.
// Both reference and candidate instantiate the real rpair leaf and this model.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk) if(ce_in) begin
  rd_out<=0;
  for(l=0;l<32;l=l+1) rd_out[8*l+:8]<=8'(addr_in+l+1);
 end
endmodule
