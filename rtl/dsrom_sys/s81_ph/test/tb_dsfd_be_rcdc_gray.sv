`timescale 1ns/1ps
module tb_dsfd_be_rcdc_gray;
    parameter integer PHASE=1;
    reg wclk=0,rclk=0,raw=0,wn=0,rn=0,wv=0,rr=0;
    reg [15:0] wd=0;wire wr,rv,ov;wire[15:0]od;wire[1:0]ovc;
    reg stopw=0,stopr=0;
    always #6 if (!stopw) wclk=~wclk;
    initial begin #(PHASE); forever #4.5 if (!stopr) rclk=~rclk; end
    dsfd_vm_be_rcdc_gray #(.W(16),.NC(2)) dut(.raw_epoch_n(raw),.wclk(wclk),.wrst_n(wn),.w_v(wv),.w_rdy(wr),.w_d(wd),.rclk(rclk),.rrst_n(rn),.r_v(rv),.r_rdy(rr),.o_v(ov),.o_d(od),.o_vc(ovc));
    integer sent=0,got=0,head=0,tail=0,errors=0,epoch=0;
    integer expected[0:10000];time wt[0:10000];time lo=999999,hi=0;
    time slot_written[0:7];
    reg [3:0] prev_pub=0;reg prev_running=0;integer pi;reg[3:0]delta;
    always @(posedge wclk) begin
      if(wv&&wr) slot_written[dut.wp[2:0]]=$time;
      #1;
      if(dut.w_st==2'b11 && prev_running && dut.wp_gray_pub!=prev_pub) begin
        delta=dut.wp_gray_pub^prev_pub;
        if((delta&(delta-1))!=0) begin $display("CDC_BAD non-unit Gray publication");errors=errors+1;end
        pi=(dut.ungray(dut.wp_gray_pub)-1)&7;
        if($time-slot_written[pi]<12) begin $display("CDC_BAD publication before full serial stability age=%0d",$time-slot_written[pi]);errors=errors+1;end
      end
      prev_pub=dut.wp_gray_pub;prev_running=(dut.w_st==2'b11);
    end
    integer cycles=0;
    reg checking=1;
    always @(negedge wclk) begin
      cycles=cycles+1; wv=wn && raw && ((cycles%7)!=2);wd=16'(sent+epoch*1000);
    end
    always @(posedge wclk) if (wv&&wr) begin expected[tail]=wd;wt[tail]=$time;tail=tail+1;sent=sent+1; end
    always @(negedge rclk) rr=rn&&raw&&(($time%56)!=5);
    always @(posedge rclk) begin
      #1;
      if (checking&&ov) begin
        if(head>=tail || od!==16'(expected[head]) || ovc!==2'b11) begin $display("CDC_BAD t=%0t head%0d tail%0d got%h expected%h vc%h",$time,head,tail,od,expected[head],ovc);errors=errors+1; end
        if($time-wt[head]<12) begin $display("CDC_BAD selected entry not stable full serial cycle age=%0d",$time-wt[head]);errors=errors+1;end
        if($time-wt[head]<lo)lo=$time-wt[head];if($time-wt[head]>hi)hi=$time-wt[head];head=head+1;got=got+1;
      end
    end
    initial begin
      #30;raw=1;wn=1;rn=1;
      #2500;
      // Raw reset pulse while both clocks are stopped and forwarded rn stays high.
      checking=0;wv=0;rr=0;stopw=1;stopr=1;#20;raw=0;#2;raw=1;
      #20;
      if(dut.wn!==0 || dut.rn!==0) begin $display("CDC_BAD stopped raw pulse missed");errors=errors+1;end
      epoch=1;head=0;tail=0;sent=0;stopw=0;stopr=0;
      // Consumers start reset; no stale acceptance is permitted once online.
      checking=1;
      #1800;
      // Receiver-only conditioned reset flushes both queues via the online
      // rendezvous. In-flight old-epoch beats before peer observation are
      // explicitly discarded during this quiescence window.
      checking=0;rn=0;wv=0;rr=0;#100;
      if(dut.w_live || dut.r_live || wr || rv) begin $display("CDC_BAD unilateral reset failed quiescence");errors=errors+1;end
      epoch=2;head=0;tail=0;sent=0;rn=1;checking=1;
      #1700;
      wv=0;wn=0;rn=0;raw=0;
      #40;
      if(errors || got<100) $fatal(1,"CDC_BAD errors=%0d got=%0d",errors,got);
      $display("CDC_GRAY_PASS phase=%0d got=%0d latency_ns=%0d..%0d errors=%0d",PHASE,got,lo,hi,errors);$finish;
    end
endmodule
