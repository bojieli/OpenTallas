`timescale 1ns/1ps
// Transport-only vehicle: unchanged arithmetic is replaced by element traffic
// stubs. All 307 input bits and compare-tree latency are checked against the
// original bundle. This does not qualify numerical arithmetic or routed timing.
module tb;
 reg clk=0, rst_n=0, go=0;
 always #0.5 clk=~clk;
 reg [16:0] row0=0;
 reg [255:0] xa=0, xb=0;
 wire rv,r0v,r4v,rf,r0f,r4f;
 wire [16:0] rr,r0r,r4r;
 wire [31:0] rb,r0b,r4b;
 head_bundle_original refdut(.clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),.res_v(rv),.res_row(rr),.res_bits(rb),.fault(rf));
 ot_dsrom_head_bundle #(.A_INPUT_STAGES(0)) d0(.clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),.res_v(r0v),.res_row(r0r),.res_bits(r0b),.fault(r0f));
 ot_dsrom_head_bundle #(.A_INPUT_STAGES(4)) d4(.clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),.res_v(r4v),.res_row(r4r),.res_bits(r4b),.fault(r4f));
 wire [306:0] pin_ref[0:3],pin0[0:3],pin4[0:3];
 reg [306:0] history[0:3][0:3];
 reg [49:0] results[0:3];
 genvar q;
 generate for(q=0;q<4;q=q+1) begin
   assign pin_ref[q]={refdut.g_a[q].u_e.go,refdut.g_a[q].u_e.b_v,refdut.g_a[q].u_e.row0,refdut.g_a[q].u_e.x,refdut.g_a[q].u_e.b_d};
   assign pin0[q]={d0.g_a[q].u_e.go,d0.g_a[q].u_e.b_v,d0.g_a[q].u_e.row0,d0.g_a[q].u_e.x,d0.g_a[q].u_e.b_d};
   assign pin4[q]={d4.g_a[q].u_e.go,d4.g_a[q].u_e.b_v,d4.g_a[q].u_e.row0,d4.g_a[q].u_e.x,d4.g_a[q].u_e.b_d};
 end endgenerate
 integer a,s;
 always @(posedge clk) begin
   for(a=0;a<4;a=a+1) begin
     history[a][0]<=pin_ref[a];
     for(s=1;s<4;s=s+1) history[a][s]<=history[a][s-1];
   end
   results[0]<={rv,rr,rb};
   for(s=1;s<4;s=s+1) results[s]<=results[s-1];
 end
 integer i,j,age=0,seed=53119,checked=0,valids=0;
 initial begin
   repeat(3) @(negedge clk);
   for(i=0;i<1500;i=i+1) begin
     @(negedge clk);
     if(age>100) begin
       for(j=0;j<4;j=j+1) begin
         if(pin0[j]!==pin_ref[j]) $fatal(1,"default changed cycle=%0d A=%0d",i,j);
         if(pin4[j]!==history[j][3]) $fatal(1,"307-bit alignment cycle=%0d A=%0d",i,j);
       end
       if(r0v!==rv || r0f!==rf || (rv && {r0r,r0b}!=={rr,rb})) $fatal(1,"default result changed");
       if(r4v!==results[3][49] || (r4v && {r4r,r4b}!==results[3][48:0])) $fatal(1,"result latency");
       if({d4.go_d,d4.xsb,d4.bo_v,d4.bo_d}!=={refdut.go_d,refdut.xsb,refdut.bo_v,refdut.bo_d}) $fatal(1,"B inputs changed");
       checked=checked+1;
       if(r4v) valids=valids+1;
     end
     rst_n=!(i==550 || i==900);
     if(!rst_n) age=0; else age=age+1;
     go=(i%53==0); row0=$random(seed);
     for(j=0;j<8;j=j+1) begin xa[32*j+:32]=$random(seed); xb[32*j+:32]=$random(seed); end
   end
   if(checked<1000 || valids<10) $fatal(1,"coverage checked=%0d valids=%0d",checked,valids);
   $display("PASS aligned307 stage0/stage4 checked=%0d validresults=%0d resetbursts=2",checked,valids);
   $finish;
 end
endmodule

module ot_dsrom_head_elem #(parameter LV=8,PAD=0,JOIN=0,ROWS=32,CUT=0,INSTANCE="h",IOREG=0,SAFE=0,SPLIT9=0)
(input clk,rst_n,go,input [16:0] row0,input [255:0] x,input b_v,input [31:0] b_d,
 output o_v,output [31:0] o_d,output l_v,output [31:0] l_d,output done,
 output [16:0] best_row,output [31:0] best_bits,best_key,output fault);
 assign o_v=x[0]; assign o_d=x[63:32]; assign l_v=0; assign l_d=0;
 assign done=x[1] | (row0[6:5]==2'd0);
 assign best_row=row0+x[20:4]; assign best_bits=x[95:64] ^ (b_v?b_d:0);
 assign best_key=x[2]?32'd42:row0; assign fault=x[3]^row0[5];
endmodule
