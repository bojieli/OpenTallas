`timescale 1ns/1ps
// Eight real CTRL roles, real service guards and real ING16 queues. The
// zero-row mapper checkpoint below is explicit component stimulus; full
// PHY/QM/mapper eight-rank proof belongs to the composed native gate.
module tb_qkd_host_token_peer_permit;
 parameter MUT=0,BAD=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,por=0,begin_v=0,early_ing=0,hold_pending7=1,hold_permit7=1;
 reg[7:0]rx_v=0,tx_cr=0;reg[511:0]rx_d[0:7];
 wire[7:0]tx_v,fault,perm,sb,advert,ready,abort,qv,qfault;
 wire[511:0]tx_d[0:7];wire[15:0]sbe[0:7],ae[0:7],le[0:7];
 wire[7:0]ack[0:7],ready8[0:7];wire[545:0]qd[0:7];wire[4:0]ic[0:7];
 wire[7:0]rx_cr;reg[7:0]qcr=0,barrier=0;integer issued[0:7];
 reg[511:0]queue[0:7][0:31];integer origin[0:7][0:31],wp[0:7],rp[0:7],nq[0:7],window[0:7];
 integer owner[0:7][0:3],ow[0:7],orr[0:7],on[0:7];
 integer checks=0,permits=0,copies[0:7],cycles=0;
 genvar G;
 generate for(G=0;G<8;G=G+1)begin:g
  qkd_host_ctrl_token_service_packet #(.DIE(G),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MUT(MUT))ctl(
   .ck(ck),.rst_n(rst),.por_n(por),.die_id(3'(G)),.rx_v(rx_v[G]),.rx_d(rx_d[G]),.rx_cr(rx_cr[G]),.tx_v(tx_v[G]),.tx_d(tx_d[G]),.tx_cr(tx_cr[G]),
   .local_tk(93'd0),.local_kst(10'd0),.local_boot(2'd3),.cmd_v(1'b0),.cmd_hc(182'd0),.fault(fault[G]),
   .startup_allowed(1'b1),.local_service_ready(ready[G]),.local_service_epoch(le[G]),.begin_v(G==0?begin_v:1'b0),.begin_epoch(16'd1),
   .service_begin_v(sb[G]),.service_begin_epoch(sbe[G]),.pending_advertised(advert[G]),.pending_epoch(ae[G]),.pending_ack8(ack[G]),.service_ready8(ready8[G]),.ingest_permission(perm[G]),
   .token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_allocator_fault(1'b0),
   .package_abort(1'b0),.abort_drained(4'd0),.token_request_ready(1'b0),.token_grant_valid(1'b0),.token_grant_epoch(16'd0),.token_grant_token(18'd0),.token_grant_position(18'd0),.token_grant_generation(2'd0),.token_grant_tag(59'd0),
   .allocated_valid(1'b0),.allocated_delivered(1'b0),.allocated_epoch(16'd0),.allocated_token(18'd0),.allocated_position(18'd0),.allocated_generation(2'd0),.terminal_accepted(1'b0));
  qkd_host_qm_ingress16_service #(.ENABLE_SERVICE(1))queue16(.ck(ck),.rst_n(rst),.in_v(early_ing),.in_cls(2'd0),.in_d(512'd2),.allow(perm[G]),.in_crn(ic[G]),.out_v(qv[G]),.out_d(qd[G]),.out_cr(qcr[G]),.fault(qfault[G]));
  qkd_host_service_guard guard(.ck_guard(ck),.rst_n(rst),.raw_faults(25'd0),.service_protocol_fault(fault[G]),.die_id(3'(G)),.physical_faults(8'd0),.transport_faults(8'd0),
   .accepted_ing_v(early_ing),.accepted_ing_cls(2'd0),.accepted_ing_header(16'd2),.done_v(1'b0),.done_d(64'd0),.boot_barrier_v(barrier[G]),.boot_barrier_target(32'd0),
   .begin_v(sb[G]),.begin_epoch(sbe[G]),.pending_advertised(advert[G]),.pending_epoch(ae[G]),.local_tk(93'd0),.service_ready(ready[G]),.service_epoch(le[G]),.abort(abort[G]));
 end endgenerate
 // Explicit bounded packet fixture: four destination CTRL slots, up to32
 // reserved waiting words; original source gets credit only on actual consume.
 always @(negedge ck)begin
  cycles++;rx_v=0;tx_cr=0;qcr=0;barrier=0;
  if(rst)begin
   for(integer d=0;d<8;d++)begin
    if(rx_cr[d])begin
     if(on[d]==0)$fatal(1,"unowned receiver credit");
     if(owner[d][orr[d]]>=0)tx_cr[owner[d][orr[d]]]=1;orr[d]=(orr[d]+1)%4;on[d]--;window[d]++;
    end
    if(qv[d])begin
     if(!perm[d]||qd[d]!==546'd2)$fatal(1,"early/wrong ING issue before genuine permit");
     issued[d]++;qcr[d]=1;barrier[d]=1;
    end
    if(tx_v[d])begin
     integer dest;dest=0;while(dest<8&&!tx_d[d][24+dest])dest++;
     if(dest==8||nq[dest]==32)$fatal(1,"unreserved fixture queue");
     queue[dest][wp[dest]]=tx_d[d];origin[dest][wp[dest]]=d;wp[dest]=(wp[dest]+1)%32;nq[dest]++;
     if(tx_d[d][7:0]==8'h23&&tx_d[d][64])begin permits++;copies[dest]++;if(ack[0]!=255)$fatal(1,"permit before all8 genuine pending ACK");end
    end
   end
   for(integer dest=0;dest<8;dest++)if(nq[dest]!=0&&window[dest]!=0)begin
    reg blocked;blocked=0;
    if(dest==0&&origin[dest][rp[dest]]==7&&queue[dest][rp[dest]][153]==0&&queue[dest][rp[dest]][169:154]==1&&hold_pending7)blocked=1;
    if(dest==7&&queue[dest][rp[dest]][7:0]==8'h23&&queue[dest][rp[dest]][64]&&hold_permit7)blocked=1;
    if(!blocked)begin
     rx_v[dest]=1;rx_d[dest]=queue[dest][rp[dest]];owner[dest][ow[dest]]=origin[dest][rp[dest]];ow[dest]=(ow[dest]+1)%4;on[dest]++;window[dest]--;
     rp[dest]=(rp[dest]+1)%32;nq[dest]--;
    end
   end
  end
 end
 task tick(input integer n);repeat(n)begin @(posedge ck);#0.05;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 integer n;
 initial begin
  for(integer d=0;d<8;d++)begin rx_d[d]=0;wp[d]=0;rp[d]=0;nq[d]=0;window[d]=4;ow[d]=0;orr[d]=0;on[d]=0;issued[d]=0;copies[d]=0;end
  tick(5);por=1;rst=1;tick(100);begin_v=1;tick(1);begin_v=0;tick(100);
  check(ack[0][6:0]==127&&!ack[0][7],"genuine delayed peer7 pending ACK");
  early_ing=1;tick(1);early_ing=0;tick(100);
  check(permits==0&&perm==0,"no permission before all8 genuine pending");
  for(integer d=0;d<8;d++)check(issued[d]==0&&!qfault[d],"early BOOT retained in actual ING16 without issue/fault");
  if(BAD!=0)begin
   // True next source sequence, but future service epoch; typed permit guard
   // must reject it before peer gate opens, independent of sequence checks.
   queue[6][wp[6]]=512'h40000223|(512'd1<<32)|(512'd2<<48)|(512'd1<<64);
   origin[6][wp[6]]=-1;wp[6]=(wp[6]+1)%32;nq[6]++;
   tick(30);
   check(fault[6]&&issued[6]==0&&!perm[6],"future epoch permit rejected before ING issue");
   $display("PASS TOKEN_PEER_PERMIT_BAD checks=%0d",checks);$finish;
  end
  hold_pending7=0;tick(200);
  check(ack[0]==255&&perm[0]&&permits==7,"all8 actualpending causes exactly7 addressed permit copies");
  check(perm[6:0]==127&&!perm[7]&&ready8[0]==127,"peer7 actual permit receipt required, no global readiness fabricated");
  for(integer d=0;d<7;d++)check(issued[d]==1&&copies[d]==(d==0?0:1),"one real retained BOOT issue per permitted rank");
  check(issued[7]==0&&g[7].queue16.count==1,"early peer7 BOOT still physically stored");
  tick(1000);check(!perm[7]&&issued[7]==0&&ready8[0]==127,"delayed genuine permit prevents eighth readiness");
  hold_permit7=0;n=0;while(ready8[0]!=255&&n<1000)begin tick(1);n++;end
  check(perm==255&&ready8[0]==255&&!fault&&!qfault&&issued[7]==1,"all8 real permit/retained BOOT completion");
  $display("PASS TOKEN_PEER_PERMIT checks=%0d delayed_pending/delayed_permit/earlyING16 retained/all8 actualready",checks);$finish;
 end
 initial begin tick(5000);$fatal(1,"timeout");end
endmodule
