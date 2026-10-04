`timescale 1ns/1ps
// Actual producer bytes enter through this port, never an RF testbench seed.
// Default off. Caller reserves owner46 and actual source/workspace leases.
// This endpoint retains RF38 past C0 completion; it cannot fabricate upstream
// retirement, global quiescence, an HBM identity, or reset rollback.
module ot_gpu_pc40_native_ingress #(parameter bit ENABLE=0)(
 input wire clk,por_n,rst_n,
 input wire publish_valid,output wire publish_ready,
 input wire [4095:0] publish_data,
 input wire [45:0] publish_owner46,
 input wire [63:0] publish_native_tag,publish_native_generation,
 input wire source_lease_reserved,workspace_reserved,issuer_namespace_reserved,
 input wire admission_stop,
 output wire c_req_valid,input wire c_req_ready,
 output wire [45:0] c_owner46,
 output wire [63:0] c_native_tag,c_native_generation,
 input wire c_wr_valid,output wire c_wr_ready,
 input wire [8:0] c_wr_slot,input wire [4095:0] c_wr_data,input wire [45:0] c_wr_owner,
 output wire c_ack_valid,input wire c_ack_ready,
 output wire [45:0] c_ack_owner,output wire [8:0] c_ack_slot,output wire c_ack_fault,
 output wire rf_wr_valid,input wire rf_wr_ready,
 output wire [8:0] rf_wr_slot,output wire [4095:0] rf_wr_data,output wire [45:0] rf_wr_owner,
 input wire rf_ack_valid,output wire rf_ack_ready,
 input wire [45:0] rf_ack_owner,input wire [8:0] rf_ack_slot,input wire rf_ack_fault,
 input wire c_done_valid,c_done_ready,input wire c_fault,
 input wire source_release_valid,input wire [54:0] source_release_identity,
 output wire source_release_ready,source_lease_live,workspace_lease_live,
 output wire source_published,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:enabled
 localparam [2:0] IDLE=0,WRITE=1,ACK=2,ISSUE=3,RUN=4,RETAIN=5;
 reg[215:0] context_q;
 reg[71:0] payload[0:63];
 wire[191:0] raw;wire[2:0] ctx_bad;wire[63:0] payload_bad;
 wire[4095:0] data;
 genvar k;
 for(k=0;k<3;k=k+1)begin:ctx
  wire[65:0]d=decode64(context_q[k*72+:72]);
  assign raw[k*64+:64]=d[63:0];assign ctx_bad[k]=d[65];
 end
 for(k=0;k<64;k=k+1)begin:body
  wire[65:0]d=decode64(payload[k]);assign data[k*64+:64]=d[63:0];assign payload_bad[k]=d[65];
 end
 wire[2:0]phase=raw[2:0];wire[45:0]owner=raw[49:4];
 wire bad=(|ctx_bad)||(|payload_bad)||(|raw[191:181])||raw[3]||phase>RETAIN;
 wire owned=phase!=IDLE;
 wire pub_ack_match=phase==ACK && rf_ack_owner==owner && rf_ack_slot==9'd38;
 wire unexpected_pub_ACK=rf_ack_valid && phase!=RUN && !pub_ack_match;
 wire release_bad=source_release_valid && (!owned || source_release_identity!={owner,9'd38});
 wire now_fault=bad||raw[178]||rf_ack_fault||c_fault||unexpected_pub_ACK||release_bad||
  (phase==RUN&&c_wr_valid&&c_wr_owner!=owner);
 wire live=por_n&&rst_n&&!now_fault;
 assign fault=now_fault;
 assign publish_ready=live&&phase==IDLE&&!admission_stop&&!rf_ack_valid&&
  source_lease_reserved&&workspace_reserved&&issuer_namespace_reserved&&publish_owner46[38:36]==0;
 assign c_req_valid=live&&phase==ISSUE&&!admission_stop;
 assign c_owner46=owner;assign c_native_tag=raw[113:50];assign c_native_generation=raw[177:114];
 assign rf_wr_valid=live&&((phase==WRITE&&!admission_stop)||(phase==RUN&&c_wr_valid));
 assign rf_wr_slot=phase==RUN?c_wr_slot:9'd38;
 assign rf_wr_data=phase==RUN?c_wr_data:data;
 assign rf_wr_owner=phase==RUN?c_wr_owner:owner;
 // Source request acceptance checks idle write-ready before it has a write.
 assign c_wr_ready=live&&(phase==RUN||phase==ISSUE)&&rf_wr_ready;
 assign rf_ack_ready=live&&((phase==ACK&&pub_ack_match&&raw[179])||(phase==RUN&&c_ack_ready));
 assign c_ack_valid=phase==RUN&&rf_ack_valid;
 assign c_ack_owner=rf_ack_owner;assign c_ack_slot=rf_ack_slot;assign c_ack_fault=rf_ack_fault;
 assign source_lease_live=owned;assign workspace_lease_live=owned&&phase!=RETAIN;
 assign source_published=owned&&phase>=ISSUE;
 assign source_release_ready=live&&phase==RETAIN&&source_release_identity=={owner,9'd38}&&!rf_ack_valid;
 reg[191:0] n;
 always @*begin
  n=raw;
  if(publish_valid&&publish_ready)begin
   n='0;n[2:0]=WRITE;n[49:4]=publish_owner46;
   n[113:50]=publish_native_tag;n[177:114]=publish_native_generation;
  end else if(live)begin
   case(phase)
    WRITE:if(rf_wr_valid&&rf_wr_ready)n[2:0]=ACK;
    ACK:if(rf_ack_valid&&pub_ack_match)begin
     n[179]=1;
     if(rf_ack_ready)begin n[2:0]=ISSUE;n[179]=0;end
    end
    ISSUE:if(c_req_valid&&c_req_ready)n[2:0]=RUN;
    RUN:if(c_done_valid&&c_done_ready)begin n[2:0]=RETAIN;n[180]=1;end
    RETAIN:if(source_release_valid&&source_release_ready)n='0;
    default:begin end
   endcase
  end
  if(now_fault || (!rst_n&&owned))n[178]=1;
 end
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin context_q<=0;for(i=0;i<64;i=i+1)payload[i]<=0;end
  else if(!bad)begin
   for(i=0;i<3;i=i+1)context_q[i*72+:72]<=encode64(n[i*64+:64]);
   if(publish_valid&&publish_ready)for(i=0;i<64;i=i+1)payload[i]<=encode64(publish_data[i*64+:64]);
  end
 end
 end else begin:disabled
 assign publish_ready=0;assign c_req_valid=0;assign c_owner46=0;
 assign c_native_tag=0;assign c_native_generation=0;assign c_wr_ready=0;
 assign c_ack_valid=0;assign c_ack_owner=0;assign c_ack_slot=0;assign c_ack_fault=0;
 assign rf_wr_valid=0;assign rf_wr_slot=0;assign rf_wr_data=0;assign rf_wr_owner=0;assign rf_ack_ready=0;
 assign source_release_ready=0;assign source_lease_live=0;assign workspace_lease_live=0;
 assign source_published=0;assign fault=0;
 end endgenerate
endmodule
