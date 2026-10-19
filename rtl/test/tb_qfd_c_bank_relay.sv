`ifndef SYNTHESIS
`timescale 1ns/1ps
// Diagnostic: can whole-bank transport fit inside existing D4/K2 lifetime?
// <=2 alternating half-cycle stages only are candidates. MUT4 deliberately
// overruns the early receiver's age window. No structural adoption implied.
module tb;
 parameter integer HOPS=0;
 reg wck=0,rck=0;always #5 wck=~wck;
 integer phase=0;
 initial begin if(!$value$plusargs("PHASE=%d",phase))phase=0; #(5+phase);rck=1;forever #5 rck=~rck;end
 reg rst=0,wrst=0,rrst=0;
 reg [257:0] i=0;
 wire [1031:0] b[0:HOPS],ref_bank;
 wire [257:0] o,ref_o;
 wire[11:0] epo;wire[3:0]vld;wire[43:0]safe_vld;
 qfd_c_land_safe_w #(.W(258)) w(wck,rst,i,b[0],safe_vld);
 genvar h;
 generate for(h=0;h<HOPS;h=h+1)begin:g_hop
  reg[1031:0]q;
  if(h%2==0)always@(negedge wck)q<=b[h];
  else always@(posedge wck)q<=b[h];
  assign b[h+1]=q;
 end endgenerate
 qfd_c_land_safe_r #(.W(258))r(rck,rst,b[HOPS],safe_vld,o);
 always@(posedge wck)wrst<=rst;always@(posedge rck)rrst<=rst;
 qfd_c_land_w #(.W(258))rw(wck,wrst,i,ref_bank,epo,vld);
 qfd_c_land_r #(.W(258))rr(rck,rrst,ref_bank,epo,vld,ref_o);
 integer n=0,k,errors=0;
 always@(negedge wck)begin
  n=n+1;rst=(n>=8&&!(n>=300&&n<310)&&!(n>=700&&n<708));
  for(k=0;k<258;k=k+1)i[k]=$random;
 end
 always@(posedge rck)begin
  #0.1;
  if(n>6&&o!==ref_o)begin errors=errors+1;if(errors<4)$display("BANK_RELAY_MISMATCH hops%0d phase%0d cycle%0d",HOPS,phase,n);end
  if(n>=1000)begin
   if(errors)$fatal(1,"BANK_RELAY_FAIL HOPS%0d PHASE%0d errors%0d",HOPS,phase,errors);
   $display("BANK_RELAY_PASS HOPS%0d PHASE%0d",HOPS,phase);$finish;
  end
 end
endmodule
`endif
