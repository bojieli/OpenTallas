# HH station plan review — actual pins included

Image `codex_hbm_hh_seams.png` was personally viewed by Codex and independently reviewed by GEOM. PASS-COND for plan/pre-place topology only; no CTS/route approval, no placed/PDN/clock or every-bit proof.

Old coherent2 DP result is GEOM FAIL: it constrained station owners and outer endpoints but ignored the intermediate fixed pin windows. Actual maximum FF-to-seam-pin distances were1136.16/1598.09um and via-pin hops1918.08/2850.58um. Its raw G0 PASS was incomplete flow-under-check evidence, not physical closure. Old result remains preserved.

New die-local solver constrains each slot's first/last FF within30um of its actual input/output window centre, and checks actual via-pin hops as well as ordinary FF distances. New maxima27.824/29.930um and51.84/59.86um respectively. Visible stations occupy the root and edge corridors outside the pictured hardcore keepouts, following the actual pin faces rather than bunching below them. Added stages are explicit: NE→NW[4,6,6]=16stations+2boundary=18cycles; reverse[6,6,7]=19+2=21cycles.

This is a point-placement result. Every-bit FIRM allocation over the wide468um/460um windows, pin-register distance, per-bit reach, channel density, PG continuity, clock tap/driver/sink sidecar regeneration, reset/START and actual GRT/timing remain physical gates. Sidecar clock/PG data is inherited and not a freeze claim. No old view becomes SIGNED through this report.
