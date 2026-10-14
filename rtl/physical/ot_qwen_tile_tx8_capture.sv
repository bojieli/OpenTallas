// Default-off grouped final XTX rung: eight390-bit banks,3120FF total.
// One architectural coherent core edge; each bank retains its valid-only
// asynchronous reset. All389 data/meta bits retain unreset capture behavior.
module ot_qwen_tile_tx8_capture (
 input wire clk,input wire [7:0] rst_n,input wire [3119:0] d,
 output reg [3119:0] q
);
 genvar i;
 generate for(i=0;i<8;i=i+1)begin:g_bank
  always @(posedge clk) q[390*i+:389]<=d[390*i+:389];
  always @(posedge clk or negedge rst_n[i])
   if(!rst_n[i])q[390*i+389]<=0;else q[390*i+389]<=d[390*i+389];
 end endgenerate
endmodule
