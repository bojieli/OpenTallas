// Candidate actual-go admission. Payload capture and toggle happen on the SAME
// core edge; acknowledged payload remains in the production accepted registers.
module ot_qwen_context_admission (
 input wire clk,rst_n,offer_go,core_ready,core_idle,
 input wire [47:0] offered_identity,accepted_identity,
 input wire accept_ack_toggle,transport_fence,
 output wire core_go,
 output reg accept_toggle,
 output reg fault
);
 reg accepted_valid;
 wire pending=accept_toggle!=accept_ack_toggle;
 wire duplicate=accepted_valid&&offered_identity==accepted_identity;
 assign core_go=offer_go&&core_ready&&!pending&&!duplicate&&!transport_fence;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin accept_toggle<=0;accepted_valid<=0;fault<=0;end
  else begin
   if(core_go)begin accept_toggle<=!accept_toggle;accepted_valid<=1;end
   if(transport_fence)begin
    if(pending||!core_idle||offer_go)fault<=1;
    else accepted_valid<=0;
   end
  end
 end
endmodule
