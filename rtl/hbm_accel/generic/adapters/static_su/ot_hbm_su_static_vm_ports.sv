`timescale 1ns/1ps
`default_nettype none
// Static SU VM interface, one quarter = NPG independently placeable port groups (GEO-H rule 10-15, main f5d89a0a8:
// one group per VM bank pair so every SU <-> LG link stays < 500 um; the die lead may add a fifth group on SW/SE).
// Each group drives the SU (near) station of the LG tap of its two banks (ot_hbm_vm_lg_static_bank, READ_RETURN 10,
// WRITE_RETURN 7). No register stage is added here: request pins go straight to the LG leaf's sampled local inputs,
// so the compiler latencies stay 10/7. No queues, credits, ready, arbitration or runtime rescheduling: the compiler
// owns every read/write edge; the group only checks the schedule:
//   * a request must address this quarter's slice (SID == QID, no mirror) and its own bank (F2 per-quarter spread);
//   * every read the group issued must return exactly READ_RETURN edges later, every write must be done exactly
//     WRITE_RETURN edges later; a missing or unsolicited return latches FAULT (never waits, never replays).
// MUT=1 (bench must fail): the group forgets the per-quarter spread and sends the logical SID-major slice bits.
module ot_hbm_su_static_vm_pg #(parameter integer QID=0,G=0,READ_RETURN=10,WRITE_RETURN=7,MUT=0)(
 input wire clk,rst_n,
 input wire [2*17-1:0] su_rq,            // {v,sector16} per bank of the pair
 input wire [2*281-1:0] su_wq,           // {v,sector16,data256,mask8}
 output wire [2*257-1:0] su_rr,          // {v,data256} at issue + READ_RETURN
 output wire [1:0] su_w_done,
 output wire [2*17-1:0] lg_rq,output wire [2*281-1:0] lg_wq,output wire [1:0] lg_read,lg_write,
 input wire [2*257-1:0] lg_rr,input wire [1:0] lg_w_done,
 output reg fault
);
 reg [1:0] rcal[0:READ_RETURN];   // rcal[k] (as seen before an edge) = request sampled k edges earlier
 reg [1:0] wcal[0:WRITE_RETURN];
 function automatic ok(input [15:0] s,input integer b);
  ok=!s[15]&&s[14:13]==2'(QID)&&s[2:0]==3'(2*G+b);
 endfunction
 for(genvar b=0;b<2;b=b+1)begin:g_b
  wire [15:0] sec=su_rq[b*17+:16];
  assign lg_rq[b*17+:17]={su_rq[b*17+16],MUT!=0?{sec[15],2'(QID^1),sec[12:0]}:sec};
  assign lg_wq[b*281+:281]=su_wq[b*281+:281];
  assign lg_read[b]=su_rq[b*17+16];
  assign lg_write[b]=su_wq[b*281+280];
  assign su_rr[b*257+:257]=lg_rr[b*257+:257];
  assign su_w_done[b]=lg_w_done[b];
 end
 integer i,b;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   fault<=0;for(i=0;i<=READ_RETURN;i=i+1)rcal[i]<=0;for(i=0;i<=WRITE_RETURN;i=i+1)wcal[i]<=0;
  end else begin
   for(i=1;i<=READ_RETURN;i=i+1)rcal[i]<=rcal[i-1];
   for(i=1;i<=WRITE_RETURN;i=i+1)wcal[i]<=wcal[i-1];
   rcal[0]<={su_rq[17+16],su_rq[16]};wcal[0]<={su_wq[281+280],su_wq[280]};
   for(b=0;b<2;b=b+1)begin
    if(su_rq[b*17+16]&&!ok(su_rq[b*17+:16],b))fault<=1;
    if(su_wq[b*281+280]&&!ok(su_wq[b*281+264+:16],b))fault<=1;
    // the LG leaf presents the return READ_RETURN edges after sampling the request (WRITE_RETURN for done)
    if(lg_rr[b*257+256]!==rcal[READ_RETURN][b])fault<=1;
    if(lg_w_done[b]!==wcal[WRITE_RETURN][b])fault<=1;
   end
  end
endmodule

module ot_hbm_su_static_vm_ports #(parameter integer QID=0,READ_RETURN=10,WRITE_RETURN=7,MUT=0)(
 input wire [3:0] pg_clk,                // one compensated clock entry per port group (same edge/phase)
 input wire rst_n,
 input wire [8*17-1:0] su_rq,input wire [8*281-1:0] su_wq,
 output wire [8*257-1:0] su_rr,output wire [7:0] su_w_done,
 output wire [8*17-1:0] lg_rq,output wire [8*281-1:0] lg_wq,output wire [7:0] lg_read,lg_write,
 input wire [8*257-1:0] lg_rr,input wire [7:0] lg_w_done,
 output wire [3:0] fault
);
 for(genvar g=0;g<4;g=g+1)begin:g_pg
  ot_hbm_su_static_vm_pg #(.QID(QID),.G(g),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) pg(
   .clk(pg_clk[g]),.rst_n(rst_n),.su_rq(su_rq[g*34+:34]),.su_wq(su_wq[g*562+:562]),
   .su_rr(su_rr[g*514+:514]),.su_w_done(su_w_done[g*2+:2]),
   .lg_rq(lg_rq[g*34+:34]),.lg_wq(lg_wq[g*562+:562]),.lg_read(lg_read[g*2+:2]),.lg_write(lg_write[g*2+:2]),
   .lg_rr(lg_rr[g*514+:514]),.lg_w_done(lg_w_done[g*2+:2]),.fault(fault[g]));
 end
endmodule
`default_nettype wire
