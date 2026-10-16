`timescale 1ns/1ps
module tb_wfc_fault_epoch;
 reg ct=1,cs=1,rt=0,rs=0;
 always #6 ct=~ct;always #8 cs=~cs;
 reg a=0,b=0,s=0;wire c,g,e;
 dsfd_vm_wfc_fault_bridge dut(ct,cs,rt,rs,cs,ct,ct,cs,rs,rt,rt,rs,a,b,s,c,g,e);
 integer phase,j,ctime,stime,inject,tests=0,ec,es;
 task reset_epoch;
 begin
  rt=0;rs=0;a=0;b=0;s=0;
  #100;
  #(47-($time%48));rt=1;rs=1;
  repeat(12)@(posedge cs);#1;
  if(c!==0 || e!==0)$fatal(1,"spurious fault after fixed-epoch warmup");
 end
 endtask
 task observe(input integer direction,input integer ph);
 begin
  inject=$time;ctime=-1;stime=-1;
  for(j=0;j<400;j=j+1)begin
   #1;
   if(c===1 && ctime<0)ctime=$time-inject;
   if(e===1 && stime<0)stime=$time-inject;
  end
  if(ctime<0 || stime<0)$fatal(1,"lost diagnostic direction%0d phase%0d core%0d serial%0d",direction,ph,ctime,stime);
  // Expected edge graph, scaled Tcore=12/Tserial=16: same-domain input capture,
  // sticky-source register, fixed bank write/read, receive pin, summary and error register.
  // Counts include the #1 sampling offset. These are not learned by the DUT or rescheduled.
  if(direction==0)begin ec=31;case(ph)0:es=123;1:es=127;2:es=131;3:es=119;endcase end
  else begin es=57;case(ph)0:ec=89;1:ec=85;2:ec=81;endcase end
  if(ctime!=ec || stime!=es)$fatal(1,"diagnostic fixed-edge mismatch dir%0d phase%0d actual%0d/%0d expected%0d/%0d",direction,ph,ctime,stime,ec,es);
  $display("WFC_FAULT_EPOCH PASS direction%0d phase%0d core_delay_ns%0d serial_delay_ns%0d",direction,ph,ctime,stime);tests=tests+1;
 end
 endtask
 initial begin
  for(phase=0;phase<4;phase=phase+1)begin
   reset_epoch();
   @(negedge ct);while(($time%48)!=(6+12*phase))@(negedge ct);
   b=1;observe(0,phase);
  end
  for(phase=0;phase<3;phase=phase+1)begin
   reset_epoch();
   @(negedge cs);while(($time%48)!=(8+16*phase))@(negedge cs);
   s=1;observe(1,phase);
  end
  if(tests!=7)$fatal(1,"missing phase coverage");
  $display("WFC_FAULT_EPOCH_GATE PASS cases%0d",tests);$finish;
 end
endmodule
