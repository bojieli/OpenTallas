`timescale 1ns/1ps
// Fixed allocation: mutable VM source ports44..47. Each drives four128-bit
// dispatch-column leaves. Compiler supplies capture_lane/storage_slot; these
// are reservations, not readiness indications. Real SRAM visibility is E10
// from this producer's E0 source pins, per the uniform VM contract b7400cf3c.
module s81_static_tp4_vm_producer(
 input wire clk,rst_n,
 input wire [3:0] gather_we,input wire [59:0] gather_rows,
 input wire [2047:0] gather_data,
 input wire [7:0] identity,input wire [7:0] capture_lane,storage_slot,
 output reg [3:0] source_v,output reg [55:0] source_row,
 output reg [63:0] source_mask,output reg [2047:0] source_data,
 output reg [31:0] source_tag,output reg [7:0] source_capture_lane,source_storage_slot,
 output reg fault
);
 reg invalid;integer r;
 always @* begin
  invalid=0;
  for(integer j=0;j<4;j=j+1)if(gather_we[j] && gather_rows[j*15+14])invalid=1;
 end
 // Registered handoff adds one edge, explicitly separate from endpoint4.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin source_v<=0;source_row<=0;source_mask<=0;source_data<=0;source_tag<=0;
   source_capture_lane<=0;source_storage_slot<=0;fault<=0;end
  else begin
   if(invalid)fault<=1;
   source_v<=invalid || fault ? 4'b0 : gather_we;
   source_data<=gather_data;source_mask<=64'hffffffffffffffff;
   source_tag<={4{identity}};source_capture_lane<=capture_lane;source_storage_slot<=storage_slot;
   for(r=0;r<4;r=r+1)source_row[r*14+:14]<=gather_rows[r*15+:14];
  end
 end
endmodule
