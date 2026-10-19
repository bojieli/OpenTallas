`timescale 1ns/1ps
// Stimulus-file bench for the default-off finite FF WTN1 witness controller
// composed with the typed SU observer (command issue -> observation +1 -> check +2).
// Lines: "<edge> <kind> <a> <b> <c> <d> <e>"; kinds:
//  0 PW addr data_hi data_lo   1 AUTH level   2 PROFILE digest_hi digest_lo epoch fusedcap
//  3 START user stage epoch    4 ISSUE user slice pidx stage epoch   5 RETIRE user mexpf
//  9 END
module tb_qwen_typed_witness_control #(parameter integer EN=1,SAFE=0,PAIR=0,SELECT=0);
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg pw_v=0;reg[9:0]pw_addr=0;reg[63:0]pw_data=0;reg auth=0,fusedcap=0;reg[63:0]dig=0;reg[15:0]pep=0;
 reg start_v=0;reg[1:0]start_user=0;reg[5:0]start_stage=0;reg[15:0]start_epoch=0;
 reg retire_v=0;reg[1:0]retire_user=0;reg mexpf=0;
 reg su_issue=0;reg[1:0]cmd_user=0;reg[8:0]su_pidx=0;reg[3:0]cmd_slice=0;
 reg[5:0]ev_stage=0,ev_stage_n=0;reg[15:0]ev_epoch=0,ev_epoch_n=0;
 wire[15:0]observation;wire obs_fault;
 wire template_ready;wire[3:0]context_active,all_complete;wire group_complete;wire[1:0]complete_user;wire[3:0]complete_group;wire fault;
 qfd_dv_typed_su_observer #(.ENABLE(EN)) obs(.ck(ck),.rst_n(rst_n),.su_issue(su_issue),.cmd_user(cmd_user),.su_pidx(su_pidx),.cmd_slice(cmd_slice),.observation(observation),.fault(obs_fault));
 qfd_dv_typed_witness_control #(.ENABLE(EN),.SAFE_COMPARE(SAFE),.SAFE_SELECT(SELECT)) dut(.ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),
  .all_copies_authenticated(auth),.fusedcap(fusedcap),.installed_digest(dig),.installed_epoch(pep),
  .start_v(start_v),.start_user(start_user),.start_stage(start_stage),.start_epoch(start_epoch),
  .retire_v(retire_v),.retire_user(retire_user),.ME_XPF_retired(mexpf),
  .observation(observation),.event_stage(ev_stage),.event_epoch(ev_epoch),
  .template_ready(template_ready),.context_active(context_active),.all_witnesses_complete(all_complete),
  .group_complete(group_complete),.complete_user(complete_user),.complete_group(complete_group),.fault(fault));
 generate if(PAIR)begin:refcheck
 wire rready,rgroup,rfault;wire[3:0]ractive,rall;wire[1:0]ru;wire[3:0]rg;
 qfd_dv_typed_witness_control #(.ENABLE(EN),.SAFE_COMPARE(0)) reference_dut(
 .ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),
 .all_copies_authenticated(auth),.fusedcap(fusedcap),.installed_digest(dig),.installed_epoch(pep),
 .start_v(start_v),.start_user(start_user),.start_stage(start_stage),.start_epoch(start_epoch),
 .retire_v(retire_v),.retire_user(retire_user),.ME_XPF_retired(mexpf),
 .observation(observation),.event_stage(ev_stage),.event_epoch(ev_epoch),
 .template_ready(rready),.context_active(ractive),.all_witnesses_complete(rall),
 .group_complete(rgroup),.complete_user(ru),.complete_group(rg),.fault(rfault));
 integer overflow_injected=0,overflow_checked=0,overflow_slot=0,oi;
 always @(negedge ck)if($test$plusargs("OVERFLOW")&&!overflow_injected&&dut.pending)begin
  // Change the same pending record in both controllers, exercising the actual
  // cache publication edge with an unsigned carry beyond the 13-bit counter.
  dut.templates[dut.pending_group][12:0]=13'd8190;
  reference_dut.templates[dut.pending_group][12:0]=13'd8190;
  for(oi=0;oi<12;oi=oi+1)begin
   dut.templates[dut.pending_group][34+8*oi+:8]=8'd255;
   reference_dut.templates[dut.pending_group][34+8*oi+:8]=8'd255;
  end
  overflow_slot=2*dut.pending_user+dut.pending_slot;overflow_injected=1;$display("F16_INJECT_OVERFLOW expected_due=253");
 end
 always @(posedge ck)begin
 #0.1;
 if(overflow_injected&&!overflow_checked&&dut.cache_valid[overflow_slot])begin
  for(oi=0;oi<12;oi=oi+1)if(dut.cache_due[overflow_slot][oi]!==13'd253)$fatal(1,"F16_DUE_OVERFLOW_MISMATCH");
  overflow_checked=1;$display("F16_ACTUAL_CACHE_OVERFLOW_PASS due=253");
 end
 if(rst_n&&{template_ready,context_active,all_complete,group_complete,complete_user,complete_group,fault}!==
 {rready,ractive,rall,rgroup,ru,rg,rfault})$fatal(1,"F16_STRUCTURAL_EDGE_MISMATCH");
 end
 end endgenerate
 integer mech_injected=0,mi;
 always @(negedge ck)if(SAFE&&EN&&!mech_injected&&dut.cache_valid[0])begin
  if($test$plusargs("SKEW"))begin
   dut.cycle[0][0]=dut.cycle[0][0]+13'd1;mech_injected=1;$display("F16_INJECT_COUNTER_SKEW");
  end
  if($test$plusargs("DUE_CORRUPT"))begin
   for(mi=0;mi<12;mi=mi+1)if(!mech_injected&&dut.cache_mask[0][mi])begin
    dut.cache_due[0][mi]=dut.cache_due[0][mi]+13'd1;mech_injected=1;$display("F16_INJECT_DUE_CORRUPT slice=%0d",mi);
   end
  end
 end
 integer select_injected=0,si,sj;reg[12:0] select_coverage=0;reg[7:0] bank_coverage=0;reg[3:0] user_coverage=0;integer consecutive=0;reg previous_pending=0;
 generate if(SELECT)begin:inject_sectors
 for(genvar xi=0;xi<15;xi=xi+1)begin:select_fault
  reg done=0;
  always@(negedge ck)if(dut.pending&&!done)begin
   if($test$plusargs("SELECT_WRONG"))begin dut.gs.sel[xi].ff.q=13'b1<<((dut.pending_group+1)%13);done=1;end
   if($test$plusargs("SELECT_CLEAR"))begin dut.gs.sel[xi].ff.q=0;done=1;end
  end
 end
 for(genvar xi=0;xi<8;xi=xi+1)begin:bank_fault
 for(genvar xj=0;xj<14;xj=xj+1)begin:sector_fault
  reg done=0;
  always@(negedge ck)if(dut.pending&&!done&&$test$plusargs("BANK_WRONG"))begin
   dut.gs.bank[xi].sector[xj].ff.q=(xi==((2*dut.pending_user+dut.pending_slot+1)%8));done=1;
  end
 end end
 end endgenerate
 always@(negedge ck)if(SELECT&&dut.pending&&!select_injected)begin
  if($test$plusargs("SELECT_WRONG"))begin
   
   select_injected=1;$display("F16_SELECT_WRONG_INJECT");
  end
  if($test$plusargs("SELECT_CLEAR"))begin
   
   select_injected=1;$display("F16_SELECT_CLEAR_INJECT");
  end
  if($test$plusargs("BANK_WRONG"))begin
   
   select_injected=1;$display("F16_BANK_WRONG_INJECT");
  end
  if($test$plusargs("RESET_CLEAR"))begin
   rst_n=0;select_injected=1;#0.1;
   for(si=0;si<15;si=si+1)if(dut.template_select[si]!==0)$fatal(1,"F16_RESET_SELECT_NOT_CLEAR");
   for(si=0;si<8;si=si+1)for(sj=0;sj<14;sj=sj+1)if(dut.publish_enable[si][sj]!==0)$fatal(1,"F16_RESET_BANK_NOT_CLEAR");
   if(dut.pending!==0||dut.cache_valid!==0||template_ready!==0)$fatal(1,"F16_RESET_OWNERSHIP_NOT_CLEAR");
   $display("F16_PENDING_ASYNC_CLEAR_PASS");$finish;
  end
 end
 always@(posedge ck)begin
 #0.1;
 if(SELECT&&$test$plusargs("CHECK_SECTORS")&&rst_n)begin
  if(dut.pending)begin
   select_coverage[dut.pending_group]=1;bank_coverage[2*dut.pending_user+dut.pending_slot]=1;user_coverage[dut.pending_user]=1;
   if(previous_pending)consecutive++;
  end
  for(integer vi=0;vi<15;vi=vi+1)
   if(dut.template_select[vi]!== (dut.pending?(13'b1<<dut.pending_group):13'd0))$fatal(1,"F16_SECTOR_GROUP_PHASE_FAIL");
  for(integer vi=0;vi<8;vi=vi+1)for(integer vj=0;vj<14;vj=vj+1)
   if(dut.publish_enable[vi][vj]!== (dut.pending&&vi==2*dut.pending_user+dut.pending_slot))$fatal(1,"F16_SECTOR_BANK_PHASE_FAIL");
  previous_pending=dut.pending;
 end
 end
 final begin
 if(SELECT&&$test$plusargs("CHECK_SECTORS"))begin
  $display("F16_SELECT_COVERAGE groups=%h banks=%h users=%h consecutive=%0d",select_coverage,bank_coverage,user_coverage,consecutive);
  if(select_coverage!==13'h1fff||bank_coverage!==8'hff||user_coverage!==4'hf||consecutive==0)$error("F16_SELECT_COVERAGE_FAIL");
 end
 end
 integer fd,r,edge_i,t,kind,completions,retired,first_fault,ready_seen,starts,maxlive;reg[63:0]a,b,c,d,e;reg done,have;
 reg[3:0]ngrp[0:3];integer q;
 initial begin
  string f;if(!$value$plusargs("STIM=%s",f))$fatal(1,"no +STIM");
  fd=$fopen(f,"r");if(fd==0)$fatal(1,"cannot open stim");
  completions=0;retired=0;first_fault=-1;ready_seen=0;starts=0;done=0;maxlive=0;for(q=0;q<4;q++)ngrp[q]=0;
  repeat(4)@(posedge ck);#0.2 rst_n=1;
  edge_i=0;have=0;
  while(!done)begin
   // drive inputs for this edge
   pw_v=0;start_v=0;retire_v=0;su_issue=0;ev_stage=ev_stage_n;ev_epoch=ev_epoch_n;ev_stage_n=0;ev_epoch_n=0;
   forever begin
    if(!have)begin r=$fscanf(fd,"%d %d %h %h %h %h %h\n",t,kind,a,b,c,d,e);if(r!=7)$fatal(1,"bad stim line");have=1;end
    if(t>edge_i)break;
    if(t<edge_i)$fatal(1,"stim out of order");
    have=0;
    case(kind)
     0:begin pw_v=1;pw_addr=a[9:0];pw_data={b[31:0],c[31:0]};end
     1:auth=a[0];
     2:begin dig={a[31:0],b[31:0]};pep=c[15:0];fusedcap=d[0];end
     3:begin start_v=1;start_user=a[1:0];start_stage=b[5:0];start_epoch=c[15:0];starts++;end
     4:begin su_issue=1;cmd_user=a[1:0];cmd_slice=b[3:0];su_pidx=c[8:0];ev_stage_n=d[5:0];ev_epoch_n=e[15:0];end
     5:begin retire_v=1;retire_user=a[1:0];mexpf=b[0];
        if(EN!=0&&!all_complete[a[1:0]])$display("TWC_RETIRE_EARLY edge=%0d user=%0d",edge_i,a);end
     9:done=1;
     default:$fatal(1,"bad kind");
    endcase
    if(done)break;
   end
   @(posedge ck);#0.2;
   if(retire_v&&!fault&&mexpf)retired++;
   if(group_complete)begin
    if(complete_group!=ngrp[complete_user])$display("TWC_ORDER_ERROR edge=%0d user=%0d group=%0d expect=%0d",edge_i,complete_user,complete_group,ngrp[complete_user]);
    ngrp[complete_user]=(complete_group==12)?0:complete_group+1;completions++;
   end
   if(template_ready)ready_seen=1;
   if($countones(context_active)>maxlive)maxlive=$countones(context_active);
   if((fault||obs_fault)&&first_fault<0)begin first_fault=edge_i;$display("TWC_FIRST_FAULT edge=%0d ctl=%0d obs=%0d",edge_i,fault,obs_fault);end
   edge_i++;
  end
  $display("TWC_SUMMARY en=%0d fault=%0d obs_fault=%0d ready_seen=%0d ready_end=%0d completions=%0d retired=%0d starts=%0d max_live=%0d active_end=%b first_fault=%0d edges=%0d",
   EN,fault,obs_fault,ready_seen,template_ready,completions,retired,starts,maxlive,context_active,first_fault,edge_i);
  if(EN!=0&&(fault||obs_fault))$display("TWC_RESULT_FAULT");else $display("TWC_RESULT_CLEAN");
  $finish;
 end
endmodule
