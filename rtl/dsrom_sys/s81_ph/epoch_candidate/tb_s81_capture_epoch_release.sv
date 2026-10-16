`timescale 1ns/1ps
// Exact tick model: stream /3, serial /4, tick = two VCO edges.
// Source model is an explicit conditional input boundary, NOT existing PLL IP.
module tb_s81_capture_epoch_release;
 reg s=1,v=1; always #3 s=~s; always #4 v=~v;
 reg rs=0,rv=0,pcs=0,pcv=0;
 wire as,av,cs,cv;
 integer tick=0,first_s=-1,first_v=-1,epoch,case_n,errors=0;
 ot_s81_capture_epoch_release #(.ENABLE(1)) u(s,v,rs,rv,pcs,pcv,as,av,cs,cv);
 always #1 begin
   tick=tick+1;
   // Grant at phase16 only after source has seen BOTH startup acknowledgments.
   if (tick%24==16) begin pcs=as&&av; pcv=as&&av; end
   if (tick%24==0) begin pcs=0; pcv=0; end
 end
 always @(posedge s) if(cs && first_s<0) first_s=$time;
 always @(posedge v) if(cv && first_v<0) first_v=$time;
 task run_case(input integer offset);
 begin
   rs=0;rv=0;#1;
   if(cs||cv) $fatal(1,"asynchronous warm reset did not assert");
   first_s=-1;first_v=-1;
   #(offset+1);rs=1; #17;rv=1;
   wait(first_s>=0 && first_v>=0);
   if(first_s!=first_v || first_s%24!=0)
     $fatal(1,"epoch mismatch offset=%0d stream=%0d serial=%0d",offset,first_s,first_v);
   #25;
 end endtask
 initial begin
   // Force real reset edges from time zero.
   #1;rs=1;rv=1;#1;
   for(case_n=0;case_n<24;case_n=case_n+1) run_case(case_n);
   $display("S81_CAPTURE_EPOCH_CONDITIONAL PASS cases=24 cold_warm_offsets=24");$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
