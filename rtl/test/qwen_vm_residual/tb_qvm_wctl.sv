`timescale 1ns/1ps
// Q-VMWB 2026-10-16: qvm_wctl27 / qvm_wctl26 (hardened E3 write-control tiles) cycle-exact against the source
// register ot_qfd_vm_write_control_t at the same width: 20,000 random edges with we/d every edge and 40 random
// asynchronous reset pulses (mid-edge assert and release).  MUT=1 swaps two control bits on the DUT input (a
// wiring fault) and MUT=2 inverts we: both must FAIL.  Prints "PASS qvm_wctl W=<w>" only on 0 mismatches.
module tb_qvm_wctl;
 parameter integer W=27, MUT=0;
 reg clk=0, rst_n=0, we=0; reg [W-1:0] d=0; always #1 clk=~clk;
 wire rq; wire [W-1:0] rd; wire dq; wire [W-1:0] dd;
 wire [W-1:0] din = (MUT==1) ? {d[W-1:2], d[0], d[1]} : d;
 wire win = (MUT==2) ? ~we : we;
 ot_qfd_vm_write_control_t #(.W(W)) u_ref(.clk(clk),.rst_n(rst_n),.we(we),.d(d),.qwe(rq),.q(rd));
 generate if (W==27) begin:g27 qvm_wctl27 u_dut(.clk(clk),.rst_n(rst_n),.we(win),.d(din),.qwe(dq),.q(dd));
 end else begin:g26 qvm_wctl26 u_dut(.clk(clk),.rst_n(rst_n),.we(win),.d(din),.qwe(dq),.q(dd)); end endgenerate
 integer i, err=0, cmp=0, rsts=0;
 initial begin
  #5 rst_n=1;
  for(i=0;i<20000;i=i+1) begin
   @(negedge clk); we=$urandom; d={$urandom,$urandom};
   if($urandom%500==0) begin #0.3 rst_n=0; rsts=rsts+1; #0.4 rst_n=1; end
   #0.5; cmp=cmp+1;
   if(rq!==dq || rd!==dd) begin err=err+1; if(err<5) $display("MISMATCH edge %0d ref %b/%h dut %b/%h",i,rq,rd,dq,dd); end
  end
  $display("%s qvm_wctl W=%0d MUT=%0d compares=%0d resets=%0d errors=%0d",(err==0&&cmp==20000&&rsts>0)?"PASS":"FAIL",W,MUT,cmp,rsts,err);
  $finish;
 end
endmodule
