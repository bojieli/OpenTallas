// Related-clock cache seam: loader keeps running on clk; read response and all
// ME state advance on core_clk. A stall freezes the whole core/ROM pipeline,
// including this response register. Implement core_clk with the die clock
// controller/ICG; this module does not infer a clock gate or waive timing.
module ot_qwen_xcache_seam #(
 parameter integer DEPTH=256, parameter integer MUT_ADDR=0
)(
 input wire clk,input wire core_clk,input wire rst_n,input wire clear,
 input wire load_v,input wire [$clog2(DEPTH)-1:0] load_slot,
 input wire [95:0] load_addr,input wire [127:0] load_x,
 input wire [3:0] read_v,input wire [95:0] read_addr,
 output wire hit,output reg [127:0] q_x,output reg fault
);
 reg [95:0] tags[0:DEPTH-1];reg [127:0] data[0:DEPTH-1];reg [DEPTH-1:0] valid;
 reg found;reg [127:0] selected;
 integer n;
 always @* begin
  found=0;selected=0;
  for(n=0;n<DEPTH;n=n+1) if(valid[n] && tags[n]==read_addr) begin
   found=1;selected=data[MUT_ADDR?(n^1):n];
  end
 end
 assign hit=!(|read_v)||found;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) valid<=0;
  else if(clear) valid<=0;
  else if(load_v) begin valid[load_slot]<=1;tags[load_slot]<=load_addr;data[load_slot]<=load_x;end
 end
 always @(posedge core_clk or negedge rst_n) begin
  if(!rst_n) begin q_x<=0;fault<=0;end
  else if(|read_v) begin
   if(found) q_x<=selected;
   else begin q_x<=0;fault<=1;end
  end
 end
endmodule
