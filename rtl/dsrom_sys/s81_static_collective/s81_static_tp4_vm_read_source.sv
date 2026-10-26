`timescale 1ns/1ps
// Wires the actual uniform VM grouped-read API to the scheduled collective
// producer. It contains no payload storage or reference data. E10 read release
// and endpoint capture edges remain compiler-assigned, accounting for pin phase.
module s81_static_tp4_vm_read_source(
 input wire clk,rst_n,
 input wire read_slot,input wire [13:0] read_row,
 input wire [2:0] read_group,input wire [4:0] read_return_slot,
 output reg [31:0] rq_v,output reg [447:0] rq_row,output reg [255:0] rq_tag,
 input wire source_slot,input wire [2:0] source_group,input wire [4:0] source_return_slot,
 input wire [31:0] owned_return_slots,
 input wire [31:0] group_v,input wire [2:0] group_id,input wire [16383:0] group_data,
 output wire src_valid,output wire [511:0] src_data,output reg fault
);
 integer position;reg [31:0] relevant,expected;
 always @* begin
  // Packet position is the inverse of the native group/slot transpose.
  position=8*int'(read_return_slot[1:0])+int'(read_return_slot[4:2]);
  rq_v=0;rq_row=0;rq_tag=0;
  if(read_slot && read_row[1:0]==read_return_slot[1:0])begin
   rq_v[position]=1;rq_row[position*14+:14]=read_row;
   rq_tag[position*8+:8]={read_group,read_return_slot};
  end
  relevant=group_id==source_group ? group_v & owned_return_slots:32'b0;
  expected=source_slot ? (32'b1 << source_return_slot):32'b0;
 end
 assign src_valid=source_slot && group_id==source_group && group_v[source_return_slot];
 assign src_data=group_data[source_return_slot*512+:512];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)fault<=0;
  else if((read_slot && read_row[1:0]!=read_return_slot[1:0]) || relevant!=expected ||
          (source_slot && !owned_return_slots[source_return_slot]))fault<=1;
 end
endmodule
