`timescale 1ns/1ps
// One rank-local join of the literal32 existing SM RF/commonACK responders.
// Parent hold is the actual enclosing all-eight-cohort drain ownership.
module ot_gpu_qwen_rf_ack_drain_join #(parameter ENABLE=0)(
 input wire clk,por_n,rst_n,run_enable,
 input wire drain_req_valid,output wire drain_req_ready,
 input wire [63:0] drain_req_identity,input wire [19:0] drain_req_key,input wire drain_hold,
 output wire [31:0] leaf_req_valid,input wire [31:0] leaf_req_ready,
 output wire [63:0] leaf_identity,output wire [19:0] leaf_key,output wire [31:0] leaf_hold,
 input wire [31:0] leaf_rsp_valid,output wire [31:0] leaf_rsp_ready,
 input wire [2687:0] leaf_rsp_tuple,input wire [31:0] leaf_rsp_empty,leaf_fault,
 output wire drain_rsp_valid,input wire drain_rsp_ready,
 output wire [63:0] drain_rsp_identity,output wire [19:0] drain_rsp_key,
 output wire drain_rsp_empty,drain_retained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:enabled
 reg [215:0] protected_state;wire [191:0] raw;wire [2:0] ue;genvar g;
 for(g=0;g<3;g=g+1)begin:decode
  wire [65:0] d=decode64(protected_state[g*72+:72]);
  assign raw[g*64+:64]=d[63:0];assign ue[g]=d[65];
 end
 wire bad=(|ue)||(|raw[191:151]);
 wire [63:0] did=raw[63:0];wire [19:0] dkey=raw[83:64];
 wire [31:0] sent=raw[115:84],seen=raw[147:116];wire active=raw[148],responded=raw[149];
 wire [31:0] wrong;
 for(g=0;g<32;g=g+1)begin:match
  assign wrong[g]=leaf_rsp_valid[g]&&(!active||!sent[g]||seen[g]||
                         !leaf_rsp_empty[g]||leaf_rsp_tuple[g*84+:84]!={dkey,did});
 end
 wire current_fault=bad||raw[150]||(|leaf_fault)||(|wrong)||(!rst_n&&active);
 wire live=por_n&&rst_n&&run_enable&&!current_fault;
 assign fault=current_fault;assign drain_retained=active;
 assign drain_req_ready=live&&!active;
 assign leaf_req_valid={32{live&&active}}&~sent;
 assign leaf_identity=did;assign leaf_key=dkey;
 assign leaf_hold={32{active}}; // ownership survives faults and runtime reset
 assign leaf_rsp_ready={32{live&&active}}&sent&~seen;
 assign drain_rsp_valid=live&&active&&!responded&&(&seen);
 assign drain_rsp_identity=did;assign drain_rsp_key=dkey;assign drain_rsp_empty=drain_rsp_valid;
 reg [191:0] n;integer j,k;
 always @*begin
  n=raw;
  if(live)begin
   if(drain_req_valid&&drain_req_ready)begin
    n[63:0]=drain_req_identity;n[83:64]=drain_req_key;n[147:84]=0;n[148]=1;n[149]=0;
    if(!drain_hold||drain_req_key[19:14]>=36)n[150]=1;
   end
   for(j=0;j<32;j=j+1)begin
    if(leaf_req_valid[j]&&leaf_req_ready[j])n[84+j]=1;
    if(leaf_rsp_valid[j]&&leaf_rsp_ready[j])n[116+j]=1;
   end
   if(drain_rsp_valid&&drain_rsp_ready)n[149]=1;
   if(active&&!drain_hold)begin
    if(!responded)n[150]=1;else begin n[148]=0;n[149]=0;n[147:84]=0;end
   end
  end
  if(current_fault)n[150]=1;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin for(k=0;k<3;k=k+1)protected_state[k*72+:72]<=encode64(64'd0);end
  else if(!bad)begin for(k=0;k<3;k=k+1)protected_state[k*72+:72]<=encode64(n[k*64+:64]);end
 end
 end else begin:disabled
 assign drain_req_ready=0;assign leaf_req_valid=0;assign leaf_identity=0;assign leaf_key=0;assign leaf_hold=0;
 assign leaf_rsp_ready=0;assign drain_rsp_valid=0;assign drain_rsp_identity=0;assign drain_rsp_key=0;
 assign drain_rsp_empty=0;assign drain_retained=0;assign fault=0;
 end endgenerate
endmodule
