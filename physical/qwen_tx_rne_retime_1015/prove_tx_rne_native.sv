// Independent original full32 rounding/mask, THEN existing TX198 packing.
module prove_tx_rne_native #(parameter integer MUT=0)(
 input wire [127:0] x,wupper,input wire [5:0]ctrl,
 input wire [3:0]gm,input wire round,output wire exact
);
 wire [205:0] packet;wire [201:0] staged;wire [197:0] actual;
 qwen_tx_rnen_r0_out #(.MUT(MUT)) r0o(.raw({round,gm,ctrl,wupper,x}),.p(packet));
 qwen_tx_rnen_r1_in #(.MUT(MUT)) r1i(.p(packet),.s(staged));
 qwen_tx_rnen_r1_out #(.MUT(MUT)) r1o(.s(staged),.f(actual));
 wire [127:0] original_x;
 wire [389:0] full_tx;
 wire [197:0] expected;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [31:0] original_word=x[32*g+:32];
  wire [31:0] rounded_full=original_word+32'h00007fff+{31'b0,original_word[16]};
  assign original_x[32*g+:32]=!gm[g]?32'b0:round?(rounded_full & 32'hffff0000):original_word;
 end
 for(g=0;g<8;g=g+1)begin:gw
  assign full_tx[128+32*g+:32]={wupper[16*g+:16],16'b0};
 end endgenerate
 assign full_tx[127:0]=original_x;
 assign full_tx[389:384]=ctrl;
 // Actual current candidate codec, independent of the retimed pack/finish.
 wire [389:0] unused;
 ot_qwen_tx198_codec codec(.full_d(full_tx),.packed_d(expected),.packed_q(198'b0),.full_q(unused));
 assign exact=actual==expected;
endmodule
