`timescale 1ns/1ps
// Default-off dedicated Markov row successor. K=256 is the released checkpoint,
// not the reduced vehicle's K=32. Independent chunk8 dot followed by add(head,mk).
// A transaction owns its head value and accepts exactly K/16 unskewed BF16 beats.
// Bubbles are legal; output is held through backpressure. No next row starts until
// the result is consumed. This finite interface is intentionally explicit: ROM
// lookup/allocation and parent placement remain separate qualification obligations.
module ot_dsrom_markov_row #(
 parameter integer K=256,
 parameter integer PINREG=0,
 parameter [8:0] CUT=511,
 parameter integer SPLIT9=1,
 parameter integer SK=1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]+SPLIT9,
 parameter integer MUTANT_FOLD=0
)(
 input wire clk,rst_n,
 input wire start,
 output wire start_ready,
 input wire [31:0] head_logit,
 input wire in_valid,
 output wire in_ready,
 input wire [255:0] weight_bf16,embed_bf16,
 output reg out_valid,
 input wire out_ready,
 output reg [31:0] out_bits,
 output reg fault
);
 localparam integer WORDS=K/16;
 localparam integer LV=$clog2(WORDS);
 reg busy;
 reg [$clog2(WORDS+1)-1:0] count;
 reg [31:0] head;
 assign start_ready=!busy && !fault;
 assign in_ready=busy && !out_valid && count<WORDS && !fault;
 wire fire=in_valid && in_ready;
 // Capture only accepted beats. The external count still tracks admission,
 // while this valid moves with its two operand buses into the multiplier.
 // Start/head already capture on accepted start; output retirement stays on
 // the real out_valid/out_ready handshake, with no delayed ready protocol.
 wire mul_fire;
 wire [255:0] mul_weight,mul_embed;
 generate if(PINREG) begin:g_pin
  reg accepted;
  reg [255:0] weight_q,embed_q;
  always @(posedge clk or negedge rst_n)
   if(!rst_n) accepted<=0; else accepted<=fire;
  // PINREG=2 removes fire from the512 payload-enable cones.
  // Invalid captured payload is ignored through the single accepted valid.
  always @(posedge clk) if(PINREG==2 || fire) begin weight_q<=weight_bf16;embed_q<=embed_bf16;end
  assign mul_fire=accepted;
  assign mul_weight=weight_q;
  assign mul_embed=embed_q;
 end else begin:g_direct
  assign mul_fire=fire;
  assign mul_weight=weight_bf16;
  assign mul_embed=embed_bf16;
 end endgenerate
 wire [31:0] p[0:15];
 wire [15:0] pf;
 reg [5:0] pv;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) pv<=0; else pv<={pv[4:0],mul_fire};
 genvar lane,c,s,k;
 generate for(lane=0;lane<16;lane=lane+1) begin:g_mul
  ot_dsrom_bmul3 u_mul(.clk(clk),.rst_n(rst_n),.v(mul_fire),
   .a({mul_weight[16*lane+:16],16'b0}),.b({mul_embed[16*lane+:16],16'b0}),.y(p[lane]),.fault(pf[lane]));
 end endgenerate
 wire [31:0] cs[0:1][0:8];
 wire cv[0:1][0:8];
 wire [1:0] ce[0:1][0:7];
 wire [15:0] bad_chunk;
 generate for(c=0;c<2;c=c+1) begin:g_chunk
  assign cs[c][0]=0;
  assign cv[c][0]=pv[5];
  for(s=0;s<8;s=s+1) begin:g_add
   wire [31:0] pd;
   if(s==0) assign pd=p[c*8+s];
   else begin:g_delay
    reg [31:0] q[0:s*SK-1];
    integer d;
    always @(posedge clk) begin
     q[0]<=p[c*8+s];
     for(d=1;d<s*SK;d=d+1) q[d]<=q[d-1];
    end
    assign pd=q[s*SK-1];
   end
   ot_v41_fadd #(.CUT(CUT),.SPLIT9(SPLIT9)) u_add(.clk(clk),.rst_n(rst_n),
    .valid_in(cv[c][s]),.a(cs[c][s]),.b(pd),.y(cs[c][s+1]),.valid_out(cv[c][s+1]),.err(ce[c][s]));
   assign bad_chunk[c*8+s]=cv[c][s+1] && ce[c][s]!=0;
  end
 end endgenerate
 wire tv[0:LV];
 wire [31:0] td[0:LV];
 wire [1:0] te[0:LV];
 wire [LV:0] bad_tree;
 ot_v41_fadd #(.CUT(CUT),.SPLIT9(SPLIT9)) u_pair(.clk(clk),.rst_n(rst_n),
  .valid_in(cv[0][8]),.a(cs[0][8]),.b(cs[1][8]),.y(td[0]),.valid_out(tv[0]),.err(te[0]));
 assign bad_tree[0]=tv[0] && te[0]!=0;
 generate for(k=0;k<LV;k=k+1) begin:g_tree
  reg have;
  reg [31:0] held;
  always @(posedge clk or negedge rst_n)
   if(!rst_n) have<=0; else if(tv[k]) have<=!have;
  always @(posedge clk) if(tv[k] && !have) held<=td[k];
  ot_v41_fadd #(.CUT(CUT),.SPLIT9(SPLIT9)) u_add(.clk(clk),.rst_n(rst_n),
   .valid_in(tv[k] && have),.a(held),.b(td[k]),.y(td[k+1]),.valid_out(tv[k+1]),.err(te[k+1]));
  assign bad_tree[k+1]=tv[k+1] && te[k+1]!=0;
 end endgenerate
 wire jv;
 wire [31:0] jd;
 wire [1:0] je;
 // Negative control intentionally omits the separate final add.
 ot_v41_fadd #(.CUT(CUT),.SPLIT9(SPLIT9)) u_join(.clk(clk),.rst_n(rst_n),
  .valid_in(tv[LV]),.a(MUTANT_FOLD ? 32'b0 : head),.b(td[LV]),.y(jd),.valid_out(jv),.err(je));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin busy<=0;count<=0;head<=0;out_valid<=0;out_bits<=0;fault<=0;end
  else begin
   if(start && !start_ready) fault<=1;
   if(start && start_ready) begin busy<=1;count<=0;head<=head_logit;end
   if(fire) count<=count+1'b1;
   if((pv[5] && |pf) || |bad_chunk || |bad_tree || (jv && je!=0)) fault<=1;
   if(jv) begin
    if(!busy || count!=WORDS || out_valid || je!=0 || fault) begin fault<=1;out_valid<=0;end
    else begin out_valid<=1;out_bits<=jd;end
   end
   if(fault) out_valid<=0;
   if(out_valid && out_ready) begin out_valid<=0;busy<=0;end
  end
 end
`ifndef SYNTHESIS
 initial if(K<16 || K%16 || (WORDS & (WORDS-1))) $fatal(1,"K must be16 times a power of two");
`endif
endmodule
