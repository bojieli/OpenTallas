HKV-ASTK 2026-10-18/19 -- production-profile calendar of the actual expanded ASTK strip, and its re-price.
Bench: rtl/test/qwen_kv_die/tb_qkd_astk_calendar.sv on qkd_astk_strip_er_st (ctl_s + 8 ep_s + 32 ex_s + 4 zn + mapped
score/e SRAM; e-read = closed star qkd_astk_er_tap_st or distributed qkd_astk_er_chain_st), Verilator 5.050, ot-epyc4.
Checks every run: LMAX/Z sideband words, 8192 score operands (T 8192), every e-read response, strip + e-read fault.
Configs: A RL1 stride16 star (hardware of the attn_calendar laws), B RL1 stride4 star (closed ctl), C RL3 stride4 star,
D RL3 stride4 distributed (OT_KV_ASTK_EXPAND=1).  Minimal LMAX, EXP-LMAX, Z-EXP (sweep*.tsv) and READ-EXP (read_sweep*.tsv):
each minimum PASSes and min-1 FAILs.  A == B (stride is hub-side only).  D vs B: LMAX +16, EXP +16, Z +40 (constant law
verified tight at every T in shift_check.tsv), e-read issue gap -9..+40 (T-dependent, d_pv_gap), e-read latency 7 -> 42.
D mutants ep_s / ctl_s FAIL (mutant_*.log).  T=100 bench expectation defect (partial 64-row group), not RTL.
Law: astk_calendar_law.json, applied by tools/qwen_kv_die/kv_static_programme.py under OT_KV_ASTK_EXPAND=1.
Re-price (reprice.json): attention service +40..+42 edges; the static slot (T 8192) +42 edges/layer x 36 = 1,512 edges
on 249,431 = 0.603 % e2e (4,810.95 -> 4,781.96 tok/s): under the 5 %/unit accepted-cost bound.
NOT a die/native claim: no routed views of the expanded strip yet.
