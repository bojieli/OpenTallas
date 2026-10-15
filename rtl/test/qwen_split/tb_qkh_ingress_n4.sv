`timescale 1ns/1ps
// All128 real word transports. Arithmetic is outside this declared input boundary.
module tb_qkh_ingress_n4;
 parameter integer HEADS=128;
 reg ck=0;always #0.5 ck=~ck;
 reg [1574:0] a[0:HEADS-1];
 wire [1574:0] b[0:HEADS-1];
 reg [1574:0] expect0[0:HEADS-1],expect1[0:HEADS-1],expect2[0:HEADS-1],expect3[0:HEADS-1];
 wire [1574:0] bad31,bad32,bad33,bad41,bad42,bad43;
 genvar h;
 generate for(h=0;h<HEADS;h=h+1)begin:g_h
   wire [1574:0] abc,gather,t1;
   qkh_head_ingress_abc u0(.ck_a(ck),.ck_b(ck),.ck_c(ck),.ti_a(a[h][1574:16]),.e_a(a[h][15:0]),.ti_b(abc[1574:16]),.e_b(abc[15:0]));
   qkh_head_gather_stage ug(.ck(ck),.ti_a(abc[1574:16]),.e_a(abc[15:0]),.ti_b(gather[1574:16]),.e_b(gather[15:0]));
   qkh_head_tstage u1(.ck(ck),.ti_a(gather[1574:16]),.e_a(gather[15:0]),.ti_b(t1[1574:16]),.e_b(t1[15:0]));
   qkh_head_tstage u2(.ck(ck),.ti_a(t1[1574:16]),.e_a(t1[15:0]),.ti_b(b[h][1574:16]),.e_b(b[h][15:0]));
   always @(posedge ck)begin expect0[h]<=a[h];expect1[h]<=expect0[h];expect2[h]<=expect1[h];expect3[h]<=expect2[h];end
 end endgenerate
 qkh_ingress_mut_chain #(.MUT(31)) m31(ck,a[0],bad31);
 qkh_ingress_mut_chain #(.MUT(32)) m32(ck,a[0],bad32);
 qkh_ingress_mut_chain #(.MUT(33)) m33(ck,a[0],bad33);
 qkh_ingress_mut_chain #(.MUT(41)) m41(ck,a[0],bad41);
 qkh_ingress_mut_chain #(.MUT(42)) m42(ck,a[0],bad42);
 qkh_ingress_mut_chain #(.MUT(43)) m43(ck,a[0],bad43);
 integer i,j,k,negative=0,checks=0;
 reg [1574:0] observed;
 initial begin
  if($value$plusargs("negative=%d",negative))begin end
  for(j=0;j<HEADS;j=j+1)a[j]=0;
  for(i=0;i<1600;i=i+1)begin
   @(negedge ck);
   if(i>4)for(j=0;j<HEADS;j=j+1)begin
    observed=b[j];
    if(j==0)case(negative)31:observed=bad31;32:observed=bad32;33:observed=bad33;41:observed=bad41;42:observed=bad42;43:observed=bad43;endcase
    checks=checks+1;
    if(observed!==expect3[j])begin $display("N4_INGRESS_FAIL head=%0d cycle=%0d mutant=%0d",j,i,negative);$fatal(1);end
   end
   for(j=0;j<HEADS;j=j+1)begin
    // A walking one covers every single bit; the per-head salt makes swaps visible.
    a[j]=0;a[j][i%1575]=1;
    for(k=0;k<1575;k=k+1)if((k+j+3*i)%67==0)a[j][k]=~a[j][k];
   end
  end
  $display("N4_INGRESS_PASS heads=%0d checks=%0d bits=1575 latency=4",HEADS,checks);$finish;
 end
endmodule
module qkh_ingress_mut_chain #(parameter integer MUT=0)
(input wire ck,input wire[1574:0] a,output wire[1574:0] b);
 wire [1574:0] abc,gather,t1;
 qkh_head_ingress_abc #(.MUT(MUT)) u0(.ck_a(ck),.ck_b(ck),.ck_c(ck),.ti_a(a[1574:16]),.e_a(a[15:0]),.ti_b(abc[1574:16]),.e_b(abc[15:0]));
 qkh_head_gather_stage #(.MUT(MUT)) ug(.ck(ck),.ti_a(abc[1574:16]),.e_a(abc[15:0]),.ti_b(gather[1574:16]),.e_b(gather[15:0]));
   qkh_head_tstage u1(.ck(ck),.ti_a(gather[1574:16]),.e_a(gather[15:0]),.ti_b(t1[1574:16]),.e_b(t1[15:0]));
 qkh_head_tstage u2(.ck(ck),.ti_a(t1[1574:16]),.e_a(t1[15:0]),.ti_b(b[1574:16]),.e_b(b[15:0]));
endmodule
