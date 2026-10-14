// Default-off physical decomposition of indexed DEPTH32/full21-bit cache.
// No extra response edge: live loader owns store, coherent core owns response.
// Store status is not an approved physical global clock enable.
module ot_qwen_xcache_store32 (
 input wire clk,input wire rst_n,input wire clear,input wire j_repeat,
 input wire load_v,input wire [20:0] load_epoch,input wire [127:0] load_x,
 input wire [20:0] read_epoch,
 output wire found,output wire [127:0] read_x
);
 reg [127:0] data[0:31];reg [20:0] tags[0:31];reg [31:0] valid;
 wire [20:0] lt=j_repeat?{load_epoch[20:3],3'b0}:load_epoch;
 wire [20:0] rt=j_repeat?{read_epoch[20:3],3'b0}:read_epoch;
 wire [4:0] li=j_repeat?load_epoch[7:3]:load_epoch[4:0];
 wire [4:0] ri=j_repeat?read_epoch[7:3]:read_epoch[4:0];
 assign found=valid[ri]&&tags[ri]==rt;
 assign read_x=data[ri];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) valid<=0;
  else if(clear) valid<=0;
  else if(load_v) begin valid[li]<=1;tags[li]<=lt;data[li]<=load_x;end
 end
endmodule
module ot_qwen_xcache_response (
 input wire clk,input wire rst_n,input wire [3:0] read_v,
 input wire found,input wire [127:0] read_x,
 output reg [127:0] q_x,output reg fault,output wire hit
);
 assign hit=!(|read_v)||found;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin q_x<=0;fault<=0;end
  else if(|read_v) begin
   if(found) q_x<=read_x;
   else begin q_x<=0;fault<=1;end
  end
 end
endmodule
module ot_qwen_xcache_split32 (
 input wire load_clk,input wire core_clk,input wire rst_n,input wire clear,
 input wire j_repeat,input wire load_v,input wire [20:0] load_epoch,
 input wire [127:0] load_x,input wire [3:0] read_v,input wire [20:0] read_epoch,
 output wire hit,output wire [127:0] q_x,output wire fault
);
 wire found;wire [127:0] read_x;
 ot_qwen_xcache_store32 u_store(.clk(load_clk),.rst_n(rst_n),.clear(clear),
 .j_repeat(j_repeat),.load_v(load_v),.load_epoch(load_epoch),.load_x(load_x),
 .read_epoch(read_epoch),.found(found),.read_x(read_x));
 ot_qwen_xcache_response u_response(.clk(core_clk),.rst_n(rst_n),
 .read_v(read_v),.found(found),.read_x(read_x),.q_x(q_x),.fault(fault),.hit(hit));
endmodule
