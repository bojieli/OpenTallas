`timescale 1ns/1ps
// Default-off source bridge. The existing KV controller owns reader leases and
// SCORES-before-PV ordering. This bridge retains ONE full native operator tuple
// per rank; a primitive or the PC40 NEG/FMAX/FMIN fragment is not that operator.
// All inputs below are enclosing actual endpoint handshakes, not timer events.
module ot_gpu_qwen_native_consumer_drain #(parameter ENABLE=0)(
 input wire clk,por_n,rst_n,run_enable,endpoint_fault,
 input wire native_issue_valid,output wire native_issue_ready,
 input wire [229:0] native_issue_tuple,
 input wire native_complete_valid,output wire native_complete_ready,
 input wire [229:0] native_complete_tuple,
 input wire native_reverse_valid,output wire native_reverse_ready,
 input wire [229:0] native_reverse_tuple,
 // Tuple = {stage1,key20,reader_lease64,rank1,SM5,PC11,native_generation64,native_tag64}.
 output wire consumer_valid,input wire consumer_ready,
 output wire [63:0] consumer_identity,output wire [19:0] consumer_key,
 output wire consumer_stage,consumer_accepted,consumer_reverse,
 input wire drain_valid,output wire drain_ready,
 input wire [63:0] drain_identity,input wire [19:0] drain_key,
 // Cohort order: stage,payload-request,payload-return,metadata,RF/commonACK,
 // consumer,requestCDC,reverseCDC. Each endpoint must stop NEW key-matching
 // admission while quiesce is asserted and retain a matching empty response.
 output wire [7:0] cohort_quiesce,cohort_req_valid,input wire [7:0] cohort_req_ready,
 output wire [63:0] cohort_identity,output wire [19:0] cohort_key,
 input wire [7:0] cohort_rsp_valid,output wire [7:0] cohort_rsp_ready,
 input wire [671:0] cohort_rsp_tuple,input wire [7:0] cohort_rsp_empty,
 output wire drain_done_valid,input wire drain_done_ready,
 output wire [63:0] drain_done_identity,output wire [19:0] drain_done_key,
 output wire [7:0] drain_done_allcopies,
 output wire native_retained,drain_retained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:enabled
 reg [431:0] control;
 wire [383:0] raw;
 wire [5:0] uncorrectable;
 genvar g;
 for(g=0;g<6;g=g+1)begin:decode
  wire [65:0] decoded=decode64(control[g*72+:72]);
  assign raw[g*64+:64]=decoded[63:0];assign uncorrectable[g]=decoded[65];
 end
 wire bad=(|uncorrectable)||(|raw[383:335]);
 wire [229:0] owner=raw[229:0];
 wire active=raw[230],completed=raw[231],reversed=raw[232];
 wire [63:0] did=raw[296:233];wire [19:0] dkey=raw[316:297];
 wire [7:0] sent=raw[324:317],seen=raw[332:325];wire draining=raw[333];
 wire [19:0] ikey=native_issue_tuple[228:209];
 wire istage=native_issue_tuple[229];
 wire [10:0] expected_PC=({5'd0,ikey[19:14]}<<5)+({5'd0,ikey[19:14]}<<4)+
                             11'd13+(ikey[13]?11'd16:11'd0)+(istage?11'd2:11'd0);
 wire issue_map_bad=ikey[19:14]>=36||native_issue_tuple[138:128]!=expected_PC||
                    native_issue_tuple[144]!=ikey[13];
 wire complete_bad=native_complete_valid&&(!active||completed||native_complete_tuple!=owner);
 wire reverse_bad=native_reverse_valid&&(!active||!completed||reversed||native_reverse_tuple!=owner);
 wire [7:0] cohort_bad;
 for(g=0;g<8;g=g+1)begin:check
  assign cohort_bad[g]=cohort_rsp_valid[g]&&(!draining||!sent[g]||seen[g]||
               !cohort_rsp_empty[g]||cohort_rsp_tuple[g*84+:84]!={dkey,did});
 end
 // CURRENT bad cones depend on raw observations/retained state, never permits.
 wire current_bad=bad||raw[334]||endpoint_fault||complete_bad||reverse_bad||(|cohort_bad)||
              (native_issue_valid&&!active&&!draining&&issue_map_bad)||
              (!rst_n&&(active||draining));
 wire live=por_n&&rst_n&&run_enable&&!current_bad;
 assign fault=current_bad;assign native_retained=active;assign drain_retained=draining;
 assign native_issue_ready=live&&!active&&!draining&&!drain_valid;
 assign native_complete_ready=live&&active&&!completed;
 assign native_reverse_ready=live&&active&&completed&&!reversed;
 assign consumer_valid=live&&active&&completed&&reversed;
 assign consumer_identity=owner[208:145];assign consumer_key=owner[228:209];
 assign consumer_stage=owner[229];assign consumer_accepted=consumer_valid;
 assign consumer_reverse=consumer_valid;
 assign drain_ready=live&&!active&&!draining;
 // Quiesce is ownership, not a permit: retain it during runtime reset/fault.
 assign cohort_quiesce={8{draining}};
 assign cohort_req_valid={8{live&&draining}}&~sent;
 assign cohort_identity=did;assign cohort_key=dkey;
 assign cohort_rsp_ready={8{live&&draining}}&sent&~seen;
 assign drain_done_valid=live&&draining&&(&seen);
 assign drain_done_identity=did;assign drain_done_key=dkey;
 assign drain_done_allcopies=seen; // ONLY matching captured endpoint responses.
 reg [383:0] next_raw;
 integer j;
 always @*begin
  next_raw=raw;
  if(live)begin
   if(native_issue_valid&&native_issue_ready)begin
    next_raw[229:0]=native_issue_tuple;next_raw[230]=1;next_raw[232:231]=0;
   end
   if(native_complete_valid&&native_complete_ready)next_raw[231]=1;
   if(native_reverse_valid&&native_reverse_ready)next_raw[232]=1;
   if(consumer_valid&&consumer_ready)next_raw[232:230]=0;
   if(drain_valid&&drain_ready)begin
    next_raw[296:233]=drain_identity;next_raw[316:297]=drain_key;
    next_raw[332:317]=0;next_raw[333]=1;
    // Validate the controller's permit-masked command on its acceptance edge.
    // A bad key retains the captured drain owner and stops before endpoint issue.
    // Using drain_valid in CURRENT fault would feed the wrapper permit back into itself.
    if(drain_key[19:14]>=36)next_raw[334]=1;
   end
   for(j=0;j<8;j=j+1)begin
    if(cohort_req_valid[j]&&cohort_req_ready[j])next_raw[317+j]=1;
    if(cohort_rsp_valid[j]&&cohort_rsp_ready[j])next_raw[325+j]=1;
   end
   if(drain_done_valid&&drain_done_ready)begin next_raw[333]=0;next_raw[332:317]=0;end
  end
  if(current_bad)next_raw[334]=1;
 end
 integer k;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin for(k=0;k<6;k=k+1)control[k*72+:72]<=encode64(64'd0);end
  else if(!bad)begin for(k=0;k<6;k=k+1)control[k*72+:72]<=encode64(next_raw[k*64+:64]);end
 end
 end else begin:disabled
 assign native_issue_ready=0;assign native_complete_ready=0;assign native_reverse_ready=0;
 assign consumer_valid=0;assign consumer_identity=0;assign consumer_key=0;assign consumer_stage=0;
 assign consumer_accepted=0;assign consumer_reverse=0;assign drain_ready=0;
 assign cohort_quiesce=0;assign cohort_req_valid=0;assign cohort_identity=0;assign cohort_key=0;
 assign cohort_rsp_ready=0;assign drain_done_valid=0;assign drain_done_identity=0;
 assign drain_done_key=0;assign drain_done_allcopies=0;assign native_retained=0;assign drain_retained=0;assign fault=0;
 end endgenerate
endmodule
