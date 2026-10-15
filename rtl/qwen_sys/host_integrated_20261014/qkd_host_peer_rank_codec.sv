`timescale 1ns/1ps
// Native-rank class9 endpoint. Ordered packet sequence belongs to this source,
// not the compiler token schedule. Every action ACK carries the full identity.
// Header payload: opcode[7:0], source rank[10:8], destination rank[13:11],
// sequence[29:14]. No request reservation is returned on transmission alone.
module qkd_host_peer_rank_codec #(parameter[2:0]RANK=0)(
 input wire ck,por_n,
 output wire tx_valid,output reg[511:0]tx_data,input wire tx_ready,
 input wire rx_valid,input wire[511:0]rx_data,output wire rx_ready,
 input wire request_v,input wire[58:0]request_tag,input wire[1:0]request_gen,
 input wire[31:0]request_trace,input wire[17:0]request_token,request_pos,output reg request_cr,request_aborted,
 input wire cancel_valid,input wire[58:0]cancel_tag,input wire[1:0]cancel_gen,input wire cancel_done,cancel_fault,input wire[3:0]cancel_drained,
 output reg cancel_accepted,cancel_release_v,output reg[58:0]cancel_release_tag,output reg[1:0]cancel_release_gen,input wire cancel_released,
 output reg result_v,output reg[58:0]result_tag,output reg[1:0]result_gen,output reg result_done,result_fault,
 output reg[3:0]result_cause,output reg[17:0]result_token,output reg[31:0]result_value,result_cycles,input wire result_cr,
 input wire service_ready,native_ready,input wire[15:0]service_epoch,input wire[3:0]drained,input wire context_owned,links_drained,link_reset_seen,retrained,
 input wire program_ready,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire step_issue_v,input wire[15:0]step_client_tag,input wire[7:0]step_slot,input wire[17:0]step_pos,
 input wire step_retire_v,step_retire_cq,input wire[15:0]step_retire_client_tag,input wire[7:0]step_retire_slot,input wire[17:0]step_retire_pos,step_retire_token,
 input wire cq_commit_v,input wire[15:0]cq_client_tag,input wire[7:0]cq_slot,input wire[17:0]cq_pos,cq_token,
 input wire certificate_v,input wire[65:0]certificate,input wire[31:0]certificate_prefix,
 output reg allocated_valid,allocated_delivered,output reg[15:0]allocated_epoch,output reg[17:0]allocated_token,allocated_position,output reg[1:0]allocated_gen,
 output reg reset_request,retrain_request,recovery_clear,output reg fault);
 reg[15:0]tx_seq,rx_seq;reg recovery_saw_reset,recovery_saw_train;
 reg req_pending,req_sent,cancel_pending,cancel_sent,cancel_seen,result_busy,barrier_wait;
 reg[511:0]req_word,cancel_word,step_word,retire_word,cq_word,cert_word;
 reg step_pending,retire_pending,cq_pending,cert_pending,credit_pending,release_pending;
 reg[58:0]last_result_tag,last_cancel_tag;reg[1:0]last_result_gen,last_cancel_gen;
 wire[106:0]status={service_epoch,program_digest,program_epoch,program_ready,links_drained,retrained,link_reset_seen,context_owned,drained,native_ready,service_ready};
 reg[106:0]last_status;reg status_sent;
 reg[3:0]choice;
 assign rx_ready=!fault;
 assign tx_valid=choice!=0&&!fault;
 always @*begin
  choice=0;tx_data=0;
  if(credit_pending)begin choice=4;tx_data[88:30]=last_result_tag;tx_data[90:89]=last_result_gen;end
  else if(release_pending)begin choice=8;tx_data[88:30]=last_cancel_tag;tx_data[90:89]=last_cancel_gen;end
  else if(cancel_pending&&!cancel_sent)begin choice=2;tx_data=cancel_word;end
  else if(req_pending&&!req_sent)begin choice=1;tx_data=req_word;end
  else if(step_pending)begin choice=5;tx_data=step_word;end
  else if(retire_pending)begin choice=6;tx_data=retire_word;end
  else if(cq_pending)begin choice=7;tx_data=cq_word;end
  else if(cert_pending)begin choice=9;tx_data=cert_word;end
  else if(!status_sent||status!=last_status)begin choice=3;tx_data[136:30]=status;end
  tx_data[7:0]={4'd0,choice};tx_data[10:8]=RANK;tx_data[13:11]=0;tx_data[29:14]=tx_seq;
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin
   recovery_saw_reset<=0;recovery_saw_train<=0;recovery_clear<=0;allocated_valid<=0;allocated_delivered<=0;allocated_epoch<=0;allocated_token<=0;allocated_position<=0;allocated_gen<=0;barrier_wait<=0;tx_seq<=0;rx_seq<=0;req_pending<=0;req_sent<=0;cancel_pending<=0;cancel_sent<=0;cancel_seen<=0;result_busy<=0;
   req_word<=0;cancel_word<=0;step_word<=0;retire_word<=0;cq_word<=0;cert_word<=0;step_pending<=0;retire_pending<=0;cq_pending<=0;cert_pending<=0;credit_pending<=0;release_pending<=0;
   last_result_tag<=0;last_cancel_tag<=0;last_result_gen<=0;last_cancel_gen<=0;last_status<=0;status_sent<=0;
   request_cr<=0;request_aborted<=0;cancel_accepted<=0;cancel_release_v<=0;cancel_release_tag<=0;cancel_release_gen<=0;
   result_v<=0;result_tag<=0;result_gen<=0;result_done<=0;result_fault<=0;result_cause<=0;result_token<=0;result_value<=0;result_cycles<=0;reset_request<=0;retrain_request<=0;fault<=0;
  end else begin
   request_cr<=0;request_aborted<=0;cancel_accepted<=0;cancel_release_v<=0;result_v<=0;recovery_clear<=0;
   if(!cancel_valid)cancel_seen<=0;
   if(request_v)begin
    if(req_pending)fault<=1;
    else begin req_pending<=1;req_sent<=0;req_word<=0;req_word[88:30]<=request_tag;req_word[90:89]<=request_gen;req_word[122:91]<=request_trace;req_word[140:123]<=request_token;req_word[158:141]<=request_pos;end
   end
   if(cancel_valid&&!cancel_seen)begin
    if(cancel_pending)fault<=1;
    else begin cancel_seen<=1;cancel_pending<=1;cancel_sent<=0;last_cancel_tag<=cancel_tag;last_cancel_gen<=cancel_gen;
     cancel_word<=0;cancel_word[88:30]<=cancel_tag;cancel_word[90:89]<=cancel_gen;cancel_word[91]<=cancel_done;cancel_word[92]<=cancel_fault;cancel_word[96:93]<=cancel_drained;end
   end
   if(cancel_released)begin if(release_pending||!barrier_wait)fault<=1;else begin release_pending<=1;barrier_wait<=0;end end
   if(result_cr)begin
    if(!result_busy||credit_pending)fault<=1;
    else begin result_busy<=0;credit_pending<=1;end
   end
   if(step_issue_v)begin
    if(RANK!=0||step_pending)fault<=1;else begin step_pending<=1;step_word<=0;step_word[45:30]<=step_client_tag;step_word[53:46]<=step_slot;step_word[71:54]<=step_pos;end
   end
   if(step_retire_v)begin
    if(RANK!=0||retire_pending)fault<=1;else begin retire_pending<=1;retire_word<=0;retire_word[45:30]<=step_retire_client_tag;retire_word[53:46]<=step_retire_slot;retire_word[71:54]<=step_retire_pos;retire_word[89:72]<=step_retire_token;retire_word[90]<=step_retire_cq;end
   end
   if(cq_commit_v)begin
    if(RANK!=0||cq_pending)fault<=1;else begin cq_pending<=1;cq_word<=0;cq_word[45:30]<=cq_client_tag;cq_word[53:46]<=cq_slot;cq_word[71:54]<=cq_pos;cq_word[89:72]<=cq_token;end
   end
   if(certificate_v)begin
    if(cert_pending)fault<=1;else begin cert_pending<=1;cert_word<=0;cert_word[95:30]<=certificate;cert_word[127:96]<=certificate_prefix;cert_word[143:128]<=service_epoch;end
   end
   if(tx_valid&&tx_ready)begin
    tx_seq<=tx_seq+1'b1;
    case(choice)
     1:req_sent<=1;2:cancel_sent<=1;3:begin last_status<=status;status_sent<=1;end
     4:credit_pending<=0;5:step_pending<=0;6:retire_pending<=0;7:cq_pending<=0;8:release_pending<=0;9:cert_pending<=0;default:fault<=1;
    endcase
   end
   if(rx_valid&&rx_ready)begin
    if(rx_data[10:8]!=0||rx_data[13:11]!=RANK||rx_data[29:14]!=rx_seq)fault<=1;
    else begin
     rx_seq<=rx_seq+1'b1;
     case(rx_data[7:0])
      8'h81:begin
       if(!req_pending||!req_sent||rx_data[88:30]!=req_word[88:30]||rx_data[90:89]!=req_word[90:89]||rx_data[511:92]!=0)fault<=1;
       else begin req_pending<=0;req_sent<=0;request_cr<=1;request_aborted<=rx_data[91];end
      end
      8'h82:begin
       if(!cancel_pending||!cancel_sent||rx_data[88:30]!=cancel_word[88:30]||rx_data[90:89]!=cancel_word[90:89]||rx_data[511:91]!=0)fault<=1;
       else begin cancel_pending<=0;cancel_sent<=0;cancel_accepted<=1;end
      end
      8'h83:begin
       if(result_busy||credit_pending||rx_data[511:179]!=0||(!rx_data[91]&&!rx_data[92]))fault<=1;
       else begin
        result_busy<=1;result_v<=1;result_tag<=rx_data[88:30];result_gen<=rx_data[90:89];result_done<=rx_data[91];result_fault<=rx_data[92];result_cause<=rx_data[96:93];result_token<=rx_data[114:97];result_value<=rx_data[146:115];result_cycles<=rx_data[178:147];last_result_tag<=rx_data[88:30];last_result_gen<=rx_data[90:89];
       end
      end
      8'h84:begin
       if(rx_data[511:32]!=0)fault<=1;
       else begin
        reset_request<=rx_data[30];retrain_request<=rx_data[31];
        if(rx_data[30])recovery_saw_reset<=1;
        if(rx_data[31]&&recovery_saw_reset)recovery_saw_train<=1;
        if(rx_data[31:30]==0&&recovery_saw_reset&&recovery_saw_train)begin recovery_clear<=1;recovery_saw_reset<=0;recovery_saw_train<=0;end
       end
      end
      8'h85:begin
       if(rx_data[511:91]!=0||release_pending||barrier_wait||
         (cancel_pending&&(rx_data[88:30]!=cancel_word[88:30]||rx_data[90:89]!=cancel_word[90:89])))fault<=1;
       else begin barrier_wait<=1;cancel_release_v<=1;cancel_release_tag<=rx_data[88:30];cancel_release_gen<=rx_data[90:89];last_cancel_tag<=rx_data[88:30];last_cancel_gen<=rx_data[90:89];end
      end
      8'h86:begin
       if(rx_data[511:111]!=0)fault<=1;
       else begin allocated_valid<=rx_data[30];allocated_delivered<=rx_data[31];allocated_epoch<=rx_data[90:75];allocated_token<=rx_data[68:51];allocated_position<=rx_data[110:93];allocated_gen<=rx_data[92:91];end
      end
      default:fault<=1;
     endcase
    end
   end
  end
 end
endmodule
