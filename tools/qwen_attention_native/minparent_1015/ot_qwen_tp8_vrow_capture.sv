`timescale 1ns/1ps
// Real fixed pipeline state, with an explicit owner/clock boundary. Align the
// V payload and identity with the actual exponent-memory read latency.
module ot_qwen_tp8_vrow_capture #(
 parameter integer LATENCY=1, MUT=0
) (
 input wire clk,rst_n,input wire [1:0] in_valid,input wire [5:0] in_slot,
 input wire [27:0] in_t,input wire [31:0] in_epoch,input wire [2047:0] in_rows,
 output wire [1:0] out_valid,output wire [5:0] out_slot,
 output wire [27:0] out_t,output wire [31:0] out_epoch,output wire [2047:0] out_rows
);
 reg [1:0] valids[0:LATENCY-1];
 reg [5:0] slots[0:LATENCY-1];
 reg [27:0] tags[0:LATENCY-1];
 reg [31:0] epochs[0:LATENCY-1];
 reg [2047:0] rows[0:LATENCY-1];
 initial if(LATENCY<1)$fatal(1,"V capture latency must be positive");
 assign out_valid=valids[LATENCY-1];assign out_slot=slots[LATENCY-1];
 assign out_t=tags[LATENCY-1];assign out_epoch=epochs[LATENCY-1];
 assign out_rows=rows[LATENCY-1] ^ (MUT ? 2048'd1 : 2048'd0);
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   for(i=0;i<LATENCY;i=i+1)begin
    valids[i]<=0;slots[i]<=0;tags[i]<=0;epochs[i]<=0;rows[i]<=0;
   end
  end else begin
   valids[0]<=in_valid;slots[0]<=in_slot;tags[0]<=in_t;epochs[0]<=in_epoch;rows[0]<=in_rows;
   for(i=1;i<LATENCY;i=i+1)begin
    valids[i]<=valids[i-1];slots[i]<=slots[i-1];tags[i]<=tags[i-1];
    epochs[i]<=epochs[i-1];rows[i]<=rows[i-1];
   end
  end
 end
endmodule
