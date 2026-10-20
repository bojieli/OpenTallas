`timescale 1ns/1ps
// MU-KV-PEER 10-19 (Qwen ROM 4 users): drop-in successor of qkd_host_post_collector (same ports and parameters).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction; original file untouched).
//   MU 1: four owned steps, one per user (user = TAG epoch[1:0] = TAG59[44:43]; HOST step positions carry the user on
//         pos[17:16], pos[15:13] must be 0, pos[12:0] must equal the TAG position).
//   Own:  a NEW allocation identity (allocated_valid with a tag different from the last one owned) opens the step of
//         its user; a new allocation for a user that still owns a step is a sticky fault (the lifecycle admits a
//         user again only after that user's POST).
//   Terminal: terminal_tag is the ACTUAL accepted terminal identity (qkd_host_coordinator_services_mu wires the
//         lifecycle's accepted-terminal tag, not the latest grant); matched to its user's owned step.
//   POST: terminals post in acceptance order (a 4-entry queue; the class9 codec releases the same head).  The head
//         posts once its terminal, HOST step retire (+ CQ when required) and the 8 rank releases of that terminal
//         are seen, the result transport is idle and the die is drained -- or other users' steps are still owned
//         (the die is then never globally drained; the static calendar emits the terminal after the step's last
//         scheduled work, the same rule as the endpoint and allocator _mu).  Faults are sticky.
//   UID_SLOT 1 (KV-HOST2 10-19, MU4 POST binding, model 164138243): the selected HOST observer
//         (ot_host_if_pb2_observed) exports RAW per-user positions (< 8192) and the real scheduler slot on step_slot /
//         step_retire_slot / cq_slot.  The user is then the CHECKED slot (slot[7:2] must be 0, else sticky fault), the
//         raw position must have pos[17:13] == 0 and pos[12:0] == the TAG position, and the slot user indexes the owned
//         step whose TAG epoch UID (TAG59[44:43]) was allocated -- so slot UID and epoch UID must agree.  Public CQ/CSR
//         position fields are untouched (this is a private decode inside the collector; no register, no edge).
//         UID_SLOT 0 keeps the pos[17:16] decoding above (existing MU benches).  MUT 2 = legacy pos decode in slot mode,
//         MUT 3 = slot range check removed (bench mutants).
module qkd_host_post_collector_mu #(parameter integer MUT=0, parameter integer MU=1, parameter integer UID_SLOT=0)(
 input wire ck,por_n,
 input wire allocated_valid,allocated_delivered,input wire[58:0]allocated_tag,input wire[1:0]allocated_gen,
 input wire step_issue_v,input wire[15:0]step_client_tag,input wire[7:0]step_slot,input wire[17:0]step_pos,
 input wire step_retire_v,step_retire_cq,input wire[15:0]step_retire_client_tag,input wire[7:0]step_retire_slot,input wire[17:0]step_retire_pos,step_retire_token,
 input wire cq_commit_v,input wire[15:0]cq_client_tag,input wire[7:0]cq_slot,input wire[17:0]cq_pos,cq_token,
 input wire terminal_accepted,input wire[58:0]terminal_tag,input wire[1:0]terminal_gen,
 input wire[7:0]cancel_released,cancel_release_required,
 input wire result_transport_idle,input wire[7:0]kv_drained,vm_drained,collective_drained,host_drained,
 input wire source_fault,
 output wire post_retired,output wire[58:0]post_tag,output wire[1:0]post_gen,output wire fault);
generate if(MU==0)begin:g_plain
 qkd_host_post_collector #(.MUT(MUT))u_plain(.ck(ck),.por_n(por_n),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),
  .allocated_tag(allocated_tag),.allocated_gen(allocated_gen),.step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),
  .step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),
  .step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),.cq_commit_v(cq_commit_v),
  .cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.terminal_accepted(terminal_accepted),
  .terminal_tag(terminal_tag),.terminal_gen(terminal_gen),.cancel_released(cancel_released),.cancel_release_required(cancel_release_required),
  .result_transport_idle(result_transport_idle),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),
  .host_drained(host_drained),.source_fault(source_fault),.post_retired(post_retired),.post_tag(post_tag),.post_gen(post_gen),.fault(fault));
end else begin:g_mu
 reg[3:0]owned,issued,retired,cq_needed,cq_seen,terminal_seen;
 reg[58:0]tag[0:3];reg[1:0]gen[0:3];reg[15:0]client[0:3];reg[7:0]slot[0:3];reg[17:0]pos[0:3],token[0:3];
 reg[7:0]release_seen,release_required[0:3];
 reg[58:0]last_alloc;reg last_alloc_v;
 reg[1:0]pq[0:3];reg[1:0]pw,pr;reg[2:0]pn;          // POST order: users in terminal-acceptance order
 reg pr_v;reg[58:0]pr_tag;reg[1:0]pr_gen;reg f;
 assign post_retired=pr_v;assign post_tag=pr_tag;assign post_gen=pr_gen;assign fault=f;
 wire drains=(&kv_drained)&&(&vm_drained)&&(&collective_drained)&&(&host_drained);
 wire[1:0]ua=allocated_tag[44:43];
 wire new_alloc=allocated_valid&&(!last_alloc_v||allocated_tag!=last_alloc);
 localparam bit SLOTDEC=(UID_SLOT!=0)&&(MUT!=2);
 wire[1:0]ui=SLOTDEC?step_slot[1:0]:step_pos[17:16],ur=SLOTDEC?step_retire_slot[1:0]:step_retire_pos[17:16],
          uc=SLOTDEC?cq_slot[1:0]:cq_pos[17:16],ut=terminal_tag[44:43];
 // slot-mode identity checks: slot in range (4 users) and a raw position (no user bits above the 13-bit TAG position)
 wire bad_si=(UID_SLOT!=0)&&(((step_slot[7:2]!=0)&&(MUT!=3))||step_pos[17:13]!=0);
 wire bad_sr=(UID_SLOT!=0)&&(((step_retire_slot[7:2]!=0)&&(MUT!=3))||step_retire_pos[17:13]!=0);
 wire bad_sc=(UID_SLOT!=0)&&(((cq_slot[7:2]!=0)&&(MUT!=3))||cq_pos[17:13]!=0);
 wire[1:0]h=pq[pr];
 wire alone=(owned&~(4'd1<<h))==4'd0;
 wire exact_step=step_retire_client_tag==client[ur]&&step_retire_slot==slot[ur]&&step_retire_pos==pos[ur];
 wire exact_cq=cq_client_tag==client[uc]&&cq_slot==slot[uc]&&cq_pos==pos[uc]&&cq_token==token[uc];
 wire post_go=pn!=0&&owned[h]&&terminal_seen[h]&&result_transport_idle&&(drains||!alone)&&!source_fault&&!f&&
      ((release_seen&release_required[h])==release_required[h])&&issued[h]&&retired[h]&&(!cq_needed[h]||cq_seen[h]||MUT==1);
 integer k;
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin
   owned<=0;issued<=0;retired<=0;cq_needed<=0;cq_seen<=0;terminal_seen<=0;release_seen<=0;last_alloc<=0;last_alloc_v<=0;
   pw<=0;pr<=0;pn<=0;pr_v<=0;pr_tag<=0;pr_gen<=0;f<=0;
   for(k=0;k<4;k=k+1)begin tag[k]<=0;gen[k]<=0;client[k]<=0;slot[k]<=0;pos[k]<=0;token[k]<=0;release_required[k]<=0;pq[k]<=0;end
  end else begin
   pr_v<=0;
   if(source_fault)f<=1;
   if(new_alloc)begin
    last_alloc<=allocated_tag;last_alloc_v<=1;
    if(owned[ua])f<=1;
    else begin owned[ua]<=1;tag[ua]<={allocated_tag[58:43],6'd37,allocated_tag[36:0]};gen[ua]<=allocated_gen;
     retired[ua]<=0;cq_needed[ua]<=0;cq_seen[ua]<=0;terminal_seen[ua]<=0;end
   end
   if(step_issue_v)begin
    if(issued[ui]||step_pos[15:13]!=0||bad_si)f<=1;
    else begin issued[ui]<=1;client[ui]<=step_client_tag;slot[ui]<=step_slot;pos[ui]<=step_pos;end
   end
   for(k=0;k<4;k=k+1)if(owned[k]&&issued[k]&&pos[k][12:0]!=tag[k][18:6])f<=1;
   if(step_retire_v)begin
    if(!owned[ur]||!issued[ur]||retired[ur]||!exact_step||bad_sr)f<=1;
    else begin retired[ur]<=1;cq_needed[ur]<=step_retire_cq;token[ur]<=step_retire_token;end
   end
   if(cq_commit_v)begin
    if(!owned[uc]||!retired[uc]||!cq_needed[uc]||cq_seen[uc]||!exact_cq||bad_sc)f<=1;
    else cq_seen[uc]<=1;
   end
   if(terminal_accepted)begin
    if(!owned[ut]||terminal_seen[ut]||terminal_tag!=tag[ut]||terminal_gen!=gen[ut]||pn==3'd4)f<=1;
    else begin terminal_seen[ut]<=1;release_required[ut]<=cancel_release_required;pq[pw]<=ut;pw<=pw+1'b1;end
   end
   if(pn!=0)release_seen<=release_seen|cancel_released;
   if(post_go)begin
    owned[h]<=0;issued[h]<=0;pr_v<=1;pr_tag<=tag[h];pr_gen<=gen[h];pr<=pr+1'b1;release_seen<=0;
   end
   pn<=pn+3'(terminal_accepted&&!(!owned[ut]||terminal_seen[ut]||terminal_tag!=tag[ut]||terminal_gen!=gen[ut]||pn==3'd4))-3'(post_go);
  end
 end
end endgenerate
endmodule
