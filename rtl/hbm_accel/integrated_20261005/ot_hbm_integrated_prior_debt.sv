`timescale 1ns/1ps
// Passive native credit accounting ONLY; not a borrower or grant generator.
// Same accepted-request -> actual original-consumer-response lifetime as the
// bf3c2e832 standalone SU owner. 4 clients x 32 credits =36 W6 rows ONCE.
module ot_hbm_integrated_prior_debt #(parameter integer ENABLE=0,NC=4)(
 input wire clk,por_n,
 input wire [NC-1:0] observe_req,observe_rsp,observe_req_we,observe_rsp_we,
 input wire [NC*16-1:0] observe_req_tag,observe_rsp_tag,
 input wire [NC-1:0] return_offer,
 input wire [31:0] native_job,input wire [3:0] native_gen,
 input wire [16:0] native_token,input wire [19:0] native_pos,
 output wire [NC-1:0] response_authorized,
 output wire debt,violation,uncorrectable
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:off
 assign debt=0;assign violation=0;assign uncorrectable=0;assign response_authorized=0;
 end else begin:on
 initial if(NC!=4)$fatal(1,"priced DS20 native four-client ledger required");
 reg [71:0] code[0:NC*9-1];wire [NC*576-1:0] raw;
 // Full CP context is held once for all native outstanding credits. The actual
 // transport has no frame fields; parent prevents CP context retirement while
 // any old native credit is alive. Grant NEVER changes these two rows.
 reg [71:0] frame_lo,frame_hi;
 wire [65:0] fl=decode64(frame_lo),fh=decode64(frame_hi);
 wire [127:0] frame={fh[63:0],fl[63:0]};
 wire frame_match=frame[73]&&frame[31:0]==native_job&&frame[35:32]==native_gen&&
  frame[52:36]==native_token&&frame[72:53]==native_pos;
 wire [NC*9-1:0] bad;
 for(genvar k=0;k<NC*9;k=k+1)begin:rows
  wire [65:0] d=decode64(code[k]);assign raw[k*64+:64]=d[63:0];assign bad[k]=|d[65:64];
 end
 reg [NC*576-1:0] next_ledger;reg invalid;
 wire [NC*32-1:0] live_slots;
 wire held_debt=|live_slots;
 // Authorization reads only the pre-edge protected ledger/frame and offered
 // response tuple. It must never depend on the downstream consumption edge.
 // Keeping it out of the retirement block removes the native response-ready
 // feedback path without registering or manufacturing authorization.
 wire [NC-1:0] authorized;
 for(genvar ac=0;ac<NC;ac=ac+1)begin:authorization
  wire [31:0] matches;
  for(genvar aslot=0;aslot<32;aslot=aslot+1)begin:slots
   assign live_slots[ac*32+aslot]=raw[ac*576+aslot*18+17];
   assign matches[aslot]=raw[ac*576+aslot*18+17]&&
    raw[ac*576+aslot*18+:16]==observe_rsp_tag[ac*16+:16]&&
    raw[ac*576+aslot*18+16]==observe_rsp_we[ac];
  end
  assign authorized[ac]=(|matches)&&frame_match;
 end
 integer c,s,found,free_slot,duplicates;
 always @*begin
  next_ledger=raw;invalid=0;
  for(c=0;c<NC;c=c+1)begin
   found=-1;free_slot=-1;duplicates=0;
   for(s=0;s<32;s=s+1)begin
    if(raw[c*576+s*18+17])begin
     if(raw[c*576+s*18+:16]==observe_rsp_tag[c*16+:16]&&
        raw[c*576+s*18+16]==observe_rsp_we[c])found=s;
     if(raw[c*576+s*18+:16]==observe_req_tag[c*16+:16])duplicates=duplicates+1;
    end else if(free_slot<0)free_slot=s;
   end
   if(return_offer[c]&&!authorized[c])invalid=1;
   if(observe_rsp[c])begin
    if(found<0||!frame_match)invalid=1;
    else begin next_ledger[c*576+found*18+:18]=0;if(free_slot<0)free_slot=found;end
   end
   if(observe_req[c])begin
    if(free_slot<0||(duplicates!=0&&!(observe_rsp[c]&&found>=0&&
       observe_req_tag[c*16+:16]==observe_rsp_tag[c*16+:16])))invalid=1;
    else next_ledger[c*576+free_slot*18+:18]={1'b1,observe_req_we[c],observe_req_tag[c*16+:16]};
   end
  end
 end
 assign response_authorized=uncorrectable?0:authorized;
 assign debt=held_debt;assign violation=invalid||(held_debt&&!frame_match);
 assign uncorrectable=(|bad)||fl[65]||fh[65];
 reg [127:0] captured;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   frame_lo<=encode64(0);frame_hi<=encode64(0);
   for(integer k=0;k<NC*9;k=k+1)code[k]<=encode64(0);
  end else if(!uncorrectable&&!violation)begin
   if(!held_debt&&|observe_req)begin
    captured={54'b0,1'b1,native_pos,native_token,native_gen,native_job};
    frame_lo<=encode64(captured[63:0]);frame_hi<=encode64(captured[127:64]);
   end
   for(integer k=0;k<NC*9;k=k+1)code[k]<=encode64(next_ledger[k*64+:64]);
  end
 end
 end endgenerate
endmodule
