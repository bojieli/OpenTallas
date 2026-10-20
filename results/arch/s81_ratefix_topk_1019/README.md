# S81-RATEFIX (10-19): top-k FINAL selector rate fix

1. Selector: INDEXED13 successor quarter (OT_S81PH_SEL_INDEXED13 + FIFO_SRAM + SRAM_P192 + SEL_SUCC + SEL_RST64 +
   SEL_FAN32 = the s81dvbk_sq_succ2 kit defines on this branch): packed type8 ingress 324 beats vs 5,983 for the legacy
   sparse rung format -> topk_final 6,554..6,698 (release legacy) -> 1,033 edges.
2. Compiler: `lower_bk.py` opened the drain window TAIL_BUDGET = 640 edges after the last ingress beat for every select.
   The FINAL select (k_dies 1, INDEXED13) now uses TAIL_FINAL = TAIL_FINAL_MIN 260 + margin 16 = 276 (topk_local / split
   jobs keep 640). Static: the drain CTL and every egress beat are compiled edges, no handshake.
   Sweep (mk_tail.py/run_tail.sh, Verilator 5.050, ot-epyc9): sweep/summary_sweep1_280_640.txt all PASS 280..640;
   sweep/summary_sweep2.txt: real L20 passes 240 (fails 220), ties 220 (fails 200), all-in-one-quarter -inf/zeros
   260 (fail 240) -> worst case 260.
3. Compiled at 276 by lower_bk itself (gen + scripts/extras.py), run_t276/: indexed13, ties, ninf, zeros PASS bit-exact
   (every egress beat at its compiled edge); corrupt, early, identity mutants FAIL. Span 1,033 -> 669 (window -364).
Not in the release die mu4c (legacy dsdv_bk_sel bound); succ quarter physical view still gating (S81-TOPK); producer
TP4 -> vi_s and IDX -> gather consumer gaps unchanged. Token impact: claude/s81-ratefix-1019
results/token_pass/ratefix_s81_1019.
