`timescale 1ns/1ps
module tb;
 reg clk=0,rst_n=0;
 ot_su64_full64_gsh1 dut(.clk(clk),.rst_n(rst_n));
 reg v,par,cpair;reg[23:0] a,b,c,d,o;reg[7:0] src;reg[4:0] sh;reg[31:0] q;
 reg oldv;reg[95:0] oldaddr;reg[7:0] oldsrc;reg[23:0] sum;
 integer i,checks=0;
 initial begin
 force dut.u.u.g_gq.q_v=v;force dut.u.u.g_gq.q_par=par;force dut.u.u.g_gq.q_cpair=cpair;
 force dut.u.u.g_gq.q_a=a;force dut.u.u.g_gq.q_b=b;force dut.u.u.g_gq.q_c=c;
 force dut.u.u.g_gq.q_d=d;force dut.u.u.g_gq.q_o=o;force dut.u.u.g_gq.q_src=src;
 force dut.u.u.g_gq.q_sh=sh;force dut.u.u.g_gq.q_q=q;
 force dut.u.u.live0=0;
 v=0;par=0;cpair=0;a=0;b=0;c=0;d=0;o=0;src=0;sh=0;q=0;oldv=0;
 #5;clk=1;#1;clk=0;rst_n=1;
 for(i=0;i<384;i=i+1)begin
 v=(i%5!=0);par=$random;cpair=$random;a=$random;b=$random;c=$random;d=$random;o=$random;src=$random;sh=i%32;q=$random;
 #5;clk=1;#1;
 if(dut.u.u.h_v!==v || dut.u.u.h_par!==par || dut.u.u.h_cpair!==cpair ||
 {dut.u.u.h_a,dut.u.u.h_b,dut.u.u.h_c,dut.u.u.h_d,dut.u.u.h_o,dut.u.u.h_src}!=={a,b,c,d,o,src} || dut.u.u.h_qs!==(q[23:0]<<sh)) $fatal(1,"GSH_METADATA cycle=%0d",i);
 if(i>0)begin
 if(dut.u.u.rd_re!=={4{oldv}}) $fatal(1,"GSH_VALID cycle=%0d",i);
 if(oldv && ({dut.u.u.rd_addr,dut.u.u.rd_src}!=={oldaddr,oldsrc})) $fatal(1,"GSH_READ_ASSOC cycle=%0d",i);
 end
 checks=checks+1;sum=a+(q[23:0]<<sh);oldaddr={d,cpair?(sum^24'd1):c,b,sum};oldsrc=src;oldv=v;
 clk=0;
 end
 rst_n=0;#1;if(dut.u.u.h_v!==0) $fatal(1,"reset retained valid");
 $display("GSH1_METADATA_PASS vectors=%0d checks=%0d shifts=32 bubbles=1",384,checks);$finish;
 end
endmodule
