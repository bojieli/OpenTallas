`timescale 1ns/1ps
// KV-PEER5 (REFILL-1330, 10-19): qkd_host_peer_root_mux r5 for the HOST cluster child qkd_hr_core_peer
// (source rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_root_mux.sv unchanged; same ports; replaces _pl of r3/r4).
//
// r4 gate (--cts, TT placement RC, signoff.sdc) reg->reg classes through this mux: allocator.grant_position ->
// coordinator codec TX choice -> root mux pick -> physical_tx_data -63.2; coordinator TX -> local rank-0 RX ->
// rank codec cancel_release_tag -68.4; peer link pr -> physical RX -> coordinator RX decode -> participant_trace -56.2;
// and the TX round robin closed a valid -> select -> ready loop back into the coordinator in one cycle.
// SAFE-AUDIT-KV r5 item: "the coordinator -> root_mux select as a registered one-hot".  Every direction is now
// registered here, so no path crosses this mux combinationally between the coordinator and either rank side:
//
//  TX ranks 1..7 -> physical: REGISTERED ONE-HOT GRANT g (no wide shifter, no runtime part-select).  g is chosen one
//     edge ahead from the valid ranks in the same round-robin priority as the source (smallest n of 1+(rr+n)%7); the
//     coordinator sees coordinator_tx_ready[r] = g[r] && !physical_tx_valid && !fault (registers only), and the
//     512-b load is an AND-OR over g.  A word waits at most ONE extra edge for its grant (+1 edge on this path).
//  TX rank 0 -> local rank (coordinator_tx[0] -> local_rx): one register slice (+1 edge).
//  RX physical -> coordinator ranks 1..7: one register slice, the shape check at its input (+1 edge).
//  RX local rank -> coordinator[0]: the r3 slice (+1 edge, unchanged).
// Every slice accepts while empty or draining in the same edge (full rate), never drops, duplicates or reorders a word;
// per channel the word sequence is the source's exactly (class9 valid/ready lifecycle transport, never on the
// compiler's per-token execution schedule).  Faults: a non-shape physical RX word and a bad coordinator TX header
// fault the mux on their handshake, as the source.  Data registers carry no reset (valid bits do).
// Bench: rtl/test/qwen_host/hr_peer_pl2_1019 (per-channel word streams vs the unchanged mux, plus fault parity).
// QKD_HR_PE_PL2_MUTANT (bench only): the physical RX slice corrupts bit 40 of the word.
module qkd_host_peer_root_mux_pl2(
 input wire ck,por_n,
 input wire physical_rx_valid,input wire[511:0]physical_rx_data,output wire physical_rx_ready,
 output reg physical_tx_valid,output reg[511:0]physical_tx_data,input wire physical_tx_ready,
 input wire local_tx_valid,input wire[511:0]local_tx_data,output wire local_tx_ready,
 output wire local_rx_valid,output wire[511:0]local_rx_data,input wire local_rx_ready,
 output reg[7:0]coordinator_rx_valid,output reg[4095:0]coordinator_rx_data,input wire[7:0]coordinator_rx_ready,
 input wire[7:0]coordinator_tx_valid,input wire[4095:0]coordinator_tx_data,output reg[7:0]coordinator_tx_ready,
 output reg fault);
 // ---- RX physical slice (ranks 1..7) ----
 reg rq_v;reg[7:0]rq_oh;reg[511:0]rq_d;
 wire[2:0]source=physical_rx_data[10:8];
 wire shape=!physical_rx_data[7]&&physical_rx_data[13:11]==0&&source!=0;
 wire rq_drain=rq_v&&((rq_oh&coordinator_rx_ready)!=0);
 assign physical_rx_ready=!fault&&(!rq_v||rq_drain);
 wire rx_take=physical_rx_valid&&physical_rx_ready;
 // ---- RX local slice (rank 0, r3) ----
 reg lq_v;reg[511:0]lq_d;
 assign local_tx_ready=!fault&&(!lq_v||coordinator_rx_ready[0]);
 // ---- TX local slice (rank 0) ----
 reg tq_v;reg[511:0]tq_d;
 assign local_rx_valid=tq_v&&!fault;
 assign local_rx_data=tq_d;
 wire tq_drain=tq_v&&local_rx_ready&&!fault;
 // ---- TX physical: registered one-hot grant ----
 reg[2:0]rr;reg[7:0]g;
 reg[7:0]hit,bad,g_next;reg[511:0]pick;reg[2:0]rr_hit,rr_eff;reg found;
 wire tx_ok=!physical_tx_valid&&!fault;
 always @*begin
  hit=g&coordinator_tx_valid&{8{tx_ok}};hit[0]=1'b0;
  bad=0;pick=0;rr_hit=0;
  for(integer r=1;r<8;r=r+1)begin
   bad[r]=coordinator_tx_data[r*512+8+:3]!=0||coordinator_tx_data[r*512+11+:3]!=3'(r)||!coordinator_tx_data[r*512+7];
   pick=pick|({512{g[r]}}&coordinator_tx_data[r*512+:512]);
   rr_hit=rr_hit|({3{g[r]}}&3'(r%7));
  end
  // the round robin pointer after this edge's transfer, and the next grant (a rank that transfers now is not
  // re-granted on the next edge: its next word, if any, is granted from the following edge on)
  rr_eff=(hit!=0&&(hit&bad)==0)?rr_hit:rr;
  g_next=0;found=0;
  for(integer n=0;n<7;n=n+1)begin
   if(!found&&coordinator_tx_valid[1+(int'(rr_eff)+n)%7]&&!hit[1+(int'(rr_eff)+n)%7])begin
    g_next[1+(int'(rr_eff)+n)%7]=1'b1;found=1'b1;
   end
  end
 end
 always @*begin
  coordinator_tx_ready=g&{8{tx_ok}};
  coordinator_tx_ready[0]=!fault&&(!tq_v||local_rx_ready);
  coordinator_rx_valid=rq_oh&{8{rq_v&&!fault}};
  coordinator_rx_valid[0]=lq_v&&!fault;
  coordinator_rx_data=0;
  coordinator_rx_data[0+:512]=lq_d;
  for(integer r=1;r<8;r=r+1)coordinator_rx_data[r*512+:512]=rq_d;
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin rr<=0;g<=0;physical_tx_valid<=0;physical_tx_data<=0;fault<=0;lq_v<=0;rq_v<=0;rq_oh<=0;tq_v<=0;end
  else begin
   g<=fault?8'd0:g_next;
   if(physical_tx_valid&&physical_tx_ready)physical_tx_valid<=0;
   if(hit!=0)begin
    if((hit&bad)!=0)fault<=1;
    else begin physical_tx_valid<=1;physical_tx_data<=pick;rr<=rr_hit;end
   end
   if(rx_take)begin
    if(!shape)fault<=1;
    else begin rq_v<=1;rq_oh<=8'd1<<source;end
   end else if(rq_drain&&!fault)rq_v<=0;
   if(local_tx_valid&&local_tx_ready)lq_v<=1;
   else if(lq_v&&coordinator_rx_ready[0]&&!fault)lq_v<=0;
   if(coordinator_tx_valid[0]&&coordinator_tx_ready[0])tq_v<=1;
   else if(tq_drain)tq_v<=0;
  end
 end
 // data registers: no reset (their valid bits are reset)
 always @(posedge ck)begin
  if(rx_take&&shape)begin
`ifdef QKD_HR_PE_PL2_MUTANT
   rq_d<=physical_rx_data^(512'd1<<40);
`else
   rq_d<=physical_rx_data;
`endif
  end
  if(local_tx_valid&&local_tx_ready)lq_d<=local_tx_data;
  if(coordinator_tx_valid[0]&&coordinator_tx_ready[0])tq_d<=coordinator_tx_data[0+:512];
 end
endmodule
