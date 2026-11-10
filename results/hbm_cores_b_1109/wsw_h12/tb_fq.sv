`timescale 1ps/1fs
// Two-clock random bench: gold ot_hbm_accel_cdc_fifo vs ot_hbm_accel_cdc_fifo_fq (W29 AW2), every output every edge.
module tb;
  reg wclk=0, rclk=0, wrst_n=0, rrst_n=0, we=0, re=0; reg [28:0] wd=0;
  wire fa, fb, ea, eb; wire [2:0] da, db; wire [28:0] qa, qb;
  ot_hbm_accel_cdc_fifo    #(.W(29),.AW(2)) A(.wclk(wclk),.wrst_n(wrst_n),.we(we),.wdata(wd),.full(fa),.rd_freed(da),.rclk(rclk),.rrst_n(rrst_n),.re(re),.rdata(qa),.empty(ea));
  ot_hbm_accel_cdc_fifo_fq #(.W(29),.AW(2)) B(.wclk(wclk),.wrst_n(wrst_n),.we(we),.wdata(wd),.full(fb),.rd_freed(db),.rclk(rclk),.rrst_n(rrst_n),.re(re),.rdata(qb),.empty(eb));
  integer errs=0, nw=0, nr=0, nfull=0, seed, i, pw, pr;
  always #(pw) wclk = ~wclk;
  always #(pr) rclk = ~rclk;
  always @(posedge wclk) if (wrst_n) begin if (fa!==fb || da!==db) errs=errs+1; if (fa) nfull=nfull+1; if (we && !fa) nw=nw+1; end
  always @(posedge rclk) if (rrst_n) begin if (ea!==eb || (!ea && qa!==qb)) errs=errs+1; if (re && !ea) nr=nr+1; end
  always @(negedge wclk) begin we = ($random(seed) & 3) != 0; wd = $random(seed); if (($random(seed) & 1023) == 0) wrst_n = 0; else wrst_n = 1; end
  always @(negedge rclk) begin re = ($random(seed) % 5) == 0 ? 1'b1 : (($random(seed) & 3) == 0); if (($random(seed) & 1023) == 0) rrst_n = 0; else rrst_n = 1; end
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    pw = 416 + (seed % 7); pr = 512 + (seed % 11);
    #2000000;
    $display("FQ seed %0d: %s errs %0d writes %0d reads %0d full-cycles %0d", seed, errs ? "FAIL" : "PASS", errs, nw, nr, nfull);
    $finish;
  end
endmodule
