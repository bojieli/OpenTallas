# QC xhead3 e_pool / POOLc LEC fix, variant B (QC-KITS-W 2026-10-30)

Failure (CHECKED, 6 kits): pre-floor LEC NOT EQUIVALENT / UNPROVEN on POOLc[0..8] in every xhead3 hc kit
(slw_hc2__cl6bcaba89 109446/109455, slw_hc0__cl4f54b7a3, sle_hc2__clcc5e3e61, slw_hc2__cla3497502__cl16607c7a,
sle_hc1__cl22c1ff36 NEQ; sle_hc0__cl929603c0__cl4baa7c9c UNPROVEN). The unkept `reg e_pool [0:1]` holds the same
value under the same write enable as the kept copies e_poolc0/e_poolc1; synthesis merges it into the copies, the gold
side keeps it as separate state, and LEC cannot correlate.

Fix: delete the duplicate state; `pool_x` reads the kept copy bit 0 (`REP_k ? e_poolc1[0] : e_poolc0[0]`).
Same write condition/value, neither has a reset, 0 added cycles, -2 FF. (Variant A, Codex e9b5e63ee = keep packed
e_pool, ran in parallel; B finished first.)

Bench: vehicle_b.sv (iverilog, real write statements + forwarded selector + POOLc update, gold = old RTL):
LOCKSTEP_PASS edges=4096 checks=12288 added_cycles=0; mutant (epoch copies swapped) caught at edge 3.
Full kit LEC: slw_hc2__cl6bcaba89 native synth + lec.py --jobs 4 = EQUIVALENT (summary json here; epyc2
/srv/opentallas-scratch2/claude/qc-kits-w/poolB/slw_hc2__cl6bcaba89/lec/lec.json, t_total 4141 s).
