`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of qkd_host_peer_root_mux_pl2 (same ports, same per-channel word streams and faults).
// The shape and bad-header checks drive only fault, rq_oh / rq_v and the grant pointer; the 512-bit data registers load
// on the handshake alone (fault is sticky, so a word loaded on a fault edge is never presented).  physical_tx_data has no
// reset (physical_tx_valid qualifies it).  QKD_HR_PE_PL2_MUTANT (bench only): the physical RX slice corrupts bit 40.
module qkd_host_peer_root_mux_r3(
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
 reg[7:0]hit,bad,g_next;reg[511:0]pick;reg[2:0]rr_hit;reg found;
 wire tx_ok=!physical_tx_valid&&!fault;
 always @*begin
  hit=g&coordinator_tx_valid&{8{tx_ok}};hit[0]=1'b0;
  bad=0;pick=0;rr_hit=0;
  for(integer r=1;r<8;r=r+1)begin
   bad[r]=coordinator_tx_data[r*512+8+:3]!=0||coordinator_tx_data[r*512+11+:3]!=3'(r)||!coordinator_tx_data[r*512+7];
   pick=pick|({512{g[r]}}&coordinator_tx_data[r*512+:512]);
   rr_hit=rr_hit|({3{g[r]}}&3'(r%7));
  end
  // next grant from the registered pointer: on a transfer edge the next g is unused (physical_tx_valid rises, tx_ok falls),
  // and the first grant that can act is computed one edge later from rr, so word order and timing are exact
  g_next=0;found=0;
  for(integer n=0;n<7;n=n+1)begin
   if(!found&&coordinator_tx_valid[1+(int'(rr)+n)%7])begin
    g_next[1+(int'(rr)+n)%7]=1'b1;found=1'b1;
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
  if(!por_n)begin rr<=0;g<=0;physical_tx_valid<=0;fault<=0;lq_v<=0;rq_v<=0;rq_oh<=0;tq_v<=0;end
  else begin
   g<=fault?8'd0:g_next;
   if(physical_tx_valid&&physical_tx_ready)physical_tx_valid<=0;
   if(hit!=0)begin
    if((hit&bad)!=0)fault<=1;
    else begin physical_tx_valid<=1;rr<=rr_hit;end
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
  if(hit!=0)physical_tx_data<=pick;
  if(rx_take)begin
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
