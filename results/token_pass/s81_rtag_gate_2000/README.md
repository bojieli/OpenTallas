# RTAG MAIN gate collection

The exact N32/SOQ source d0f5b0128 completed the MAIN pre-route gate with WARN: zero failures and five guidance warnings. The physical gate does not constitute a closed view or full token qualification.

The mapped census has 77,722 roots, maximum dynamic load 32, and zero violations. All 3,272 signal/clock pins have accessible geometry. Trial global route has zero overflow, with M3 at 58.83% usage. Setup and hold slack are nonnegative. The ck root TT/FF pin-flop spread is 10.1/9.3 ps; the worst of all five roots is io_e at 36.4/35.2 ps.

Utilization is 61.2% and the largest clock root has 17,685 sinks, both reported as guidance warnings. Floorplan and density were inspected; ROOT independently approved the exact geometry and raw gate for ordinary route qualification; REVIEW.json records that approval. The fallback gate remains a separate active run.

The source archive and helper identities are pinned in identity.json and the full gate_result.json. Helper snapshot 71db1a4a2 preserves the already published main tools used by the run; do not merge that snapshot as new helper development. The existing behavioural and two mutant benches remain the normal closure qualification tasks.

The fallback pre-route gate also finished WARN with zero failures, native maximum load 32, and zero GRT overflow. Its frozen archive and source manifest are separate in fallback_identity.json and its full gate_result.json. This gate is preserved as alternate evidence; MAIN normal closure is already running, so no second closure route was submitted. The gate used its reported effective global-placement density of 0.600; it does not prove final fallback routing at an alternate density.
