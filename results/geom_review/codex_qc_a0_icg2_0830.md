# A0 ICG2 NL / NK V1L pre-placement review, 2026-10-29

Picture: results/codex_qc_a0_0830/a0_icg2_pre_place.png, rendered and personally VIEWED by Codex.

Verdict PASS-COND for exactly ONE placement each (COORD 08:05); no CTS/GRT/DRT/signoff authorization.

NK uses GEOM-56 V1L homes: NODE R0 (15.12,688.656), rawfault columns 73.44/199.80/325.94, ROM column0=16.20. Moving NODE beside W-facing a/b/y/t_out removes the old 2,056-bit upper-half crossing. RF arrays remain aligned with their pipelines and regular horizontal streets. Channels match reviewed legal 10.8-12.32 um form; lower ROM central street remains available, with aligned rows and no overlap or wall. Watch narrow west W strip (1028 input captures), vertical traffic over NODE on M7 and all actual r2r hops <=405. NL retains the reset6 macro base, not the rejected unconverged ICG0 placement.

Clock: ICG2 uses 34 NL /36 NK per-entry gates, K0 for body/NKfaces/NODE and K2 for delayed clusters. Gate/enable hop actual homes are unknown before placement. Measure K0 enable reach and K2 registered hops on actual placement; do not infer timing from this macro picture. Centre clock entry remains (228.972,578.88); no global tree claim. Hard-child PG views and standard parent grid are unchanged. Actual PG continuity, pin density, sink distribution, clock latency and channel congestion need the placed review before any CTS. Two operational proof gaps (mutant8, NLmutant3) must close before signoff.
