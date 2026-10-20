`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0; reg [1:0] stack=0; reg [799:0] hv=0; wire [783:0] h=hv[783:0];
 wire [779:0] a,b; reg [779:0] ad; always @(posedge ck) ad<=a;
 wire [776:0] rr,ss; reg [776:0] rr_d; always @(posedge ck) rr_d<=rr;
 qkd_kv_stack_relays_l #(.HW(0),.FW(334),.GW(144),.RW(299)) rr0(.ck(ck),.dn(h[333:0]),.g_i(h[143:0]),.r_i(h[298:0]),.fan(rr[333:0]),.g(rr[477:334]),.r(rr[776:478]));
 qkd_kv_stack_relays_s32 #(.HW(0),.FW(334),.GW(144),.RW(299)) rr1(.ck(ck),.dn(h[333:0]),.g_i(h[143:0]),.r_i(h[298:0]),.fan(ss[333:0]),.g(ss[477:334]),.r(ss[776:478]));
 qkd_kv_es_fan_stack_bl refdut(.ck(ck),.rst_n(rst_n),.stack(stack),.h(h),.d(a));
 qkd_kv_es_fan_stack_safe32 #(.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.stack(stack),.h(h),.d(b));
 integer i,j,checked=0,errors=0;
 initial begin
  for(i=0;i<2100;i=i+1) begin
   @(negedge ck);
   rst_n=(i>=5 && !(i>=1000 && i<1005));
   stack=i%4;
   for(j=0;j<25;j=j+1) hv[j*32+:32]=$urandom;
   @(posedge ck); #1;
   if(i>8) begin
    checked=checked+1;
    if(ad!==b || rr_d!==ss) begin errors=errors+1; if(errors<4) $display("MISMATCH edge=%0d",i); end
   end
  end
  if(errors==0) $display("SAFE32 PASS checked=%0d mut=%0d",checked,MUT);
  else begin $display("SAFE32 FAIL errors=%0d checked=%0d mut=%0d",errors,checked,MUT); $fatal; end
  $finish;
 end
endmodule
