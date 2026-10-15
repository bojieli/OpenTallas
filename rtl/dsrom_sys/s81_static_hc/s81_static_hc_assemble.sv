`timescale 1ns/1ps
// No output queue: compiler schedules 16 input-word writes, then an emit edge.
// Emit requires a complete row from one tag and exact expected word positions.
// Missing, duplicate or mistagged input is sticky fault, never a runtime wait.
// Emit and writes are separate reservations; a same-edge write/emit is illegal.
module s81_static_hc_assemble #(parameter integer MUT=0)(
 input wire clk,rst_n,write_slot,
 input wire [3:0] word_index,
 input wire word_valid,
 input wire [511:0] word_data,
 input wire [31:0] word_tag,
 input wire word_error,
 input wire emit_slot,
 input wire [31:0] emit_tag,
 output reg row_valid,
 output reg [8191:0] row_data,
 output reg [31:0] row_tag,
 output reg fault
);
 reg [8191:0] assembly;
 reg [15:0] seen;
 reg [31:0] assembly_tag;
 wire write_good=write_slot && word_valid && !word_error &&
                 !seen[word_index] && ((seen==0)||(assembly_tag==word_tag));
 wire emit_good=emit_slot && !write_slot && (&seen) && (assembly_tag==emit_tag);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin seen<=0;row_valid<=0;fault<=0;end
  else begin
   row_valid<=emit_good;
   if(write_slot!=word_valid || (write_slot&&!write_good) || (emit_slot&&!emit_good)) fault<=1;
   if(write_good) seen[word_index]<=1;
   if(emit_slot) seen<=0;
  end
 end
 always @(posedge clk)begin
  if(write_good)begin
   assembly[((MUT==1)?(word_index^4'd1):word_index)*512+:512]<=word_data;
   if(seen==0) assembly_tag<=word_tag;
  end
  if(emit_good)begin row_data<=assembly;row_tag<=assembly_tag;end
 end
endmodule
