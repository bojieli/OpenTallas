// Distinct default-off streaming metadata companion. Historical0c81/36f
// mailboxes stand. Registered tag accompanies the unchanged TOREG word on
// actualedge46; it is a posted level, qualified by actual numeric t_vout and
// producing output_step. A live queue MUST reserve capacity BEFORE that edge.
// No publication ACK/mailbox is inserted here; query-generation credit remains
// independently required. Actual source/gate phase/CDC and cost are unqualified.
module ot_qwen_tile_numeric_output_metadata (
 input wire core_clk,rst_n,
 input wire query_issue_v,
 input wire [39:0] query_sequence,
 input wire [15:0] query_context,
 input wire [31:0] query_version,
 output wire [88:0] numeric_tuple
);
 reg [87:0] metadata[0:44];reg [44:0] valid;
 reg has_query;reg [87:0] payload;
 assign numeric_tuple={has_query,payload};
 integer i;
 always @(posedge core_clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;has_query<=0;end
  else begin valid<={valid[43:0],query_issue_v};has_query<=valid[44];end
 end
 // Datapath metadata carries no reset, as the unchanged numeric pipeline does.
 // Valid/type reset and actual t_vout qualify it after the transport fence.
 always @(posedge core_clk)begin
  metadata[0]<={query_context,query_version,query_sequence};
  for(i=1;i<45;i=i+1)metadata[i]<=metadata[i-1];
  payload<={metadata[44][87:40],valid[44]?metadata[44][39:0]:40'd0};
 end
endmodule
