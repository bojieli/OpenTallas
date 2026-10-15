`timescale 1ns/1ps
// Per-token POST certificate from actual HOST state transitions and successful
// CQ DMA retirement. Prefill steps have no CQ by the real HOST ABI; generated
// steps do. Cancellation still requires its actual HOST step retirement and
// fault CQ when required; an empty native context does not mean no HOST step.
// Future SQ work and a multi-token descriptor do not block retirement.
module qkd_host_post_collector #(parameter integer MUT=0)(
 input wire ck,por_n,
 input wire allocated_valid,allocated_delivered,input wire[58:0]allocated_tag,input wire[1:0]allocated_gen,
 input wire step_issue_v,input wire[15:0]step_client_tag,input wire[7:0]step_slot,input wire[17:0]step_pos,
 input wire step_retire_v,step_retire_cq,input wire[15:0]step_retire_client_tag,input wire[7:0]step_retire_slot,input wire[17:0]step_retire_pos,step_retire_token,
 input wire cq_commit_v,input wire[15:0]cq_client_tag,input wire[7:0]cq_slot,input wire[17:0]cq_pos,cq_token,
 input wire terminal_accepted,input wire[58:0]terminal_tag,input wire[1:0]terminal_gen,
 input wire[7:0]cancel_released,cancel_release_required,
 input wire result_transport_idle,input wire[7:0]kv_drained,vm_drained,collective_drained,host_drained,
 input wire source_fault,
 output reg post_retired,output reg[58:0]post_tag,output reg[1:0]post_gen,output reg fault);
 reg owned,issued,retired,cq_needed,cq_seen,terminal_seen;
 reg[58:0]tag;reg[1:0]gen;reg[15:0]client;reg[7:0]slot;reg[17:0]pos,token;
 reg[7:0]release_seen,release_required;
 wire drains=(&kv_drained)&&(&vm_drained)&&(&collective_drained)&&(&host_drained);
 wire exact_step=step_retire_client_tag==client&&step_retire_slot==slot&&step_retire_pos==pos;
 wire exact_cq=cq_client_tag==client&&cq_slot==slot&&cq_pos==pos&&cq_token==token;
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin owned<=0;issued<=0;retired<=0;cq_needed<=0;cq_seen<=0;terminal_seen<=0;tag<=0;gen<=0;client<=0;slot<=0;pos<=0;token<=0;release_seen<=0;release_required<=0;post_retired<=0;post_tag<=0;post_gen<=0;fault<=0;end
  else begin
   post_retired<=0;
   if(source_fault)fault<=1;
   if(allocated_valid&&!owned)begin
    begin owned<=1;tag<={allocated_tag[58:43],6'd37,allocated_tag[36:0]};gen<=allocated_gen;retired<=0;cq_needed<=0;cq_seen<=0;terminal_seen<=0;release_seen<=0;end
   end
   if(step_issue_v)begin
    if(issued||step_pos[17:13]!=0)fault<=1;
    else begin issued<=1;client<=step_client_tag;slot<=step_slot;pos<=step_pos;end
   end
   if(owned&&issued&&pos[12:0]!=tag[18:6])fault<=1;
   if(step_retire_v)begin
    if(!owned||!issued||retired||!exact_step)fault<=1;
    else begin retired<=1;cq_needed<=step_retire_cq;token<=step_retire_token;end
   end
   if(cq_commit_v)begin
    if(!owned||!retired||!cq_needed||cq_seen||!exact_cq)fault<=1;
    else cq_seen<=1;
   end
   if(terminal_accepted)begin
    if(!owned||terminal_seen||terminal_tag!=tag||terminal_gen!=gen)fault<=1;
    else begin terminal_seen<=1;release_required<=cancel_release_required;end
   end
   if(owned)release_seen<=release_seen|cancel_released;
   if(owned&&terminal_seen&&result_transport_idle&&drains&&!source_fault&&!fault&&
      ((release_seen&release_required)==release_required)&&issued&&retired&&(!cq_needed||cq_seen||MUT==1))begin
    owned<=0;issued<=0;post_retired<=1;post_tag<=tag;post_gen<=gen;
   end
  end
 end
endmodule
