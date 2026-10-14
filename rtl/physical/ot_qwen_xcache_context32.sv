// Default-off context/mode repair candidate; no root ABI/physical adoption.
// read fields must be registered with the production pre-update request.
// load fields must be resolved from the fill's descriptor, never latest IB.
module ot_qwen_xcache_context32 #(
 parameter integer MUT_LIVE_MODE=0,MUT_RESIDENT=0
)(
 input wire load_clk,core_clk,rst_n,clear,
 input wire live_j_repeat,read_j_repeat,load_j_repeat,load_v,
 input wire [20:0] load_epoch,read_epoch,
 input wire [15:0] load_context,read_context,
 input wire [31:0] load_version,read_version,
 input wire [95:0] load_addr,read_addr,
 input wire [127:0] load_x,input wire [3:0] read_v,
 output wire hit,output reg [127:0] q_x,output reg fault
);
 reg [127:0] data[0:31];reg [20:0] tags[0:31];
 reg [15:0] contexts[0:31];reg [31:0] versions[0:31];
 reg [95:0] addresses[0:31];reg [31:0] valid,modes;
 wire rm=(MUT_LIVE_MODE!=0)?live_j_repeat:read_j_repeat;
 wire [20:0] lt=load_j_repeat?{load_epoch[20:3],3'b0}:load_epoch;
 wire [20:0] rt=rm?{read_epoch[20:3],3'b0}:read_epoch;
 wire [4:0] li=load_j_repeat?load_epoch[7:3]:load_epoch[4:0];
 wire [4:0] ri=rm?read_epoch[7:3]:read_epoch[4:0];
 wire found=valid[ri]&&tags[ri]==rt&&((MUT_RESIDENT!=0)||
  (modes[ri]==rm&&contexts[ri]==read_context&&versions[ri]==read_version&&addresses[ri]==read_addr));
 assign hit=!(|read_v)||found;
 always @(posedge load_clk or negedge rst_n) begin
  if(!rst_n)valid<=0;
  else if(clear)valid<=0;
  else if(load_v)begin
   valid[li]<=1;data[li]<=load_x;tags[li]<=lt;modes[li]<=load_j_repeat;
   contexts[li]<=load_context;versions[li]<=load_version;addresses[li]<=load_addr;
  end
 end
 always @(posedge core_clk or negedge rst_n) begin
  if(!rst_n)begin q_x<=0;fault<=0;end
  else if(|read_v)begin
   if(found)q_x<=data[ri];else begin q_x<=0;fault<=1;end
  end
 end
endmodule
