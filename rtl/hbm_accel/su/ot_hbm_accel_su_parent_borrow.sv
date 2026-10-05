`timescale 1ns/1ps
// Model e72bb27c1: actual SM0 LSU borrower, CAP1, no software grant.
// Request debt starts at producer acceptance and ends at producer response
// consumption. CDC arrival is not retirement. All prior clients are monitored.
module ot_hbm_accel_su_parent_borrow #(
 parameter integer ENABLE=0,NSM=2,NC=2*NSM,MAXO=32
)(
 input wire clk,rst_n,
 input wire [NSM-1:0] launch_v,sm_busy,
 input wire [31:0] launch_pc,
 input wire su_done,su_fault,
 output reg pending,owned,done,fault,
 output reg [31:0] selected_pc,
 input wire [NC-1:0] observe_req,observe_rsp,
 input wire [NC*16-1:0] observe_req_tag,observe_rsp_tag,
 input wire [NC-1:0] observe_req_we,observe_rsp_we,
 input wire sm_req_v,output wire sm_req_rdy,input wire [336:0] sm_req,
 output wire sm_rsp_v,input wire sm_rsp_rdy,output wire [272:0] sm_rsp,
 input wire su_req_v,output wire su_req_rdy,input wire [336:0] su_req,
 output wire su_rsp_v,input wire su_rsp_rdy,output wire [272:0] su_rsp,
 output wire req_v,input wire req_rdy,output wire [336:0] req,
 input wire rsp_v,output wire rsp_rdy,input wire [272:0] rsp
);
 import ot_gpu_w6_secded_pkg::*;
 // 32*(tag16+kind1+valid1)=576 bits/client, packed into nine SECDED words.
 reg [71:0] ledger[0:NC*9-1];
 reg [71:0] request_hold[0:5],response_hold[0:4];
 reg [3:0] rq_age,rs_age;
 reg rq_captured,rs_captured,inflight,request_sent;
 reg [15:0] inflight_tag;
 reg inflight_we;
 reg [2:0] quiet_age;
 wire source_v=owned?su_req_v:sm_req_v;
 wire [336:0] source_req=owned?su_req:sm_req;
 wire sink_rdy=owned?su_rsp_rdy:sm_rsp_rdy;
 wire [383:0] request_raw;
 wire [319:0] response_raw;
 wire [NC*576-1:0] ledger_raw;
 wire [NC*9-1:0] ledger_bad;
 wire [5:0] request_bad;
 wire [4:0] response_bad;
 genvar g;
 generate for(g=0;g<NC*9;g=g+1) begin:g_ledger
  wire [65:0] q=decode64(ledger[g]);
  assign ledger_raw[g*64+:64]=q[63:0];
  assign ledger_bad[g]=|q[65:64];
 end
 for(g=0;g<6;g=g+1) begin:g_request
  wire [65:0] q=decode64(request_hold[g]);
  assign request_raw[g*64+:64]=q[63:0];assign request_bad[g]=|q[65:64];
 end
 for(g=0;g<5;g=g+1) begin:g_response
  wire [65:0] q=decode64(response_hold[g]);
  assign response_raw[g*64+:64]=q[63:0];assign response_bad[g]=|q[65:64];
 end endgenerate
 assign req=request_raw[336:0];assign sm_rsp=response_raw[272:0];assign su_rsp=sm_rsp;
 assign req_v=ENABLE && !fault && rq_captured && rq_age==5 && !(|request_bad);
 assign sm_req_rdy=ENABLE && !owned && !fault && !inflight && !rq_captured && rq_age==2;
 assign su_req_rdy=ENABLE && owned && !fault && !inflight && !rq_captured && rq_age==2;
 wire response_matches=inflight && request_sent && rsp[272:257]==inflight_tag && rsp[256]==inflight_we;
 assign rsp_rdy=ENABLE && !fault && !rs_captured && rs_age==2 && response_matches;
 assign sm_rsp_v=ENABLE && !owned && !fault && rs_captured && rs_age==5 && !(|response_bad);
 assign su_rsp_v=ENABLE && owned && !fault && rs_captured && rs_age==5 && !(|response_bad);
 reg [NC*576-1:0] ledger_next;
 reg ledger_fault,debt;
 integer c,i,free_slot,matched_slot,duplicates;
 always @* begin
  ledger_next=ledger_raw;ledger_fault=0;debt=0;
  for(c=0;c<NC;c=c+1) begin
   matched_slot=-1;free_slot=-1;duplicates=0;
   for(i=0;i<MAXO;i=i+1) begin
    if(ledger_raw[c*576+i*18+17]) begin
     debt=1;
     if(ledger_raw[c*576+i*18+:16]==observe_rsp_tag[c*16+:16] &&
        ledger_raw[c*576+i*18+16]==observe_rsp_we[c]) matched_slot=i;
     if(ledger_raw[c*576+i*18+:16]==observe_req_tag[c*16+:16]) duplicates=duplicates+1;
    end else if(free_slot<0) free_slot=i;
   end
   // Retire only the real old producer's accepted response edge.
   if(observe_rsp[c]) begin
    if(matched_slot<0) ledger_fault=1;
    else begin
     ledger_next[c*576+matched_slot*18+:18]=0;
     if(free_slot<0) free_slot=matched_slot;
    end
   end
   if(observe_req[c]) begin
    if(free_slot<0 || (duplicates!=0 && !(observe_rsp[c] &&
       observe_req_tag[c*16+:16]==observe_rsp_tag[c*16+:16]))) ledger_fault=1;
    else ledger_next[c*576+free_slot*18+:18]={1'b1,observe_req_we[c],observe_req_tag[c*16+:16]};
   end
  end
 end
 integer k;
 wire source_accept=source_v && (owned?su_req_rdy:sm_req_rdy);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   pending<=0;owned<=0;done<=0;fault<=0;selected_pc<=0;quiet_age<=0;
   rq_age<=0;rs_age<=0;rq_captured<=0;rs_captured<=0;inflight<=0;request_sent<=0;
   inflight_tag<=0;inflight_we<=0;
   for(k=0;k<NC*9;k=k+1) ledger[k]<=encode64(0);
   for(k=0;k<6;k=k+1) request_hold[k]<=encode64(0);
   for(k=0;k<5;k=k+1) response_hold[k]<=encode64(0);
  end else if(ENABLE) begin
   done<=0;
   if(ledger_fault || (|ledger_bad) || su_fault) fault<=1;
   for(k=0;k<NC*9;k=k+1) ledger[k]<=encode64(ledger_next[k*64+:64]);
   if(!fault) begin
    if((|launch_v) && launch_pc[31]) begin
     if(pending || owned || launch_v!={{(NSM-1){1'b0}},1'b1}) fault<=1;
     else begin pending<=1;selected_pc<=launch_pc;end
    end
    if(debt || (|observe_req) || (|observe_rsp) || (|sm_busy) ||
       (|launch_v) || rq_captured || rs_captured || inflight) quiet_age<=0;
    else if(quiet_age<3) quiet_age<=quiet_age+1;
    if(pending && quiet_age==3 && !debt && !(|sm_busy) && !(|launch_v) &&
       !(|observe_req) && !(|observe_rsp) && !source_v &&
       !inflight && !rq_captured && !rs_captured) begin
     owned<=1;pending<=0;quiet_age<=0;
    end
    // Source must hold until the end of the two-edge encode interval.
    if(!inflight && !rq_captured) begin
     if(source_v) begin
      if(rq_age<2) rq_age<=rq_age+1;
      if(source_accept) begin
       for(k=0;k<6;k=k+1) request_hold[k]<=encode64(({47'd0,source_req}>>(k*64)));
       rq_captured<=1;rq_age<=3;inflight<=1;request_sent<=0;
       inflight_tag<=source_req[15:0];inflight_we<=source_req[336];
      end
     end else rq_age<=0;
    end else if(rq_captured && rq_age<5) rq_age<=rq_age+1;
    if(req_v && req_rdy) begin rq_captured<=0;rq_age<=0;request_sent<=1;end
    if(rsp_v && !rs_captured && response_matches) begin
     if(rs_age<2) rs_age<=rs_age+1;
     if(rsp_rdy) begin
      for(k=0;k<5;k=k+1) response_hold[k]<=encode64(({47'd0,rsp}>>(k*64)));
      rs_captured<=1;rs_age<=3;
     end
    end else if(rs_captured && rs_age<5) rs_age<=rs_age+1;
    if((owned?su_rsp_v:sm_rsp_v) && sink_rdy) begin
     rs_captured<=0;rs_age<=0;inflight<=0;request_sent<=0;
    end
    if((rq_captured && |request_bad) || (rs_captured && |response_bad)) fault<=1;
    // No terminal pulse/lease release until the real route is empty.
    if(owned && su_done && !debt && !inflight && !rq_captured && !rs_captured &&
       !(|observe_req) && !(|observe_rsp)) begin owned<=0;done<=1;end
   end
  end
 end
 initial if(ENABLE && (MAXO!=32 || NC!=2*NSM)) $fatal(1,"priced DS20 prior-credit inventory");
endmodule
