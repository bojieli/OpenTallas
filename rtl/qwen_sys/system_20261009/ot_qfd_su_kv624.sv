`timescale 1ns/1ps
// Q3 full64-lane exact descriptor. This only packs values that the SU already
// rounded onto E4M3; f32_e4m3 is copied byte-for-byte from the pinned service.
// Two bases encode fixed K stride16 or V stride1. Every active address must
// reconstruct exactly; otherwise the packet is suppressed and fault is sticky.
module ot_qfd_su_kv624 #(parameter integer AW=24, MUT_ADDR=0)(
 input wire clk,rst_n,input wire [63:0] i_mask,
 input wire [64*AW-1:0] i_addr,input wire [2047:0] i_data,
 output reg [63:0] o_mask,output reg [AW-1:0] o_a0,o_a1,
 output reg [511:0] o_data,output reg fault
);
    function automatic [8:0] f32_e4m3(input [31:0] b);   // {bad, code}
        reg [7:0] e; reg [22:0] m;
        begin
            e = b[30:23]; m = b[22:0];
            if (e == 0 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd0};
            else if (e >= 8'd121 && e <= 8'd135 && m[19:0] == 0) f32_e4m3 = {1'b0, b[31], e[3:0] - 4'd8, m[22:20]};
            else if (e == 8'd120 && m[20:0] == 0) f32_e4m3 = {1'b0, b[31], 4'd0, 1'b1, m[22:21]};
            else if (e == 8'd119 && m[21:0] == 0) f32_e4m3 = {1'b0, b[31], 5'd0, 1'b1, m[22]};
            else if (e == 8'd118 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd1};
            else f32_e4m3 = {1'b1, 8'd0};
        end
    endfunction
 reg [63:0] in_mask;reg [1535:0] in_addr;reg [2047:0] in_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin in_mask<=0;in_addr<=0;in_data<=0;end
  else begin in_mask<=i_mask;in_addr<=i_addr;in_data<=i_data;end
 end
 localparam integer VBASE=131072*16;
 reg [AW-1:0] bases[0:1];reg found[0:1];
 reg [511:0] codes;reg bad;integer i,g,stride;reg [8:0] code;
 reg [AW:0] expected;reg [AW-1:0] addr;
 always @(*)begin
  bases[0]=0;bases[1]=0;found[0]=0;found[1]=0;codes=0;bad=0;code=0;addr=0;expected=0;g=0;stride=0;
  for(i=0;i<64;i=i+1)begin
   g=i/32;addr=in_addr[i*AW+:AW];stride=(addr<VBASE)?16:1;
   if(in_mask[i]&&!found[g])begin bases[g]=addr-AW'((i%32)*stride);found[g]=1;end
  end
  for(i=0;i<64;i=i+1)begin
   g=i/32;addr=in_addr[i*AW+:AW];stride=(bases[g]<VBASE)?16:1;
   expected={1'b0,bases[g]}+(AW+1)'((i%32)*stride+(MUT_ADDR!=0?1:0));
   code=f32_e4m3(in_data[i*32+:32]);codes[i*8+:8]=code[7:0];
   if(in_mask[i]&&(code[8]||expected[AW]||expected[AW-1:0]!=addr||addr>=2*VBASE))bad=1;
  end
 end
 reg [63:0] mask_q;reg [AW-1:0] a0_q,a1_q;reg [511:0] data_q;reg bad_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin mask_q<=0;a0_q<=0;a1_q<=0;data_q<=0;bad_q<=0;o_mask<=0;o_a0<=0;o_a1<=0;o_data<=0;fault<=0;end
  else begin
   mask_q<=in_mask;a0_q<=bases[0];a1_q<=bases[1];data_q<=codes;bad_q<=bad;
   o_mask<=(bad_q||fault)?64'd0:mask_q;o_a0<=a0_q;o_a1<=a1_q;o_data<=data_q;
   fault<=fault||bad_q;
  end
 end
endmodule
