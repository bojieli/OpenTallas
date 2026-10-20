`timescale 1ns/1ps
// QW-N59-4 (10-19): RANDOM-stimulus lockstep of the hardened native59 split vs qfd_native59_dv_service_r1 (SAFE 2,
// RST_FOREST 1, EMB_RELAY 1, NU / MCTX as given).  Complements the directed programs (tb_qfd_native59_dv_service /
// tb_qfd_native59_dv_mu with n59_split_shadow): here every input is random every edge (bursty valids, legal-looking and
// malformed dd words, Q seats, requests, EMB commands, slots, records), so fault paths, collisions and the exact edge of
// every relay / registered bank word are exercised.  Reset is re-asserted every RST_EVERY edges; the inputs stay idle for
// QUIET edges around each release and the comparison skips the reset window (the split's service releases on the same
// absolute edge as its bank: one service edge earlier, unobservable under the static calendar's idle window).
// Pass line N59RND_PASS; any mismatch N59RND_FAIL (+ $fatal).
module tb_n59_split_random #(parameter integer SAFE=2,EMBR=1,SEED=1,CYCLES=40000,NU=4,MCTX=1,SPLIT_MUT=0,QB_MUT=0,LP_MUT=0,
                              SPL_SOFF=1,SPL_BOFF=0,SPL_ROFF=1,RST_EVERY=400,QUIET=12)(input wire clk);
 localparam[379:0]TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg[31:0]cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 wire[31:0]ph=cyc%RST_EVERY;
 wire rst_n=!(ph<4);
 wire quiet=ph<4+QUIET;
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
 wire[523:0]x3;wire[58:0]xid;wire[1:0]xg;wire tv;wire[547:0]td;wire[519:0]dr;wire cre,sre;wire[23:0]caddr;wire[17:0]saddr;
 wire done,flt;wire[94:0]ret;
 qfd_native59_dv_service_r1 #(.NU(NU),.MCTX(MCTX),.SAFE(2),.RST_FOREST(1),.EMB_RELAY(1)) ref0(
  .ck(clk),.rst_n(rst_n),.host_epoch_valid(hev),.host_fused_capability(hfc),.host_epoch(he),.host_tag(ht),.host_generation(hg),
  .layer_context_v(lcv),.command_stage(stage),.native_token(tok),.native_position(pos),.native_cmd(cmd),.dd_i(dd),
  .kv_word_slot(kvs),.kv_word_index(kvi),.kv_x3_slot(x3s),.x3(x3),.x3_identity(xid),.x3_generation(xg),.q_slot(qs),.q_slot_beat(qb),
  .tx_slot(ts),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(tv),.native_tx_payload(td),.native_rx_v(rv),.native_rx_payload(rp),
  .rx_slot(rs),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr),.emb_code_re(cre),.emb_code_addr(caddr),.emb_scale_re(sre),
  .emb_scale_addr(saddr),.emb_code_q(ecq),.emb_scale_q(esq),.visibility_slot(vis),.complete_slot(cs),.completed(done),.native_ret(ret),.fault(flt));
 integer sh_mism,sh_cmp;
 n59_split_shadow #(.NU(NU),.MCTX(MCTX),.EMBR(1),.MUT(SPLIT_MUT),.QB_MUT(QB_MUT),.LP_MUT(LP_MUT),.SOFF(SPL_SOFF),.BOFF(SPL_BOFF),.ROFF(SPL_ROFF)) shadow(
  .ck(clk),.rst_n(rst_n),.cmp_en(cmp_en),.host_epoch_valid(hev),.host_fused_capability(hfc),.host_epoch(he),.host_tag(ht),.host_generation(hg),
  .layer_context_v(lcv),.command_stage(stage),.native_token(tok),.native_position(pos),.native_cmd(cmd),.dd_i(dd),
  .kv_word_slot(kvs),.kv_word_index(kvi),.kv_x3_slot(x3s),.q_slot(qs),.q_slot_beat(qb),.tx_slot(ts),.tx_slot_kind(tk),.tx_slot_beat(tb),
  .native_rx_v(rv),.native_rx_payload(rp),.rx_slot(rs),.rx_slot_kind(rk),.rx_slot_beat(rb),.emb_code_q(ecq),.emb_scale_q(esq),
  .visibility_slot(vis),.complete_slot(cs),
  .r_x3(x3),.r_x3_identity(xid),.r_x3_generation(xg),.r_native_tx_v(tv),.r_native_tx_payload(td),.r_dr_o(dr),.r_emb_code_re(cre),
  .r_emb_code_addr(caddr),.r_emb_scale_re(sre),.r_emb_scale_addr(saddr),.r_completed(done),.r_native_ret(ret),.r_fault(flt),
  .mism(sh_mism),.compared(sh_cmp));

 // INTERNAL probes (the sticky fault saturates the outputs under random stimulus; the per-edge fault causes, the Q
 // word, the formatter face and the bank state do not): service internals ROFF edges, bank internals BOFF edges after r1
`ifdef N59_SPLIT_LP
 `define N59_SH shadow.u_split
`else
 `define N59_SH shadow.u_split
`endif
 localparam integer PW=1+1+1+1+1+524+64+1536+2048+1+1+1+1+512+1+512;
 wire[PW-1:0]pr_ref={ref0.u_core.dd_form_bad,ref0.u_core.q_in_bad,ref0.u_core.kv_in_bad,ref0.u_core.q_miss,ref0.u_core.q_committed,
  ref0.u_core.q,ref0.u_core.kv_we,ref0.u_core.kv_waddr,ref0.u_core.kv_wdata,ref0.u_core.begin_slot,ref0.u_core.request_slot,
  ref0.u_core.src_fault,ref0.u_core.vm_write_v,ref0.u_core.vm_write_data,ref0.u_core.kvn_v,ref0.u_core.kvn_data};
 wire[PW-1:0]pr_spl={`N59_SH.u_svc.dd_form_bad,`N59_SH.u_svc.q_in_bad,`N59_SH.u_svc.kv_in_bad,`N59_SH.u_svc.q_miss,`N59_SH.u_svc.q_committed,
  `N59_SH.u_svc.q,`N59_SH.u_svc.kv_we,`N59_SH.u_svc.kv_waddr,`N59_SH.u_svc.kv_wdata,`N59_SH.u_svc.begin_slot,`N59_SH.u_svc.request_slot,
  `N59_SH.u_svc.src_fault,`N59_SH.u_svc.vm_write_v,`N59_SH.u_svc.vm_write_data,`N59_SH.u_svc.kvn_v,`N59_SH.u_svc.kvn_data};
 localparam integer BW_=512+1+512;
 wire[BW_-1:0]pb_ref={ref0.u_core.qseen,ref0.u_core.qctx,ref0.u_core.qrow};
 wire[BW_-1:0]pb_spl={`N59_SH.u_qb.qseen,`N59_SH.u_qb.qctx,`N59_SH.u_qb.qrow};
 reg[PW-1:0]pr_d[1:SPL_ROFF];
 always @(posedge clk)begin pr_d[1]<=pr_ref;for(integer j=2;j<=SPL_ROFF;j=j+1)pr_d[j]<=pr_d[j-1];end
 wire[BW_-1:0]pb_dl;
 generate if(SPL_BOFF==0)begin:g_pb0 assign pb_dl=pb_ref; end else begin:g_pbd
  reg[BW_-1:0]pb_d[1:SPL_BOFF];
  always @(posedge clk)begin pb_d[1]<=pb_ref;for(integer j=2;j<=SPL_BOFF;j=j+1)pb_d[j]<=pb_d[j-1];end
  assign pb_dl=pb_d[SPL_BOFF];
 end endgenerate
 integer pmis=0,bmis=0,pcmp=0,n_qw=0,n_kv=0,n_bad=0;
 always @(posedge clk)if(cmp_en)begin
  pcmp<=pcmp+1;
  if(pr_spl!==pr_d[SPL_ROFF])begin pmis<=pmis+1;if(pmis<6)$display("N59RND_PROBE_ERR cycle %0d: service internals != r1 %0d edges earlier",cyc,SPL_ROFF);end
  if(pb_spl!==pb_dl)begin bmis<=bmis+1;if(bmis<6)$display("N59RND_PROBE_ERR cycle %0d: bank internals != r1 %0d edges earlier",cyc,SPL_BOFF);end
  n_qw<=n_qw+ref0.u_core.q[523];n_kv<=n_kv+(|ref0.u_core.kv_we);n_bad<=n_bad+(ref0.u_core.q_in_bad||ref0.u_core.dd_form_bad||ref0.u_core.kv_in_bad);
 end
 // activity (the comparison means something only if the reference does things)
 integer n_tx=0,n_x3=0,n_dr0=0,n_dr1=0,n_done=0,n_flt=0,n_ret=0;reg[94:0]ret_d=0;
 always @(posedge clk)if(cmp_en)begin
  n_tx<=n_tx+tv;n_x3<=n_x3+x3[523];n_dr0<=n_dr0+(dr[519]&&!dr[518]);n_dr1<=n_dr1+(dr[519]&&dr[518]);n_done<=n_done+done;
  n_flt<=n_flt+flt;ret_d<=ret;n_ret<=n_ret+(ret!=ret_d);
 end
 always @(posedge clk)if(cyc==CYCLES)begin
  $display("N59RND activity: tx %0d x3 %0d dr0 %0d dr1 %0d done %0d fault-edges %0d ret-changes %0d q-words %0d kv-writes %0d bad-dd %0d; compared %0d mism %0d probes %0d/%0d (svc/bank mism) of %0d",
           n_tx,n_x3,n_dr0,n_dr1,n_done,n_flt,n_ret,n_qw,n_kv,n_bad,sh_cmp,sh_mism,pmis,bmis,pcmp);
  if(sh_mism!=0||pmis!=0||bmis!=0||sh_cmp<CYCLES/2)begin $display("N59RND_FAIL seed %0d: %0d of %0d edges differ (outputs), probes %0d/%0d",SEED,sh_mism,sh_cmp,pmis,bmis);$fatal(1);end
  $display("N59RND_PASS seed %0d NU %0d MCTX %0d: %0d random edges, every output of the split == r1 (SOFF %0d BOFF %0d ROFF %0d)",SEED,NU,MCTX,sh_cmp,SPL_SOFF,SPL_BOFF,SPL_ROFF);
  $finish;
 end
endmodule
