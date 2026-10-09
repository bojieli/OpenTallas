`timescale 1ns/1ps
module tb_hbm_retry_pop_cdc;
 reg sc=0,dc=0;always#0.416667 sc=~sc;
 initial begin#0.17;forever#0.416667 dc=~dc;end
 reg sr=0,dr=0,pop=0;wire op,flt;wire[9:0]pending;
 ot_hbm_retry_pop_cdc dut(.s_clk(sc),.s_rst_n(sr),.s_pop(pop),.d_clk(dc),.d_rst_n(dr),.d_pop(op),.fault(flt),.pending(pending));
 integer sent=0,seen=0,i;
 always@(posedge sc)if(sr&&pop)sent<=sent+1;
 always@(posedge dc)if(dr&&op)seen<=seen+1;
 initial begin
 #30;sr=1;dr=1;
 for(i=0;i<1800;i=i+1)begin @(negedge sc);pop=(i%7!=0);end
 @(negedge sc);pop=0;repeat(20)@(posedge dc);#1;
 if(sent!=seen||sent<1024||flt||pending!=0)$fatal(1,"lost/duplicate GrayCDC pop sent%0d seen%0d debt%0d",sent,seen,pending);
 $display("PASS independentphase1p2GHz source/destination,1530+events,Graywrap,noeventloss");
 // Coordinated reset discards session debt before linktraining admission.
 sr=0;dr=0;#30;sent=0;seen=0;sr=1;dr=1;
 repeat(32)begin @(negedge sc);pop=1;end
 @(negedge sc);pop=0;repeat(20)@(posedge dc);#1;
 if(sent!=seen||sent!=32||flt)$fatal(1,"reset CDC debt");
 $display("PASS coordinatedreset eventidentity");$display("PASS_ALL");$finish;
 end
 initial begin#30000;$fatal(1,"watchdog");end
endmodule
