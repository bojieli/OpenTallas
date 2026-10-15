// TX RNE successor #3 (Q-COMPUTE-ELEM r14, 2026-10-15), PROPOSED, needs compiler acceptance of +1 TX edge.
// Measured: no zero-edge split of the RNE cone fits the native 220/190 boundary split
//   rnen: r1 capture 228.2 ps; rnep: r0 launch 248.1 ps / r1 capture 198.9 ps.
// Structure: R0 = 267-bit pin flop -> complete exact RNE (low16 carry, +1, upper keep) + group mask -> 198-bit output
// flop.  The whole cone is an internal reg-to-reg path (no logic between pin and flop on either side).
// R1 = 198-bit pure capture register (existing second TX edge).  Edges: 3 (+1 vs the original two).
module qwen_tx_rnes_core #(parameter integer MUT=0)(input wire [266:0] raw, output wire [197:0] f);
 wire round=raw[266]; wire [3:0] gm=raw[265:262]; wire [5:0] ctrl=raw[261:256];
 wire [127:0] wupper=raw[255:128], x=raw[127:0];
 wire [63:0] r;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [31:0] w=x[32*g+:32];
  wire carry=(MUT==1)?(w[14] & ((|w[13:0]) | w[16])):(MUT==2)?(w[15] & (|w[14:0])):(w[15] & ((|w[14:0]) | w[16]));
  wire [15:0] up=w[31:16]+{15'b0,round&carry};
  localparam integer G=(MUT==4)?(3-g):g;
  assign r[16*G+:16]=((MUT==3)||gm[g])?up:16'b0;
 end endgenerate
 assign f={ctrl,wupper,r};
endmodule
module qwen_tx_rnes_r0 #(parameter integer MUT=0)(
 input wire clk,rst_n, input wire [127:0] x,wupper, input wire [5:0] ctrl, input wire [3:0] gm, input wire round,
 output wire [197:0] q);
 wire [266:0] raw; wire [197:0] f;
 ot_qkh_packet_pipe #(.W(267),.MUT(MUT==5?1:0)) capture(.clk(clk),.rst_n((MUT==6)?1'b1:rst_n),.d({round,gm,ctrl,wupper,x}),.q(raw));
 qwen_tx_rnes_core #(.MUT(MUT)) core(.raw(raw),.f(f));
 ot_qkh_packet_pipe #(.W(198)) launch(.clk(clk),.rst_n(rst_n),.d(f),.q(q));
endmodule
module qwen_tx_rnes_r1 #(parameter integer MUT=0)(input wire clk,rst_n, input wire [197:0] d, output wire [197:0] q);
 ot_qkh_packet_pipe #(.W(198)) capture(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
