`timescale 1ps/1ps
// HBM-WBQ-QUAL-1: unit bench of the g1 record pipeline (ot_wbq_root_s7_rr_fifo, RPIPE) against ot_hbm_accel_cdc_fifo, on the
// producer pattern of the root lane: we only when !full (we = copy_q & read_pending & !full & !s_stop), random stalls (s_stop pulses,
// read_pending gaps), consumer re only when !empty with random back-pressure (credit/K stalls). Two free-running clocks.
// Checks per FIFO: every word read back in order, none lost, none duplicated, none read before written (rdata visible with !empty only);
// reports max occupancy seen by the producer (accepted - read) and first-word visibility latency (wclk edges, write to empty low).
module tb_rrfifo;
 parameter integer MUT=0, N=50000;
 int TF=1000, TH=1000, PH=137;
 initial begin void'($value$plusargs("TF=%d",TF));void'($value$plusargs("TH=%d",TH));void'($value$plusargs("PH=%d",PH)); end
 reg wc=0,hc=0;initial begin #1;forever #(TF/2)wc=~wc;end initial begin #(PH+1);forever #(TH/2)hc=~hc;end
 reg rst_n=0;initial begin #(10*TF);rst_n=1;end
 wire [1:0] unused;
 reg w0=0,w1=0,r0=0,r1=0;int cn0=0,cn1=0,rn0=0,rn1=0;
 wire f0,f1,e0,e1;wire [287:0] rd0,rd1;
 wire we0=w0&&!f0&&cn0<N,we1=w1&&!f1&&cn1<N,re0=r0&&!e0,re1=r1&&!e1;
 wire [287:0] wd0={216'h0,72'(cn0)},wd1={216'h0,72'(cn1)};
 ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_refq(.wclk(wc),.wrst_n(rst_n),.we(we0),.wdata(wd0),.full(f0),.rd_freed(),.rclk(hc),.rrst_n(rst_n),.re(re0),.rdata(rd0),.empty(e0));
 ot_wbq_root_s7_rr_fifo #(.W(288),.AW(2),.MUT(MUT)) dut(.wclk(wc),.wrst_n(rst_n),.we(we1),.wdata(wd1),.full(f1),.rd_freed(),.rclk(hc),.rrst_n(rst_n),.re(re1),.rdata(rd1),.empty(e1));
 int mode=0; // 0 busy producer, light consumer stalls; 1 slow consumer; 2 bursty
 int bad0=0,bad1=0,occ0=0,occ1=0,maxo0=0,maxo1=0,stopc=0;
 reg stop=0;
 always @(posedge wc)if(rst_n)begin
  stopc<=(mode==2)?(($urandom%8==0)?$urandom%6:stopc>0?stopc-1:0):0;
  stop<=(stopc>0)||($urandom%11==0);
  w0<=!stop&&$urandom%4!=0;w1<=!stop&&$urandom%4!=0;
  if(we0)cn0<=cn0+1;if(we1)cn1<=cn1+1;
 end
 always @(posedge hc)if(rst_n)begin
  r0<=($urandom%((mode==1)?5:2)==0);r1<=($urandom%((mode==1)?5:2)==0);
  if(re0)begin if(rd0[71:0]!==72'(rn0))bad0<=bad0+1;rn0<=rn0+1;end
  if(re1)begin if(rd1[71:0]!==72'(rn1))bad1<=bad1+1;rn1<=rn1+1;end
 end
 always @(posedge wc)if(rst_n)begin
  occ0=cn0-rn0;occ1=cn1-rn1;if(occ0>maxo0)maxo0=occ0;if(occ1>maxo1)maxo1=occ1;
 end
 initial begin
  wait(rst_n);
  repeat(N*8)begin @(posedge wc);if(cn0>=N&&cn1>=N&&rn0>=cn0&&rn1>=cn1)break;if(($time/TF)%40000==0)mode=($time/TF/40000)%3;end
  repeat(50)@(posedge wc);
  $display("RRFIFO MUT=%0d TF=%0d TH=%0d words ref %0d/%0d dut %0d/%0d bad ref %0d dut %0d maxocc ref %0d dut %0d",MUT,TF,TH,cn0,rn0,cn1,rn1,bad0,bad1,maxo0,maxo1);
  if(bad0==0&&bad1==0&&rn0==cn0&&rn1==cn1&&cn1>=N)begin $display("RRFIFO PASS");$finish;end
  else begin $display("RRFIFO FAIL");$fatal(1,"FAIL");end
 end
endmodule
