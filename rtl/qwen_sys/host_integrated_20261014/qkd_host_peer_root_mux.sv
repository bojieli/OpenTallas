`timescale 1ns/1ps
// HOST0 owns the singleton. Local rank0 events stay on chip. Physical HOST0
// class9 RX carries only upstream native ranks1..7; downstream packets for
// those ranks leave the same real HOST0 FDI. No C++ peer aggregation.
module qkd_host_peer_root_mux(
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
 reg[2:0]rr;integer chosen;
 always @*begin
  coordinator_rx_valid=0;coordinator_rx_data=0;coordinator_tx_ready=0;chosen=-1;
  coordinator_rx_valid[0]=local_tx_valid&&!fault;coordinator_rx_data[0+:512]=local_tx_data;
  for(integer r=1;r<8;r=r+1)begin
   coordinator_rx_valid[r]=physical_rx_valid&&shape&&source==3'(r)&&!fault;
   coordinator_rx_data[r*512+:512]=physical_rx_data;
  end
  coordinator_tx_ready[0]=local_rx_ready&&!fault;
  for(integer n=6;n>=0;n=n-1)begin
   if(coordinator_tx_valid[1+(int'(rr)+n)%7])chosen=1+(int'(rr)+n)%7;
  end
  if(!physical_tx_valid&&chosen>=0&&!fault)coordinator_tx_ready[chosen]=1;
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin rr<=0;physical_tx_valid<=0;physical_tx_data<=0;fault<=0;end
  else begin
   if(physical_rx_valid&&physical_rx_ready&&!shape)fault<=1;
   if(physical_tx_valid&&physical_tx_ready)physical_tx_valid<=0;
   if(!physical_tx_valid&&chosen>=0&&!fault)begin
    if(coordinator_tx_data[chosen*512+8+:3]!=0||coordinator_tx_data[chosen*512+11+:3]!=3'(chosen)||!coordinator_tx_data[chosen*512+7])fault<=1;
    else begin physical_tx_valid<=1;physical_tx_data<=coordinator_tx_data[chosen*512+:512];rr<=3'(chosen%7);end
   end
  end
 end
endmodule
