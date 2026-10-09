`timescale 1ns/1ps
// Exactness bench of the pin-registered idle pacer wrapper against the core (redesign-hbm 2026-10-08):
// every cycle wrapper.slot == core.slot and wrapper.send == core.send of the previous cycle, over random,
// bursty and saturated in_v.  Marker PASS_IDLE_PIN; any mismatch -> IDLE_PIN_MISMATCH.
module tb_coll_idle_tx_pin;
 parameter integer M=1024, NCYC=200000;
 reg clk=0,rst_n=0,in_v=0;
 always #0.4166 clk=~clk;
 wire slot_c,send_c,slot_w,send_w;
 // the core sees the reset release the wrapper's local synchroniser produces (two edges later)
 reg [1:0] rs=0;always @(posedge clk or negedge rst_n)if(!rst_n)rs<=0;else rs<={rs[0],1'b1};
 ot_hbm_coll_idle_insert #(.M(M),.PPM(200),.CHECK(0)) u_c(.clk(clk),.rst_n(rs[1]),.in_v(in_v),.slot(slot_c),.send(send_c));
 hfd_coll_idle_tx #(.M(M)) u_w(.clk(clk),.rst_n(rst_n),.in_v(in_v),.slot(slot_w),.send(send_w));
 reg send_c_d=0;integer cyc=0,sends=0,idles=0,mode=0;
 always @(posedge clk)begin
  if(rs[1])begin
   if(slot_w!==slot_c)$fatal(1,"IDLE_PIN_MISMATCH slot cycle %0d wrapper %b core %b",cyc,slot_w,slot_c);
   if(send_w!==send_c_d)$fatal(1,"IDLE_PIN_MISMATCH send cycle %0d wrapper %b core(t-1) %b",cyc,send_w,send_c_d);
   if(send_c)sends=sends+1;if(in_v&&!slot_c)idles=idles+1;
  end
  send_c_d<=rs[1]?send_c:1'b0;cyc=cyc+1;
 end
 always @(negedge clk)begin
  mode=(cyc/5000)%4;
  in_v=rs[1]&&((mode==0)?1'b1:(mode==1)?($urandom%100<97):(mode==2)?($urandom%2):($urandom%1000!=0));
 end
 initial begin
  repeat(3)@(posedge clk);rst_n=1;
  repeat(NCYC)@(posedge clk);
  if(idles==0||idles<NCYC/(8*(M+1)))$fatal(1,"IDLE_PIN_MISMATCH too few forced idles %0d (rule not exercised)",idles);
  $display("PASS_IDLE_PIN M=%0d cycles=%0d sends=%0d forced_idles=%0d",M,NCYC,sends,idles);
  $finish;
 end
endmodule
