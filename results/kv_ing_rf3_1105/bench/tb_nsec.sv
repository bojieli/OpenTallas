`timescale 1ns/1ps
// KV-ING-1 11-05 r3 cut 18 unit bench: 32-bit counter (r2 form) vs split halves with a registered low-all-ones flag (r3 form),
// random increments for 400k edges from reset (the low half wraps several times); outputs compared every edge.
// +mut=1: the high half steps without the flag (must FAIL); +mut=2: flag from the current value (must FAIL).
module tb;
  reg clk = 0; always #1 clk = ~clk;
  reg rst_n = 0, wf_q = 0; integer mut = 0, i, bad = 0, wraps = 0; reg [31:0] seed = 7;
  reg [31:0] nsec_r;
  reg [15:0] nsec_lo, nsec_hi; reg nsec_lf;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin nsec_r <= 32'd0; nsec_lo <= 16'd0; nsec_hi <= 16'd0; nsec_lf <= 1'b0; end
    else begin
      if (wf_q) nsec_r <= nsec_r + 32'd1;
      if (mut == 0) begin if (wf_q) begin nsec_lo <= nsec_lo + 16'd1; nsec_lf <= nsec_lo == 16'hfffe; if (nsec_lf) nsec_hi <= nsec_hi + 16'd1; end end
      else if (mut == 1) begin if (wf_q) begin nsec_lo <= nsec_lo + 16'd1; nsec_lf <= nsec_lo == 16'hfffe; nsec_hi <= nsec_hi + {15'd0, nsec_lo[15]}; end end
      else begin if (wf_q) begin nsec_lo <= nsec_lo + 16'd1; nsec_lf <= nsec_lo == 16'hffff; if (nsec_lf) nsec_hi <= nsec_hi + 16'd1; end end
    end
  initial begin
    if (!$value$plusargs("mut=%d", mut)) mut = 0;
    repeat (3) @(negedge clk); rst_n = 1;
    for (i = 0; i < 400000; i = i + 1) begin
      @(negedge clk);
      if ({nsec_hi, nsec_lo} !== nsec_r) begin bad = bad + 1; if (bad < 4) $display("MISMATCH i=%0d %h / %h", i, nsec_r, {nsec_hi, nsec_lo}); end
      if (nsec_lo == 16'hffff && wf_q) wraps = wraps + 1;
      seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5);
      wf_q = (seed % 8) != 0;
    end
    $display("NSEC mut=%0d final=%h wraps=%0d mismatches=%0d %s", mut, nsec_r, wraps, bad, bad == 0 ? "PASS" : "FAIL");
    $finish;
  end
endmodule
