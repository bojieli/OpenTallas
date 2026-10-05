`timescale 1ns/1ps
// Actual per-SM W4/W6 receipt observer and held RF/commonACK cohort responder.
// Caller binding_valid is a source issuer classification, including non-KV work.
// Never supply default false KV_related to hide a KV obligation.
module ot_gpu_qwen_rf_ack_drain #(parameter ENABLE=0)(
 input wire clk,por_n,rst_n,run_enable,source_fault,
 input wire rf_write_accept,input wire [54:0] rf_write_owner55,
 input wire wr_binding_valid,wr_KV_related,input wire [63:0] wr_identity,input wire [19:0] wr_key,
 output wire wr_permit,
 input wire rf_ack_valid,rf_ack_accept,input wire [54:0] rf_ack_owner55,input wire rf_ack_fault,
 output wire rf_ack_allow,
 input wire rf_read_accept,input wire [8:0] rf_read_a,rf_read_b,
 input wire rd_binding_valid,rd_KV_related,input wire [63:0] rd_identity,input wire [19:0] rd_key,
 output wire rd_permit,
 input wire rf_rsp_valid,rf_rsp_accept,output wire rf_rsp_allow,
 input wire w6_request_accept,input wire [54:0] w6_request_owner55,
 input wire w6_binding_valid,w6_KV_related,w6_internal_SIMD,
 input wire [63:0] w6_identity,input wire [19:0] w6_key,output wire w6_permit,
 input wire w6_host_ACK_accept,w6_SIMD_ACK_accept,input wire [54:0] w6_ACK_owner55,
 input wire w6_consumer_accept,input wire [54:0] w6_consumer_owner55,
 input wire w6_child_accept,input wire [54:0] w6_child_owner55,
 input wire w6_parent_accept,input wire [54:0] w6_parent_owner55,
 input wire w6_CDC_accept,input wire [54:0] w6_CDC_owner55,
 input wire w6_retire_accept,input wire [54:0] w6_retire_owner55,
 // Actual W6 retained drain tuple/owner/reset scope, including no-owner BOOT.
 input wire [54:0] w6_local_drain_owner55,
 input wire w6_local_drain_has_owner,w6_local_drain_reset_scope,
 input wire drain_req_valid,output wire drain_req_ready,
 input wire [63:0] drain_req_identity,input wire [19:0] drain_req_key,
 // Parent holds quiesce through the ALL-cohort response/release, not only this ACK.
 input wire drain_hold,
 output wire drain_rsp_valid,input wire drain_rsp_ready,
 output wire [63:0] drain_rsp_identity,output wire [19:0] drain_rsp_key,
 output wire drain_rsp_empty,drain_retained,
 output wire write_retained,read_retained,w6_retained,w6_local_RF_empty,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:enabled
 reg [575:0] protected_state;wire [511:0] raw;wire [7:0] ue;
 genvar g;
 for(g=0;g<8;g=g+1)begin:decode
  wire [65:0] d=decode64(protected_state[g*72+:72]);
  assign raw[g*64+:64]=d[63:0];assign ue[g]=d[65];
 end
 wire bad=(|ue)||(|raw[511:479]);
 wire wr_live=raw[140],rd_live=raw[244],w6_live=raw[385];
 wire draining=raw[476],responded=raw[477];wire [63:0] did=raw[455:392];wire [19:0] dkey=raw[475:456];
 wire write_match=wr_live&&raw[139]&&raw[138:119]==dkey;
 wire read_match=rd_live&&raw[243]&&raw[242:223]==dkey;
 wire w6_match=w6_live&&raw[384]&&raw[383:364]==dkey;
 wire matching_empty=!(write_match||read_match||w6_match);
 wire new_matching_accept=(rf_write_accept&&wr_KV_related&&wr_key==dkey)||
      (rf_read_accept&&rd_KV_related&&rd_key==dkey)||
      (w6_request_accept&&w6_KV_related&&w6_key==dkey);
 // Provider return observations are raw, never masked by these permits.
 wire ACK_bad=rf_ack_valid&&(!wr_live||rf_ack_owner55!=raw[54:0]||rf_ack_fault);
 wire response_bad=rf_rsp_valid&&!rd_live;
 wire current_fault=bad||raw[478]||source_fault||ACK_bad||response_bad||
                    (!rst_n&&(wr_live||rd_live||w6_live||draining));
 wire live=por_n&&rst_n&&run_enable&&!current_fault;
 wire stop=draining||drain_req_valid||drain_hold;
 wire [19:0] stop_key=draining?dkey:drain_req_key;
 assign wr_permit=live&&wr_binding_valid&&!wr_live&&!rd_live&&
                !(stop&&wr_KV_related&&wr_key==stop_key);
 assign rd_permit=live&&rd_binding_valid&&!rd_live&&!wr_live&&
                !(stop&&rd_KV_related&&rd_key==stop_key);
 assign w6_permit=live&&w6_binding_valid&&!w6_live&&
                !(stop&&w6_KV_related&&w6_key==stop_key);
 assign rf_ack_allow=live&&wr_live&&rf_ack_valid&&rf_ack_owner55==raw[54:0]&&!rf_ack_fault;
 assign rf_rsp_allow=live&&rd_live&&rf_rsp_valid;
 assign drain_req_ready=live&&!draining;
 assign drain_rsp_valid=live&&draining&&!responded&&matching_empty&&!new_matching_accept;
 assign drain_rsp_identity=did;assign drain_rsp_key=dkey;
 assign drain_rsp_empty=drain_rsp_valid;
 assign drain_retained=draining;assign write_retained=wr_live;assign read_retained=rd_live;
 assign w6_retained=w6_live;assign fault=current_fault;
 // W6's LOCAL allcopy RF bit excludes its own retained row to avoid waiting
 // for its own RETIRE. It still requires actual W4 receipts/held returns empty
 // and actual matching W6 ACK observed. This is NOT the KV cohort response.
 assign w6_local_RF_empty=live&&
    ((w6_local_drain_has_owner&&w6_live&&raw[387]&&w6_local_drain_owner55==raw[299:245])||
     (!w6_local_drain_has_owner&&w6_local_drain_reset_scope&&!w6_live))&&
    !wr_live&&!rd_live&&!rf_ack_valid&&!rf_rsp_valid&&!rf_write_accept&&!rf_read_accept;
 reg [511:0] n;integer j;
 always @*begin
  n=raw;
  // Observed ACCEPTED receipts are recorded even if a source admission adapter
  // violated a permit. Such a violation faults and preserves the received owner.
  if(rf_write_accept&&!wr_live)begin
   n[54:0]=rf_write_owner55;n[118:55]=wr_identity;n[138:119]=wr_key;
   n[139]=wr_KV_related;n[140]=1;
  end
  if(rf_read_accept&&!rd_live)begin
   n[149:141]=rf_read_a;n[158:150]=rf_read_b;n[222:159]=rd_identity;
   n[242:223]=rd_key;n[243]=rd_KV_related;n[244]=1;
  end
  if(w6_request_accept&&!w6_live)begin
   n[299:245]=w6_request_owner55;n[363:300]=w6_identity;n[383:364]=w6_key;
   n[384]=w6_KV_related;n[385]=1;n[386]=w6_internal_SIMD;n[391:387]=0;
  end
  if(rf_write_accept&&!wr_permit)n[478]=1;
  if(rf_read_accept&&!rd_permit)n[478]=1;
  if(w6_request_accept&&!w6_permit)n[478]=1;
  if(live)begin
   if(rf_ack_accept)begin
    if(!rf_ack_allow)n[478]=1;else n[140]=0;
   end
   if(rf_rsp_accept)begin
    if(!rf_rsp_allow)n[478]=1;else n[244]=0;
   end
   if(w6_host_ACK_accept||w6_SIMD_ACK_accept)begin
    if(!w6_live||raw[387]||w6_ACK_owner55!=raw[299:245]||
       (w6_host_ACK_accept&&raw[386])||(w6_SIMD_ACK_accept&&!raw[386])||
       (w6_host_ACK_accept&&w6_SIMD_ACK_accept))n[478]=1;
    else n[387]=1;
   end
   if(w6_consumer_accept)begin
    if(!w6_live||!raw[387]||raw[388]||w6_consumer_owner55!=raw[299:245])n[478]=1;
    else n[388]=1;
   end
   if(w6_child_accept)begin
    if(!w6_live||!raw[388]||raw[389]||w6_child_owner55!=raw[299:245])n[478]=1;
    else n[389]=1;
   end
   if(w6_parent_accept)begin
    if(!w6_live||!raw[389]||raw[390]||w6_parent_owner55!=raw[299:245])n[478]=1;
    else n[390]=1;
   end
   if(w6_CDC_accept)begin
    if(!w6_live||!raw[390]||raw[391]||w6_CDC_owner55!=raw[299:245])n[478]=1;
    else n[391]=1;
   end
   if(w6_retire_accept)begin
    if(!w6_live||!(&raw[391:387])||w6_retire_owner55!=raw[299:245])n[478]=1;
    else n[385]=0;
   end
   if(drain_req_valid&&drain_req_ready)begin
    n[455:392]=drain_req_identity;n[475:456]=drain_req_key;n[476]=1;n[477]=0;
    if(drain_req_key[19:14]>=36||!drain_hold)n[478]=1;
   end
   if(drain_rsp_valid&&drain_rsp_ready)n[477]=1;
   if(draining&&!drain_hold)begin
    if(!responded||!matching_empty)n[478]=1;else begin n[476]=0;n[477]=0;end
   end
  end
  if(current_fault)n[478]=1;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin for(j=0;j<8;j=j+1)protected_state[j*72+:72]<=encode64(64'd0);end
  else if(!bad)begin for(j=0;j<8;j=j+1)protected_state[j*72+:72]<=encode64(n[j*64+:64]);end
 end
 end else begin:disabled
 assign wr_permit=0;assign rd_permit=0;assign w6_permit=0;
 assign rf_ack_allow=0;assign rf_rsp_allow=0;assign drain_req_ready=0;assign drain_rsp_valid=0;
 assign drain_rsp_identity=0;assign drain_rsp_key=0;assign drain_rsp_empty=0;assign drain_retained=0;
 assign write_retained=0;assign read_retained=0;assign w6_retained=0;assign w6_local_RF_empty=0;assign fault=0;
 end endgenerate
endmodule
