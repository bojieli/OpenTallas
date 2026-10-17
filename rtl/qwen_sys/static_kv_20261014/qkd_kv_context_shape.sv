`timescale 1ns/1ps
// Context-parametric K/V descriptor geometry. Pure hardware, no image tables.
// ordinal is a count of ACTUAL requested sectors; sector is the physical address.
// T is the number of visible tokens (1..8192), shared with landing/front calendars.
module qkd_kv_context_shape # (parameter integer MUT=0)(
 input wire [13:0] ctx_t,input wire [1:0] stack,input wire [2:0] group,
 input wire vpass,input wire [8:0] ordinal,
 output wire [8:0] count,output wire [7:0] k_count0,
 output wire k_order_b,output wire [9:0] sector,output wire last,invalid
);
 wire signed [15:0] xk=$signed({2'b0,ctx_t})-$signed({7'b0,stack,7'b0})-$signed({13'b0,group});
 wire signed [15:0] xv=$signed({2'b0,ctx_t})-$signed({7'b0,stack,7'b0})-$signed({10'b0,group[2:1],4'b0})-$signed({15'b0,group[0]});
 function automatic [8:0] cnt(input signed [15:0] x,input integer sh);
 reg [8:0] r;reg [9:0] a,b;
 begin
 r=x[8:0];a=({1'b0,r}+10'((1<<sh)-1))>>sh;
 b=r>64?({1'b0,r}-10'd64+10'((1<<sh)-1))>>sh:10'd0;
 cnt=x<=0?9'd0:x>=8192?9'd256:{x[12:9],4'b0}+9'(a>=8?8:a)+9'(b>=8?8:b);
 end endfunction
 wire [9:0] h0=({1'b0,xk[8:0]}+10'd7)>>3;
 assign k_count0=xk<=0?8'd0:xk>=8192?8'd128:{xk[13:9],3'b0}+8'(h0>=8?8:h0);
 assign count=(MUT==1)?9'd256: vpass?cnt(xv,1):cnt(xk,3);
 assign k_order_b=ctx_t[13:9]>8 || (ctx_t[13:9]==8 && {1'b0,ctx_t[8:0]}>{1'b0,stack,7'b0});
 wire [7:0] o=ordinal[7:0];
 wire [9:0] perm={vpass,1'b0,o[3],o[7:4],o[2:0]};
 assign sector=(MUT==2)?{vpass,1'b0,o}:!vpass&&k_order_b?
    (o<k_count0?{2'b0,o}:{2'b0,1'b1,7'(o-k_count0)}):perm;
 assign last=ordinal+9'd1==count;
 assign invalid=ctx_t==0||ctx_t>8192||ordinal>=count;
endmodule
