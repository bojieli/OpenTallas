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
 wire [7:0] reset_q;wire [79:0] valid_q;
 for(genvar r=0;r<8;r=r+1)begin:R
  (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(100+r)) u(.clk(clk),.d(rst_n),.q(reset_q[r]));
 end
 for(genvar n=0;n<8;n=n+1)begin:V
  for(genvar j=0;j<10;j=j+1)begin:C
   (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(200+n*10+j)) u(.clk(clk),.d(reset_q[n]&&lane_dq[n*281+280]),.q(valid_q[n*10+j]));
  end
 end
 reg [280:0] selected;reg [4:0] selected_destination;reg collision,seen;
 always @(posedge clk)begin
  data_q<=lane_dq;dest_q<=lane_destination;
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
 wire [3:0] reset_q;wire [39:0] valid_q;
 for(genvar r=0;r<4;r=r+1)begin:R
  (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(400+QID*100+r)) u(.clk(clk),.d(rst_n),.q(reset_q[r]));
 end
 for(genvar n=0;n<4;n=n+1)begin:V
  for(genvar j=0;j<10;j=j+1)begin:C
   (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(410+QID*100+n*10+j)) u(.clk(clk),
    .d(reset_q[n]&&source_packet[n*281+280]&&(source_destination[n*5+3+:2]==2'(QID))),.q(valid_q[n*10+j]));
  end
 end
 reg [280:0] selected;reg [2:0] selected_bank;reg collision,seen;
 always @(posedge clk)begin
  data_q<=source_packet;dest_q<=source_destination;
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
 wire [9:0] reset_q,rv,lv;
 for(genvar j=0;j<10;j=j+1)begin:C
  (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(1000+BANK*40+j)) r(.clk(clk),.d(rst_n),.q(reset_q[j]));
  (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(1010+BANK*40+j)) a(.clk(clk),.d(reset_q[j]&&raw_dq[280]),.q(rv[j]));
  (* keep_hierarchy="yes" *) ot_hbm_dma_route_copy #(.COPY_ID(1020+BANK*40+j)) b(.clk(clk),.d(reset_q[j]&&take_load),.q(lv[j]));
 end
 reg safe_q;
 wire take_load=load_dq[280]&&(load_bank==3'(BANK));
 wire collision=raw_dq[280]&&take_load;
 always @(posedge clk)begin
  raw_q<=raw_dq[279:0];load_q<=load_dq[279:0];
  safe_q<=rst_n&&!collision;
  if(!rst_n)fault<=0;else fault<=fault|collision;
 end
 for(genvar k=0;k<280;k=k+1)begin:G
  assign dq[k]=(raw_q[k]&rv[k/32])|(load_q[k]&lv[k/32]);
 end
 assign dq[280]=safe_q&&(rv[9]||lv[9]);
endmodule
// Separate parameter specialisations retain real copies through hierarchical
// synthesis; an RTL array of identical flops can otherwise be merged.
(* keep_hierarchy="yes" *)
module ot_hbm_dma_route_copy #(parameter integer COPY_ID=0)(input wire clk,d,output wire q);
 (* keep="true" *)reg value;
 always @(posedge clk)value<=d;
 assign q=value;
endmodule
`default_nettype wire
