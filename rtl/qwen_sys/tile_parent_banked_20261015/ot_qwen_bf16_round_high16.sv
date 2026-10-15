// Exact upper16 of the ORIGINAL modulo32 RNE expression
// (x + 32'h7fff + x[16]) & 32'hffff0000, for EVERY bit pattern.
// No NaN/Inf or subnormal reinterpretation, and no input-bit discard before RNE.
module ot_qwen_bf16_round_high16(input wire [31:0] x,output wire [15:0] y);
 wire carry=x[15] & ((|x[14:0]) | x[16]);
 assign y=x[31:16]+{15'b0,carry};
endmodule
