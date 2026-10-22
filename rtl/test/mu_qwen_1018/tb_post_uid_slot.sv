`timescale 1ns/1ps
// KV-HOST2 10-19: MU4 POST UID binding bench for qkd_host_post_collector_mu #(MU 1, UID_SLOT 1).
// Drives the collector exactly as the selected HOST observer does (ot_host_if_pb2_observed: RAW per-user positions
// < 8192 on step_pos / step_retire_pos / cq_pos, the real scheduler slot on *_slot) for 4 users x 3 rounds, with
// overlapping ownership, terminals accepted out of user order, 8-rank releases and drains.  PASS needs every user's
// POST in terminal-acceptance order with its own TAG/gen and no fault.
// Plusargs: +NEG_SLOT4 (a step on slot 4 must raise the sticky fault), +NEG_POSHI (a position with bit 16 set must
// fault), +NEG_UIDX (slot 2 carrying user 1's position/TAG must fault).  Parameters UID_SLOT / MUT select the build.
module tb_post_uid_slot;
 parameter integer UID_SLOT=1, MUT=0;
 reg ck=0, por_n=0; always #1 ck=~ck;
 reg allocated_valid=0; reg[58:0]allocated_tag=0; reg[1:0]allocated_gen=0;
 reg step_issue_v=0; reg[15:0]step_client_tag=0; reg[7:0]step_slot=0; reg[17:0]step_pos=0;
 reg step_retire_v=0, step_retire_cq=0; reg[15:0]rc=0; reg[7:0]rs=0; reg[17:0]rp=0, rt=0;
 reg cq_commit_v=0; reg[15:0]cc=0; reg[7:0]cs=0; reg[17:0]cp=0, ct=0;
 reg terminal_accepted=0; reg[58:0]terminal_tag=0; reg[1:0]terminal_gen=0;
 reg[7:0]cancel_released=0;
 wire post_retired; wire[58:0]post_tag; wire[1:0]post_gen; wire fault;
 qkd_host_post_collector_mu #(.MUT(MUT),.MU(1),.UID_SLOT(UID_SLOT)) dut(.ck(ck),.por_n(por_n),
  .allocated_valid(allocated_valid),.allocated_delivered(1'b1),.allocated_tag(allocated_tag),.allocated_gen(allocated_gen),
  .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),
  .step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(rc),.step_retire_slot(rs),
  .step_retire_pos(rp),.step_retire_token(rt),.cq_commit_v(cq_commit_v),.cq_client_tag(cc),.cq_slot(cs),.cq_pos(cp),
  .cq_token(ct),.terminal_accepted(terminal_accepted),.terminal_tag(terminal_tag),.terminal_gen(terminal_gen),
  .cancel_released(cancel_released),.cancel_release_required(8'hFF),.result_transport_idle(1'b1),
  .kv_drained(8'hFF),.vm_drained(8'hFF),.collective_drained(8'hFF),.host_drained(8'hFF),.source_fault(1'b0),
  .post_retired(post_retired),.post_tag(post_tag),.post_gen(post_gen),.fault(fault));
 // TAG59: [58:45] seq, [44:43] user (epoch UID), [42:37] stored as 37 by the collector, [18:6] 13-bit position
 function automatic [58:0] mk(input [13:0] seq, input [1:0] u, input [12:0] p);
  mk={seq,u,6'd37,18'h2a5a5,p,6'd9};
 endfunction
 reg[58:0]tg[0:3]; reg[12:0]ps[0:3]; reg[58:0]exp_q[0:15]; reg[1:0]exp_g[0:15]; integer ew=0, er=0, posts=0, errs=0;
 integer r,u,k; integer neg=0; reg[7:0]bad_slot; reg[17:0]bad_pos;
 always @(posedge ck) if(por_n&&post_retired) begin
  if(er>=ew||post_tag!==exp_q[er]||post_gen!==exp_g[er]) begin errs=errs+1;
   $display("MISMATCH post %0d tag %h gen %0d exp %h", er, post_tag, post_gen, exp_q[er]); end
  er=er+1; posts=posts+1;
 end
 task tick; @(negedge ck); endtask
 initial begin
  if($test$plusargs("NEG_SLOT4")) neg=1; if($test$plusargs("NEG_POSHI")) neg=2; if($test$plusargs("NEG_UIDX")) neg=3;
  repeat(3) tick; por_n=1; tick;
  for(r=0;r<3;r=r+1) begin
   for(u=0;u<4;u=u+1) begin ps[u]=13'(r==2 ? 8191-u*37 : r*1200+u*511+5); tg[u]=mk(14'(r+1),2'(u),ps[u]); end
   // four allocations (each opens its user's step), interleaved with issues of the already-owned users
   for(u=0;u<4;u=u+1) begin
    tick; allocated_valid=1; allocated_tag=tg[u]; allocated_gen=2'(r); tick; allocated_valid=0;
    step_issue_v=1; step_client_tag=16'(100*r+u); step_slot=8'(u); step_pos={5'd0,ps[u]};
    if(neg==1&&r==1&&u==2) step_slot=8'd6;          // slot 4+ : must fault (6[1:0]==2 aliases user 2)
    if(neg==2&&r==1&&u==1) step_pos={2'b01,3'd0,ps[u]};
    if(neg==3&&r==2&&u==2) step_pos={5'd0,ps[1]};   // slot 2 with user 1's position: slot UID != TAG epoch UID
    tick; step_issue_v=0;
   end
   // retire + CQ in reverse user order (overlap: all four owned)
   for(k=3;k>=0;k=k-1) begin
    tick; step_retire_v=1; step_retire_cq=1; rc=16'(100*r+k); rs=8'(k); rp={5'd0,ps[k]}; rt=18'(1000+k);
    if(neg==1&&r==1&&k==2) rs=8'd6;               // same out-of-range slot on retire and CQ (consistent alias)
    tick; step_retire_v=0;
    cq_commit_v=1; cc=rc; cs=rs; cp=rp; ct=rt; tick; cq_commit_v=0;
   end
   // terminals accepted in order 2,0,3,1; releases of the head between terminals
   for(k=0;k<4;k=k+1) begin
    u = (k==0)?2:(k==1)?0:(k==2)?3:1;
    tick; terminal_accepted=1; terminal_tag=tg[u]; terminal_gen=2'(r); exp_q[ew%16]=tg[u]; exp_g[ew%16]=2'(r); ew=ew+1;
    tick; terminal_accepted=0; cancel_released=8'hFF; tick; cancel_released=8'h00; tick; tick;
   end
   repeat(8) tick;
  end
  repeat(10) tick;
  if(neg!=0) begin
   if(fault) $display("POST_UID_SLOT PASS neg=%0d sticky fault raised (UID_SLOT=%0d MUT=%0d)", neg, UID_SLOT, MUT);
   else $display("POST_UID_SLOT FAIL neg=%0d no fault (UID_SLOT=%0d MUT=%0d)", neg, UID_SLOT, MUT);
  end else if(!fault && errs==0 && posts==12 && er==ew)
   $display("POST_UID_SLOT PASS users=4 rounds=3 posts=%0d (UID_SLOT=%0d MUT=%0d)", posts, UID_SLOT, MUT);
  else $display("POST_UID_SLOT FAIL fault=%0d errs=%0d posts=%0d/%0d (UID_SLOT=%0d MUT=%0d)", fault, errs, posts, ew, UID_SLOT, MUT);
  $finish;
 end
endmodule
