`timescale 1ns/1ps
// DEFAULT_OFF executable binding from genuine transported HC182 to actual
// native execution and back to original TK93. No token/logit is synthesized.
// All faces use one compensated native/core clock family and pin registers.
// Request and result producer each starts with ONE reservation credit. Result
// slot returns only after genuine terminal result and all real drain flags.
// Shared token epoch16 is allocated once at die0 and transported with HC182.
// TAG59={epoch16,stage6,token18,position13,segment6}; terminal stage37/segment0.
// Trace32 is diagnostic only. Service-prefill epoch is a separate prerequisite.
module qkd_host_native_token_endpoint_cancel #(parameter integer ENABLE_NATIVE=0,MUT=0)(
 input wire ck,por_n,rst_n,input wire[181:0]hc,input wire[92:0]legacy_tk,
 input wire image_ready,input wire shared_epoch_valid,input wire[15:0]shared_epoch,
 output reg request_v,output reg[58:0]request_tag,output reg[31:0]request_trace,output reg[1:0]request_gen,
 output reg[17:0]request_token,request_pos,input wire request_cr,
 output reg[142:0]native_pr,
 input wire result_v,input wire[58:0]result_tag,input wire[1:0]result_gen,
 input wire result_done,result_fault,input wire[3:0]result_cause,
 input wire[17:0]result_token,input wire[31:0]result_value,result_cycles,
 output reg result_cr,
 input wire kv_drained,vm_drained,collective_drained,host_drained,collective_busy,kv_flush,
 input wire recovery_clear,input wire cancel_release_v,input wire[58:0]cancel_release_tag,input wire[1:0]cancel_release_gen,
 output wire context_owned,output reg cancel_released,output reg[92:0]local_tk,output reg protocol_fault
);
 reg[181:0]hc_q;reg[92:0]legacy_q;
 reg image_ready_q;
 reg cr_q,rv,rdone,rfault,kq,cq,cbq,kfq,vq,hq,epoch_valid_q;reg[15:0]epoch_q;reg[58:0]rtag;
 reg[31:0]rvv,rcy;reg[1:0]rg;reg[3:0]rcause;reg[17:0]rt;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
 image_ready_q<=0;hc_q<=0;legacy_q<=0;cr_q<=0;rv<=0;rdone<=0;rfault<=0;kq<=0;cq<=0;cbq<=0;kfq<=0;vq<=0;hq<=0;
 epoch_valid_q<=0;epoch_q<=0;rtag<=0;rvv<=0;rcy<=0;rg<=0;rcause<=0;rt<=0;
 end else begin
 image_ready_q<=image_ready;hc_q<=hc;legacy_q<=legacy_tk;cr_q<=request_cr;
 epoch_valid_q<=shared_epoch_valid;epoch_q<=shared_epoch;
 rv<=result_v;rtag<=result_tag;rg<=result_gen;rdone<=result_done;rfault<=result_fault;
 rcause<=result_cause;rt<=result_token;rvv<=result_value;rcy<=result_cycles;
 kq<=kv_drained;vq<=vm_drained;hq<=host_drained;cq<=collective_drained;cbq<=collective_busy;kfq<=kv_flush;
 end
 reg active,pending,issued,credit,seen,done_q,fault_q;
 assign context_owned=active||pending;
 reg released_valid;reg[58:0]released_tag;reg[1:0]released_gen;
 wire previously_retired=released_valid&&released_tag=={epoch_q,6'd37,hc_q[35:18],hc_q[12:0],6'd0}&&released_gen==hc_q[37:36];
 reg release_pending;reg[58:0]release_tag;reg[1:0]release_gen;
 wire release_matches=release_tag==terminal_tag&&release_gen==gen_q;
 wire release_fire=release_pending&&active&&release_matches&&(MUT==4||(kq&&vq&&cq&&hq))&&credit;
 reg[31:0]trace_counter,job_trace,cycles_q,value_q;reg[15:0]job_epoch;
 reg[1:0]gen_q;reg[17:0]token_q,pos_q,next_q;reg[3:0]cause_q;
 wire start=ENABLE_NATIVE&&hc_q[38]&&!protocol_fault&&!fault_q;
 wire accept=start&&(image_ready_q||MUT==5)&&(MUT==6||!previously_retired)&&!active&&!pending&&epoch_valid_q&&hc_q[17:13]==0;
 wire issue=ENABLE_NATIVE&&pending&&(credit||MUT==3)&&!protocol_fault&&!fault_q&&!release_pending&&!cancel_release_v;
 wire[58:0]terminal_tag={job_epoch,6'd37,token_q,pos_q[12:0],6'd0};
 wire result_ok=rv&&active&&issued&&!seen&&(MUT==2||(rtag==terminal_tag&&rg==gen_q));
 wire retire=active&&seen&&done_q&&(MUT==1||(kq&&vq&&cq&&hq))&&!protocol_fault;
 always @(posedge ck or negedge por_n)if(!por_n)trace_counter<=0;
 else if(rst_n&&accept)trace_counter<=trace_counter+1'b1;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
 active<=0;pending<=0;issued<=0;credit<=1;seen<=0;done_q<=0;fault_q<=0;
 job_epoch<=0;job_trace<=0;cycles_q<=0;value_q<=0;gen_q<=0;token_q<=0;pos_q<=0;next_q<=0;cause_q<=0;
 request_v<=0;request_tag<=0;request_trace<=0;request_gen<=0;request_token<=0;request_pos<=0;
 native_pr<=0;result_cr<=0;local_tk<=0;protocol_fault<=0;released_valid<=0;released_tag<=0;released_gen<=0;release_pending<=0;release_tag<=0;release_gen<=0;cancel_released<=0;
 end else begin
 native_pr<=hc_q[181:39];request_v<=0;result_cr<=0;cancel_released<=0;
 if(recovery_clear)begin
  if(active||pending||release_pending||!credit||!kq||!vq||!cq||!hq)protocol_fault<=1;
  else begin released_valid<=0;protocol_fault<=0;fault_q<=0;seen<=0;done_q<=0;cause_q<=0;end
 end
 if(cancel_release_v)begin
  if(release_pending||(active&&(cancel_release_tag!=terminal_tag||cancel_release_gen!=gen_q)))protocol_fault<=1;
  else begin release_pending<=1;release_tag<=cancel_release_tag;release_gen<=cancel_release_gen;end
 end
 if(!ENABLE_NATIVE)begin local_tk<=legacy_q;end
 else begin
  local_tk<={retire||(local_tk[92]&&!accept),gen_q,kq&&vq&&cq&&hq,
   fault_q||protocol_fault,(protocol_fault?4'hf:cause_q),cbq,kfq,next_q,value_q,cycles_q};
  if(start&&!accept)protocol_fault<=1;
  if(accept)begin
   active<=1;pending<=1;issued<=0;seen<=0;done_q<=0;
   job_epoch<=epoch_q;job_trace<=trace_counter+1'b1;gen_q<=hc_q[37:36];token_q<=hc_q[35:18];pos_q<=hc_q[17:0];
   local_tk[92]<=0;local_tk[91:90]<=hc_q[37:36];
  end
  if(cr_q&&credit&&!issue)protocol_fault<=1;
  else credit<=credit+1'(cr_q)-1'(issue);
  if(issue)begin
   request_v<=1;request_tag<={job_epoch,6'd0,token_q,pos_q[12:0],6'd0};request_trace<=job_trace;request_gen<=gen_q;
   request_token<=token_q;request_pos<=pos_q;pending<=0;issued<=1;
  end
  if(rv)begin
   if(!result_ok||(!rdone&&!rfault))protocol_fault<=1;
   else begin
    if(rfault)begin fault_q<=1;cause_q<=rcause;end
    if(rdone)begin seen<=1;done_q<=1;next_q<=rt;value_q<=rvv;cycles_q<=rcy;end
    else result_cr<=1; // nonterminal genuine fault alert occupies no result slot
   end
  end
  if(retire)begin active<=0;result_cr<=1;end
  // Exceptional coordinator acceptance releases only this owned context, after
  // all true drains and the original request reservation has been returned.
  // A fault-only alert already returned its own result slot at receipt.
  if(release_fire)begin
   active<=0;pending<=0;issued<=0;release_pending<=0;cancel_released<=1;released_valid<=1;released_tag<=release_tag;released_gen<=release_gen;
   if(seen&&done_q&&!retire)result_cr<=1;
  end
  if(release_pending&&!active&&!pending&&credit&&kq&&vq&&cq&&hq&&!start&&!hc_q[38]&&!hc[38]&&!request_v)begin release_pending<=0;cancel_released<=1;released_valid<=1;released_tag<=release_tag;released_gen<=release_gen;end
 end
 end
endmodule
