// Standalone candidate ONLY. No parent ABI, physical view or latency adoption.
// TX R0/R1 replace the SAME two existing captures: +0 compiler edges.
// R0 external payload267 = xfull128 + wupper128 + ctrl6 + gm4 + round1.
// R0 stored207 = rawxupper64 + wupper128 + ctrl6 + carry4 + gm4 + round1.
// R1 stored198 = masked/rounded xupper64 + wupper128 + ctrl6.
// Bit order in each vector is the original lane order, lowest lane at low bits.
module qwen_tx_rne_pack #(parameter integer MUT=0)(
 input wire [127:0] x, wupper,
 input wire [5:0] ctrl,
 input wire [3:0] gm,
 input wire round,
 output wire [206:0] packet
);
 wire [63:0] rawupper;
 wire [3:0] carry;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [31:0] word_x=x[32*g+:32];
  assign rawupper[16*g+:16]=word_x[31:16];
  // Exact carry into bit16 from ORIGINAL modulo32 RNE addition.
  assign carry[g]=(MUT==1)?(word_x[14] & ((|word_x[13:0]) | word_x[16])):
                  (MUT==2)?(word_x[15] & (|word_x[14:0])):
                           (word_x[15] & ((|word_x[14:0]) | word_x[16]));
 end endgenerate
 assign packet={round,gm,carry,ctrl,wupper,rawupper};
endmodule

module qwen_tx_rne_finish #(parameter integer MUT=0)(
 input wire [206:0] packet,
 output wire [197:0] finished
);
 wire round=packet[206];
 wire [3:0] gm=packet[205:202];
 wire [3:0] carry=packet[201:198];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [15:0] rawupper=packet[16*((MUT==4)?(3-g):g)+:16];
  wire [15:0] rounded=rawupper+{15'b0,(round & carry[g])};
  assign finished[16*g+:16]=((MUT==3)||gm[g])?rounded:16'b0;
 end endgenerate
 assign finished[197:64]=packet[197:64];
endmodule

module qwen_tx_rne_r0 #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire [127:0] x,wupper,
 input wire [5:0] ctrl,
 input wire [3:0] gm,
 input wire round,
 output wire [206:0] q
);
 wire [206:0] packet;
 qwen_tx_rne_pack #(.MUT(MUT)) pack(.x(x),.wupper(wupper),.ctrl(ctrl),.gm(gm),.round(round),.packet(packet));
 // Real packet reset: async assertion, three local release edges, then capture.
 ot_qkh_packet_pipe #(.W(207),.MUT(MUT==5?1:0)) capture
  (.clk(clk),.rst_n((MUT==6)?1'b1:rst_n),.d(packet),.q(q));
endmodule

module qwen_tx_rne_r1 #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire [206:0] d,
 output wire [197:0] q
);
 wire [197:0] finished;
 qwen_tx_rne_finish #(.MUT(MUT)) finish(.packet(d),.finished(finished));
 ot_qkh_packet_pipe #(.W(198)) capture(.clk(clk),.rst_n(rst_n),.d(finished),.q(q));
endmodule
