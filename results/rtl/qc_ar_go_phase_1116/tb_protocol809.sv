`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;reg[3:0]sid=0;reg[452:0]hr=0;wire[452:0]q,offq,maxq,badq;wire f,offf,maxf,badf;
localparam[191:0]T={16'd2,16'd55,16'd106,16'd160,16'd211,16'd264,16'd315,16'd367,16'd419,16'd471,16'd524,16'd576};
qfd_dv_ar_go_phase #(.ENABLE(1),.HGD_TABLE(T)) d(ck,rst,sid,hr,q,f);
qfd_dv_ar_go_phase #(.ENABLE(0),.HGD_TABLE(T)) off(ck,rst,sid,hr,offq,offf);
qfd_dv_ar_go_phase #(.ENABLE(1),.HGD_TABLE({12{16'd65535}})) mx(ck,rst,sid,hr,maxq,maxf);
qfd_dv_ar_go_phase #(.ENABLE(1),.HGD_TABLE({12{16'd1}})) bad(ck,rst,sid,hr,badq,badf);
wire[452:0]q805;wire f805;
qfd_dv_ar_go_phase805 #(.ENABLE(1),.HGD_TABLE(T)) old805(ck,rst,sid,hr,q805,f805);
reg[378:0]ib,held;integer age,phase,n,checks=0,maxn=0;reg[15:0]phases[0:11];
task tick;
 begin @(posedge ck);if(q805!==q||f805!==f)$fatal(1,"RESET_FACTOR_MITER");if(offq!==hr||offf)$fatal(1,"OFF_WIRE");if(q[1]!== (hr[0]&&hr[1]))$fatal(1,"XPF_VALID");checks++;end
endtask
task reset;
 begin @(negedge ck);rst=0;hr=0;repeat(4)tick();@(negedge ck);rst=1;repeat(4)tick();end
endtask
initial begin
 ib=0;ib[378:361]=4096;ib[360:343]=3;ib[342:325]=2;ib[128:125]=8;ib[26]=1;
 for(integer s=0;s<12;s++)phases[s]=T[16*s+:16];
 for(integer s=0;s<12;s++)begin
  sid=s;reset();held=ib;held[323:300]=24'(s+100);n=0;
  for(age=0;age<=phases[s]+3;age++)begin
   @(negedge ck);hr={1'b0,379'(age*15+3),72'h3,1'b0};
   if(age==0)hr={1'b1,held,72'd0,1'b1};
   tick();
   if(q[452])begin if(age!=phases[s]||q[451:73]!==held)$fatal(1,"PHASE s%0d a%0d",s,age);n++;end
  end
  if(n!=1||f||!badf)$fatal(1,"SUM s%0d n%0d fault%b bad%b",s,n,f,badf);
 end
 // Maximum16bit interval, stale IB and XPF remain live throughout the wait.
 sid=0;reset();held=ib;
 for(age=0;age<65539;age++)begin
  @(negedge ck);hr={1'b0,379'(age*7+4),72'h3,1'b0};if(age==0)hr={1'b1,held,72'd0,1'b1};tick();
  if(maxq[452])begin if(age!=65535||maxq[451:73]!==held)$fatal(1,"MAX16 %0d",age);maxn++;end
 end
 if(maxn!=1||maxf)$fatal(1,"MAX_SUM");
 // Every non-AR discriminator bypasses at its original receiver edge.
 for(integer op=0;op<9;op++)begin
  reset();held=ib;
  case(op)
   0:held[378:361]=768;
   1:held[360:343]=1;
   2:held[342:325]=8;
   3:held[342:325]=32;
   4:held[324]=1;
   5:held[128:125]=9;
   6:held[27]=1;
   7:held[26]=0;
   8:held[25]=1;
  endcase
  @(negedge ck);hr={1'b1,held,72'd0,1'b1};tick();
  if(q!==hr||f)$fatal(1,"BYPASS op%0d",op);
 end
 // Down K6 is the same complete AR role, with full IB retained.
 sid=11;reset();held=ib;held[342:325]=6;n=0;
 for(age=0;age<6;age++)begin
  @(negedge ck);hr=0;if(age==0)hr={1'b1,held,72'd0,1'b1};tick();
  if(q[452])begin if(age!=2||q[451:73]!==held)$fatal(1,"DOWN_ROLE");n++;end
 end
 if(n!=1||f)$fatal(1,"DOWN_COUNT");sid=0;
 // A second GO during pending/emitting is faulted and never queued.
 reset();n=0;
 for(age=0;age<582;age++)begin
  @(negedge ck);hr=0;if(age==0||age==10||age==576)hr={1'b1,ib,72'd0,1'b1};tick();if(q[452])n++;
 end
 if(n!=1||!f)$fatal(1,"SECOND_GO n%0d f%b",n,f);
 // SID mutation cancels pending GO; reset cancels and permits a new transaction.
 reset();n=0;
 for(age=0;age<580;age++)begin
  @(negedge ck);hr=0;if(age==0)hr={1'b1,ib,72'd0,1'b1};if(age==20)sid=1;tick();if(q[452])n++;
 end
 if(n||!f)$fatal(1,"SID_IDENTITY");
 sid=0;reset();
 for(age=0;age<600;age++)begin
  @(negedge ck);hr=0;if(age==0)hr={1'b1,ib,72'd0,1'b1};if(age==10)rst=0;if(age==14)rst=1;tick();if(q[452])$fatal(1,"RESET_LEAK");
 end
 $display("AR_PHASE_RESET809_PROTOCOL_PASS checks%0d all12table max65535 secondGO SID reset defaultoff invalidphase XPFqual",checks);$finish;
end
endmodule
