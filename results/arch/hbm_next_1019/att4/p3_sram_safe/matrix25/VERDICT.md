# P3 ATT SAFE_RESET full matrix (25 legs) -- collected by LH-P3UNITS 10-19
Source codex/hnext-p3att-safe-1019@16ca1193e, defines HNX_ATT_SAFE_RESET=1 (+OT_FP_DATA_NORST in the kit), Verilator 5.050, fleet ot-epyc8 /srv/opentallas-scratch/claude/codex-hnext-p3att-safe-1019/out (session 92609 / pid 1436535).
- Nominal 11/11 PASS, every leg safe_reset=true: sh_s00 / sh_s03 / sh_s10 / sh_sdj / sh_k486 / sh_k490 / sh_k500 (160/160 ops each), nl4_s03, pub_m0 + pub_s2 (576 nodes), sched3 (faults 0).
- Mutants 14/14 FAIL (mutant_detected): sh_smut1/2/3/4k/6 (storage smut6 included), sh_imut1..4, pub_m1..m5.
- Matches the non-safe SRAM baseline matrix (545732f84): 10 nominal PASS + 14 mutants FAIL (+ pub_s2 here). Exactness of the safe variant is PROVEN; physical gate r2 pending.
