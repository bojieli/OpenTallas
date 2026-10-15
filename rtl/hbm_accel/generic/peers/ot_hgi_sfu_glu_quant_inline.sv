`timescale 1ns/1ps
// BOUNDED ONE-CONTEXT component. Seven NC8 contexts remain OPEN: zero fields
// here are a col0 mapping experiment, not eight real activation vectors.
// Exact GLU BF16 output feeds the unchanged AQ. Fixed compiler quant launches
// occur even on missing producer output (fault, no waiting/replay/ready).
module ot_hgi_sfu_glu_quant_inline #(parameter integer MUT=0)(
 input wire [2:0] clk_math,input wire clk_control,
 input wire clk_aq_core,clk_aq_delay,clk_aq_encode,
 input wire [3:0] clk_code,input wire rst_n,
 input wire glu_issue,input wire [31:0] gate,up,route,input wire [31:0] word_id,
 input wire quant_launch,input wire [6:0] quant_block,
 input wire emit_v,input wire [4:0] emit_addr,input wire [3:0] emit_group,
 output reg xw_en,output reg [6:0] xw_addr,xw_grp,output reg [2047:0] xw_data,
 output wire glu_valid,output wire [31:0] glu_data,glu_tag,
 output wire aq_valid,output wire [255:0] aq_codes,output wire signed [9:0] aq_exp,
 output wire [511:0] aq_dequant,
 output wire fault
);
 wire glu_fault;
 ot_hgi_sfu_fused_glu_split glu(.clk(clk_math),.rst_n(rst_n),.v(glu_issue),
  .gate(gate),.up(up),.route(route),.tag(word_id),.vo(glu_valid),.y(glu_data),.out_tag(glu_tag),.fault(glu_fault));
 reg [1023:0] collector,aq_x;
 reg aq_v;reg [6:0] aq_block;
 reg [17:0] qv;reg [6:0] qt[0:17];
 reg own_fault;wire aq_fault;
 reg [31:0] seen;reg [31:0] expected_word;
 wire [31:0] actual_last=glu_data^(MUT==2?32'h80000000:32'd0);
 ot_hbm_sm_aq_static aq(.clk_core(clk_aq_core),.clk_delay(clk_aq_delay),.clk_encode(clk_aq_encode),
  .rst_n(rst_n),.v(aq_v),.x(aq_x),.vo(aq_valid),.q(aq_codes),.e(aq_exp),.y(aq_dequant),.fault(aq_fault));
 always @(posedge clk_control)begin
  if(glu_valid)collector[glu_tag[4:0]*32+:32]<=glu_data;
  // The compiler launches only when the 32nd actual GLU result is due.
  aq_x<={actual_last,collector[991:0]};aq_block<=quant_block;
  qt[0]<=aq_block;for(integer i=1;i<18;i=i+1)qt[i]<=qt[i-1];
 end
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin aq_v<=0;qv<=0;own_fault<=0;seen<=0;expected_word<=0;end
  else begin
   aq_v<=quant_launch;qv<={qv[16:0],aq_v};
   if(glu_valid)begin
    seen[glu_tag[4:0]]<=1;expected_word<=expected_word+1;
    if(glu_data[15:0]!=0||glu_tag!=expected_word)own_fault<=1;
   end
   if(quant_launch)begin seen<=0;if(seen[30:0]!=31'h7fffffff)own_fault<=1;end
   if(quant_launch&&(!glu_valid||glu_tag[4:0]!=31||glu_tag[11:5]!=quant_block||quant_block>=96))own_fault<=1;
   if(aq_valid!=qv[17]||aq_fault)own_fault<=1;
   if(emit_v&&(emit_addr>=24||emit_group>=13))own_fault<=1;
  end
 end
 wire [1023:0] macro_q;reg [1023:0] code_capture;
 wire [39:0] exp_q;reg [39:0] exp_capture;
 wire [3:0] code_fault;
 wire [4:0] packet_row={qt[17][6:5],qt[17][2:0]};
 genvar j,h;
 generate for(j=0;j<4;j=j+1)begin:packet_bank
  reg [9:0] exponents[0:31];reg [31:0] loaded;
  reg [9:0] exponent_read;reg bad;
  wire wr=aq_valid&&qt[17][4:3]==j;
  wire rd=emit_v&&emit_group==0;
  wire [255:0] actual_codes=aq_codes^((MUT==1&&qt[17]==0)?256'd1:256'd0);
  for(h=0;h<2;h=h+1)begin:half
   ot_sram_1r1w_32x128_m1 ram(.clk(clk_code[j]),.r_ce_in(rd),.r_addr_in(emit_addr),.rd_out(macro_q[j*256+h*128+:128]),
    .w_ce_in(wr),.w_addr_in(packet_row),.wd_in(actual_codes[h*128+:128]),.w_mask_in({128{1'b1}}));
  end
  always @(posedge clk_code[j])begin
   if(wr)exponents[packet_row]<=aq_exp;
   if(rd)exponent_read<=exponents[emit_addr];
  end
  always @(posedge clk_code[j] or negedge rst_n)begin
   if(!rst_n)begin loaded<=0;bad<=0;end
   else begin
    if(wr)loaded[packet_row]<=1;
    if(rd&&!loaded[emit_addr])bad<=1;
   end
  end
  assign exp_q[j*10+:10]=exponent_read;assign code_fault[j]=bad;
 end endgenerate
 reg v0,v1;reg [4:0] addr0,addr1;reg [3:0] group0,group1;
 wire [1063:0] fragment;
 generate for(j=0;j<4;j=j+1)begin:pack
  assign fragment[j*266+:266]={exp_capture[j*10+:10],code_capture[j*256+:256]};
 end endgenerate
 always @(posedge clk_control)begin
  code_capture<=macro_q;exp_capture<=exp_q;
  addr0<=emit_addr;addr1<=addr0;group0<=emit_group;group1<=group0;
  xw_addr<={2'd0,addr1};xw_grp<={3'd0,group1};
  xw_data<=group1==0?{984'd0,fragment}:2048'd0;
 end
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin v0<=0;v1<=0;xw_en<=0;end
  else begin v0<=emit_v;v1<=v0;xw_en<=v1;end
 end
 assign fault=own_fault|glu_fault|(|code_fault);
endmodule
