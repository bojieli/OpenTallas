`timescale 1ns/1ps
module tb;
 parameter USE_HARD_DELAY8=0;
 parameter USE_MIN_DELAY_CELLS=0;
 reg clk=0,rst_n=0,go=0; always #0.5 clk=~clk;
 reg [16:0] row0=0;
 reg [255:0] xa=0,xb=0;
 wire rv,flt;wire[16:0] rr;wire[31:0] rb;
 ot_dsrom_head_bundle refdut(.clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),.res_v(rv),.res_row(rr),.res_bits(rb),.fault(flt));
 wire [67:0] rows;wire[127:0] bits_,keys;
 genvar q;generate for(q=0;q<4;q=q+1)begin
 assign rows[17*q+:17]=refdut.a_row[q];assign bits_[32*q+:32]=refdut.a_bits[q];assign keys[32*q+:32]=refdut.a_key[q];end endgenerate
 wire gd,rv2,f2;wire[255:0] sa,sb;wire[3:0] bv;wire[31:0] bd,rb2;wire[16:0] rr2,r0b;wire[67:0] r0a;
 ot_dsrom_head_bundle_glue #(.USE_HARD_DELAY8(USE_HARD_DELAY8),.USE_MIN_DELAY_CELLS(USE_MIN_DELAY_CELLS)) dut(.clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),.bo_v(refdut.bo_v),.bo_d(refdut.bo_d),.b_fault(refdut.b_fault),.a_done(refdut.a_done),.a_fault(refdut.a_fault),.a_row_flat(rows),.a_bits_flat(bits_),.a_key_flat(keys),.go_d(gd),.xsa(sa),.xsb(sb),.bv_r(bv),.bd_r(bd),.row0_a(r0a),.row0_b(r0b),.res_v(rv2),.res_row(rr2),.res_bits(rb2),.fault(f2));
 integer i,j,seed=12345,valids=0;
 initial begin
 repeat(3) @(negedge clk);rst_n=1;
 for(i=0;i<1200;i=i+1)begin
 @(negedge clk);
 if(i>64 && {gd,sa,sb,bv,bd,rv2,rr2,rb2,f2} !== {refdut.go_d,refdut.xsa,refdut.xsb,refdut.bv_r,refdut.bd_r,rv,rr,rb,flt}) $fatal(1,"lockstep cycle %0d",i);
 for(j=0;j<4;j=j+1)if(r0a[17*j+:17]!==((row0+17'd32*j)&17'h1ffff))$fatal(1,"row offset");
 if(r0b!==0)$fatal(1,"B row");
 if(rv)valids=valids+1;
 go=(i%91==0);row0=$random(seed);for(j=0;j<8;j=j+1)begin xa[32*j+:32]=$random(seed);xb[32*j+:32]=$random(seed);end
 end
 if(valids<20)$fatal(1,"no result coverage");
 $display("PASS glue lockstep 1200 cycles results=%0d",valids);$finish;
 end
endmodule
// Element ports only: deterministic traffic stub isolates original glue without running numerical head.
module ot_dsrom_head_elem #(parameter LV=8,PAD=0,JOIN=0,ROWS=32,CUT=0,INSTANCE="h")
(input clk,rst_n,go,input[16:0]row0,input[255:0]x,input b_v,input[31:0]b_d,output o_v,output[31:0]o_d,output l_v,output[31:0]l_d,output done,output[16:0]best_row,output[31:0]best_bits,best_key,output fault);
 assign o_v=x[0];assign o_d=x[63:32];assign l_v=0;assign l_d=0;
 assign done=x[1] | (row0[6:5]==2'd0);assign best_row=row0+x[20:4];assign best_bits=x[95:64];
 // Frequent ties exercise lowest-row tie rule.
 assign best_key=x[2]?32'd42:row0;assign fault=x[3]^row0[5];
endmodule
