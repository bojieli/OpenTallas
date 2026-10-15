`default_nettype none
// Compiler-fixed local/mirror IDX read face. A descriptor at edge n produces
// a registered request; bank samples at n+1, responds n+7 (bank ABI n+6),
// and this face captures at n+8. No queue, credit, lease or runtime waiting.
// SID, bank ownership, and all eight capture edges belong to the compiler.
module ot_hbm_idx_vm_static #(
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire [1:0] sid,
 input wire [135:0] read_slot, // eight {valid,mirror/global_sector15}
 input wire [127:0] read_tag,
 output reg [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output reg [2055:0] result,
 output reg [127:0] result_tag,
 output reg fault
);
 reg [7:0] due[0:7];
 reg [127:0] tags[0:7];
 wire [7:0] expected=due[(MUT==2)?6:7];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   vm_rq<=0;result<=0;result_tag<=0;fault<=0;
   for(integer d=0;d<8;d=d+1) begin due[d]<=0;tags[d]<=0;end
  end else begin
   for(integer d=1;d<8;d=d+1) begin due[d]<=due[d-1];tags[d]<=tags[d-1];end
   tags[0]<=read_tag;
   result_tag<=tags[(MUT==3)?6:7];
   for(integer b=0;b<8;b=b+1) begin
    // Remote main reads are illegal on this face, never silently remapped.
    due[0][b]<=read_slot[17*b+16];
    vm_rq[17*b+:17]<=read_slot[17*b+:17];
    if(MUT==1 && read_slot[17*b+16]) vm_rq[17*b+3]<=~read_slot[17*b+3];
    if(read_slot[17*b+16] && (read_slot[17*b+:3]!=3'(b) ||
      (!read_slot[17*b+15] && read_slot[17*b+13+:2]!=sid))) begin
     fault<=1;vm_rq[17*b+16]<=0;due[0][b]<=0;
    end
    if(vm_rr[257*b+256]!=expected[b]) fault<=1;
    result[257*b+:257]<={expected[b] && vm_rr[257*b+256],vm_rr[257*b+:256]};
   end
  end
 end
endmodule
`default_nettype wire
