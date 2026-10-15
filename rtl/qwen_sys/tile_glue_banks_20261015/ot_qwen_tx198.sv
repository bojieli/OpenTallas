// Candidate ABI tx198-v1: compression occurs AFTER original rounding/masking.
// The unchanged LAT8 LSL multiplier decodes only operand bits31:16, including
// sign, exponent, zero/nonfinite flags. FP32 accumulator/tree remain unchanged.
module ot_qwen_tx198_codec #(parameter integer MUT=0)(
 input wire [389:0] full_d, output wire [197:0] packed_d,
 input wire [197:0] packed_q, output wire [389:0] full_q
);
 genvar i;
 generate for(i=0;i<4;i=i+1) begin:gx
  assign packed_d[16*i+:16]=full_d[32*i+((MUT==1)?0:16)+:16];
  assign full_q[32*i+:32]={packed_q[16*((MUT==2)?(3-i):i)+:16],16'b0};
 end
 for(i=0;i<8;i=i+1) begin:gw
  assign packed_d[64+16*i+:16]=full_d[128+32*i+((MUT==1)?0:16)+:16];
  assign full_q[128+32*i+:32]={packed_q[64+16*i+:16],16'b0};
 end endgenerate
 assign packed_d[197:192]=full_d[389:384];
 assign full_q[389:384]=packed_q[197:192];
endmodule

// Each physical rung is one existing CLOSED V256 master and one actual root.
// Two rungs retain the original XTX=2 data age. Unused58bits are literal zero;
// full128-bit s2_x MUST remain separately captured before original FP32 RNE.
module ot_qwen_tx198 #(parameter integer MUT=0)(
 input wire [1:0] ck,rst_n,input wire [389:0] d,output wire [389:0] q
);
 wire [197:0] p,unused_p;
 wire [255:0] r0,r1;
 ot_qwen_tx198_codec #(.MUT(MUT)) codec(.full_d(d),.packed_d(p),.packed_q(r1[197:0]),.full_q(q));
 qkh_packet_v256 rung0(.clk(ck[0]),.rst_n(rst_n[0]),.d({58'b0,p}),.q(r0));
 qkh_packet_v256 rung1(.clk(ck[1]),.rst_n(rst_n[1]),.d(r0),.q(r1));
endmodule
