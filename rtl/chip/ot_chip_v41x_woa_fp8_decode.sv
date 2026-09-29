`timescale 1ns/1ps
// Candidate local wo_a decoder: exact FP8 E4M3 * UE8M0 -> BF16.
// One registered result per cycle. Invalid FP8 NaN / UE8M0 255 is refused.
// Not yet connected to ME or adopted in the physical resource model.
module ot_chip_v41x_woa_fp8_decode (
 input wire clk, rst_n, in_v,
 input wire [7:0] code, scale,
 output reg out_v, fault,
 output reg [15:0] value
);
 integer sig, p, lead, be, shift, q, remainder, half;
 reg [15:0] decoded;
 reg invalid;
 always @* begin
   decoded=16'b0;invalid=0;sig=0;p=0;lead=0;be=0;shift=0;q=0;remainder=0;half=0;
   if ((code[6:3]==15 && code[2:0]==7) || scale==255) invalid=1;
   else begin
     sig=code[6:3]==0 ? {29'b0,code[2:0]} : 8+{29'b0,code[2:0]};
     p=(code[6:3]==0 ? -9 : {28'b0,code[6:3]}-10)+{24'b0,scale}-127;
     decoded={code[7],15'b0};
     if(sig!=0) begin
       if(sig>=8)lead=3;else if(sig>=4)lead=2;else if(sig>=2)lead=1;
       be=p+lead+127;
       if(be>=255) decoded={code[7],8'hff,7'b0};
       else if(be>0) decoded={code[7],8'(be),7'((sig<<(7-lead))-128)};
       else begin
         shift=p+133;
         if(shift>=0)q=sig<<shift;
         else if(shift>=-8) begin
           q=sig>>(-shift);remainder=sig- (q<<(-shift));half=1<<(-shift-1);
           if(remainder>half || (remainder==half && (q&1)))q=q+1;
         end
         decoded={code[7],15'(q)};
       end
     end
   end
 end
 always @(posedge clk) begin
   if(!rst_n)begin out_v<=0;value<=0;fault<=0;end
   else begin out_v<=in_v;fault<=in_v&&invalid;if(in_v)value<=decoded;end
 end
endmodule
