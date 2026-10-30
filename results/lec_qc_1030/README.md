QC station v1 LEC correspondence diagnosis (2026-10-30)

The original st_a_v1__cl67389ecd result is NOT EQUIVALENT with 72 failed SRAM wd input comparisons (130196/130268 proved). Its raw AIGs/maps and hypotheses were copied before diagnosis to epyc2:/srv/opentallas-scratch2/claude/codex-flow-lec-1030/st_a. Original verdict is unchanged.

The default vector re-layout rekeys every used_q bit when the gate retains a strict superset: gold keeps [0:1], gate [0:2]. Function correspondence then merges mode-state copies across USE2 instances and distinct reset leaves. Existing main option OT_LEC_SUPERSET_VEC=1 retains the common 1-D bit identities. With that option the retained-AIG diagnostic proves all 72 previously failing cones (st_a_72.json; ot-heavy unit1220076 on epyc2). Existing flag and per-extra-bit receipt tests pass (8 tests).

This is a diagnostic, not a full EQ receipt. The diagnostic retains only old hypotheses whose keys exist under the new naming and does not re-prove the full hypothesis set. Production requires a fresh ordinary whole-kit LEC and its existing extra-bit unobservability receipt; routed LEC must explicitly use the same flag. Main signoff.py already enforces those obligations.

Fresh st_a proof could not run because its old run/results directory had already been removed; the QC collector owns regenerating that kit. Fresh st_b_v1 proof with this option started on intel1 unit2478836 in the same lane root/st_b_fresh (fresh AIG generation, source kit read only). No RTL change or cycle change.

Fresh ordinary st_b proof completed EQUIVALENT on 2026-10-30: all 108,647 comparison points proved, zero differences or undecided points (6,089.5 seconds, intel1 unit oth-ubuntu-2478836-1793356889). The existing OT_LEC_SUPERSET_VEC=1 method is the only opted-in switch; the actual receipt records the standard four-edge reset, no debug overrides, complete KEEP retention, and all 640 extra gate-vector bits shown under the ordinary inductive/unobservability checks. No RTL change, output mask or inherited pass was used. The full receipt is st_b_fresh_lec.json. Original failed receipts and earlier filtered diagnostics remain preserved.
