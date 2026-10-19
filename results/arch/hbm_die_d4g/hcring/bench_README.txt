HC-RINGPLAN2 10-19: GEN2d closed HC ring lockstep (bankq0 DRLY 2, XRLY 0 = no b7->b0 die relay, hub/root DRLY 2, CPR 1), Verilator 5.050
on ot-epyc5, src = claude/hcbank-1019 2f897abc3 + runner RAW0 fix 6f4d7c4c7 (same RTL/tb as this branch 5d4077246), run_hbm_hc_eng4_ring.sh
HC_XDEF="+define+HC_DRLY=2 +define+HC_XRLY=0" -> programme RAW0 178 (165 + 11 CPR + 2 for DRLY 2).
  bench_ring_drly2.log              MUT 0               HC_ENG PASS, rc 0
  bench_ring_drly2_mut1.log         MUT 1 (bank-3 rot)  HC_ENG FAIL (witness)
  bench_ring_drly2_qdrly1_neg.log   root QDRLY 1        HC_ENG_FAULT ps=1 (root not told about the 2nd relay register) -> FAIL as required
The first run (9d1689ba4 runner) faulted core=1 in the positive case only because the vectors kept RAW0 176.
