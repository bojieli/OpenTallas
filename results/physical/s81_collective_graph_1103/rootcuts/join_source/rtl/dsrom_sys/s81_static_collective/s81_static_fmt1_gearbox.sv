`timescale 1ns/1ps
// Existing FMT1 wire format: three596-bit slots across four512-bit beats;
// marker bit0, idle bit1, reversevalid bit2, reverse53 at[55:3], payload[511:56].
// Compiler supplies fixed beat phases and frame reservations. No FIFO/arbitration.
module s81_static_fmt1_gearbox(
 input wire clk,rst_n,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire tx_frame_v,input wire[594:0]tx_frame,
 output reg phy_tx_valid,output reg[511:0]phy_tx_data,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 input wire phy_rx_valid,input wire[511:0]phy_rx_data,
 output reg rx_frame_v,output reg[594:0]rx_frame,output reg fault
);
 wire[595:0]slot=tx_frame_slot && tx_frame_v ? {tx_frame,1'b1}:596'b0;
 reg[595:0]rem;reg[455:0]pay,hold;reg[595:0]cut;
 always @*begin
  case(tx_phase)
   0:pay=slot[455:0];
   1:pay={slot[315:0],rem[595:456]};
   2:pay={slot[175:0],rem[595:316]};
   default:pay={36'b0,rem[595:176]};
  endcase
  case(rx_phase)
   1:cut={phy_rx_data[195:56],hold};
   2:cut={phy_rx_data[335:56],hold[315:0]};
   default:cut={phy_rx_data[475:56],hold[175:0]};
  endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rem<=0;hold<=0;phy_tx_valid<=0;phy_tx_data<=0;rx_frame_v<=0;rx_frame<=0;fault<=0;end
  else begin
   phy_tx_valid<=tx_beat_slot;rx_frame_v<=0;
   if(tx_frame_v != (tx_beat_slot && tx_frame_slot))fault<=1;
   if(tx_beat_slot)begin
    if(tx_phase==3 && tx_frame_slot)fault<=1;
    phy_tx_data<={pay,53'b0,1'b0,1'b0,tx_phase==0};
    if(tx_phase!=3)rem<=slot;
   end
   if(phy_rx_valid!=rx_beat_slot)fault<=1;
   if(rx_beat_slot)begin
    if(phy_rx_data[55:1]!=0 || phy_rx_data[0]!=(rx_phase==0))fault<=1;
    case(rx_phase)
     0:hold<=phy_rx_data[511:56];
     1:hold<={140'b0,phy_rx_data[511:196]};
     2:hold<={280'b0,phy_rx_data[511:336]};
     default:hold<=hold;
    endcase
    if(rx_phase!=0)begin
     if(cut[0]!=rx_frame_slot)fault<=1;
     rx_frame_v<=rx_frame_slot && cut[0];rx_frame<=cut[595:1];
    end else if(rx_frame_slot)fault<=1;
   end
  end
 end
endmodule
