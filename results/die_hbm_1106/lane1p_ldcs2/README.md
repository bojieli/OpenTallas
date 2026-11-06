# Lane1p LDCS2 same-edge compressor pruning

Routed vA ECO exhausted at TT -42.70ps, one endpoint, FF hold passes, DRC0. Path d_q[1578] -> g_ld3c.g_s[1].p[39] includes redundant second compression with fourth term zero. LN7 groups are3,3,1 terms.

LDCS2 keeps first compressor s1 and c1 when group has <=3 terms. Its modular sum equals the previous two output rows. Larger groups and LDCS0/1 unchanged. Optional OT_L1P_LDCS2 selects LDCS2 in lane1p; canonical default remains LDCS1. No additional cycles, pins or geometry change. Existing MLAT5 ALAT3 interface ledger remains.

Existing results/die_hbm_1104/reform_a/part17/ldcs_bench generator and main reference were used with new source in /srv/opentallas-scratch2/claude/codex-hbm-l1p-prune/src (epyc5). Both 20000-cycle controls vC/vC_b: LOCKSTEP PASS435600 checks each; source-fault comparisons active. Final-row carry-drop mutant:2010437 errors. Focused new-pruned-carry shift mutant:2493397 errors. Negative runs correctly fail. First invocation used malformed lane-ID literal; corrected to decimal127/693, not counted as functional result. Submitted through ot-run24GB/8threads. Logs and map files here; shell commands reference maintained benchmark scripts and copied source staging.

No physical pass claimed; fresh opt-in synthesis/route required. Original routed vA/vB and ECO artifacts retained.
