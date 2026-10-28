`timescale 1ns/1ps
module tb;
  reg clk = 0; always #1 clk = ~clk;
  reg r_ce, w_ce; reg [5:0] ra, wa; reg [511:0] wd, wm; wire [511:0] q_ref, q_new;
  reg mut_now;
  wire [5:0] ra_new = `ifdef MUT (mut_now ? ra ^ 1 : ra) `else ra `endif ;
  ot_sram_1r1w_64x512_m1_r2c2 u_ref (.clk(clk), .r_ce_in(r_ce), .r_addr_in(ra), .rd_out(q_ref), .w_ce_in(w_ce),
      .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
  ot_sram_1r1w_64x512_m1_r0c0_pc u_new (.clk(clk), .r_ce_in(r_ce), .r_addr_in(ra_new), .rd_out(q_new), .w_ce_in(w_ce),
      .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm));
  integer i, err = 0, reads = 0;
  initial begin
    r_ce = 0; w_ce = 0; ra = 0; wa = 0; wd = 0; wm = 0; mut_now = 0;
    for (i = 0; i < 20000; i = i + 1) begin
      @(negedge clk);
      if (q_ref !== q_new) begin err = err + 1; if (err < 5) $display("MISMATCH cyc %0d", i); end
      r_ce = ($urandom % 4) != 0; w_ce = (i < 128) ? 1 : (($urandom % 3) == 0);
      ra = $urandom; wa = (i < 128) ? i : $urandom; if (($urandom % 8) == 0) ra = wa;
      wd = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}; wm = (($urandom % 4) == 0) ? {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom} : {512{1'b1}};
      mut_now = ($urandom % 16) == 0; if (r_ce) reads = reads + 1;
    end
    $display("LOCKSTEP 64x512_m1 cycles 20000 reads %0d mismatches %0d -> %s", reads, err, err ? "FAIL" : "PASS");
    $finish;
  end
endmodule
