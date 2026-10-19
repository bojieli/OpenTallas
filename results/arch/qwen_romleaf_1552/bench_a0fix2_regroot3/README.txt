Q-A0FIX2 10-19: REGROOT 3 (landed per-half S1B select copies, ot_qwen_w12_matvec g_operand_rr.g_lsel) on the A0
ROM-leaf parents qfd_tile_{nl,nk}_rp2_romleaf_rr.  Benches tools/qwen_romleaf/parent_bench_rr.sh (NL) and
parent_nk_bench_rr.sh (NK), Verilator 5.050 (fleet ot-agidock128, ot-run), against the REGROOT-0 reference tile.
MUT0 PASS (checks 6399, valids 2560, nonzero 2560) both; MUT28 (W copy s1b_gm_w held 0) and MUT29 (E copy s1b_gm_e
held 0) FAIL with errors 6250 both.  0 cycles, bit-identical (s1b_* <= s1_* on the shared tile clock).
