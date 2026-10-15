`timescale 1ns/1ps
// Digital framing and CRC are DUT logic. Only phy_* wires/analog flight may be
// modeled externally. Two consecutive 512-bit PHY beats per reserved frame.
// Fixed latency, no retry in normal mode; corrupt/missing beats fault closed.
module s81_static_phy_digital(
 input wire clk,rst_n,input wire tx_valid,input wire [568:0] tx_frame,
 output reg phy_tx_valid,output reg [511:0] phy_tx_data,
 input wire phy_rx_valid,input wire [511:0] phy_rx_data,
 output reg rx_valid,output reg [568:0] rx_frame,output reg fault
);
 function automatic [31:0] crc(input [568:0] d);
  reg [31:0] c;reg b;integer j;
  begin c=32'hffffffff;for(j=0;j<569;j=j+1)begin b=c[31]^d[j];c={c[30:0],1'b0};if(b)c=c^32'h04c11db7;end crc=~c;end
 endfunction
 reg tx_tail,rx_tail;reg [88:0] tail;reg [511:0] head;reg [568:0] assembled;
 always @* assembled={phy_rx_data[56:0],head};
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin tx_tail<=0;rx_tail<=0;tail<=0;head<=0;phy_tx_valid<=0;phy_tx_data<=0;rx_valid<=0;rx_frame<=0;fault<=0;end
  else begin
   phy_tx_valid<=tx_valid || tx_tail;rx_valid<=0;
   if(tx_tail)begin phy_tx_data<={423'b0,tail};tx_tail<=0;if(tx_valid)fault<=1;end
   else if(tx_valid)begin phy_tx_data<=tx_frame[511:0];tail<={crc(tx_frame),tx_frame[568:512]};tx_tail<=1;end
   if(rx_tail)begin
    rx_tail<=0;
    if(!phy_rx_valid || phy_rx_data[511:89]!=0 || phy_rx_data[88:57]!=crc(assembled))fault<=1;
    else begin rx_frame<=assembled;rx_valid<=1;end
   end else if(phy_rx_valid)begin head<=phy_rx_data;rx_tail<=1;end
  end
 end
endmodule
