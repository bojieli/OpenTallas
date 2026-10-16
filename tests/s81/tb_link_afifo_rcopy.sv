`timescale 1ns/1ps
// ot_link_afifo RCOPY (kept read-address copies) vs the single-pointer FIFO: same random traffic on two unrelated
// clocks, every read-side output compared every rclk edge. +define+OT_LINK_AFIFO_MUT_RCOPY must FAIL.
module tb_link_afifo_rcopy;
  reg wclk=0, rclk=0; always #2.1 wclk=~wclk; always #3.7 rclk=~rclk;
  reg wrst_n=0, rrst_n=0, wr=0, rd=0; reg [513:0] wdata=0;
  wire f0,f1,e0,e1,o0,o1; wire [513:0] d0,d1; wire [5:0] fr0,fr1,c0,c1;
  ot_link_afifo #(.W(514),.AW(5)) a0(.wclk(wclk),.wrst_n(wrst_n),.wr(wr),.wdata(wdata),.wfull(f0),.wfreed(fr0),.ovf(o0),
    .rclk(rclk),.rrst_n(rrst_n),.rd(rd),.rempty(e0),.rdata(d0),.rcount(c0));
  ot_link_afifo #(.W(514),.AW(5),.RCOPY(32)) a1(.wclk(wclk),.wrst_n(wrst_n),.wr(wr),.wdata(wdata),.wfull(f1),.wfreed(fr1),.ovf(o1),
    .rclk(rclk),.rrst_n(rrst_n),.rd(rd),.rempty(e1),.rdata(d1),.rcount(c1));
  integer n=0, pops=0, seed=7;
  always @(negedge wclk) if (wrst_n) begin wr <= ($random(seed) & 3) != 0; wdata <= {$random(seed),$random(seed),$random(seed),$random(seed),
      $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
      $random(seed),$random(seed),$random(seed),$random(seed)}; end
  always @(negedge rclk) if (rrst_n) begin rd <= ($random(seed) & 1); end
  always @(posedge rclk) if (rrst_n) begin
    n = n + 1; if (rd && !e0) pops = pops + 1;
    if (e0 !== e1 || c0 !== c1 || (!e0 && d0 !== d1)) begin $display("FATAL RCOPY mismatch at %0d", n); $fatal(1); end
    if (n == 20000) begin $display("PASS link afifo RCOPY 32 equivalent: %0d rclk edges, %0d pops", n, pops); $finish; end
  end
  initial begin #20 wrst_n=1; rrst_n=1; end
endmodule
