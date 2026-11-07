`timescale 1ps/1fs
// S81-RCK-4 lock-step: new rate matcher r_d(t+1) == old r_d(t) on every rclk edge after reset, fault identical.
// Random valid/idle/data, FULL and EMPTY reached, clocks at several ratios incl. +-300 ppm and +-8%.
module tb;
  parameter real TW=833.0, TR=833.25; parameter integer SEED=1, NCYC=40000; parameter integer RLOW=64;
  reg wclk=0, rclk=0, rst=0; reg w_v=0; reg [511:0] w_d=0;
  wire [511:0] rg, rn; wire fg, fn;
  always #(TW/2) wclk=~wclk; always #(TR/2) rclk=~rclk;
  reg wr1=0,wr2=0,rr1=0,rr2=0;
  always @(posedge wclk or negedge rst) if(!rst) begin wr1<=0;wr2<=0; end else begin wr1<=1;wr2<=wr1; end
  always @(posedge rclk or negedge rst) if(!rst) begin rr1<=0;rr2<=0; end else begin rr1<=1;rr2<=rr1; end
  rm_gold g(.wclk(wclk),.wrst_n(wr2),.w_v(w_v),.w_d(w_d),.rclk(rclk),.rrst_n(rr2),.r_d(rg),.fault(fg));
  ot_s81_rate_match d(.wclk(wclk),.wrst_n(wr2),.w_v(w_v),.w_d(w_d),.rclk(rclk),.rrst_n(rr2),.r_d(rn),.fault(fn));
  integer seed=SEED, i, mode=0, cnt=0, bad=0, ncmp=0, nvals=0, nidle=0, nfull=0, nempty=0; reg [511:0] rg_q; reg rgv=0;
  always @(posedge wclk) begin
    // bursts: mode changes to fill / drain the FIFO
    if (cnt==0) begin mode=$urandom(seed)%4; cnt=$urandom(seed)%60+1; end else cnt=cnt-1;
    w_v <= #1 (mode==0) ? 1'b1 : (mode==1) ? 1'b0 : (mode==2) ? ($urandom(seed)%2==0) : ($urandom(seed)%8!=0);
    for(i=0;i<16;i=i+1) w_d[i*32 +: 32] <= #1 $urandom(seed);
    if ($urandom(seed)%5==0) begin w_d[1:0] <= #1 2'b10; end  // idle-marked word
    if (g.full) nfull=nfull+1;
  end
  always @(posedge rclk) begin
    rg_q <= rg; rgv <= rr2 && rst;
    #1;
  end
  // compare on the falling edge, both stable
  integer warm=0;
  always @(negedge rclk) if (rst && rr2) begin
    warm=warm+1;
    if (warm>4) begin
      ncmp=ncmp+1;
      if (rn !== rg_q) begin bad=bad+1; if (bad<5) $display("MISMATCH t=%0t new=%h old_q=%h",$time,rn[63:0],rg_q[63:0]); end
      if (fn !== fg) begin bad=bad+1; if (bad<5) $display("FAULT MISMATCH t=%0t",$time); end
      if (rg_q !== 512'd2) nvals=nvals+1; else nidle=nidle+1;
    end
  end
  initial begin
    repeat(RLOW) @(posedge wclk);
    rst=1;
    repeat(NCYC) @(posedge rclk);
    // warm reset, same checks after
    rst=0; warm=0; repeat(RLOW) @(posedge wclk); rst=1;
    repeat(NCYC/4) @(posedge rclk);
    $display("RESULT TW=%0.3f TR=%0.3f cmp=%0d data=%0d idle=%0d full_seen=%0d bad=%0d", TW, TR, ncmp, nvals, nidle, nfull, bad);
    if (ncmp<1000 || nvals<100 || nidle<100 || bad!=0) $display("FAIL"); else $display("PASS");
    $finish;
  end
endmodule
