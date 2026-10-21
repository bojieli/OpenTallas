`timescale 1ns/1ps
`default_nettype none
// Position-strapped SU VM bank leaf (OWN-PGLG 2026-10-18): ot_hbm_su_static_vm_bank_leaf with QID / B from the slice's
// position strap (pgslice STRAP 1) instead of parameters, so one hardened slice master serves every quarter / bank pair.
// Logic, return edges (READ_RETURN / WRITE_RETURN) and checks are those of ot_hbm_su_static_vm_bank_leaf (MUT 0):
//   a request must address this quarter (sector[14:13] == qid, no mirror bit 15) and its own bank (sector[2:0] == b);
//   every read returns exactly READ_RETURN edges later, every write is done exactly WRITE_RETURN edges later;
//   a missing or unsolicited return latches FAULT. No queues, credits, ready or replay.
module ot_hbm_su_static_vm_bank_leaf_s #(parameter integer READ_RETURN=10,WRITE_RETURN=7)(
 input wire clk,rst_n,
 input wire [1:0] qid,                   // position strap (die tie)
 input wire [2:0] b,                     // position strap: VM bank 2G+h
 input wire [16:0] su_rq,                // {v,sector16}
 input wire [280:0] su_wq,               // {v,sector16,data256,mask8}
 output wire [256:0] su_rr,              // {v,data256} at issue + READ_RETURN
 output wire su_w_done,
 output wire [16:0] lg_rq,output wire [280:0] lg_wq,
 input wire [256:0] lg_rr,input wire lg_w_done,
 output reg fault
);
 reg rcal[0:READ_RETURN];
 reg wcal[0:WRITE_RETURN];
 wire rq_ok=!su_rq[15]&&su_rq[14:13]==qid&&su_rq[2:0]==b;
 wire wq_ok=!su_wq[279]&&su_wq[278:277]==qid&&su_wq[266:264]==b;
 assign lg_rq=su_rq;
 assign lg_wq=su_wq;
 assign su_rr=lg_rr;
 assign su_w_done=lg_w_done;
 integer i;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   fault<=0;for(i=0;i<=READ_RETURN;i=i+1)rcal[i]<=0;for(i=0;i<=WRITE_RETURN;i=i+1)wcal[i]<=0;
  end else begin
   for(i=1;i<=READ_RETURN;i=i+1)rcal[i]<=rcal[i-1];
   for(i=1;i<=WRITE_RETURN;i=i+1)wcal[i]<=wcal[i-1];
   rcal[0]<=su_rq[16];wcal[0]<=su_wq[280];
   if(su_rq[16]&&!rq_ok)fault<=1;
   if(su_wq[280]&&!wq_ok)fault<=1;
   if(lg_rr[256]!==rcal[READ_RETURN])fault<=1;
   if(lg_w_done!==wcal[WRITE_RETURN])fault<=1;
  end
endmodule
`default_nettype wire
