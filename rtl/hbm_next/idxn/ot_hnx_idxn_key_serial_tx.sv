`default_nettype none
// A compiler-selected4-slot lane, never an arbiter. Normal SVG packet layout
// (valid1098/tag1097:1088/payload1087:0) becomes the existing keybuf layout.
// One registered output envelope is the named1112-bit transport boundary.
module ot_hnx_idxn_key_serial_tx(
 input wire clk,rst_n,input wire[2:0]strap_lane_base,
 input wire slot_v,input wire[1:0]slot_lane,input wire[7:0]slot_row,
 input wire slot_cohort,input wire[4395:0]source_packets,
 output reg[1111:0]tx,output reg fault
);
 wire[1098:0]packet=source_packets[int'(slot_lane)*1099+:1099];
 wire[2:0]physical_lane=strap_lane_base+3'(slot_lane);
 wire[9:0]tag={physical_lane,7'b0}+{2'b0,slot_row};
 reg off_slot_packet;
 always @*begin
  off_slot_packet=0;
  for(integer p=0;p<4;p=p+1)
   if(p!=int'(slot_lane)&&source_packets[p*1099+1098])off_slot_packet=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin tx<=0;fault<=0;end
  else begin
   tx<={slot_v,slot_cohort,slot_row,physical_lane,packet[1087:0],packet[1097:1088],packet[1098]};
   if(slot_v&&(!packet[1098]||packet[1097:1088]!=tag||slot_row>8'd170||off_slot_packet))fault<=1;
  end
 end
endmodule
`default_nettype wire
