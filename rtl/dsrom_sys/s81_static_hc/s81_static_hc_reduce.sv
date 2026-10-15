`timescale 1ns/1ps
// Physical source split: one scalar tree per independent lane clock pin, and
// one metadata/control clock pin. Pins/phase/CTS/slot remain unqualified.
module s81_static_hc_reduce_clocked #(parameter integer MUT=0)(
 input wire [15:0] clk_lane, input wire clk_control,rst_n,slot,
 input wire [3:0] rank_valid,
 input wire [2047:0] rank_data,
 input wire [31:0] tag,
 input wire [15:0] seq,
 input wire last,
 output wire word_valid,
 output wire [511:0] word_data,
 output wire [31:0] word_tag,
 output wire [15:0] word_seq,
 output wire word_last,
 output wire word_error,
 output reg fault

);
 reg [48:0] identity[0:17];integer k;
 wire [15:0] lv,le;
 always @(posedge clk_control)begin
  identity[0]<={tag,seq,last};
  for(k=1;k<18;k=k+1)identity[k]<=identity[k-1];
 end
 assign {word_tag,word_seq,word_last}=identity[17];
 assign word_valid=&lv;
 assign word_error=word_valid && (|le);
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)fault<=0;
  else if((slot&&rank_valid!=15)||(!slot&&(|rank_valid))||
          (word_valid&&word_error)||((|lv)&&!( &lv)))fault<=1;
 end
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:L
  s81_static_hc_scalar_reduce #(.MUT(MUT)) leaf(.clk(clk_lane[g]),.rst_n(rst_n),
   .slot(slot && (&rank_valid)),
   .rank_data({rank_data[1536+g*32+:32],rank_data[1024+g*32+:32],rank_data[512+g*32+:32],rank_data[g*32+:32]}),
   .word_data(word_data[g*32+:32]),.word_valid(lv[g]),.word_error(le[g]));
 end endgenerate
endmodule

// Actual scalar arithmetic leaf: 3 pipelined adders, local input/output flops.
module s81_static_hc_scalar_reduce #(parameter integer MUT=0)(
 input wire clk,rst_n,slot,input wire[127:0]rank_data,
 output reg [31:0]word_data,output reg word_valid,word_error
);
 reg qv;reg[127:0]qd;
 always @(posedge clk or negedge rst_n)if(!rst_n)qv<=0;else qv<=slot;
 always @(posedge clk)qd<=rank_data;
 wire[31:0]ab,cd,y;wire av,cv,yv;wire[1:0]ae,ce,ye;
 reg[7:0]inner_error;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)inner_error<=0;else inner_error<={inner_error[6:0],av&&((|ae)||(|ce))};
 ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) a01(
  .clk(clk),.rst_n(rst_n),.valid_in(qv),.a(qd[31:0]),.b(qd[((MUT==1)?2:1)*32+:32]),.y(ab),.err(ae),.valid_out(av));
 ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) a23(
  .clk(clk),.rst_n(rst_n),.valid_in(qv),.a(qd[((MUT==1)?1:2)*32+:32]),.b(qd[127:96]),.y(cd),.err(ce),.valid_out(cv));
 ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) aout(
  .clk(clk),.rst_n(rst_n),.valid_in(av),.a(ab),.b(cd),.y(y),.err(ye),.valid_out(yv));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin word_valid<=0;word_error<=0;end
  else begin word_valid<=yv;word_error<=yv&&((|ye)||inner_error[7]);end
 always @(posedge clk)word_data<=y;
endmodule

// Functional compatibility wrapper. Physical parents use *_clocked, supplying
// each lane's real clock at its own pin, with explicit common-epoch/phi-R proof.
module s81_static_hc_reduce #(parameter integer MUT=0)(
 input wire clk,rst_n,slot,
 input wire [3:0] rank_valid,
 input wire [2047:0] rank_data,
 input wire [31:0] tag,
 input wire [15:0] seq,
 input wire last,
 output wire word_valid,
 output wire [511:0] word_data,
 output wire [31:0] word_tag,
 output wire [15:0] word_seq,
 output wire word_last,
 output wire word_error,
 output wire fault

);
 s81_static_hc_reduce_clocked #(.MUT(MUT)) core(.clk_lane({16{clk}}),.clk_control(clk),
  .rst_n(rst_n),.slot(slot),.rank_valid(rank_valid),.rank_data(rank_data),.tag(tag),.seq(seq),.last(last),
  .word_valid(word_valid),.word_data(word_data),.word_tag(word_tag),.word_seq(word_seq),.word_last(word_last),
  .word_error(word_error),.fault(fault));
endmodule
