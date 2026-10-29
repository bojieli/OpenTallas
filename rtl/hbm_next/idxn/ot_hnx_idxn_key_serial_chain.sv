`default_nettype none
// Distributed static transport: each source owns only its own packet pins.
// The seed has no unprovided upstream input. Every merge is one registered
// local2:1 choice; the compiler guarantees exclusive slots, collision faults.
module ot_hnx_idxn_key_serial_seed(
 input wire clk,rst_n,input wire inject_v,input wire[2:0]physical_lane,
 input wire[7:0]row,input wire cohort,input wire[1098:0]packet,
 output reg[1111:0]rail,output reg fault
);
 wire[9:0]tag={physical_lane,7'b0}+{2'b0,row};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rail<=0;fault<=0;end
  else begin
   rail<={inject_v,cohort,row,physical_lane,packet[1087:0],packet[1097:1088],packet[1098]};
   if(inject_v&&(!packet[1098]||packet[1097:1088]!=tag||row>8'd170))fault<=1;
  end
 end
endmodule
module ot_hnx_idxn_key_serial_merge(
 input wire clk,rst_n,input wire[1111:0]upstream,
 input wire inject_v,input wire[2:0]physical_lane,
 input wire[7:0]row,input wire cohort,input wire[1098:0]packet,
 output reg[1111:0]rail,output reg fault
);
 wire[9:0]tag={physical_lane,7'b0}+{2'b0,row};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rail<=0;fault<=0;end
  else begin
   rail<=inject_v?{inject_v,cohort,row,physical_lane,packet[1087:0],packet[1097:1088],packet[1098]}:upstream;
   if(inject_v&&(upstream[1111]||!packet[1098]||packet[1097:1088]!=tag||row>8'd170))fault<=1;
  end
 end
endmodule
`default_nettype wire
