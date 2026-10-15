`timescale 1ns/1ps
`default_nettype none
// Calendar phase advances unconditionally. expected_frame is a compiler/model
// observation; frame_v only checks the reservation, never selects a transfer.
// start clears all partial words and activates the first slot on the NEXT edge.
// Wide shifts are functional RTL, not a hardened/pin-qualified implementation.
module ot_hbm_static_gearbox_tx #(
 parameter integer F=612, W=487, MUT=0
)(input wire clk,rst_n,start,
 input wire frame_v,input wire [F-1:0] frame,
 output wire expected_frame,
 output reg word_v,output reg [W-1:0] word,
 output reg fault);
 localparam integer CW=$clog2(F+1);
 reg active;
 reg [CW-1:0] count;
 reg [F+W-1:0] pending;
 wire due=count<W;
 wire [F+W-1:0] extended_frame={{W{1'b0}},frame};
 wire [F+W-1:0] joined=due ? (pending | (extended_frame << count)) : pending;
 assign expected_frame=active && due && !start;
 initial if(W<=0 || W>=F) $fatal(1,"unsupported static gearbox ratio");
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;count<=0;pending<=0;word_v<=0;word<=0;fault<=0;end
  else if(start) begin active<=1;count<=0;pending<=0;word_v<=0;word<=0;fault<=0;end
  else if(active) begin
   fault<=fault | (frame_v!=due);
   word_v<=1;
   word<=joined[W-1:0] ^ ((MUT==1)? {{(W-1){1'b0}},1'b1} : {W{1'b0}});
   pending<=joined >> W;
   if(due) count<=count+F-W; else count<=count-W;
  end else if(frame_v) fault<=1;
 end
endmodule

// RX start must be scheduled so its first active edge samples the first TX
// word. No search/valid-driven phase adaptation is allowed in normal execution.
module ot_hbm_static_gearbox_rx #(
 parameter integer F=612, W=487, MUT=0
)(input wire clk,rst_n,start,
 input wire word_v,input wire [W-1:0] word,
 output reg frame_v,output reg [F-1:0] frame,
 output reg fault);
 localparam integer CW=$clog2(F+1);
 reg active;
 reg [CW-1:0] count;
 reg [F+W-1:0] pending;
 wire [CW:0] total={1'b0,count}+W;
 wire due=total>=F;
 wire [F+W-1:0] extended_word={{F{1'b0}},word};
 wire [F+W-1:0] joined=pending | (extended_word << count);
 initial if(W<=0 || W>=F) $fatal(1,"unsupported static gearbox ratio");
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;count<=0;pending<=0;frame_v<=0;frame<=0;fault<=0;end
  else if(start) begin active<=1;count<=0;pending<=0;frame_v<=0;frame<=0;fault<=0;end
  else if(active) begin
   fault<=fault | !word_v;
   frame_v<=due;
   if(due) begin
    frame<=joined[F-1:0];
    pending<=joined >> ((MUT==2)?F-1:F);
    count<=total-F;
   end else begin pending<=joined;count<=total;end
  end else frame_v<=0;
 end
endmodule
`default_nettype wire
