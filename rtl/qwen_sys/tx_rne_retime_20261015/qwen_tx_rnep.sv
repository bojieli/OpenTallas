// Native-boundary successor #2 of qwen_tx_rne_r0/r1 (Q-COMPUTE-ELEM r14, 2026-10-15).
// Measured on the CLOSED rnen pair (jobs qwen_tx_rnen_r{0,1}-n1-8ef69bd8d, audit_boundary_lib.py on the record views):
//   rnen_r0 native PASS (TT launch 197.3 / capture 125.0 ps), rnen_r1 FAIL TT capture 228.2 ps (> 190) on d[*]:
//   the 16-bit "+inc" carry chain sits before the R1 capture flop.
// Structural fix (same two existing TX edges, zero compiler edges): R0, after its pin flop and IN PARALLEL with the
// existing low16 carry tree, forms the per-group prefix AND pre_i = &xu[i-1:0] (i = 1..15, 60 bits; a log-depth tree
// no deeper than the carry tree).  R1's input side then needs one AND + one XOR per bit (r_i = xu_i ^ (inc_g & pre_i))
// instead of an incrementer; mask after the R1 flop as before.  Cost: +60 R0->R1 wires/pins, no added FF on R0,
// +0 FF on R1 (still captures 202 bits).
module qwen_tx_rnep_r0_out #(parameter integer MUT=0)(input wire [266:0] raw, output wire [265:0] p);
 wire round=raw[266]; wire [3:0] gm=raw[265:262]; wire [5:0] ctrl=raw[261:256];
 wire [127:0] wupper=raw[255:128], x=raw[127:0];
 wire [63:0] xu; wire [3:0] inc; wire [59:0] pre;
 genvar g,i;
 generate for(g=0;g<4;g=g+1)begin:gx
  wire [31:0] w=x[32*g+:32];
  wire carry=(MUT==1)?(w[14] & ((|w[13:0]) | w[16])):(MUT==2)?(w[15] & (|w[14:0])):(w[15] & ((|w[14:0]) | w[16]));
  assign inc[g]=round & carry;
  assign xu[16*g+:16]=w[31:16];
  for(i=1;i<16;i=i+1)begin:gp
   // pre[15g+i-1] = AND of upper-word bits [i-1:0]
   if(MUT==7 && i==9) begin:gm7 assign pre[15*g+i-1]=&w[16+:(i-1)]; end
   else begin:gok assign pre[15*g+i-1]=&w[16+:i]; end
  end
 end endgenerate
 assign p={pre,gm,inc,ctrl,wupper,xu};
endmodule
module qwen_tx_rnep_r1_in #(parameter integer MUT=0)(input wire [265:0] p, output wire [201:0] s);
 wire [59:0] pre=p[265:206];
 wire [3:0] gm=p[205:202], inc=p[201:198];
 wire [63:0] r;
 genvar g,i;
 generate for(g=0;g<4;g=g+1)begin:gx
  localparam integer G=(MUT==4)?(3-g):g;
  assign r[16*g]=p[16*G]^inc[g];
  for(i=1;i<16;i=i+1)begin:gb
   assign r[16*g+i]=p[16*G+i]^(inc[g]&pre[15*G+i-1]);
  end
 end endgenerate
 assign s={gm,p[197:64],r};
endmodule
module qwen_tx_rnep_r1_out #(parameter integer MUT=0)(input wire [201:0] s, output wire [197:0] f);
 wire [3:0] gm=s[201:198];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:gx
  assign f[16*g+:16]=((MUT==3)||gm[g])?s[16*g+:16]:16'b0;
 end endgenerate
 assign f[197:64]=s[197:64];
endmodule
module qwen_tx_rnep_r0 #(parameter integer MUT=0)(
 input wire clk,rst_n, input wire [127:0] x,wupper, input wire [5:0] ctrl, input wire [3:0] gm, input wire round,
 output wire [265:0] q);
 wire [266:0] raw;
 ot_qkh_packet_pipe #(.W(267),.MUT(MUT==5?1:0)) capture(.clk(clk),.rst_n((MUT==6)?1'b1:rst_n),.d({round,gm,ctrl,wupper,x}),.q(raw));
 qwen_tx_rnep_r0_out #(.MUT(MUT)) out(.raw(raw),.p(q));
endmodule
module qwen_tx_rnep_r1 #(parameter integer MUT=0)(input wire clk,rst_n, input wire [265:0] d, output wire [197:0] q);
 wire [201:0] s,sq;
 qwen_tx_rnep_r1_in #(.MUT(MUT)) in_(.p(d),.s(s));
 ot_qkh_packet_pipe #(.W(202)) capture(.clk(clk),.rst_n(rst_n),.d(s),.q(sq));
 qwen_tx_rnep_r1_out #(.MUT(MUT)) out(.s(sq),.f(q));
endmodule
