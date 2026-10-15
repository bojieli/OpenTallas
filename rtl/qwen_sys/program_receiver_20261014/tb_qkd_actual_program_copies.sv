`timescale 1ns/1ps
// Minimum actual TT+SU parent write-path proof. No engine start is issued;
// arithmetic, actual native token execution and physical phases are not tested.
module tb_qkd_actual_program_copies;
 reg ck=0;always #1 ck=~ck;reg rst_n=0,beg=0,auth=0,pv=0,dv=0;
 reg[9:0]pa=0;reg[2:0]da=0;reg[63:0]pd=0,dd=0;reg[63:0]image[0:1023];
 wire[75:0]tt_obs,su_obs;wire[68:0]desc_obs,tt_desc;
 wire me_ready,su_ready,xready,xmready,xfault;wire all_stores=me_ready&&su_ready&&xready&&xmready&&!xfault;wire[1:0]rdy,flt,cap;wire[31:0]ep;wire[127:0]dg;
 wire cv,ready,fault,fused;wire[15:0]epoch;wire[63:0]digest;
 reg[63:0]expected;integer mut=0,n,tc=0,sc=0,dc=0,commits=0;string path;
 wire xc,xv,xs;wire[2:0]xi;wire[187:0]xd;wire[3:0]xn;wire[5:0]xstage;wire[31:0]xstop;
 ot_qfd_xpf_dense_pw_loader xload(.clk(ck),.rst_n(rst_n),.stage_active(1'b0),.pw_v(tt.q_pw_v),.pw_addr(tt.q_pw_addr),.pw_data(tt.q_pw_data),.cfg_clear(xc),.cfg_v(xv),.cfg_seal(xs),.cfg_index(xi),.cfg_data(xd),.cfg_count(xn),.stage(xstage),.stop_cycle(xstop),.image_ready(xready),.fault(xfault));
 ot_qfd_xpf_static_schedule #(.N(4),.ARM_TRANSPORT_EDGES(13))xstore(.clk(ck),.rst_n(rst_n),.cfg_clear(xc),.cfg_v(xv),.cfg_seal(xs),.cfg_index(xi[1:0]),.cfg_data(xd),.cfg_count(xn[2:0]),.start(1'b0),.stop(1'b0),.stage(xstage),.me_issue(1'b0),.me_pc(12'd0),.su_issue(1'b0),.su_pc(12'd0),.cp_issue(1'b0),.cp_pc(12'd0),.image_ready(xmready),.fault());
 wire tt_pv=pv&&!(mut==1&&pa==53);
 wire su_pv=pv&&!(mut==2&&pa==53);
 qfd_tt_ctlm_head_static #(.PSRAM(1),.DENSE_IMAGE(1))tt(
  .clk(ck),.ck_sched(ck),.rst_n(rst_n),.h_start(1'b0),.token(18'd1),.pos(18'd7),.prog_base(12'd0),
  .pw_v(tt_pv),.pw_addr(pa),.pw_data(pd),.x_oacc(24'd0),.x_oidle(1'b1),.x_oprog(16'hffff),.x_orows(16'hffff),
  .kv_ok(1'b1),.kv_write_drained(1'b1),.me_mem_ok(1'b0),.cp_active(1'b0),.ret(95'd3),.program_obs(tt_obs),.me_image_ready(me_ready));
 ot_qfd_seq_su_bi_static #(.PSRAM(1))su(
  .clk(ck),.ck_sched(ck),.rst_n(rst_n),.h_start(1'b0),.stage_in(6'd37),.cb_st_rdy(1'b1),.cb_st_rdy_stage(6'd37),
  .tp_token(18'd1),.tp_pos(18'd7),.kv_write_drained(1'b1),.vm_rq(512'd0),.vm_rvalid(1'b0),
  .c_ready(1'b1),.r_valid(1'b0),.r_data(512'd0),.r_last(1'b0),.r_rank(3'd0),.r_err(1'b0),
  .pw_v(su_pv),.pw_addr(pa),.pw_data(pd),.dw_v(dv&&!(mut==3&&da==7)),.dw_addr(da),.dw_data(dd),
  .pi_su_rt_active(1'b0),.pi_su_rt_inflight(8'd0),.pi_su_ready(1'b1),.pi_su_idle(1'b1),
  .pi_su_wrom_re(1'b0),.pi_su_wrom_addr(24'd0),.pi_su_kv_we(64'd0),.pi_su_progress(16'd0),.pi_su_progress_rows(16'd0),
  .pi_su_fault(1'b0),.x_oacc(24'd0),.x_oidle(1'b1),.x_oprog(16'hffff),.x_ofin(1'b0),.x_fidx(18'd0),.x_fval(32'd0),.pi_su_acc(24'd0),
  .program_obs(su_obs),.descriptor_obs(desc_obs),.cfg_image_ready(su_ready));
 // TT's actual input bank-register stage is one edge deeper than SU's. Retiming
 // the genuine descriptor receipt preserves its data and count; no write or ACK
 // is inferred, and no program issue/replay is stalled.
 qkd_program_descriptor_receipt_relay relay(ck,rst_n,desc_obs,tt_desc);
 wire[75:0]po[0:1];wire[68:0]de[0:1];assign po[0]=tt_obs;assign po[1]=su_obs;assign de[0]=tt_desc;assign de[1]=desc_obs;
 for(genvar i=0;i<2;i=i+1)begin:g_ledger
  qkd_program_commit ledger(.ck(ck),.rst_n(rst_n),.execution_active(1'b0),.control_stores_ready(all_stores),
   .begin_v(beg),.begin_epoch(16'h42b1),.expected_pw(11'd1024),.expected_dw(4'd8),.auth_v(auth),.auth_epoch(16'h42b1),.auth_digest(expected),
   .pw_v(po[i][75]),.pw_addr(po[i][73:64]),.pw_data(po[i][63:0]),.pw_full_word(po[i][74]),
   .dw_v(de[i][68]),.dw_addr(de[i][66:64]),.dw_data(de[i][63:0]),.dw_full_word(de[i][67]),
   .ready(rdy[i]),.fault(flt[i]),.installed_fusedcap(cap[i]),.commit_epoch(ep[16*i+:16]),.commit_digest(dg[64*i+:64]));
 end
 qkd_program_commit_join joiner(.ck(ck),.rst_n(rst_n),.begin_v(beg),.auth_v(auth),.execution_active(1'b0),.control_stores_ready(all_stores),
  .auth_epoch(16'h42b1),.auth_digest(expected),.sink_ready(rdy),.sink_fault(flt),.sink_fusedcap(cap),.sink_epoch(ep),.sink_digest(dg),
  .commit_v(cv),.ready(ready),.fault(fault),.installed_fusedcap(fused),.commit_epoch(epoch),.commit_digest(digest));
 always @(negedge ck)begin
  if(cv)commits=commits+1;
  if(tt_obs[75])begin
   tc=tc+1;if(!tt_obs[74])$fatal(1,"TTpartialwrite");
   if(tt_obs[67])begin if(tt.g_psram.g_m[1].u_pm.arr[tt_obs[73:68]][64*tt_obs[66:64]+:64]!==tt_obs[63:0])$fatal(1,"TT1readback");end
   else if(tt.g_psram.g_m[0].u_pm.arr[tt_obs[73:68]][64*tt_obs[66:64]+:64]!==tt_obs[63:0])$fatal(1,"TT0readback");
  end
  if(su_obs[75])begin
   sc=sc+1;if(!su_obs[74])$fatal(1,"SUpartialwrite");
   if(su_obs[67])begin if(su.g_psram.g_m[1].u_pm.arr[su_obs[73:68]][64*su_obs[66:64]+:64]!==su_obs[63:0])$fatal(1,"SU1readback");end
   else if(su.g_psram.g_m[0].u_pm.arr[su_obs[73:68]][64*su_obs[66:64]+:64]!==su_obs[63:0])$fatal(1,"SU0readback");
  end
  if(desc_obs[68])begin dc=dc+1;if(su.desc_mem[desc_obs[66:64]]!==desc_obs[63:0])$fatal(1,"actualDWreadback");end
 end
 initial begin
  if(!$value$plusargs("IMAGE=%s",path))$fatal(1,"actualsourceimage required");$readmemh(path,image);
  if(!$value$plusargs("MUT=%d",mut))mut=0;
  expected=64'h51484f5354505247;
  for(n=0;n<1024;n=n+1)expected={expected[56:0],expected[63:57]}^image[n]^{54'd0,10'(n)};
  for(n=0;n<8;n=n+1)expected={expected[56:0],expected[63:57]}^{53'd0,1'b1,10'(n)};
  repeat(6)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);beg=1;@(negedge ck);beg=0;auth=1;@(negedge ck);auth=0;
  for(n=0;n<1024;n=n+1)begin pv=1;pa=10'(n);pd=image[n];@(negedge ck);end
  pv=0;for(n=0;n<8;n=n+1)begin dv=1;da=3'(n);dd=0;@(negedge ck);end
  dv=0;repeat(16)@(negedge ck);
  if(mut==0)begin
   if(!ready||fault||fused||epoch!=16'h42b1||digest!=expected||commits!=1||tc!=1024||sc!=1024||dc!=8)$fatal(1,"actualcopyjoin ready%0b fault%0b caps%0b seals%0b%0b counts%0d/%0d/%0d",ready,fault,cap,me_ready,su_ready,tc,sc,dc);
   $display("PASS actual_TT_SU_PSRAM1_two_copy_commit 1024PW_each8DW allactualreadback epoch_digest authsourcefixture_cap0");
   rst_n=0;repeat(4)@(negedge ck);
   if(ready||(|rdy)||fused||me_ready||su_ready||xready||xmready)$fatal(1,"reset left staleinstalledwitness");
   $display("PASS actual_native_reset_revokes_image_seals_and_receiver_valid reload_required");
  end else begin
   if(ready||fused||commits)$fatal(1,"badactualcopy committed%0d",mut);
   $display("PASS actual_copy_missing_write_rejected%0d TT%0d SU%0d DW%0d",mut,tc,sc,dc);
  end
  $finish;
 end
endmodule
