`timescale 1ns/1ps
// QW-N59-4 (10-19): RANDOM-stimulus lockstep of the hardened native59 split vs qfd_native59_dv_service_r1 (SAFE 2,
// RST_FOREST 1, EMB_RELAY 1, NU / MCTX as given).  Complements the directed programs (tb_qfd_native59_dv_service /
// tb_qfd_native59_dv_mu with n59_split_shadow): here every input is random every edge (bursty valids, legal-looking and
// malformed dd words, Q seats, requests, EMB commands, slots, records), so fault paths, collisions and the exact edge of
// every relay / registered bank word are exercised.  Reset is re-asserted every RST_EVERY edges; the inputs stay idle for
// QUIET edges around each release and the comparison skips the reset window (the split's service releases on the same
// absolute edge as its bank: one service edge earlier, unobservable under the static calendar's idle window).
// Pass line N59RND_PASS; any mismatch N59RND_FAIL (+ $fatal).
module tb_n59_boundary_pair #(parameter integer RECV_MUT=0,SAFE=2,EMBR=1,SEED=1,CYCLES=40000,NU=4,MCTX=1,SPLIT_MUT=0,QB_MUT=0,LP_MUT=0,
                              SPL_SOFF=3,SPL_BOFF=0,SPL_ROFF=3,RST_EVERY=400,QUIET=12)(input wire clk);
 localparam[379:0]TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg[31:0]cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 wire[31:0]ph=cyc%RST_EVERY;
 wire rst_n=!(ph<4);
 wire quiet=ph<4+QUIET||ph>=RST_EVERY-QUIET;   // idle on both sides of every reset (the split's bank runs one edge behind
                                                 // its face registers: traffic on the edge before an async reset would be cut one edge earlier)
 wire cmp_en=!(ph<4+QUIET+8||ph>=RST_EVERY-4);
 reg hev,hfc;reg[15:0]he;reg[58:0]ht;reg[1:0]hg;reg lcv;reg[5:0]stage;reg[17:0]tok,pos;reg[379:0]cmd;reg[547:0]dd;
 reg kvs,x3s,qs,ts,rv,rs,vis,cs;reg[1:0]kvi;reg[4:0]qb,tb,rb;reg[3:0]tk,rk;reg[547:0]rp;reg[511:0]ecq;reg[15:0]esq;
 integer l,r;
 reg[63:0]rs_=64'h9E3779B97F4A7C15^(64'(SEED)*64'hD1B54A32D192ED03);
 function automatic [31:0] rnd();begin rs_^=rs_>>12;rs_^=rs_<<25;rs_^=rs_>>27;rnd=32'((rs_*64'h2545F4914F6CDD1D)>>32);end endfunction
 function automatic bit pr(input integer n);pr=(rnd()%n)==0;endfunction
 always @(posedge clk)begin
  // HOST face: mostly a stable user-0 context, sometimes perturbed
  if(pr(500)||cyc<2)begin he={14'(rnd()),2'(rnd()%4==0?rnd():0)};hg=2'(rnd());end
  hev=!pr(2000);hfc=!pr(2000);
  ht={he,6'd0,18'(rnd()%151936),13'(rnd()%8192),6'd0};if(pr(1000))ht=59'({rnd(),rnd()});
  lcv=pr(40);stage=pr(8)?6'(rnd()):6'(1+rnd()%36);tok=18'(rnd()%160000);pos=18'(rnd());
  if(pr(3))pos[15:13]=0;
  cmd=0;
  if(pr(30))cmd=TEMPLATE;
  else if(pr(150))begin cmd[379:376]=4'hE;cmd[375:358]=18'(rnd()%152000);end
  else if(pr(2000))for(l=0;l<12;l=l+1)cmd[32*l+:32]=rnd();
  if(pr(4))cmd[299:280]=20'(rnd());
  dd=0;
  if(pr(2))begin
   dd[547]=1;r=rnd()%16;dd[546:545]=(r<8)?2'd0:(r<11)?2'd1:(r<14)?2'd2:2'(rnd());
   dd[544:537]=pr(8)?8'(rnd()):8'hff;
   for(l=0;l<8;l=l+1)begin
    dd[345+24*l+:24]=(dd[546:545]==2'd0)?24'(rnd()%512):(dd[546:545]==2'd1)?24'(rnd()%1048576):24'(1048576+rnd()%1048576);
    if(pr(400))dd[345+24*l+:24]=24'(rnd());
    dd[89+32*l+:32]=rnd();
   end
   if(pr(400))dd[88:0]=89'(rnd());
  end else if(pr(400))dd[546:0]=547'({rnd(),rnd()});
  kvs=pr(6);kvi=2'(rnd());x3s=pr(6);
  qs=pr(4);qb=5'(rnd());ts=pr(3);tk=4'(rnd()%5);tb=5'(rnd());
  rv=pr(3);rs=pr(3);rk=4'(rnd()%6);rb=5'(rnd());
  for(l=0;l<17;l=l+1)rp[32*l+:32]=rnd();rp[547:544]=4'(rnd());
  if(pr(2))begin rp[547:512]={5'd0,4'(rnd()%6),6'd0,he,5'(rnd())};end
  for(l=0;l<16;l=l+1)ecq[32*l+:32]=rnd();esq=16'(rnd());
  vis=pr(40);cs=pr(40);
  if(quiet)begin
   lcv=0;cmd=0;dd=0;kvs=0;x3s=0;qs=0;ts=0;rv=0;rs=0;vis=0;cs=0;rp=0;ecq=0;esq=0;stage=0;tok=0;pos=0;kvi=0;qb=0;tb=0;rb=0;tk=0;rk=0;
  end
 end
 wire [523:0] a_x3;
 wire [58:0] a_x3_identity;
 wire [1:0] a_x3_generation;
 wire  a_native_tx_v;
 wire [547:0] a_native_tx_payload;
 wire [519:0] a_dr_o;
 wire  a_emb_code_re;
 wire [23:0] a_emb_code_addr;
 wire  a_emb_scale_re;
 wire [17:0] a_emb_scale_addr;
 wire  a_completed;
 wire [94:0] a_native_ret;
 wire  a_fault;
 qfd_native59_split_flat #(.NU(NU),.MCTX(MCTX),.EMB_RELAY(1),.SVC_RECV(0),.SVC_RECV_MUT(0)) a(
  .ck(clk),
  .rst_n(rst_n),
  .host_epoch_valid(hev),
  .host_fused_capability(hfc),
  .host_epoch(he),
  .host_tag(ht),
  .host_generation(hg),
  .layer_context_v(lcv),
  .command_stage(stage),
  .native_token(tok),
  .native_position(pos),
  .native_cmd(cmd),
  .dd_i(dd),
  .kv_word_slot(kvs),
  .kv_word_index(kvi),
  .kv_x3_slot(x3s),
  .x3(a_x3),
  .x3_identity(a_x3_identity),
  .x3_generation(a_x3_generation),
  .q_slot(qs),
  .q_slot_beat(qb),
  .tx_slot(ts),
  .tx_slot_kind(tk),
  .tx_slot_beat(tb),
  .native_tx_v(a_native_tx_v),
  .native_tx_payload(a_native_tx_payload),
  .native_rx_v(rv),
  .native_rx_payload(rp),
  .rx_slot(rs),
  .rx_slot_kind(rk),
  .rx_slot_beat(rb),
  .dr_o(a_dr_o),
  .emb_code_re(a_emb_code_re),
  .emb_code_addr(a_emb_code_addr),
  .emb_scale_re(a_emb_scale_re),
  .emb_scale_addr(a_emb_scale_addr),
  .emb_code_q(ecq),
  .emb_scale_q(esq),
  .visibility_slot(vis),
  .complete_slot(cs),
  .completed(a_completed),
  .native_ret(a_native_ret),
  .fault(a_fault));
 wire [523:0] b_x3;
 wire [58:0] b_x3_identity;
 wire [1:0] b_x3_generation;
 wire  b_native_tx_v;
 wire [547:0] b_native_tx_payload;
 wire [519:0] b_dr_o;
 wire  b_emb_code_re;
 wire [23:0] b_emb_code_addr;
 wire  b_emb_scale_re;
 wire [17:0] b_emb_scale_addr;
 wire  b_completed;
 wire [94:0] b_native_ret;
 wire  b_fault;
 qfd_native59_split_flat #(.NU(NU),.MCTX(MCTX),.EMB_RELAY(1),.SVC_RECV(1),.SVC_RECV_MUT(RECV_MUT)) b(
  .ck(clk),
  .rst_n(rst_n),
  .host_epoch_valid(hev),
  .host_fused_capability(hfc),
  .host_epoch(he),
  .host_tag(ht),
  .host_generation(hg),
  .layer_context_v(lcv),
  .command_stage(stage),
  .native_token(tok),
  .native_position(pos),
  .native_cmd(cmd),
  .dd_i(dd),
  .kv_word_slot(kvs),
  .kv_word_index(kvi),
  .kv_x3_slot(x3s),
  .x3(b_x3),
  .x3_identity(b_x3_identity),
  .x3_generation(b_x3_generation),
  .q_slot(qs),
  .q_slot_beat(qb),
  .tx_slot(ts),
  .tx_slot_kind(tk),
  .tx_slot_beat(tb),
  .native_tx_v(b_native_tx_v),
  .native_tx_payload(b_native_tx_payload),
  .native_rx_v(rv),
  .native_rx_payload(rp),
  .rx_slot(rs),
  .rx_slot_kind(rk),
  .rx_slot_beat(rb),
  .dr_o(b_dr_o),
  .emb_code_re(b_emb_code_re),
  .emb_code_addr(b_emb_code_addr),
  .emb_scale_re(b_emb_scale_re),
  .emb_scale_addr(b_emb_scale_addr),
  .emb_code_q(ecq),
  .emb_scale_q(esq),
  .visibility_slot(vis),
  .complete_slot(cs),
  .completed(b_completed),
  .native_ret(b_native_ret),
  .fault(b_fault));
 wire[1794:0] a_out={a_x3,a_x3_identity,a_x3_generation,a_native_tx_v,a_native_tx_payload,a_dr_o,a_emb_code_re,a_emb_code_addr,a_emb_scale_re,a_emb_scale_addr,a_completed,a_native_ret,a_fault};
 wire[1794:0] b_out={b_x3,b_x3_identity,b_x3_generation,b_native_tx_v,b_native_tx_payload,b_dr_o,b_emb_code_re,b_emb_code_addr,b_emb_scale_re,b_emb_scale_addr,b_completed,b_native_ret,b_fault};
 wire[5205:0] a_probe={a.u_svc.dd_form_bad,a.u_svc.q_in_bad,a.u_svc.kv_in_bad,a.u_svc.q_miss,a.u_svc.q_committed,a.u_svc.q,a.u_svc.kv_we,a.u_svc.kv_waddr,a.u_svc.kv_wdata,a.u_svc.begin_slot,a.u_svc.request_slot,a.u_svc.src_fault,a.u_svc.vm_write_v,a.u_svc.vm_write_v?a.u_svc.vm_write_data:512'd0,a.u_svc.kvn_v,a.u_svc.kvn_data};
 wire[5205:0] b_probe={b.u_svc.dd_form_bad,b.u_svc.q_in_bad,b.u_svc.kv_in_bad,b.u_svc.q_miss,b.u_svc.q_committed,b.u_svc.q,b.u_svc.kv_we,b.u_svc.kv_waddr,b.u_svc.kv_wdata,b.u_svc.begin_slot,b.u_svc.request_slot,b.u_svc.src_fault,b.u_svc.vm_write_v,b.u_svc.vm_write_v?b.u_svc.vm_write_data:512'd0,b.u_svc.kvn_v,b.u_svc.kvn_data};
 reg[1794:0] prior_out;
 reg[5205:0] prior_probe;
 always @(posedge clk)begin prior_out<=a_out;prior_probe<=a_probe;end
 integer compared=0,mism=0,pmism=0,qwords=0,kvwrites=0,changes=0;
 reg[5205:0] last_probe;
 always @(posedge clk)begin
  last_probe<=a_probe;
  if(cmp_en)begin
   compared<=compared+1;
   qwords<=qwords+a.u_svc.q[523];kvwrites<=kvwrites+(|a.u_svc.kv_we);
   changes<=changes+(a_probe!=last_probe);
   if(b_out!==prior_out)begin mism<=mism+1;if(mism<4)$display("N59PAIR_ERR cycle %0d output diff %0d",cyc,$countones(b_out^prior_out));end
   if(b_probe!==prior_probe)begin pmism<=pmism+1;if(pmism<4)$display("N59PAIR_ERR cycle %0d internal diff %0d",cyc,$countones(b_probe^prior_probe));end
  end
  if(cyc==CYCLES)begin
   $display("N59PAIR_ACTIVITY compared %0d output_mism %0d internal_mism %0d qwords %0d kvwrites %0d changes %0d",compared,mism,pmism,qwords,kvwrites,changes);
   if(mism!=0||pmism!=0||compared<CYCLES/2||qwords<100||kvwrites<100||changes<100)begin $display("N59PAIR_FAIL MUT %0d",RECV_MUT);$fatal(1);end
   $display("N59PAIR_PASS MUT %0d NU %0d MCTX %0d: source-v3 graph +1 edge, NOT golden-release qualification",RECV_MUT,NU,MCTX);$finish;
  end
 end
endmodule
