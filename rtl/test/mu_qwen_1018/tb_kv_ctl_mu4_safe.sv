`timescale 1ns/1ps
module tb_kv_ctl_mu4_safe;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,we=0,go=0,h=1,u=1;reg[1:0]addr=0;reg[31:0]data=0,gd='1,gf=0;
 wire n0,v0,r0,a0,d0,c0,f0,n1,v1,r1,a1,d1,c1,f1;wire[31:0]y0,y1;wire[7:0]fc0,fc1;
 qkd_static_kv_ownership_calendar_mu #(.MU(1),.PIPE(1),.SAFE(0)) ref0(ck,rst,we,addr,data,go,h,u,gd,gf,n0,v0,r0,a0,d0,c0,y0,f0,fc0);
 qkd_static_kv_ownership_calendar_mu #(.MU(1),.PIPE(1),.SAFE(1)) dut(ck,rst,we,addr,data,go,h,u,gd,gf,n1,v1,r1,a1,d1,c1,y1,f1,fc1);
 task tick;begin @(posedge ck);#1;end endtask
 task drive;begin @(negedge ck);end endtask
 task word(input[1:0]a,input[31:0]d);begin drive();we=1;addr=a;data=d;tick();drive();we=0;repeat(3)tick();end endtask
 task setup;begin drive();rst=0;we=0;go=0;gd='1;gf=0;h=1;u=1;repeat(3)tick();drive();rst=1;repeat(3)tick();word(0,10);word(1,24);word(2,30);word(3,32'h514b564d);repeat(3)tick();end endtask
 task start;begin drive();go=1;tick();drive();go=0;tick();end endtask
 integer ep,i,checks=0,failures=0,drainfault=0,groupfault=0,rearms=0;
 task check(input bit ok);begin checks++;if(!ok)begin failures++;$display("FAIL MU4 check %0d cycle=%0d fc=%h halt=%b",checks,y1,fc1,dut.g_mu.halt_q);end end endtask
 initial begin
  for(ep=0;ep<32;ep++)begin
   setup();start();
   for(i=0;i<65;i++)begin
    drive();go=(i==14 || i==22);if(go)rearms++;tick();
    check({n0,v0,r0,a0,d0,c0,y0,f0,fc0}==={n1,v1,r1,a1,d1,c1,y1,f1,fc1});
   end
   check(!f1&&!a1&&!r1&&c1);
   // Every group must participate in the staged guard reduction.
   setup();drive();gd[ep]=0;repeat(4)tick();start();repeat(14)begin tick();check(f0===f1);end
   check(f1&&fc1[3]&&!v1&&!a1&&r1);if(f1&&fc1[3])drainfault++;
   check(dut.g_mu.halt_q==4'b1111);
   // Fault pipeline: original stops first; SAFE stops exactly one edge later.
   setup();start();repeat(3)tick();drive();gf[ep]=1;tick();tick();
   check(f0&&!f1);tick();check(f1&&fc1[5]&&!v1&&!a1&&r1);if(f1&&fc1[5])groupfault++;
  end
  if(failures || drainfault!=32 || groupfault!=32 || rearms!=64)$fatal(1,"FAIL MU4 errors%0d drain%0d group%0d",failures,drainfault,groupfault);
  $display("PASS MU4_SAFE checks%0d drain32 group32 rearm64 clean_trace_equal fault_plus1",checks);$finish;
 end
endmodule
