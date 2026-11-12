# DIE-LAYOUT-HBM 11-12: HBM event on d52 = d52 + d6e + opsa_group0 form B + scorer rows

COORD 11-12: compose the next HBM event on d52 (claude/hbm-d52-event-1111@6d875d7fc5bc, plan 9a52537c5f06),
folding in the adopted d6e (CPL-HBM-B1 q_b001 L15_o, no pin cycle) and opsa_group0 form B.

Precondition, checked: q_b001, q_b001__physical_v1, q_b113, q_b113__physical_v1, q_b000 and q_b000__physical_v1 are
byte-equal in d52 and in base0 (fc8d47cd, where d6e, form B and the scorer rows were derived), so every step re-applies unchanged.
d52 contains no scorer rows.

| step | input | plan sha |
|---|---|---|
| base | d52 (hbm-cut-1111/compose/t26) | 9a52537c5f06 |
| + d6e | deltas/d6e_q001_l15_cplb1_1112.json (b351dafd), compose apply, 1347 ops | a9d07e629b29 |
| + opsa_group0 form B | ../opsa_b/opsaB_delta_on_base0.json.gz (whole-type set q_b113, q_b113__physical_v1) + cores/ot_hgi_sfu_opsa_group0__895.32x270__d51opsaB.json (provisional pins, 8fd3b5c9) | 596c1c28e55d |
| + scorer rows | ../scorer_d6e/sc_d6e.json.gz (4 ops) | 5adec4ec8a4d |

One delta for the whole event: ev52_delta.json.gz = compose diff d52 -> final (die_plan.json 511 ops + 1 raw cores file),
also at epyc7 hbm-cut-1111/deltas/ev52_d6e_opsaB_scorer_dlhbm_1112.json (sha 057dfbfa). Re-applied onto d52, it reproduces 5adec4ec.

EQ (compose classify d52 -> final, classify_pB.json): 511 paths, 6 types changed (q_b000, q_b001, q_b113 and their pv1s).
Classes: ft_bands_windows 336, positions_orients 167 (hard-core moves, q_b001 d6e frames + q_b113 g0), outline 4 + pins_file 2
(opstore_a__g0 760.32x233.28 -> 895.32x270, the declared form B overload, being built to sign-off by HBM-CORES-B), notes 2.
No register-count, latency or bus-depth change: 0 cycles.

G0 (tools/die_plan/check.py, src_hbm_main_fe0002fac6): d52 ERROR 551 -> 550. 0 new ERROR checks; the 3 'new' cut rows
are the same NW_b001 cuts with new track counts (ratios 0.69/0.73/0.79 vs 0.79/0.73/0.81), and one vertical cut is gone.
WARN 1800 -> 1834: +35 net hard_cores 8.64-lattice advisories on the d6e q_b001 frames (CPL's positions), reach and core_faces
reshuffled with no net growth.
Strict two-pass bind: BIND_OK, 92 partitions, 420 crossings, 0 errors, stale 0, uncovered 0, pad_flops 945867 (receipt.txt).

Changed types (re-kit): q_b000, q_b000__physical_v1, q_b001, q_b001__physical_v1, q_b113, q_b113__physical_v1.
Not included: svgr_top u_program_lo (HBM-COMPOSE-2 folds it into d53a).
