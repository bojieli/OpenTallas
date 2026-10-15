`timescale 1ns/1ps
// Fixed compiler calendar: start at E0, payload slots E1..E16 inclusive.
// No feedback can change any operand slot or result pulse. Every data/diagnostic
// input has an unconditional capture flop; every output is driven by a flop.
module ot_s81_markov_ctl_static (
 input wire clk,rst_n,start,input wire[31:0] head_logit,
 input wire[255:0] weight_bf16,embed_bf16,
 input wire[15:0] pf,bad_chunk,input wire[4:0] bad_tree,
 input wire jv,input wire[31:0] jd,input wire[1:0] je,
 output reg out_valid,output reg[31:0] out_bits,output reg fault,
 output reg mul_fire,output reg[255:0] mul_weight,mul_embed,
 output reg[31:0] head,output wire pv_last
);
 reg[1:0] rs_q;wire rl_n=rs_q[1];
 always @(posedge clk or negedge rst_n)
  if(!rst_n) rs_q<=0;else rs_q<={rs_q[0],1'b1};
 reg[15:0] slots;reg[176:0] done_slots;reg start_q;reg[31:0] h_q,held_head;
 reg[15:0] pf_q,bc_q;reg[4:0] bt_q;reg[1:0] je_q;reg jv_q;
 reg sticky,done_q;reg[5:0] pv;
 wire operand_slot=|slots;
 always @(posedge clk) begin
  h_q<=head_logit;
  pf_q<=pf;bc_q<=bad_chunk;bt_q<=bad_tree;je_q<=je;
  mul_weight<=weight_bf16;mul_embed<=embed_bf16;
  if(start_q) held_head<=h_q;
  head<=held_head;
  out_bits<=jd;
 end
 always @(posedge clk or negedge rl_n) begin
  if(!rl_n) begin slots<=0;done_slots<=0;start_q<=0;mul_fire<=0;pv<=0;jv_q<=0;done_q<=0;out_valid<=0;sticky<=0;fault<=0;end
  else begin
   slots<={slots[14:0],start};done_slots<={done_slots[175:0],start};start_q<=start;
   `ifdef OT_S81_MARKOV_STATIC_DROP_BEAT
   mul_fire<=operand_slot && !slots[7];
`else
   mul_fire<=operand_slot;
`endif
   pv<={pv[4:0],mul_fire};
   jv_q<=jv;done_q<=done_slots[176];out_valid<=done_slots[176];
   if((|pf_q) || |bc_q || |bt_q || (jv_q && je_q!=0) || (start_q && |done_slots[176:1]) || (jv_q != done_q)) sticky<=1;
   fault<=sticky;
  end
 end
 assign pv_last=pv[5];
endmodule

module ot_s81_markov_k256_static #(parameter integer MUTANT_FOLD=0) (
 input wire clk,rst_n,input wire[37:0] clk_leaf,input wire start,
 input wire[31:0] head_logit,
 input wire[255:0] weight_bf16,embed_bf16,output wire out_valid,
 output wire[31:0] out_bits,output wire fault
);
 wire mul_fire,pv_last;wire[255:0] mul_weight,mul_embed;wire[31:0] head;
 wire[15:0] pf,bad_chunk;wire[4:0] bad_tree;wire jv;wire[31:0] jd;wire[1:0] je;
 ot_s81_markov_ctl_static u_ctl (.clk(clk),.rst_n(rst_n),.start(start),.head_logit(head_logit),
  .weight_bf16(weight_bf16),.embed_bf16(embed_bf16),.pf(pf),.bad_chunk(bad_chunk),.bad_tree(bad_tree),
  .jv(jv),.jd(jd),.je(je),.out_valid(out_valid),.out_bits(out_bits),.fault(fault),
  .mul_fire(mul_fire),.mul_weight(mul_weight),.mul_embed(mul_embed),.head(head),.pv_last(pv_last));
 wire[31:0] p[0:15];
 generate for(genvar lane=0;lane<16;lane=lane+1) begin:g_mul
  ot_s81_markov_mul_native u_mul (.clk(clk_leaf[lane]),.rst_n(rst_n),.v(mul_fire),
   .a(mul_weight[16*lane +: 16]),.b(mul_embed[16*lane +: 16]),.y(p[lane]),.fault(pf[lane]));
 end endgenerate
 wire[31:0] cs[0:1][0:8];wire cv[0:1][0:8];
 assign cv[0][0]=pv_last;
 ot_s81_markov_chunk0_native u_c0s0 (.clk(clk_leaf[16]),.rst_n(rst_n),.vin(cv[0][0]),
  .p(p[0]),.y(cs[0][1]),.vout(cv[0][1]),.bad(bad_chunk[0]));
 ot_s81_markov_chunk1_native u_c0s1 (.clk(clk_leaf[17]),.rst_n(rst_n),.vin(cv[0][1]),
  .sum(cs[0][1]),.p(p[1]),.y(cs[0][2]),.vout(cv[0][2]),.bad(bad_chunk[1]));
 ot_s81_markov_chunk2_native u_c0s2 (.clk(clk_leaf[18]),.rst_n(rst_n),.vin(cv[0][2]),
  .sum(cs[0][2]),.p(p[2]),.y(cs[0][3]),.vout(cv[0][3]),.bad(bad_chunk[2]));
 ot_s81_markov_chunk3_native u_c0s3 (.clk(clk_leaf[19]),.rst_n(rst_n),.vin(cv[0][3]),
  .sum(cs[0][3]),.p(p[3]),.y(cs[0][4]),.vout(cv[0][4]),.bad(bad_chunk[3]));
 ot_s81_markov_chunk4_native u_c0s4 (.clk(clk_leaf[20]),.rst_n(rst_n),.vin(cv[0][4]),
  .sum(cs[0][4]),.p(p[4]),.y(cs[0][5]),.vout(cv[0][5]),.bad(bad_chunk[4]));
 ot_s81_markov_chunk5_native u_c0s5 (.clk(clk_leaf[21]),.rst_n(rst_n),.vin(cv[0][5]),
  .sum(cs[0][5]),.p(p[5]),.y(cs[0][6]),.vout(cv[0][6]),.bad(bad_chunk[5]));
 ot_s81_markov_chunk6_native u_c0s6 (.clk(clk_leaf[22]),.rst_n(rst_n),.vin(cv[0][6]),
  .sum(cs[0][6]),.p(p[6]),.y(cs[0][7]),.vout(cv[0][7]),.bad(bad_chunk[6]));
 ot_s81_markov_chunk7_native u_c0s7 (.clk(clk_leaf[23]),.rst_n(rst_n),.vin(cv[0][7]),
  .sum(cs[0][7]),.p(p[7]),.y(cs[0][8]),.vout(cv[0][8]),.bad(bad_chunk[7]));
 assign cv[1][0]=pv_last;
 ot_s81_markov_chunk0_native u_c1s0 (.clk(clk_leaf[24]),.rst_n(rst_n),.vin(cv[1][0]),
  .p(p[8]),.y(cs[1][1]),.vout(cv[1][1]),.bad(bad_chunk[8]));
 ot_s81_markov_chunk1_native u_c1s1 (.clk(clk_leaf[25]),.rst_n(rst_n),.vin(cv[1][1]),
  .sum(cs[1][1]),.p(p[9]),.y(cs[1][2]),.vout(cv[1][2]),.bad(bad_chunk[9]));
 ot_s81_markov_chunk2_native u_c1s2 (.clk(clk_leaf[26]),.rst_n(rst_n),.vin(cv[1][2]),
  .sum(cs[1][2]),.p(p[10]),.y(cs[1][3]),.vout(cv[1][3]),.bad(bad_chunk[10]));
 ot_s81_markov_chunk3_native u_c1s3 (.clk(clk_leaf[27]),.rst_n(rst_n),.vin(cv[1][3]),
  .sum(cs[1][3]),.p(p[11]),.y(cs[1][4]),.vout(cv[1][4]),.bad(bad_chunk[11]));
 ot_s81_markov_chunk4_native u_c1s4 (.clk(clk_leaf[28]),.rst_n(rst_n),.vin(cv[1][4]),
  .sum(cs[1][4]),.p(p[12]),.y(cs[1][5]),.vout(cv[1][5]),.bad(bad_chunk[12]));
 ot_s81_markov_chunk5_native u_c1s5 (.clk(clk_leaf[29]),.rst_n(rst_n),.vin(cv[1][5]),
  .sum(cs[1][5]),.p(p[13]),.y(cs[1][6]),.vout(cv[1][6]),.bad(bad_chunk[13]));
 ot_s81_markov_chunk6_native u_c1s6 (.clk(clk_leaf[30]),.rst_n(rst_n),.vin(cv[1][6]),
  .sum(cs[1][6]),.p(p[14]),.y(cs[1][7]),.vout(cv[1][7]),.bad(bad_chunk[14]));
 ot_s81_markov_chunk7_native u_c1s7 (.clk(clk_leaf[31]),.rst_n(rst_n),.vin(cv[1][7]),
  .sum(cs[1][7]),.p(p[15]),.y(cs[1][8]),.vout(cv[1][8]),.bad(bad_chunk[15]));
 wire[4:0] tv;wire[31:0] td[0:4];
 ot_s81_markov_pair_native u_pair (.clk(clk_leaf[32]),.rst_n(rst_n),.vin(cv[0][8]),.a(cs[0][8]),.b(cs[1][8]),
  .y(td[0]),.vout(tv[0]),.bad(bad_tree[0]));
 generate for(genvar k=0;k<4;k=k+1) begin:g_tree
  ot_s81_markov_fold_native u_fold (.clk(clk_leaf[33+k]),.rst_n(rst_n),.vin(tv[k]),.x(td[k]),
   .y(td[k+1]),.vout(tv[k+1]),.bad(bad_tree[k+1]));
 end endgenerate
 ot_s81_markov_join_native #(.MUTANT_FOLD(MUTANT_FOLD)) u_join (.clk(clk_leaf[37]),.rst_n(rst_n),.vin(tv[4]),
  .head(head),.x(td[4]),.y(jd),.vout(jv),.err(je));
endmodule
