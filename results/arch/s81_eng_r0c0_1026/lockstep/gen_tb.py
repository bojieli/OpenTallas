"""Emit a lockstep testbench: <shape>_r2c2 (repair inputs tied 0, as dsdv_eng_rr_e had them) vs <shape>_r0c0_pc.
Random reads / masked writes every cycle incl. same-address read+write; rd_out compared every cycle.  MUT=1 flips one
address bit on the r0c0_pc side for one in 16 reads (must FAIL)."""
import sys
words, bits, mux = map(int, sys.argv[1:4]); shape = f"{words}x{bits}_m{mux}"; cyc = int(sys.argv[4])
aw = (words - 1).bit_length(); rrw = {"512x128_m4": 14, "64x512_m1": 12, "128x256_m1": 14}[shape]
crw = {"512x128_m4": 14, "64x512_m1": 18, "128x256_m1": 16}[shape]
nw = (bits + 31) // 32
rnd = lambda w: "{" + ",".join(["$urandom"] * ((w + 31) // 32)) + "}"
print(f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #1 clk = ~clk;
  reg r_ce, w_ce; reg [{aw-1}:0] ra, wa; reg [{bits-1}:0] wd, wm; wire [{bits-1}:0] q_ref, q_new;
  reg mut_now;
  wire [{aw-1}:0] ra_new = `ifdef MUT (mut_now ? ra ^ 1 : ra) `else ra `endif ;
  ot_sram_1r1w_{shape}_r2c2 u_ref (.clk(clk), .r_ce_in(r_ce), .r_addr_in(ra), .rd_out(q_ref), .w_ce_in(w_ce),
      .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm), .rr_en(2'b00), .rr_addr({rrw}'d0), .cr_en(2'b00), .cr_sel({crw}'d0));
  ot_sram_1r1w_{shape}_r0c0_pc u_new (.clk(clk), .r_ce_in(r_ce), .r_addr_in(ra_new), .rd_out(q_new), .w_ce_in(w_ce),
      .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm));
  integer i, err = 0, reads = 0;
  initial begin
    r_ce = 0; w_ce = 0; ra = 0; wa = 0; wd = 0; wm = 0; mut_now = 0;
    for (i = 0; i < {cyc}; i = i + 1) begin
      @(negedge clk);
      if (q_ref !== q_new) begin err = err + 1; if (err < 5) $display("MISMATCH cyc %0d", i); end
      r_ce = ($urandom % 4) != 0; w_ce = (i < {words * 2}) ? 1 : (($urandom % 3) == 0);
      ra = $urandom; wa = (i < {words * 2}) ? i : $urandom; if (($urandom % 8) == 0) ra = wa;
      wd = {rnd(bits)}; wm = (($urandom % 4) == 0) ? {rnd(bits)} : {{{bits}{{1'b1}}}};
      mut_now = ($urandom % 16) == 0; if (r_ce) reads = reads + 1;
    end
    $display("LOCKSTEP {shape} cycles {cyc} reads %0d mismatches %0d -> %s", reads, err, err ? "FAIL" : "PASS");
    $finish;
  end
endmodule""")
