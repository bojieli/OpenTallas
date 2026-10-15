`timescale 1ns/1ps
// Exactly one coordinator endpoint consumes eight real class9 packet streams.
// Native-rank order is explicit. Per-rank packet sequence rejects duplicates;
// requests remain owned until real cohort acceptance or explicit terminal discard.
module qkd_host_peer_coordinator_codec(
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
 output reg fault);
 reg[15:0]rx_seq[0:7],tx_seq[0:7];
 reg[7:0]request_queued;
 reg[7:0]request_ack,cancel_ack,request_abort,terminal_send,result_send,result_return;
 reg[471:0]request_ack_tag,cancel_ack_tag;reg[15:0]request_ack_gen,cancel_ack_gen;
 reg terminal_active,result_busy;reg[58:0]accepted_tag;reg[1:0]accepted_gen;
 reg[511:0]result_word;reg[1:0]last_recovery[0:7];reg[7:0]recovery_sent;
 reg[3:0]choice[0:7];
 wire[80:0]allocation={allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid};
 reg[80:0]last_allocation[0:7];reg[7:0]allocation_sent;
 wire[1:0]recovery={retraining_request,link_reset_request};
 assign rx_ready={8{!fault}};
 assign result_transport_idle=!result_busy&&request_queued==0&&request_ack==0&&cancel_ack==0&&terminal_send==0&&(!terminal_active||(&terminal_released))&&!result_v;
 generate for(genvar g=0;g<8;g=g+1)begin:g_tx
  assign tx_valid[g]=choice[g]!=0&&!fault;
 end endgenerate
 always @*begin
  tx_data=0;
  for(integer k=0;k<8;k=k+1)begin
   choice[k]=0;
   if(terminal_send[k]&&!result_busy)begin choice[k]=5;tx_data[k*512+30+:59]=accepted_tag;tx_data[k*512+89+:2]=accepted_gen;end
   else if(request_ack[k])begin choice[k]=1;tx_data[k*512+30+:59]=request_ack_tag[k*59+:59];tx_data[k*512+89+:2]=request_ack_gen[k*2+:2];tx_data[k*512+91]=request_abort[k];end
   else if(cancel_ack[k])begin choice[k]=2;tx_data[k*512+30+:59]=cancel_ack_tag[k*59+:59];tx_data[k*512+89+:2]=cancel_ack_gen[k*2+:2];end
   else if(result_send[k])begin choice[k]=3;tx_data[k*512+:512]=result_word;end
   else if(!allocation_sent[k]||last_allocation[k]!=allocation)begin choice[k]=6;tx_data[k*512+30+:81]=allocation;end
   else if(!recovery_sent[k]||last_recovery[k]!=recovery)begin choice[k]=4;tx_data[k*512+30+:2]=recovery;end
   tx_data[k*512+:8]=8'h80|8'(choice[k]);tx_data[k*512+8+:3]=0;tx_data[k*512+11+:3]=3'(k);tx_data[k*512+14+:16]=tx_seq[k];
  end
 end
 integer i;
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin
   request_queued<=0;participant_valid<=0;participant_tag<=0;participant_gen<=0;participant_trace<=0;participant_token<=0;participant_pos<=0;
   cancel_valid<=0;cancel_done<=0;cancel_fault<=0;cancel_tag<=0;cancel_gen<=0;
   service_epoch<=0;certificate_epoch<=0;service_ready<=0;native_ready<=0;kv_drained<=0;vm_drained<=0;collective_drained<=0;host_drained<=0;context_owned<=0;links_drained<=0;link_reset_seen<=0;retrained<=0;program_ready<=0;program_epoch<=0;program_digest<=0;
   request_ack<=0;cancel_ack<=0;request_abort<=0;terminal_send<=0;result_send<=0;result_return<=0;request_ack_tag<=0;cancel_ack_tag<=0;request_ack_gen<=0;cancel_ack_gen<=0;
   terminal_active<=0;result_busy<=0;accepted_tag<=0;accepted_gen<=0;result_word<=0;recovery_sent<=0;allocation_sent<=0;terminal_released<=0;result_cr<=0;
   step_issue_v<=0;step_client_tag<=0;step_slot<=0;step_pos<=0;step_retire_v<=0;step_retire_cq<=0;step_retire_client_tag<=0;step_retire_slot<=0;step_retire_pos<=0;step_retire_token<=0;
   cq_commit_v<=0;cq_client_tag<=0;cq_slot<=0;cq_pos<=0;cq_token<=0;certificate_valid<=0;certificate<=0;certificate_prefix<=0;fault<=0;
   for(i=0;i<8;i=i+1)begin rx_seq[i]<=0;tx_seq[i]<=0;last_recovery[i]<=0;last_allocation[i]<=0;end
  end else begin
   result_cr<=0;step_issue_v<=0;step_retire_v<=0;cq_commit_v<=0;participant_valid<=0;
   if(result_v)begin
    if(result_busy||(!result_done&&!result_fault))fault<=1;
    else begin result_busy<=1;result_send<=255;result_return<=0;result_word<=0;result_word[88:30]<=result_tag;result_word[90:89]<=result_gen;result_word[91]<=result_done;result_word[92]<=result_fault;result_word[96:93]<=result_cause;result_word[114:97]<=result_token;result_word[146:115]<=result_value;result_word[178:147]<=result_cycles;end
   end
   if(result_busy&&(&result_return))begin result_busy<=0;result_cr<=1;end
   if(terminal_accepted)begin
    if(terminal_active)fault<=1;
    else begin terminal_active<=1;accepted_tag<=terminal_tag;accepted_gen<=terminal_gen;terminal_send<=255;terminal_released<=0;end
   end
   if(post_retired)begin if(!terminal_active||!result_transport_idle)fault<=1;else terminal_active<=0;end
   for(i=0;i<8;i=i+1)begin
    if(participant_accepted[i])begin
     if(!request_queued[i]||request_ack[i])fault<=1;
     else begin request_queued[i]<=0;request_ack[i]<=1;request_abort[i]<=0;request_ack_tag[i*59+:59]<=participant_tag[i*59+:59];request_ack_gen[i*2+:2]<=participant_gen[i*2+:2];end
    end
    if(cancel_accepted[i])begin
     if(!cancel_valid[i]||cancel_ack[i])fault<=1;
     else begin cancel_valid[i]<=0;cancel_ack[i]<=1;cancel_ack_tag[i*59+:59]<=cancel_tag[i*59+:59];cancel_ack_gen[i*2+:2]<=cancel_gen[i*2+:2];end
    end
    // A request that reached this queue after terminal acceptance is discarded
    // here by identity. Its real queue reservation returns with abort=1; it is
    // never reported as accepted by the execution cohort.
    if(terminal_active&&request_queued[i]&&!request_ack[i])begin
     if({participant_tag[i*59+43+:16],6'd37,participant_tag[i*59+:37]}!=accepted_tag||participant_gen[i*2+:2]!=accepted_gen)fault<=1;
     else begin request_queued[i]<=0;request_ack[i]<=1;request_abort[i]<=1;request_ack_tag[i*59+:59]<=participant_tag[i*59+:59];request_ack_gen[i*2+:2]<=participant_gen[i*2+:2];end
    end
    if(tx_valid[i]&&tx_ready[i])begin
     tx_seq[i]<=tx_seq[i]+1'b1;
     case(choice[i])1:request_ack[i]<=0;2:cancel_ack[i]<=0;3:result_send[i]<=0;4:begin last_recovery[i]<=recovery;recovery_sent[i]<=1;end 5:terminal_send[i]<=0;6:begin last_allocation[i]<=allocation;allocation_sent[i]<=1;end default:fault<=1;endcase
    end
    if(rx_valid[i]&&rx_ready[i])begin:consume
     reg[511:0]d;d=rx_data[i*512+:512];
     if(d[10:8]!=3'(i)||d[13:11]!=0||d[29:14]!=rx_seq[i])fault<=1;
     else begin
      rx_seq[i]<=rx_seq[i]+1'b1;
      case(d[7:0])
       1:begin
        if(request_queued[i]||request_ack[i]||d[511:159]!=0||
          ((!allocated_valid||d[88:30]!=allocated_tag||d[90:89]!=allocated_gen)&&
           (!terminal_active||{d[88:73],6'd37,d[66:30]}!=accepted_tag||d[90:89]!=accepted_gen)))fault<=1;
        else begin request_queued[i]<=1;if(!terminal_active&&!terminal_accepted)participant_valid[i]<=1;participant_tag[i*59+:59]<=d[88:30];participant_gen[i*2+:2]<=d[90:89];participant_trace[i*32+:32]<=d[122:91];participant_token[i*18+:18]<=d[140:123];participant_pos[i*18+:18]<=d[158:141];end
       end
       2:begin
        if(cancel_valid[i]||cancel_ack[i]||d[511:97]!=0||(!d[91]&&!d[92]))fault<=1;
        else begin cancel_valid[i]<=1;cancel_tag[i*59+:59]<=d[88:30];cancel_gen[i*2+:2]<=d[90:89];cancel_done[i]<=d[91];cancel_fault[i]<=d[92];end
       end
       3:begin
        if(d[511:137]!=0)fault<=1;
        else begin service_epoch[i*16+:16]<=d[136:121];service_ready[i]<=d[30];native_ready[i]<=d[31];kv_drained[i]<=d[32];vm_drained[i]<=d[33];collective_drained[i]<=d[34];host_drained[i]<=d[35];context_owned[i]<=d[36];link_reset_seen[i]<=d[37];retrained[i]<=d[38];links_drained[i]<=d[39];program_ready[i]<=d[40];program_epoch[i*16+:16]<=d[56:41];program_digest[i*64+:64]<=d[120:57];end
       end
       4:begin
        if(!result_busy||result_send[i]||result_return[i]||d[88:30]!=result_word[88:30]||d[90:89]!=result_word[90:89]||d[511:91]!=0)fault<=1;
        else result_return[i]<=1;
       end
       5:begin if(i!=0||d[511:72]!=0||step_issue_v)fault<=1;else begin step_issue_v<=1;step_client_tag<=d[45:30];step_slot<=d[53:46];step_pos<=d[71:54];end end
       6:begin if(i!=0||d[511:91]!=0||step_retire_v)fault<=1;else begin step_retire_v<=1;step_retire_client_tag<=d[45:30];step_retire_slot<=d[53:46];step_retire_pos<=d[71:54];step_retire_token<=d[89:72];step_retire_cq<=d[90];end end
       7:begin if(i!=0||d[511:90]!=0||cq_commit_v)fault<=1;else begin cq_commit_v<=1;cq_client_tag<=d[45:30];cq_slot<=d[53:46];cq_pos<=d[71:54];cq_token<=d[89:72];end end
       8:begin
        if(!terminal_active||terminal_send[i]||terminal_released[i]||d[88:30]!=accepted_tag||d[90:89]!=accepted_gen||d[511:91]!=0)fault<=1;
        else terminal_released[i]<=1;
       end
       9:begin if(d[511:144]!=0)fault<=1;else begin certificate_epoch[i*16+:16]<=d[143:128];certificate_valid[i]<=1;certificate[i*66+:66]<=d[95:30];certificate_prefix[i*32+:32]<=d[127:96];end end
       default:fault<=1;
      endcase
     end
    end
   end
  end
 end
endmodule
