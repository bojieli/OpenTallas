// Native-boundary successor of qwen_tx_rne_r0/r1 (Q-COMPUTE-ELEM r13, 2026-10-15).
// Measured: the CLOSED r0/r1 views FAIL the native TT capture budget (S+R <= 190 ps): r0 x[48] 203.3 (carry OR15
// before the capture flop), r1 d[206] 223.8 (round fanned to four 16-bit incrementers + mask before the flop); both
// launches pass (176.8 / 175.5 <= 220).  Same two existing TX edges, zero compiler edges; logic moves to the side
// with margin:
//  R0  captures the raw 267 input bits at its pins; AFTER the flop forms carry_g and inc_g = round & carry_g and
//      emits 206 bits {gm4, inc4, ctrl6, wupper128, xupper64} (round no longer crosses: it is folded into inc).
//  R1  input side only adds inc_g into each 16-bit upper word (no round fanout, no mask) and captures 202 bits
//      {gm4, ctrl6, wupper128, rounded64}; AFTER the flop applies the group mask -> 198 bits (one AND per bit).
// Values on every TX edge equal the original pack/finish chain (formal: prove_tx_rne_native.sv).
module qwen_tx_rnen_r0_out #(parameter integer MUT=0)(input wire [266:0] raw, output wire [205:0] p);
 wire round=raw[266]; wire [3:0] gm=raw[265:262]; wire [5:0] ctrl=raw[261:256];
 wire [127:0] wupper=raw[255:128], x=raw[127:0];
 wire [63:0] xu; wire [3:0] inc;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [31:0] w=x[32*g+:32];
  wire carry=(MUT==1)?(w[14] & ((|w[13:0]) | w[16])):(MUT==2)?(w[15] & (|w[14:0])):(w[15] & ((|w[14:0]) | w[16]));
  assign inc[g]=round & carry;
  assign xu[16*g+:16]=w[31:16];
 end endgenerate
 assign p={gm,inc,ctrl,wupper,xu};
endmodule
module qwen_tx_rnen_r1_in #(parameter integer MUT=0)(input wire [205:0] p, output wire [201:0] s);
 wire [3:0] gm=p[205:202], inc=p[201:198];
 wire [63:0] r;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  assign r[16*g+:16]=p[16*((MUT==4)?(3-g):g)+:16]+{15'b0,inc[g]};
 end endgenerate
 assign s={gm,p[197:64],r};
endmodule
module qwen_tx_rnen_r1_out #(parameter integer MUT=0)(input wire [201:0] s, output wire [197:0] f);
 wire [3:0] gm=s[201:198];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  assign f[16*g+:16]=((MUT==3)||gm[g])?s[16*g+:16]:16'b0;
 end endgenerate
 assign f[197:64]=s[197:64];
endmodule
module qwen_tx_rnen_r0 #(parameter integer MUT=0)(
 input wire clk,rst_n, input wire [127:0] x,wupper, input wire [5:0] ctrl, input wire [3:0] gm, input wire round,
 output wire [205:0] q);
 wire [266:0] raw;
 ot_qkh_packet_pipe #(.W(267),.MUT(MUT==5?1:0)) capture(.clk(clk),.rst_n((MUT==6)?1'b1:rst_n),.d({round,gm,ctrl,wupper,x}),.q(raw));
 qwen_tx_rnen_r0_out #(.MUT(MUT)) out(.raw(raw),.p(q));
endmodule
module qwen_tx_rnen_r1 #(parameter integer MUT=0)(input wire clk,rst_n, input wire [205:0] d, output wire [197:0] q);
 wire [201:0] s,sq;
 qwen_tx_rnen_r1_in #(.MUT(MUT)) in_(.p(d),.s(s));
 ot_qkh_packet_pipe #(.W(202)) capture(.clk(clk),.rst_n(rst_n),.d(s),.q(sq));
 qwen_tx_rnen_r1_out #(.MUT(MUT)) out(.s(sq),.f(q));
endmodule
