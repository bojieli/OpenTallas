// Indexed local response leaf,32 entries by default (<5k storage flops).
// Full production pre-update{k18,j3} tag guards slot wrap. Native xjs0 maps
// repeated J slots to one K entry; arbitraryJ uses full tag. Misses require
// coherent whole-pipeline pause and a fresh exact source response before resume.
// No wire-ABI adoption: load tag must be proved from source context/addresses.
module ot_qwen_xcache_indexed #(
 parameter integer DEPTH=32,parameter integer MUT_ROW=0
)(
 input wire load_clk,input wire core_clk,input wire rst_n,input wire clear,
 input wire j_repeat,input wire load_v,input wire [20:0] load_epoch,
 input wire [127:0] load_x,input wire [3:0] read_v,input wire [20:0] read_epoch,
 output wire hit,output reg [127:0] q_x,output reg fault
);
 localparam integer AB=$clog2(DEPTH);
 reg [127:0] data[0:DEPTH-1];reg [20:0] tags[0:DEPTH-1];reg [DEPTH-1:0] valid;
 wire [20:0] lt=j_repeat?{load_epoch[20:3],3'b0}:load_epoch;
 wire [20:0] rt=j_repeat?{read_epoch[20:3],3'b0}:read_epoch;
 wire [AB-1:0] li=j_repeat?load_epoch[AB+2:3]:load_epoch[AB-1:0];
 wire [AB-1:0] ri=j_repeat?read_epoch[AB+2:3]:read_epoch[AB-1:0];
 wire found=valid[ri]&&tags[ri]==rt;
 assign hit=!(|read_v)||found;
 always @(posedge load_clk or negedge rst_n) begin
  if(!rst_n) valid<=0;
  else if(clear) valid<=0;
  else if(load_v) begin valid[li]<=1;tags[li]<=lt;data[li]<=load_x;end
 end
 always @(posedge core_clk or negedge rst_n) begin
  if(!rst_n) begin q_x<=0;fault<=0;end
  else if(|read_v) begin
   if(found) q_x<=data[MUT_ROW?(ri^1):ri];
   else begin q_x<=0;fault<=1;end
  end
 end
endmodule
