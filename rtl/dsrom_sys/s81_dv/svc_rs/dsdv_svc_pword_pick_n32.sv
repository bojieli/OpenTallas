`timescale 1ns/1ps
// Same-edge P-bank word swap. Real parity-state cohorts bound both sides of
// selector capture; no added clock/reset/data age and no initialized values.
module dsdv_svc_pword_pick_n32 #(parameter integer W=512,PMEM=1,MUT=0)(
 input wire clk,rst_n,step,oddstep,input wire[2*W-1:0]banks,
 output wire[W-1:0]word0,word1);
 localparam integer N=(W+7)/8,C=(N+30)/31;
 wire[N-1:0]sel;
 for(genvar c=0;c<C;c=c+1)begin:g_cohort
  wire p;wire pn=p^(step&&oddstep);
  ot_hdc_v41x_kreg #(.W(1),.R(1))u_p(.clk(clk),.rst_n(rst_n),.d(pn),.q(p));
  wire sd=(PMEM!=0)?((MUT==4)?~((MUT==5)?p:pn):((MUT==5)?p:pn)):1'b0;
  for(genvar j=0;j<31;j=j+1)begin:g_copy
   if(c*31+j<N)begin:g_valid
    ot_hdc_v41x_kreg #(.W(1),.R(0))u_s(.clk(clk),.rst_n(1'b1),.d(sd),.q(sel[c*31+j]));
   end
  end
 end
 for(genvar b=0;b<W;b=b+1)begin:g_bit
  assign word0[b]=sel[b/8]?banks[W+b]:banks[b];
  assign word1[b]=sel[b/8]?banks[b]:banks[W+b];
 end
 initial if(W<1)$error("invalid P-word width");
endmodule
