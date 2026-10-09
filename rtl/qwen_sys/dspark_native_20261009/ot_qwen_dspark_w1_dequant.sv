`timescale 1ns/1ps
// Exact INT8 * BF16 row scale -> FP32. Product has <=15 significant bits,
// so no finite product loses bits at the golden FP32 RNE point. Includes
// BF16 subnormals and canonical +0. Overflow/nonfinite scale quarantines.
module ot_qwen_dspark_w1_dequant #(parameter integer ENABLE=0,MUT_SIGN=0)(
 input wire clk,rst_n,input wire i_v,output wire i_r,
 input wire [511:0] i_codes,input wire [15:0] i_scale,
 input wire [63:0] i_id,input wire [1:0] i_quarter,input wire i_last,
 output reg o_v,input wire o_r,output reg [2047:0] o_values,
 output reg [63:0] o_id,output reg [1:0] o_quarter,output reg o_last,
 output reg fault
);
 reg busy,v1;reg [14:0] product[0:63];reg [63:0] sign;
 reg [7:0] exp1;reg bad1;reg [63:0] id1;reg [1:0] quarter1;reg last1;
 wire fire=i_v&&i_r;
 assign i_r=(ENABLE!=0)&&!fault&&!busy;
 integer lane,k;reg [7:0] mag,mant;integer leading,exponent;reg [31:0] fraction;
 reg [2047:0] converted;reg conversion_bad;
 always @* begin
  converted=0;conversion_bad=bad1;
  for(integer l=0;l<64;l=l+1)begin
   leading=0;
   for(k=0;k<15;k=k+1)if(product[l][k])leading=k;
   exponent=((exp1==0)?1:exp1)-7+leading;
   fraction=32'(product[l])<<(23-leading);
   if(product[l]==0)converted[l*32+:32]=0;
   else if(exponent>=255)begin converted[l*32+:32]={sign[l],8'hff,23'b0};conversion_bad=1;end
   else if(exponent<=0)converted[l*32+:32]={sign[l],8'b0,23'(32'(product[l])<<16)};
   else converted[l*32+:32]={sign[l],8'(exponent),fraction[22:0]};
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;v1<=0;o_v<=0;fault<=0;end
  else begin
   v1<=fire;
   if(fire)busy<=1;
   if(v1)begin
    if(conversion_bad)fault<=1;
    else begin o_v<=1;o_values<=converted;o_id<=id1;o_quarter<=quarter1;o_last<=last1;end
   end
   if(o_v&&o_r)begin o_v<=0;busy<=0;end
  end
 end
 always @(posedge clk)if(fire)begin
  exp1<=i_scale[14:7];bad1<=i_scale[14:7]==8'hff;id1<=i_id;quarter1<=i_quarter;last1<=i_last;
  mant={i_scale[14:7]!=0,i_scale[6:0]};
  for(lane=0;lane<64;lane=lane+1)begin
   mag=i_codes[lane*8+7]?(~i_codes[lane*8+:8]+8'b1):i_codes[lane*8+:8];
   product[lane]<=mag*mant;
   sign[lane]<=(MUT_SIGN!=0)?i_scale[15]:(i_codes[lane*8+7]^i_scale[15]);
  end
 end
endmodule
