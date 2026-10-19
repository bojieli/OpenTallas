`timescale 1ns/1ps
// KV-HROOT-PEER 10-18: qkd_host_peer_root_mux restructured for the HOST cluster child qkd_hr_core_peer
// (source rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_root_mux.sv, unchanged; same ports).
//
// Gate ca25bcce7 (placement, TT): reg->reg -272.8 ps, worst endpoints u_coordinator.u_peer.step_slot (rank-0 RX) and
// last_allocation / tx_seq (coordinator TX).  Two changes:
//
// (1) CYCLE-EXACT: the coordinator-TX round robin is a one-hot select (same priority: the valid rank with the
//     smallest n of 1+(rr+n)%7 wins) and the 512-b physical_tx_data load is an AND-OR over the one-hot select, in
//     place of `integer chosen` and the runtime part-select coordinator_tx_data[chosen*512+:512] (a 512-b $shiftx
//     whose select fanned out to ~1k loads).  Every output is identical in every cycle.
//
// (2) ONE ADDED CYCLE on the local rank-0 path (rank codec TX -> coordinator RX[0]): a register slice.  Before, the
//     rank codec's combinational TX choice (status-change compare, 5:1 word mux) fed the coordinator's RX checks
//     (sequence compare, d[511:N]==0 reductions) and their ~1k-flop enables in one cycle (step_slot path, 15+
//     levels).  Now the word is registered here first.  local_tx_ready is the SAME function as before
//     (coordinator_rx_ready[0] && !fault): whenever the rank side hands over a word the slice is empty or drains in
//     that cycle, so the slice never stalls the rank codec and never drops or reorders a word; the coordinator sees
//     the same rank-0 word sequence exactly one cycle later.  Valid/ready class9 transport (exceptional lifecycle
//     traffic, never on the compiler's execution cycle schedule).  Bench: rtl/test/qwen_host/hr_peer_pl_1018.
//
// QKD_HR_PE_PL_MUTANT (bench only): the slice corrupts bit 40 of the word.
module qkd_host_peer_root_mux_pl(
 input wire ck,por_n,
 input wire physical_rx_valid,input wire[511:0]physical_rx_data,output wire physical_rx_ready,
 output reg physical_tx_valid,output reg[511:0]physical_tx_data,input wire physical_tx_ready,
 input wire local_tx_valid,input wire[511:0]local_tx_data,output wire local_tx_ready,
 output wire local_rx_valid,output wire[511:0]local_rx_data,input wire local_rx_ready,
 output reg[7:0]coordinator_rx_valid,output reg[4095:0]coordinator_rx_data,input wire[7:0]coordinator_rx_ready,
 input wire[7:0]coordinator_tx_valid,input wire[4095:0]coordinator_tx_data,output reg[7:0]coordinator_tx_ready,
 output reg fault);
 wire[2:0]source=physical_rx_data[10:8];
 wire shape=!physical_rx_data[7]&&physical_rx_data[13:11]==0&&source!=0;
 assign physical_rx_ready=!fault&&(shape?coordinator_rx_ready[source]:1'b1);
 assign local_tx_ready=coordinator_rx_ready[0]&&!fault;
 assign local_rx_valid=coordinator_tx_valid[0]&&!fault;
 assign local_rx_data=coordinator_tx_data[0+:512];
 // (2) rank-0 local slice
 reg lq_v;reg[511:0]lq_d;
 // (1) one-hot round robin over ranks 1..7 (sel[0] unused)
 reg[2:0]rr;reg[7:0]sel;reg found;
 reg[7:0]bad;reg[511:0]pick;reg[2:0]rr_next;
 always @*begin
  sel=0;found=0;
  for(integer n=0;n<7;n=n+1)begin
   if(!found&&coordinator_tx_valid[1+(int'(rr)+n)%7])begin sel[1+(int'(rr)+n)%7]=1;found=1;end
  end
  bad=0;pick=0;rr_next=0;
  for(integer r=1;r<8;r=r+1)begin
   bad[r]=coordinator_tx_data[r*512+8+:3]!=0||coordinator_tx_data[r*512+11+:3]!=3'(r)||!coordinator_tx_data[r*512+7];
   pick=pick|({512{sel[r]}}&coordinator_tx_data[r*512+:512]);
   rr_next=rr_next|({3{sel[r]}}&3'(r%7));
  end
 end
 always @*begin
  coordinator_rx_valid=0;coordinator_rx_data=0;coordinator_tx_ready=0;
  coordinator_rx_valid[0]=lq_v&&!fault;coordinator_rx_data[0+:512]=lq_d;
  for(integer r=1;r<8;r=r+1)begin
   coordinator_rx_valid[r]=physical_rx_valid&&shape&&source==3'(r)&&!fault;
   coordinator_rx_data[r*512+:512]=physical_rx_data;
  end
  coordinator_tx_ready[0]=local_rx_ready&&!fault;
  for(integer r=1;r<8;r=r+1)coordinator_tx_ready[r]=sel[r]&&!physical_tx_valid&&!fault;
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin rr<=0;physical_tx_valid<=0;physical_tx_data<=0;fault<=0;lq_v<=0;lq_d<=0;end
  else begin
   if(physical_rx_valid&&physical_rx_ready&&!shape)fault<=1;
   if(physical_tx_valid&&physical_tx_ready)physical_tx_valid<=0;
   if(!physical_tx_valid&&found&&!fault)begin
    if(|(sel&bad))fault<=1;
    else begin physical_tx_valid<=1;physical_tx_data<=pick;rr<=rr_next;end
   end
   if(local_tx_valid&&local_tx_ready)begin
    lq_v<=1;
`ifdef QKD_HR_PE_PL_MUTANT
    lq_d<=local_tx_data^(512'd1<<40);
`else
    lq_d<=local_tx_data;
`endif
   end else if(lq_v&&coordinator_rx_ready[0]&&!fault)lq_v<=0;
  end
 end
endmodule
