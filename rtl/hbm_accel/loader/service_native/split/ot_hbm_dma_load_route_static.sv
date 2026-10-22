`timescale 1ns/1ps
`default_nettype none
// Fixed-slot routing, no grants/credits/retry. Each merge captures input and
// kept valid copies, then registers its result. Collisions suppress the edge.
// Packet = {valid, sector16, data256, mask8}. Destination = {quadrant2, bank3}.
module ot_hbm_dma_load_source_join (
 input wire clk,rst_n,input wire [2247:0] lane_dq,input wire [39:0] lane_destination,
 output reg [280:0] packet,output reg [4:0] destination,output reg fault
);
 reg [2247:0] data_q;reg [39:0] dest_q;
 (* keep = "true", dont_touch = "true" *) reg [79:0] valid_q;
 reg [280:0] selected;reg [4:0] selected_destination;reg collision,seen;
 always @(posedge clk)begin
  data_q<=lane_dq;dest_q<=lane_destination;
  for(integer n=0;n<8;n=n+1)for(integer j=0;j<10;j=j+1)
   valid_q[n*10+j]<=rst_n&&lane_dq[n*281+280];
 end
 always @*begin
  selected=0;selected_destination=0;collision=0;seen=0;
  for(integer n=0;n<8;n=n+1)begin
   collision=collision|(seen&&valid_q[n*10+9]);seen=seen|valid_q[n*10+9];
   for(integer k=0;k<280;k=k+1)selected[k]=selected[k]|(data_q[n*281+k]&&valid_q[n*10+k/32]);
   selected_destination=selected_destination|(dest_q[n*5+:5]&{5{valid_q[n*10+9]}});
  end
  selected[280]=seen;
 end
 always @(posedge clk)begin
  packet[279:0]<=selected[279:0];destination<=selected_destination;
  if(!rst_n)begin packet[280]<=0;fault<=0;end
  else begin packet[280]<=selected[280]&&!collision;fault<=fault|collision;end
 end
endmodule
module ot_hbm_dma_load_destination_join #(parameter integer QID=0)(
 input wire clk,rst_n,input wire [1123:0] source_packet,input wire [19:0] source_destination,
 output reg [280:0] packet,output reg [2:0] bank,output reg fault
);
 reg [1123:0] data_q;reg [19:0] dest_q;
 (* keep = "true", dont_touch = "true" *) reg [39:0] valid_q;
 reg [280:0] selected;reg [2:0] selected_bank;reg collision,seen;
 always @(posedge clk)begin
  data_q<=source_packet;dest_q<=source_destination;
  for(integer n=0;n<4;n=n+1)for(integer j=0;j<10;j=j+1)
   valid_q[n*10+j]<=rst_n&&source_packet[n*281+280]&&source_destination[n*5+3+:2]==2'(QID);
 end
 always @*begin
  selected=0;selected_bank=0;collision=0;seen=0;
  for(integer n=0;n<4;n=n+1)begin
   collision=collision|(seen&&valid_q[n*10+9]);seen=seen|valid_q[n*10+9];
   for(integer k=0;k<280;k=k+1)selected[k]=selected[k]|(data_q[n*281+k]&&valid_q[n*10+k/32]);
   selected_bank=selected_bank|(dest_q[n*5+:3]&{3{valid_q[n*10+9]}});
  end
  selected[280]=seen;
 end
 always @(posedge clk)begin
  packet[279:0]<=selected[279:0];bank<=selected_bank;
  if(!rst_n)begin packet[280]<=0;fault<=0;end
  else begin packet[280]<=selected[280]&&!collision;fault<=fault|collision;end
 end
endmodule
// Local bank input capture adds one edge to BOTH raw and converted delivery.
// No priority: a double reservation faults and emits no valid write.
module ot_hbm_dma_load_bank_join #(parameter integer BANK=0)(
 input wire clk,rst_n,input wire [280:0] raw_dq,load_dq,input wire [2:0] load_bank,
 output wire [280:0] dq,output reg fault
);
 reg [279:0] raw_q,load_q;
 (* keep = "true", dont_touch = "true" *) reg [9:0] rv,lv;
 reg safe_q;
 wire take_load=load_dq[280]&&(load_bank==3'(BANK));
 wire collision=raw_dq[280]&&take_load;
 always @(posedge clk)begin
  raw_q<=raw_dq[279:0];load_q<=load_dq[279:0];
  safe_q<=rst_n&&!collision;
  for(integer j=0;j<10;j=j+1)begin rv[j]<=rst_n&&raw_dq[280];lv[j]<=rst_n&&take_load;end
  if(!rst_n)fault<=0;else fault<=fault|collision;
 end
 for(genvar k=0;k<280;k=k+1)begin:G
  assign dq[k]=(raw_q[k]&rv[k/32])|(load_q[k]&lv[k/32]);
 end
 assign dq[280]=safe_q&&(rv[9]||lv[9]);
endmodule
`default_nettype wire
