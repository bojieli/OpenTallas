// Default-off fixed node-latency sideband. The real node has one input edge
// followed by8 valid-delay edges, hence9 capture stages. No arithmetic edge
// changes. Caller pauses ALL coherent clocks while node_credit is low, keeping
// the real n_y/n_vy stable until the consumer retires the produced event.
module ot_qwen_tile_node_lifetime (
 input wire core_clk,rst_n,clear_context,
 input wire node_va,
 input wire [15:0] node_context,node_sequence,
 input wire [31:0] node_version,
 input wire producer_seal_v,
 input wire [15:0] producer_seal_context,
 input wire [31:0] producer_seal_version,
 input wire node_retire_ack_toggle,
 output wire node_credit,
 output reg node_produced_toggle,
 output reg [63:0] node_produced_tuple,
 output wire [63:0] node_output_tuple,
 output wire node_output_valid,
 output reg node_accept_toggle,
 output reg [63:0] node_accept_tuple,
 input wire node_accept_ack_toggle,
 output wire node_accept_credit,
 output reg node_drained,
 output wire [47:0] node_active_identity,
 output reg fault
);
 reg [63:0] metadata[0:8];reg [8:0] valid;
 reg [47:0] active_identity;
 reg identity_valid,sealed,seen_retire;
 reg [15:0] outstanding;
 wire retired=(seen_retire!=node_retire_ack_toggle);
 wire [47:0] offered_identity={node_context,node_version};
 wire [47:0] seal_identity={producer_seal_context,producer_seal_version};
 assign node_credit=node_produced_toggle==node_retire_ack_toggle;
 assign node_accept_credit=node_accept_toggle==node_accept_ack_toggle;
 assign node_output_tuple=metadata[8];assign node_output_valid=valid[8];
 assign node_active_identity=active_identity;
 integer i;
 always @(posedge core_clk or negedge rst_n)begin
  if(!rst_n)begin
   valid<=0;identity_valid<=0;sealed<=0;seen_retire<=0;outstanding<=0;
   node_produced_toggle<=0;node_accept_toggle<=0;node_drained<=0;fault<=0;
  end else begin
   // clear_context is allowed ONLY after all local obligations and transport
   // receipts retire. It may not erase pending evidence or an arithmetic pipe.
   if(clear_context)begin
    if(outstanding!=0||(|valid)||!node_credit||!node_accept_credit)fault<=1;
    else begin identity_valid<=0;sealed<=0;node_drained<=0;end
   end
   valid<={valid[7:0],node_va};metadata[0]<={node_context,node_version,node_sequence};
   for(i=1;i<9;i=i+1)metadata[i]<=metadata[i-1];
   if(node_va)begin
    if(!node_accept_credit||!node_credit||sealed||
       (identity_valid&&active_identity!=offered_identity))fault<=1;
    else begin
     identity_valid<=1;active_identity<=offered_identity;
     node_accept_tuple<={node_context,node_version,node_sequence};
     node_accept_toggle<=!node_accept_toggle;
    end
   end
   if(valid[7])begin
    if(!node_credit)fault<=1;
    else begin node_produced_toggle<=!node_produced_toggle;
     node_produced_tuple<=metadata[7];end
   end
   if(retired)begin
    if(node_produced_toggle!=node_retire_ack_toggle||outstanding==0)fault<=1;
    seen_retire<=node_retire_ack_toggle;
   end
   case({node_va,retired})
    2'b10:outstanding<=outstanding+1'b1;
    2'b01:if(outstanding!=0)outstanding<=outstanding-1'b1;
    default:outstanding<=outstanding;
   endcase
   if(producer_seal_v)begin
    if((identity_valid&&active_identity!=seal_identity)||node_va)fault<=1;
    else begin identity_valid<=1;active_identity<=seal_identity;sealed<=1;end
   end
   node_drained<=!fault&&!clear_context&&identity_valid&&sealed&&outstanding==0&&!(|valid)&&node_credit&&node_accept_credit&&!node_va;
  end
 end
endmodule
