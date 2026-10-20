`ifndef SYNTHESIS
`timescale 1ns/1ps
// MODEL ONLY: A separately generated model copies the production logic with a516bit shape guard. No full
// physical kit, storage waiver, or adoption is implied by behavioral equality.
module tb;
 parameter integer W=516,MUT=0;
 localparam integer H=W/2,F=4*((W+23)/24),HF=4*((H+23)/24);
 reg wc=0,rc=0;always #5 wc=~wc;
 integer phase=0;
 initial begin if(!$value$plusargs("PHASE=%d",phase))phase=0;#(5+phase);rc=1;forever #5 rc=~rc;end
 reg rst=0,wrst=0,rrst=0;reg[W-1:0]i=0;
 wire[4*W-1:0]bank,rb;wire[4*H-1:0]sb0,sb1;
 wire[F-1:0]fv;wire[HF-1:0]v0,v1;wire[3:0]rv;wire[11:0]re;
 wire[W-1:0]o,ro;wire[H-1:0]o0,o1;
 qfd_c_land_model_safe_w #(.W(W))wf(wc,rst,i,bank,fv);
 qfd_c_land_model_safe_r #(.W(W),.K(MUT?3:2))rf(rc,rst,bank,fv,o);
 qfd_c_land_safe_w #(.W(H))w0(wc,rst,i[0+:H],sb0,v0);
 qfd_c_land_safe_w #(.W(H))w1(wc,rst,i[H+:H],sb1,v1);
 qfd_c_land_safe_r #(.W(H))r0(rc,rst,sb0,v0,o0);
 qfd_c_land_safe_r #(.W(H))r1(rc,rst,sb1,v1,o1);
 always@(posedge wc)wrst<=rst;always@(posedge rc)rrst<=rst;
 qfd_c_land_w #(.W(W))wr(wc,wrst,i,rb,re,rv);
 qfd_c_land_r #(.W(W))rr(rc,rrst,rb,re,rv,ro);
 integer n=0,j,errors=0;
 always@(negedge wc)begin
  n=n+1;rst=n>=10&&!(n>=300&&n<320)&&!(n>=700&&n<720);
  for(j=0;j<W;j=j+1)i[j]=$random;
 end
 always@(posedge rc)begin
  #0.1;
  if(n>7&&(o!=={o1,o0}||o!==ro))begin errors=errors+1;if(errors<4)$display("FULL_LAND_MISMATCH W%0d MUT%0d PHASE%0d cycle%0d",W,MUT,phase,n);end
  if(n>=1000)begin
   if(errors)$fatal(1,"FULL_LAND_FAIL W%0d MUT%0d PHASE%0d errors%0d",W,MUT,phase,errors);
   $display("FULL_LAND_PASS W%0d MUT%0d PHASE%0d words_per_clock1 latency2",W,MUT,phase);$finish;
  end
 end
endmodule
`endif
