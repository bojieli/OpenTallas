// KV-PARAMS2 10-19: formal SAT model vs the real sram_gen behavioural model (physical/asap7_memory_macros/
// ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v, faults off).  Random reads/writes/masks/CE, same-address collisions;
// rd_out compared every cycle once every word was fully written (no power-up claim).  MUT=1: model ignores the mask.
module tb;
  reg clk = 0; reg re, we; reg [4:0] ra, wa; reg [127:0] d, m; wire [127:0] q_ref, q_mod;
  ot_sram_1r1w_32x128_m1 u_ref (.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q_ref),.w_ce_in(we),.w_addr_in(wa),.wd_in(d),.w_mask_in(m));
  ot_sram_formal_dut u_mod (.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q_mod),.w_ce_in(we),.w_addr_in(wa),.wd_in(d),.w_mask_in(m));
  integer cyc = 0, errs = 0, checks = 0, coll = 0;
  function [127:0] r128; input integer x; r128 = {$urandom, $urandom, $urandom, $urandom}; endfunction
  always #1 clk = ~clk;
  initial begin
    re = 0; we = 0; ra = 0; wa = 0; d = 0; m = 0;
    repeat (200000) begin
      @(negedge clk);
      if (cyc > 34 && q_ref !== q_mod) begin errs = errs + 1; if (errs < 5) $display("MISMATCH cyc=%0d ref=%h mod=%h", cyc, q_ref, q_mod); end
      if (cyc > 34) checks = checks + 1;
      if (cyc < 32) begin we = 1; wa = cyc[4:0]; d = r128(0); m = {128{1'b1}}; re = 0; end
      else begin
        we = ($urandom % 3) != 0; re = ($urandom % 4) != 0; wa = $urandom; ra = ($urandom % 4 == 0) ? wa : $urandom;
        d = r128(0); m = ($urandom % 2) ? r128(0) : {128{1'b1}};
        if (we && re && ra == wa) coll = coll + 1;
      end
      cyc = cyc + 1;
    end
    if (errs == 0) $display("SRAM_MODEL PASS checks=%0d collisions=%0d errors=0", checks, coll);
    else $display("SRAM_MODEL FAIL checks=%0d errors=%0d", checks, errs);
    $finish;
  end
endmodule
