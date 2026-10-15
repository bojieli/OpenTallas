`timescale 1ns/1ps
// Opt-in source component. Every input is sampled on a compiler slot; no
// ready/credits. 18 register stages (sampled issue edge -> output edge +17).
// Ranks are ABSOLUTE 0,1,2,3. Pairwise rounding matches the acceptedpop golden.
module s81_static_hc_reduce #(parameter integer MUT=0)(
 input wire clk,rst_n,slot,
 input wire [3:0] rank_valid,
 input wire [2047:0] rank_data,
 input wire [31:0] tag,
 input wire [15:0] seq,
 input wire last,
 output reg word_valid,
 output reg [511:0] word_data,
 output wire [31:0] word_tag,
 output wire [15:0] word_seq,
 output wire word_last,
 output reg word_error,
 output reg fault
);
 reg qv; reg [2047:0] qd;
 reg [48:0] identity[0:17];
 integer k;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin qv<=0;fault<=0; end
  else begin
   qv<=slot && (&rank_valid);
   if ((slot && rank_valid!=4'hf) || (!slot && (|rank_valid))) fault<=1;
   if(word_valid && word_error) fault<=1;
  end
 end
 always @(posedge clk) begin
  qd<=rank_data;
  identity[0]<={tag,seq,last};
  for(k=1;k<18;k=k+1) identity[k]<=identity[k-1];
 end
 assign {word_tag,word_seq,word_last}=identity[17];
 wire [511:0] ab,cd,y;
 wire [15:0] av,cv,yv;
 wire [31:0] ae,ce,ye;
 reg [7:0] inner_error;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) inner_error<=0;
  else inner_error<={inner_error[6:0],av[0] && ((|ae)||(|ce))};
 genvar g;
 generate for(g=0;g<16;g=g+1) begin:L
  // MUT=1 changes the real arithmetic tree to (p0+p2)+(p1+p3).
  ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) a01(
   .clk(clk),.rst_n(rst_n),.valid_in(qv),.a(qd[g*32+:32]),
   .b(qd[((MUT==1)?2:1)*512+g*32+:32]),.y(ab[g*32+:32]),.err(ae[g*2+:2]),.valid_out(av[g]));
  ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) a23(
   .clk(clk),.rst_n(rst_n),.valid_in(qv),.a(qd[((MUT==1)?1:2)*512+g*32+:32]),
   .b(qd[1536+g*32+:32]),.y(cd[g*32+:32]),.err(ce[g*2+:2]),.valid_out(cv[g]));
  ot_s81ph_fp32_add_rne_preexp #(.SPLIT(7),.KS(1)) aout(
   .clk(clk),.rst_n(rst_n),.valid_in(av[g]),.a(ab[g*32+:32]),.b(cd[g*32+:32]),
   .y(y[g*32+:32]),.err(ye[g*2+:2]),.valid_out(yv[g]));
 end endgenerate
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin word_valid<=0;word_error<=0; end
  else begin word_valid<=yv[0]; word_error<=yv[0] && ((|ye)||inner_error[7]); end
 end
 always @(posedge clk) word_data<=y;
endmodule
