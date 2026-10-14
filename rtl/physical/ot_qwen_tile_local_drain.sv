// Default-off local arithmetic drain candidate. All clocks must be the exact
// coherent native core family; no base-clock counting. A registered last-issue
// marker is observed one CC edge later, then48 edges expire to issue+49.
// This does NOT cover independent incoming node n_va, replay, or source drain.
module ot_qwen_tile_local_drain (
 input wire core_clk,rst_n,
 input wire issue_last,
 input wire [15:0] issue_context,
 input wire [31:0] issue_version,
 input wire [3:0] drain_ack_toggle,
 output reg [3:0] drain_toggle,
 output wire [191:0] drain_tuple,
 output reg overflow_fault
);
 reg [3:0] busy;
 reg [5:0] remaining[0:3];
 reg [47:0] identities[0:3];
 integer i;integer selected;
 always @*begin
  selected=-1;
  for(integer s=3;s>=0;s=s-1)
   if(!busy[s] && drain_toggle[s]==drain_ack_toggle[s])selected=s;
 end
 genvar n;generate for(n=0;n<4;n=n+1)begin:g_identity
  assign drain_tuple[48*n+:48]=identities[n];
 end endgenerate
 always @(posedge core_clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;drain_toggle<=0;overflow_fault<=0;end
  else begin
   for(i=0;i<4;i=i+1)if(busy[i])begin
    if(remaining[i]==1)begin busy[i]<=0;drain_toggle[i]<=!drain_toggle[i];end
    else remaining[i]<=remaining[i]-1'b1;
   end
   if(issue_last)begin
    if(selected<0)overflow_fault<=1;
    else begin busy[selected]<=1;remaining[selected]<=6'd48;
     identities[selected]<={issue_context,issue_version};end
   end
  end
 end
endmodule
