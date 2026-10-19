`timescale 1ns/1ps
// Stimulus-file bench for the default-off finite FF WTN1 witness controller
// composed with the typed SU observer (command issue -> observation +1 -> check +2).
// Lines: "<edge> <kind> <a> <b> <c> <d> <e>"; kinds:
//  0 PW addr data_hi data_lo   1 AUTH level   2 PROFILE digest_hi digest_lo epoch fusedcap
//  3 START user stage epoch    4 ISSUE user slice pidx stage epoch   5 RETIRE user mexpf
//  9 END
module tb_qwen_typed_witness_control #(parameter integer EN=1);
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg pw_v=0;reg[9:0]pw_addr=0;reg[63:0]pw_data=0;reg auth=0,fusedcap=0;reg[63:0]dig=0;reg[15:0]pep=0;
 reg start_v=0;reg[1:0]start_user=0;reg[5:0]start_stage=0;reg[15:0]start_epoch=0;
 reg retire_v=0;reg[1:0]retire_user=0;reg mexpf=0;
 reg su_issue=0;reg[1:0]cmd_user=0;reg[8:0]su_pidx=0;reg[3:0]cmd_slice=0;
 reg[5:0]ev_stage=0,ev_stage_n=0;reg[15:0]ev_epoch=0,ev_epoch_n=0;
 wire[15:0]observation;wire obs_fault;
 wire template_ready;wire[3:0]context_active,all_complete;wire group_complete;wire[1:0]complete_user;wire[3:0]complete_group;wire fault;
 qfd_dv_typed_su_observer #(.ENABLE(EN)) obs(.ck(ck),.rst_n(rst_n),.su_issue(su_issue),.cmd_user(cmd_user),.su_pidx(su_pidx),.cmd_slice(cmd_slice),.observation(observation),.fault(obs_fault));
 qfd_dv_typed_witness_control #(.ENABLE(EN)) dut(.ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),
  .all_copies_authenticated(auth),.fusedcap(fusedcap),.installed_digest(dig),.installed_epoch(pep),
  .start_v(start_v),.start_user(start_user),.start_stage(start_stage),.start_epoch(start_epoch),
  .retire_v(retire_v),.retire_user(retire_user),.ME_XPF_retired(mexpf),
  .observation(observation),.event_stage(ev_stage),.event_epoch(ev_epoch),
  .template_ready(template_ready),.context_active(context_active),.all_witnesses_complete(all_complete),
  .group_complete(group_complete),.complete_user(complete_user),.complete_group(complete_group),.fault(fault));
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
