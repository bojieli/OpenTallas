// Default-off fixed native output identity. Source query allocation is already
// registered on issueedge0;46 real coherent capture edges align this companion
// with the unchanged actual node TOREG numeric output atissue+46.
// A mailbox toggle is produced on THAT edge, not a later edge after a pause.
module ot_qwen_tile_query_output_identity (
 input wire core_clk,rst_n,
 input wire query_issue_v,
 input wire [39:0] query_sequence,
 input wire [15:0] query_context,
 input wire [31:0] query_version,
 input wire query_output_ack_toggle,
 output wire query_output_credit,
 output reg query_output_toggle,
 output reg [87:0] query_output_tuple,
 output reg fault
);
 reg [87:0] metadata[0:44];reg [44:0] valid;
 assign query_output_credit=query_output_toggle==query_output_ack_toggle;
 integer i;
 always @(posedge core_clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;query_output_toggle<=0;fault<=0;end
  else begin
   valid<={valid[43:0],query_issue_v};
   metadata[0]<={query_context,query_version,query_sequence};
   for(i=1;i<45;i=i+1)metadata[i]<=metadata[i-1];
   // stage44 is the next word entering the46th capture. This is aligned
   // to post-edge real t_out/t_vout and is qualified ONLY by queryallocation.
   if(valid[44])begin
    if(!query_output_credit)fault<=1;
    else begin query_output_toggle<=!query_output_toggle;query_output_tuple<=metadata[44];end
   end
  end
 end
endmodule
