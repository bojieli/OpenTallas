`timescale 1ps/1fs
// Lockstep equivalence bench: ot_hbm_accel_cdc_fifo (r0, unchanged) vs ot_hbm_accel_cdc_fifo_r2, same random
// writes/reads on two asynchronous clocks; full and rd_freed compared at every write-clock edge, empty at every
// read-clock edge, rdata at every read-clock edge where the FIFO is not empty (r0's rdata is a don't-care when
// empty).  Plusargs +SEED +CYC (write cycles); -G WP RP (write/read periods ps) PW PR (1/P enable probabilities).
module tb_cdc_fifo_lockstep;
  parameter integer W = 256, AW = 6, WP = 1024, RP = 833, PW = 2, PR = 2;
  reg wclk = 0, rclk = 0, wrst_n = 0, rrst_n = 0, we = 0, re = 0; reg [W-1:0] wdata = 0;
  always #(WP/2) wclk = ~wclk;
  always #(RP/2) rclk = ~rclk;
  wire fa, fb, ea, eb; wire [2:0] da, db; wire [W-1:0] qa, qb;
  ot_hbm_accel_cdc_fifo    #(.W(W), .AW(AW)) a(.wclk(wclk), .wrst_n(wrst_n), .we(we), .wdata(wdata), .full(fa), .rd_freed(da),
    .rclk(rclk), .rrst_n(rrst_n), .re(re), .rdata(qa), .empty(ea));
  ot_hbm_accel_cdc_fifo_r2 #(.W(W), .AW(AW)) b(.wclk(wclk), .wrst_n(wrst_n), .we(we), .wdata(wdata), .full(fb), .rd_freed(db),
    .rclk(rclk), .rrst_n(rrst_n), .re(re), .rdata(qb), .empty(eb));
  integer seed, cyc, i, k, mw = 0, mr = 0, pushes = 0, pops = 0, fulls = 0, freed = 0;
  reg done = 0;
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 100000;
    repeat (3) @(posedge wclk); #7 wrst_n = 1; rrst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge wclk);
      if (fa !== fb || da !== db) begin mw = mw + 1; if (mw < 10) $display("WMISMATCH i=%0d full %b/%b freed %0d/%0d", i, fa, fb, da, db); end
      if (we && !fa) pushes = pushes + 1; if (fa) fulls = fulls + 1; freed = freed + da;
      we = ($unsigned($random(seed)) % PW) == 0;
      for (k = 0; k < W / 32; k = k + 1) wdata[32*k +: 32] = $random(seed);
    end
    done = 1;
    $display("SUMMARY cdc_lockstep W=%0d AW=%0d WP=%0d RP=%0d PW=%0d PR=%0d cycles=%0d wmismatches=%0d rmismatches=%0d pushes=%0d pops=%0d full_cycles=%0d freed=%0d verdict=%s",
             W, AW, WP, RP, PW, PR, cyc, mw, mr, pushes, pops, fulls, freed, (mw == 0 && mr == 0) ? "PASS" : "FAIL");
    $finish;
  end
  integer rs = 7;
  always @(negedge rclk) if (rrst_n && !done) begin
    if (ea !== eb || (!ea && qa !== qb)) begin mr = mr + 1; if (mr < 10) $display("RMISMATCH t=%0t empty %b/%b", $time, ea, eb); end
    if (re && !ea) pops = pops + 1;
    re = ($unsigned($random(rs)) % PR) == 0;
  end
endmodule
