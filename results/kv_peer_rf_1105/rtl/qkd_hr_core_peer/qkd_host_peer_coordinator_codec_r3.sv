`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of qkd_host_peer_coordinator_codec_mu (MU 1 body; same ports, frames, per-user rules).
//  RX: header, sequence, shape and identity compares drive only `fault`; action and capture registers load on the opcode
//    alone.  fault rises on the same edge as the source and is sticky (rx_ready, tx_valid fall).  A bad frame can only
//    update registers on the edge the fault appears.
//  request_ack_tag / cancel_ack_tag are gone: participant_tag / cancel_tag cannot change while their ack is set (a new
//    frame with the ack set is a fault), so the ack frame reads them directly.  Exact.
//  Allocation frames: one dirty bit per rank against one previous-allocation register (+1 edge; a change is never lost,
//    a value that changes while a frame leaves costs one more frame with the current value).
//  Terminal head: accepted_tag is a register loaded one edge after the head changes; class5 starts on that edge (+1).
//    terminal_released clears on the source's edge, so head_done and result_transport_idle stay false across the gap.
//  TX frame choice: a per-rank register (+1 edge on every class, at most one frame per 2 edges per rank, rank-side rate only).  A frame
//    held by back pressure stays presented, a timing the source also has when ready comes one edge earlier.  Recovery request +1.
//  RX and shape compares register once before fault (+1 edge): fault stays sticky, and the frame after a bad one can still act.
//  Terminal queue count moves on the pulses alone: a duplicate user, an overflow and a retire before the head is done drive only the sticky fault.
//  Request identity compare registers on its own (rid_q, fault +1 as the other RX compares).
//  participant_*, cancel_tag/gen, program_*, service/certificate data, tq/al/term data, result word: no reset, valid qualified.
module qkd_host_peer_coordinator_codec_r3 #(parameter integer MU=1)(
 input wire ck,por_n,
 input wire[7:0]rx_valid,input wire[4095:0]rx_data,output wire[7:0]rx_ready,
 output wire[7:0]tx_valid,output reg[4095:0]tx_data,input wire[7:0]tx_ready,
 input wire allocated_valid,allocated_delivered,input wire[58:0]allocated_tag,input wire[1:0]allocated_gen,input wire[17:0]allocated_position,
 output reg[7:0]participant_valid,output reg[471:0]participant_tag,output reg[15:0]participant_gen,
 output reg[255:0]participant_trace,output reg[143:0]participant_token,participant_pos,input wire[7:0]participant_accepted,
 output reg[7:0]cancel_valid,cancel_done,cancel_fault,output reg[471:0]cancel_tag,output reg[15:0]cancel_gen,input wire[7:0]cancel_accepted,
 output reg[7:0]service_ready,native_ready,kv_drained,vm_drained,collective_drained,host_drained,context_owned,links_drained,link_reset_seen,retrained,
 output reg[127:0]service_epoch,certificate_epoch,output reg[7:0]program_ready,output reg[127:0]program_epoch,output reg[511:0]program_digest,
 input wire result_v,input wire[58:0]result_tag,input wire[1:0]result_gen,input wire result_done,result_fault,
 input wire[3:0]result_cause,input wire[17:0]result_token,input wire[31:0]result_value,result_cycles,output reg result_cr,
 input wire terminal_accepted,input wire[58:0]terminal_tag,input wire[1:0]terminal_gen,input wire post_retired,
 output reg[7:0]terminal_released,output wire result_transport_idle,
 input wire link_reset_request,retraining_request,
 output reg step_issue_v,output reg[15:0]step_client_tag,output reg[7:0]step_slot,output reg[17:0]step_pos,
 output reg step_retire_v,step_retire_cq,output reg[15:0]step_retire_client_tag,output reg[7:0]step_retire_slot,output reg[17:0]step_retire_pos,step_retire_token,
 output reg cq_commit_v,output reg[15:0]cq_client_tag,output reg[7:0]cq_slot,output reg[17:0]cq_pos,cq_token,
 output reg[7:0]certificate_valid,output reg[527:0]certificate,output reg[255:0]certificate_prefix,
 output wire fault);
 function automatic sel4(input[3:0]x,input[1:0]i);sel4=i[1]?(i[0]?x[3]:x[2]):(i[0]?x[1]:x[0]);endfunction
 reg fault_r;
 assign fault=fault_r;
 reg[58:0] tq_tag[0:3];
 reg[1:0] tq_gen[0:3];
 reg[1:0] tq_w,tq_r;
 reg[2:0] tq_n;
 reg[3:0] al_v,term_v;
 reg[58:0] al_tag[0:3],term_tag[0:3];
 reg[1:0] al_gen[0:3],term_gen[0:3];
 reg[58:0] al_last;
 reg al_last_v;
 reg[15:0] rx_seq[0:7],tx_seq[0:7];
 reg[7:0] request_queued;
 reg[7:0] request_ack,cancel_ack,request_abort,terminal_send,result_send,result_return;
 reg result_busy;
 reg start_q;
 reg[58:0] accepted_tag;reg[1:0] accepted_gen;
 reg[148:0] rw;              // result word bits [178:30]
 reg[1:0] last_recovery[0:7];
 reg[7:0] recovery_sent;
 reg[31:0] choice;reg[3:0] choice_n[0:7];reg[7:0] rx_bad_q,rid_q;reg[1:0] recovery_q;
 wire[80:0] allocation;
 reg[80:0] allocation_prev;
 reg[7:0] allocation_dirty;
 wire[1:0] recovery;
 integer i;
 wire t_u_busy=sel4(term_v,terminal_tag[44:43]);
 wire tq_push=terminal_accepted;
 wire terminal_active=tq_n!=0;
 wire head_done=terminal_active&&terminal_send==0&&(&terminal_released);
 wire tq_pop=post_retired;
 wire[2:0] tq_next=tq_n+3'(tq_push)-3'(tq_pop);
 wire tq_start=(tq_push&&tq_n==0)||(tq_pop&&tq_next!=0);
 assign allocation={allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid};
 wire allocation_change=allocation!=allocation_prev;
 assign recovery=recovery_q;
 // DIE-KV-73 11-05 r4: rank copies of the sticky fault (+1 edge, each holds itself so synthesis keeps them apart), one TX slice per rank
 // (+1 edge per frame; order and payload exact, payload sampled when the slice loads), one-hot payload select from choice next state.
 reg[7:0] flt_q,o_v;reg[5:0] ch_oh[0:7];reg[4095:0] i_data;
 wire[7:0] i_valid,i_ready;
 assign rx_ready=~flt_q;
 assign result_transport_idle=!result_busy&&request_queued==0&&request_ack==0&&cancel_ack==0&&terminal_send==0&&(!terminal_active||(&terminal_released))&&!result_v&&o_v==0;
 for(genvar g=0;g<8;g=g+1)begin:g_tx
  assign i_valid[g]=choice[g*4+:4]!=0&&!flt_q[g];
  assign i_ready[g]=!o_v[g]||tx_ready[g];
  assign tx_valid[g]=o_v[g]&&!flt_q[g];
 end
 always @*begin
  i_data=0;
  for(integer k=0;k<8;k=k+1)begin
   choice_n[k]=(terminal_send[k]&&!result_busy)?4'd5:request_ack[k]?4'd1:cancel_ack[k]?4'd2:result_send[k]?4'd3:allocation_dirty[k]?4'd6:(!recovery_sent[k]||last_recovery[k]!=recovery)?4'd4:4'd0;
   if(ch_oh[k][4])begin i_data[k*512+30+:59]=accepted_tag;i_data[k*512+89+:2]=accepted_gen;end
   else if(ch_oh[k][0])begin i_data[k*512+30+:59]=participant_tag[k*59+:59];i_data[k*512+89+:2]=participant_gen[k*2+:2];i_data[k*512+91]=request_abort[k];end
   else if(ch_oh[k][1])begin i_data[k*512+30+:59]=cancel_tag[k*59+:59];i_data[k*512+89+:2]=cancel_gen[k*2+:2];end
   else if(ch_oh[k][2])begin i_data[k*512+30+:149]=rw;end
   else if(ch_oh[k][5])begin i_data[k*512+30+:81]=allocation;end
   else if(ch_oh[k][3])begin i_data[k*512+30+:2]=recovery;end
   i_data[k*512+:8]=8'h80|8'(choice[k*4+:4]);i_data[k*512+8+:3]=0;i_data[k*512+11+:3]=3'(k);i_data[k*512+14+:16]=tx_seq[k];
  end
 end
 // per-rank frame checks (ranks 1..7 read one slice, so synthesis merges their identical cones)
 wire[7:0] rx_fire=rx_valid&rx_ready;
 wire[7:0] op1,op2,op3,op4,op5,op6,op7,op8,op9,rx_bad,rid_bad,late_u,late_abort,late_abort_bad;
 for(genvar g=0;g<8;g=g+1)begin:g_rx
  wire[511:0] d=rx_data[g*512+:512];
  wire[1:0] u=d[74:73];
  wire hdr_bad=d[10:8]!=3'(g)||d[13:11]!=0||d[29:14]!=rx_seq[g];
  assign op1[g]=d[7:0]==1;assign op2[g]=d[7:0]==2;assign op3[g]=d[7:0]==3;assign op4[g]=d[7:0]==4;assign op5[g]=d[7:0]==5;
  assign op6[g]=d[7:0]==6;assign op7[g]=d[7:0]==7;assign op8[g]=d[7:0]==8;assign op9[g]=d[7:0]==9;
  wire req_id_bad=(!sel4(al_v,u)||d[88:30]!=al_tag[u]||d[90:89]!=al_gen[u])&&
                  (!sel4(term_v,u)||{d[88:73],6'd37,d[66:30]}!=term_tag[u]||d[90:89]!=term_gen[u]);
  assign rx_bad[g]=hdr_bad||
   (op1[g]&&(request_queued[g]||request_ack[g]||d[511:159]!=0))||
   (op2[g]&&(cancel_valid[g]||cancel_ack[g]||d[511:97]!=0||(!d[91]&&!d[92])))||
   (op3[g]&&d[511:137]!=0)||
   (op4[g]&&(!result_busy||result_send[g]||result_return[g]||d[88:30]!=rw[58:0]||d[90:89]!=rw[60:59]||d[511:91]!=0))||
   (op5[g]&&(g!=0||d[511:72]!=0||step_issue_v))||
   (op6[g]&&(g!=0||d[511:91]!=0||step_retire_v))||
   (op7[g]&&(g!=0||d[511:90]!=0||cq_commit_v))||
   (op8[g]&&(!terminal_active||terminal_send[g]||terminal_released[g]||d[88:30]!=accepted_tag||d[90:89]!=accepted_gen||d[511:91]!=0))||
   (op9[g]&&d[511:144]!=0)||
   !(op1[g]||op2[g]||op3[g]||op4[g]||op5[g]||op6[g]||op7[g]||op8[g]||op9[g]);
  assign rid_bad[g]=op1[g]&&req_id_bad;
  assign late_u[g]=sel4(term_v,u)||(terminal_accepted&&terminal_tag[44:43]==u);
  assign late_abort[g]=sel4(term_v,participant_tag[g*59+43+:2])&&request_queued[g]&&!request_ack[g]&&!participant_accepted[g];
  assign late_abort_bad[g]={participant_tag[g*59+43+:16],6'd37,participant_tag[g*59+:37]}!=term_tag[participant_tag[g*59+43+:2]]||participant_gen[g*2+:2]!=term_gen[participant_tag[g*59+43+:2]];
 end
 // data registers: no reset, valid qualified
 always @(posedge ck)begin
  if(result_v)begin rw[58:0]<=result_tag;rw[60:59]<=result_gen;rw[61]<=result_done;rw[62]<=result_fault;rw[66:63]<=result_cause;rw[84:67]<=result_token;rw[116:85]<=result_value;rw[148:117]<=result_cycles;end
  if(allocated_valid&&(!al_last_v||allocated_tag!=al_last))begin al_tag[allocated_tag[44:43]]<=allocated_tag;al_gen[allocated_tag[44:43]]<=allocated_gen;end
  if(terminal_accepted)begin tq_tag[tq_w]<=terminal_tag;tq_gen[tq_w]<=terminal_gen;term_tag[terminal_tag[44:43]]<=terminal_tag;term_gen[terminal_tag[44:43]]<=terminal_gen;end
  if(start_q)begin accepted_tag<=tq_tag[tq_r];accepted_gen<=tq_gen[tq_r];end
  allocation_prev<=allocation;
 end
 always @(posedge ck)for(integer k=0;k<8;k=k+1)if(rx_fire[k])begin
  if(op1[k])begin participant_tag[k*59+:59]<=rx_data[k*512+30+:59];participant_gen[k*2+:2]<=rx_data[k*512+89+:2];participant_trace[k*32+:32]<=rx_data[k*512+91+:32];participant_token[k*18+:18]<=rx_data[k*512+123+:18];participant_pos[k*18+:18]<=rx_data[k*512+141+:18];end
  if(op2[k])begin cancel_tag[k*59+:59]<=rx_data[k*512+30+:59];cancel_gen[k*2+:2]<=rx_data[k*512+89+:2];end
  if(op3[k])begin service_epoch[k*16+:16]<=rx_data[k*512+121+:16];program_epoch[k*16+:16]<=rx_data[k*512+41+:16];program_digest[k*64+:64]<=rx_data[k*512+57+:64];end
  if(op9[k])begin certificate_epoch[k*16+:16]<=rx_data[k*512+128+:16];certificate[k*66+:66]<=rx_data[k*512+30+:66];certificate_prefix[k*32+:32]<=rx_data[k*512+96+:32];end
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin
   request_queued<=0;participant_valid<=0;choice<=0;rx_bad_q<=0;rid_q<=0;recovery_q<=0;
   cancel_valid<=0;cancel_done<=0;cancel_fault<=0;
   service_ready<=0;native_ready<=0;kv_drained<=0;vm_drained<=0;collective_drained<=0;host_drained<=0;context_owned<=0;links_drained<=0;link_reset_seen<=0;retrained<=0;program_ready<=0;
   request_ack<=0;cancel_ack<=0;request_abort<=0;terminal_send<=0;result_send<=0;result_return<=0;
   result_busy<=0;start_q<=0;tq_w<=0;tq_r<=0;tq_n<=0;al_v<=0;term_v<=0;al_last<=0;al_last_v<=0;recovery_sent<=0;allocation_dirty<=8'hff;terminal_released<=0;result_cr<=0;
   step_issue_v<=0;step_client_tag<=0;step_slot<=0;step_pos<=0;step_retire_v<=0;step_retire_cq<=0;step_retire_client_tag<=0;step_retire_slot<=0;step_retire_pos<=0;step_retire_token<=0;
   cq_commit_v<=0;cq_client_tag<=0;cq_slot<=0;cq_pos<=0;cq_token<=0;certificate_valid<=0;fault_r<=0;
   for(i=0;i<8;i=i+1)begin rx_seq[i]<=0;tx_seq[i]<=0;last_recovery[i]<=0;ch_oh[i]<=0;end
   flt_q<=0;o_v<=0;
  end else begin
   rx_bad_q<=rx_fire&rx_bad;rid_q<=rx_fire&rid_bad;if((|rx_bad_q)||(|rid_q))fault_r<=1;recovery_q<={retraining_request,link_reset_request};
   result_cr<=0;step_issue_v<=0;step_retire_v<=0;cq_commit_v<=0;participant_valid<=0;start_q<=tq_start;
   if(result_v)begin
    if(result_busy||(!result_done&&!result_fault))fault_r<=1;
    result_busy<=1;result_send<=255;result_return<=0;
   end
   if(result_busy&&(&result_return))begin result_busy<=0;result_cr<=1;end
   if(allocated_valid&&(!al_last_v||allocated_tag!=al_last))begin
    al_last<=allocated_tag;al_last_v<=1;al_v[allocated_tag[44:43]]<=1;
   end
   if(terminal_accepted)begin
    if(tq_n==3'd4||t_u_busy)fault_r<=1;
    tq_w<=tq_w+1'b1;al_v[terminal_tag[44:43]]<=0;term_v[terminal_tag[44:43]]<=1;
   end
   if(post_retired)begin if(!head_done)fault_r<=1;tq_r<=tq_r+1'b1;term_v[accepted_tag[44:43]]<=0;end
   if(tq_start)terminal_released<=0;
   if(start_q)terminal_send<=255;
   tq_n<=tq_next;
   for(i=0;i<8;i=i+1)begin
    if(participant_accepted[i])begin
     if(!request_queued[i]||request_ack[i])fault_r<=1;
     request_queued[i]<=0;request_ack[i]<=1;request_abort[i]<=0;
    end
    if(cancel_accepted[i])begin
     if(!cancel_valid[i]||cancel_ack[i])fault_r<=1;
     cancel_valid[i]<=0;cancel_ack[i]<=1;
    end
    // A request that reached this queue after terminal acceptance is discarded here by identity; its real queue
    // reservation returns with abort=1 and is never reported as accepted by the execution cohort.
    if(late_abort[i])begin
     if(late_abort_bad[i])fault_r<=1;
     request_queued[i]<=0;request_ack[i]<=1;request_abort[i]<=1;
    end
    if(i_valid[i]&&i_ready[i])begin
     tx_seq[i]<=tx_seq[i]+1'b1;choice[i*4+:4]<=0;
     case(choice[i*4+:4])1:request_ack[i]<=0;2:cancel_ack[i]<=0;3:result_send[i]<=0;4:begin last_recovery[i]<=recovery;recovery_sent[i]<=1;end 5:terminal_send[i]<=0;6:;default:fault_r<=1;endcase
    end
    if(choice[i*4+:4]==0)choice[i*4+:4]<=choice_n[i];
    if(i_valid[i]&&i_ready[i])ch_oh[i]<=0;
    else if(choice[i*4+:4]==0)ch_oh[i]<={choice_n[i]==4'd6,choice_n[i]==4'd5,choice_n[i]==4'd4,choice_n[i]==4'd3,choice_n[i]==4'd2,choice_n[i]==4'd1};
    flt_q[i]<=flt_q[i]|fault_r;
    if(i_ready[i])o_v[i]<=i_valid[i];
    if(allocation_change)allocation_dirty[i]<=1;
    else if(i_valid[i]&&i_ready[i]&&choice[i*4+:4]==6)allocation_dirty[i]<=0;
    if(rx_fire[i])begin
     rx_seq[i]<=rx_seq[i]+1'b1;
     if(op1[i])begin request_queued[i]<=1;if(!late_u[i])participant_valid[i]<=1;end
     if(op2[i])begin cancel_valid[i]<=1;cancel_done[i]<=rx_data[i*512+91];cancel_fault[i]<=rx_data[i*512+92];end
     if(op3[i])begin service_ready[i]<=rx_data[i*512+30];native_ready[i]<=rx_data[i*512+31];kv_drained[i]<=rx_data[i*512+32];vm_drained[i]<=rx_data[i*512+33];collective_drained[i]<=rx_data[i*512+34];host_drained[i]<=rx_data[i*512+35];context_owned[i]<=rx_data[i*512+36];link_reset_seen[i]<=rx_data[i*512+37];retrained[i]<=rx_data[i*512+38];links_drained[i]<=rx_data[i*512+39];program_ready[i]<=rx_data[i*512+40];end
     if(op4[i])result_return[i]<=1;
     if(op5[i]&&i==0)begin step_issue_v<=1;step_client_tag<=rx_data[45:30];step_slot<=rx_data[53:46];step_pos<=rx_data[71:54];end
     if(op6[i]&&i==0)begin step_retire_v<=1;step_retire_client_tag<=rx_data[45:30];step_retire_slot<=rx_data[53:46];step_retire_pos<=rx_data[71:54];step_retire_token<=rx_data[89:72];step_retire_cq<=rx_data[90];end
     if(op7[i]&&i==0)begin cq_commit_v<=1;cq_client_tag<=rx_data[45:30];cq_slot<=rx_data[53:46];cq_pos<=rx_data[71:54];cq_token<=rx_data[89:72];end
     if(op8[i])terminal_released[i]<=1;
     if(op9[i])certificate_valid[i]<=1;
    end
   end
  end
 end
 // TX slice data: no reset, o_v qualifies it
 always @(posedge ck)for(integer k=0;k<8;k=k+1)if(i_valid[k]&&i_ready[k])tx_data[k*512+:512]<=i_data[k*512+:512];
endmodule
