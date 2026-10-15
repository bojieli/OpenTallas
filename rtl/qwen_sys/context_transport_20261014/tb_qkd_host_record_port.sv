`timescale 1ns/1ps
// Real HOST loader -> registered physical SRAM inputs -> actual SRAM model and
// consumed-write ledger. Expected data is used for external authorization and
// readback assertions only; it never supplies the replay or sink write values.
module tb_qkd_host_record_port;
 reg ck=0;always #1 ck=~ck;reg rst_n=0,beg=0,wv=0,desc=0,seal=0,auth=0;
 reg[9:0]wa=0;reg[63:0]wd=0;wire[142:0]pr;wire lr,lf;wire[63:0]ld;wire[15:0]le;
 reg[63:0]expected_digest;integer mut=0,n,s,commits=0;
 qkd_host_program_loader loader(.ck(ck),.rst_n(rst_n),.begin_image(beg),.image_epoch(16'h42a1),
  .pw_count(11'd1024),.dw_count(4'd8),.word_v(wv),.word_desc(desc),.word_addr(wa),.word_data(wd),
  .seal(seal),.auth_v(auth),.auth_epoch(16'h42a1),.auth_digest(expected_digest),.execution_active(1'b0),
  .pr(pr),.program_ready(lr),.fault(lf),.digest(ld),.program_epoch(le),.authorized_footer_valid(footer_v),.authorized_footer(footer));
 wire footer_v;wire[63:0]footer;
 reg[1:0]send_kind=0;reg witness_slot=0;
 wire tv,to,tf,cvh,installed,icap;wire[547:0]tx,wr;wire wvout,wo,wf;
 wire[15:0]ceh;wire[63:0]cdh;
 qkd_host_record_port host(.ck(ck),.rst_n(rst_n),.send_kind(send_kind),
 .request_v(1'b0),.request_tag(59'd0),.request_gen(2'd0),.request_token(18'd0),.request_position(18'd0),
 .token_epoch_valid(1'b0),.token_epoch(16'd0),
 .begin_v(beg),.begin_epoch(16'h42a1),.expected_pw(11'd1024),.expected_dw(4'd8),
 .auth_v(auth),.auth_epoch(16'h42a1),.auth_digest(expected_digest),
 .program_ready(lr),.program_epoch(le),.program_digest(ld),
 .authorized_footer_valid(footer_v),.authorized_footer(footer),
 .witness_slot(witness_slot),.rx_v(wvout),.rx_record(wr^(mut==6?(548'd1<<64):548'd0)),
 .commit_v(cvh),.installed_valid(installed),.installed_fusedcap(icap),.commit_epoch(ceh),.commit_digest(cdh),
 .tx_v(tv),.tx_observed_v(to),.tx_record(tx),.fault(tf));
 wire rb,rauth,rf;wire[15:0]re,rae;wire[10:0]rnp;wire[3:0]rnd;wire[63:0]rad;
 reg receive_slot=0;always @(posedge ck)receive_slot<=send_kind==1||send_kind==2;
 reg decode_slot=0;always @(posedge ck)decode_slot<=receive_slot;
 reg send_witness=0;
 wire ready2,fault2,cap2,cv2;wire[15:0]epoch2;wire[63:0]digest2;
 reg[151:0]actual_program_obs=0;reg[137:0]actual_descriptor_obs=0;
 always @(posedge ck)begin actual_program_obs<={pv2,pfull2,pa2,pd2,pv,pfull,pa,pd};actual_descriptor_obs<={dv2,1'b1,da2,dd2,dv,1'b1,da,dd};end
 wire joined_ready,joined_cap,joined_commit,jhev;wire[15:0]joined_epoch,jhe;wire[63:0]joined_digest;wire[58:0]jht;wire[1:0]jhg;
 qfd_program_record_port rx(.ck(ck),.rst_n(rst_n),.auth_slot(decode_slot),.context_slot(1'b0),.witness_slot(send_witness),
 .rx_v(tv),.rx_record(tx^(mut==5&&tx[1:0]==2?(548'd1<<2):548'd0)),
 .execution_active(1'b0),.cfg_image_ready(2'b11),
 .program_obs2(actual_program_obs),.descriptor_obs(actual_descriptor_obs[137:69]),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),
 .begin_v(rb),.begin_epoch(re),.expected_pw(rnp),.expected_dw(rnd),.auth_v(rauth),.auth_epoch(rae),.auth_digest(rad),
 .program_ready(joined_ready),.installed_fusedcap(joined_cap),.commit_v(joined_commit),.program_epoch(joined_epoch),.program_digest(joined_digest),
 .host_epoch_valid(jhev),.host_epoch(jhe),.host_tag(jht),.host_gen(jhg),.tx_v(wvout),.tx_observed_v(wo),.tx_record(wr),.fault(rf));
 assign wf=rf;
 // Actual related-clock relay flops delay data by four edges; no modeled memory.
 reg[142:0]p0=0,p1=0,p2=0,p3=0;
 always @(posedge ck)begin p0<=pr;p1<=p0;p2<=p1;p3<=p2;end
 reg[1:0]ce=0;reg[11:0]row=0;reg[1023:0]md=0,mask=0;
 reg dv=0;reg[2:0]da=0;reg[63:0]dd=0;
 always @(posedge ck)begin
  if(!rst_n)begin ce<=0;dv<=0;end else begin
   ce<=(p3[74]&&!(mut==1&&p3[73:64]==53))?(2'b1<<p3[67]):0;
   row<={p3[73:68],p3[73:68]};md<={16{p3[63:0]}};
   mask<=({960'd0,64'hffffffffffffffff}<<(64*p3[66:64]+512*p3[67]));
   if(mut==2&&p3[74]&&p3[73:64]==53)md<={16{p3[63:0]^64'h1}};
   if(mut==3&&p3[74]&&p3[73:64]==53)mask<=({960'd0,64'hfffffffffffffffe}<<(64*p3[66:64]+512*p3[67]));
   dv<=p3[142]&&!(mut==4&&p3[141:139]==7);da<=p3[141:139];dd<=p3[138:75];
  end
 end
 wire pv,pfull;wire[9:0]pa;wire[63:0]pd;
 qkd_program_pw_observer observe(ce,row,md,mask,pv,pa,pd,pfull);
 wire cv,ready,fault,cap;wire[15:0]epoch;wire[63:0]digest;
 qkd_program_commit ledger(.ck(ck),.rst_n(rst_n),.execution_active(1'b0),.control_stores_ready(1'b1),
  .begin_v(rb),.begin_epoch(re),.expected_pw(rnp),.expected_dw(rnd),
  .auth_v(rauth),.auth_epoch(rae),.auth_digest(rad),
  .pw_v(pv),.pw_addr(pa),.pw_data(pd),.pw_full_word(pfull),.dw_v(dv),.dw_addr(da),.dw_data(dd),.dw_full_word(1'b1),
  .commit_v(cv),.ready(ready),.fault(fault),.installed_fusedcap(cap),.commit_epoch(epoch),.commit_digest(digest));
 reg rce=0;reg[5:0]ra=0;wire[1023:0]rd;
 for(genvar b=0;b<2;b=b+1)begin:g_memory
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(ck),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rd[512*b+:512]),
   .w_ce_in(ce[b]),.w_addr_in(row[6*b+:6]),.wd_in(md[512*b+:512]),.w_mask_in(mask[512*b+:512]),
   .rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(18'd0));
 end
 // Second real TT/SU program copy: independent consumed-macro pins and ledger.
 reg[1:0]ce2=0;reg[11:0]row2=0;reg[1023:0]md2=0,mask2=0;
 reg dv2=0;reg[2:0]da2=0;reg[63:0]dd2=0;
 always @(posedge ck)begin
 if(!rst_n)begin ce2<=0;dv2<=0;end else begin
 ce2<=(p3[74]&&!(mut==7&&p3[73:64]==53))?(2'b1<<p3[67]):0;
 row2<={p3[73:68],p3[73:68]};md2<={16{p3[63:0]}};
 mask2<=({960'd0,64'hffffffffffffffff}<<(64*p3[66:64]+512*p3[67]));
 dv2<=p3[142];da2<=p3[141:139];dd2<=p3[138:75];end
 end
 wire pv2,pfull2;wire[9:0]pa2;wire[63:0]pd2;
 qkd_program_pw_observer observe2(ce2,row2,md2,mask2,pv2,pa2,pd2,pfull2);
 qkd_program_commit ledger2(.ck(ck),.rst_n(rst_n),.execution_active(1'b0),.control_stores_ready(1'b1),
 .begin_v(rb),.begin_epoch(re),.expected_pw(rnp),.expected_dw(rnd),.auth_v(rauth),.auth_epoch(rae),.auth_digest(rad),
 .pw_v(pv2),.pw_addr(pa2),.pw_data(pd2),.pw_full_word(pfull2),.dw_v(dv2),.dw_addr(da2),.dw_data(dd2),.dw_full_word(1'b1),
 .commit_v(cv2),.ready(ready2),.fault(fault2),.installed_fusedcap(cap2),.commit_epoch(epoch2),.commit_digest(digest2));
 wire[1023:0]rd2;reg[63:0]dm2[0:7];always @(posedge ck)if(dv2)dm2[da2]<=dd2;
 for(genvar b2=0;b2<2;b2=b2+1)begin:g_memory_copy2
 ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(ck),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rd2[512*b2+:512]),
 .w_ce_in(ce2[b2]),.w_addr_in(row2[6*b2+:6]),.wd_in(md2[512*b2+:512]),.w_mask_in(mask2[512*b2+:512]),
 .rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(18'd0));
 end
 always @(negedge ck)if(cv)commits=commits+1;
 function automatic[63:0]word(input integer i);
  word=i==1023?64'h5850463100001006:64'hbd51a94f3862ec70^(64'(i)*64'h81d07934baf16705);
 endfunction
 initial begin
  if(!$value$plusargs("MUT=%d",mut))mut=0;
  expected_digest=64'h51484f5354505247;
  for(n=0;n<1032;n=n+1)expected_digest={expected_digest[56:0],expected_digest[63:57]}^word(n)^{53'd0,1'(n>=1024),10'(n>=1024?n-1024:n)};
  repeat(4)@(negedge ck);rst_n=1;beg=1;@(negedge ck);beg=0;
  repeat(2)@(negedge ck);send_kind=1;@(negedge ck);send_kind=0;
  for(n=0;n<1032;n=n+1)begin wv=1;desc=n>=1024;wa=10'(desc?n-1024:n);wd=word(n);@(negedge ck);end
  wv=0;seal=1;@(negedge ck);seal=0;auth=1;@(negedge ck);auth=0;
  repeat(2)@(negedge ck);send_kind=2;@(negedge ck);send_kind=0;
  // Fixed maximum observation horizon is only a bench assertion deadline. The
  // hardware emits commit solely from actual1032consumed writes, never a timer.
  repeat(1060)@(negedge ck);
  if(lf||!lr)$fatal(1,"actual HOST loader failed normal authorization/replay");
  if(mut==0||mut>=5)begin
   send_witness=1;@(negedge ck);send_witness=0;witness_slot=1;@(negedge ck);witness_slot=0;repeat(2)@(negedge ck);
   if(mut>=5)begin
    if(installed||icap||(!tf&&!wf&&!fault))$fatal(1,"typed metadata/witness mutant accepted %0d",mut);
    $display("PASS real_HOST_loader_typed_record_mutant_rejected %0d",mut);$finish;
   end
   if(!installed||!icap||ceh!=le||cdh!=ld||tf||wf||rf)$fatal(1,"HOST typed mismatch installed%0b cap%0b hostep%h/%h digest%h/%h tf%0b wf%0b rf%0b ready%0b fault%0b cv%0b footer%0b/%h",installed,icap,ceh,le,cdh,ld,tf,wf,rf,ready,fault,cv,footer_v,footer);
   if(!ready||fault||!cap||commits!=1||epoch!=16'h42a1||digest!=expected_digest)$fatal(1,"actual producer/sink witness mismatch");
   rce=1;for(n=0;n<64;n=n+1)begin ra=6'(n);@(negedge ck);@(negedge ck);
    for(s=0;s<16;s=s+1)if(rd[64*s+:64]!==word(16*n+s)||rd2[64*s+:64]!==word(16*n+s))$fatal(1,"real loader -> actual SRAM readback mismatch");end
   for(n=0;n<8;n=n+1)if(dm2[n]!==word(1024+n))$fatal(1,"actual DW write mismatch");
   $display("PASS real_HOST_loader_kind13_actual_macro_kind14_HOST_commit 2x1024PW_singleSU8DW actual4SRAM_readback cap_epoch_digest");
  end else begin
   if(ready||cap||commits)$fatal(1,"actual sink mutant accepted%0d",mut);
   if(mut!=4&&!fault)$fatal(1,"actual sink mutant missedfault%0d",mut);
   $display("PASS real_HOST_loader_sink_mutant_rejected%0d fault%0d",mut,fault);
  end
  $finish;
 end
endmodule
