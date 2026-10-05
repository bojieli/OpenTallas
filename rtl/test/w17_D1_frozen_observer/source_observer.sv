`timescale 1ns/1ps
// SIMULATION ONLY, one-credit original WINDOW. No signal feeds back into DUT.
module w17_D1_source_observer #(parameter bit ENABLED=0)(
 input wire clk,rst_n,fault,
 input wire accept,we,input wire [2:0] state,
 input wire [29:0] address,input wire [15:0] tag,
 input wire response,input wire [15:0] response_tag,input wire [3:0] beat,
 input wire poison,write_done,
 output wire available,
 output reg [63:0] read_accepts,read_returns,write_accepts,write_acks,
 output reg [7:0] violations,
 output reg pending,output reg [29:0] pending_address,output reg [15:0] pending_tag
);
 assign available=ENABLED;
 reg pending_write,pending_scale;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   read_accepts<=0;read_returns<=0;write_accepts<=0;write_acks<=0;violations<=0;
   pending<=0;pending_write<=0;pending_scale<=0;pending_address<=0;pending_tag<=0;
  end else if(ENABLED)begin
   if(fault)violations[0]<=1;
   // Fault wins over callback/completion on this edge and stays sticky.
   if(!fault && violations==0)begin
    if(accept)begin
     if(pending || response || write_done || (!we && state!=5) || (we && state!=1 && state!=3))violations[1]<=1;
     else begin
      pending<=1;pending_write<=we;pending_scale<=state==3;pending_address<=address;pending_tag<=tag;
      if(we)write_accepts<=write_accepts+64'd1;else read_accepts<=read_accepts+64'd1;
     end
    end
    if(response)begin
     if(!pending || pending_write || accept || state!=6 || response_tag!=pending_tag || beat!=0 || poison)violations[2]<=1;
     else begin pending<=0;read_returns<=read_returns+64'd1;end
    end
    if(write_done)begin
     if(!pending || !pending_write || accept || response || state!=(pending_scale ? 4 : 2))violations[3]<=1;
     else begin pending<=0;write_acks<=write_acks+64'd1;end
    end
   end
  end
 end
endmodule
