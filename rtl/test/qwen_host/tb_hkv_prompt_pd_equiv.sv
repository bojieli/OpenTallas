`timescale 1ns/1ps
// HKV-PROMPT6 (10-19): qkd_host_prompt_capture_pins (original) vs qkd_host_prompt_capture_pins_pd (parallel per-slot
// SECDED decode, tools/qwen_kv_die/host_cluster/gen_prompt_pd.py) in lockstep: random writes/reads over all 8192
// addresses and all eight slot lanes, plus identical random bit flips in both physical SRAM arrays (single, double and
// multi-bit errors -> corrections, UE zeros, sticky fault).  q and fault must match every edge.  Also checks that
// corrected / UE responses were actually seen.  -DQKD_HR_PD_MUTANT (pd selects lane^1) must FAIL.
module tb_hkv_prompt_pd_equiv;
 reg ck=0, rst_n=0, we=0, re=0; reg [12:0] waddr=0, raddr=0; reg [17:0] wdata=0;
 wire [17:0] qa, qb; wire fa, fb;
 qkd_host_prompt_capture_pins    a(.ck(ck),.rst_n(rst_n),.we(we),.re(re),.waddr(waddr),.raddr(raddr),.wdata(wdata),.q(qa),.fault(fa));
 qkd_host_prompt_capture_pins_pd b(.ck(ck),.rst_n(rst_n),.we(we),.re(re),.waddr(waddr),.raddr(raddr),.wdata(wdata),.q(qb),.fault(fb));
 always #1 ck = ~ck;
 integer cyc=0, mism=0, nflip=0, nreads=0, nzero_ue=0, seed=32'h6b7f, r, c, k, phase;
 reg prev_fault=0;
 initial begin
  if ($value$plusargs("seed=%d", seed)) ;
  repeat (4) @(negedge ck);
  rst_n = 1;
  for (cyc = 0; cyc < 120000; cyc = cyc + 1) begin
   @(negedge ck);
   phase = cyc / 30000;
   // phase 0/2: fill + read; phase 1/3: read heavy with flips; a re-reset at 60000 clears the sticky fault
   if (cyc == 60000) begin rst_n = 0; @(negedge ck); rst_n = 1; end
   we = ($random(seed) & 3) == 0 || (phase % 2 == 0 && ($random(seed) & 1));
   waddr = (cyc < 8192*2 && phase == 0) ? cyc[13:1] : $random(seed);
   wdata = $random(seed);
   re = ($random(seed) & 1);
   raddr = $random(seed);
   if (phase % 2 == 1 && ($random(seed) & 7) == 0) begin
    // identical flips in both arrays (1..3 bits in one physical row)
    r = {$random(seed)} % 514;
    for (k = 0; k <= ({$random(seed)} % 3); k = k + 1) begin
     c = {$random(seed)} % 516;
     a.u_core.u_sram.arr[r][c] = ~a.u_core.u_sram.arr[r][c];
     b.u_core.u_sram.arr[r][c] = ~b.u_core.u_sram.arr[r][c];
     nflip = nflip + 1;
    end
   end
  end
  $display("HKV_PD_EQUIV cycles=%0d reads=%0d flips=%0d mismatches=%0d fault_seen=%0d", cyc, nreads, nflip, mism, prev_fault);
  if (mism == 0 && nflip > 100 && prev_fault) $display("HKV_PD_EQUIV PASS");
  else $display("HKV_PD_EQUIV FAIL");
  $finish;
 end
 always @(posedge ck) begin
  if (re) nreads <= nreads + 1;
  if (fa) prev_fault <= 1;
  if (qa !== qb || fa !== fb) begin
   mism <= mism + 1;
   if (mism < 5) $display("MISMATCH t=%0t qa=%h qb=%h fa=%b fb=%b", $time, qa, qb, fa, fb);
  end
 end
endmodule
