# TL-SLC1XT8 handoff (successor 11-14 19:40 PST)
Work dir /srv/opentallas-scratch2/claude/tl-slc1xt8 (epyc9 runs, intel2 same-path unit.log+result.json).
Live: fA2, fB2 (B3v regen, fB = sparse GPL) on epyc9 inside run_kit.sh: yosys rtl_lint (rtl_lint.ys) running ~1 h, 77% CPU (not hung); place not yet started. fC5 (legalized plan fC, 3 cores moved) in gen_lint docker (8g) ~1h15, same yosys lint.
Dead/failed: fC4 gen_lint FAIL yosys rc 143 (killed) -> fC5 is retry (same lint; if 143 again => lint timeout is the structural cause, advisory: bypass lint via preflight skip only with COORD ok).
Superseded wave kit vl3s/b/C1 cancelled by NOPROG watchdog (grt 25 h), NEEDS-LANE 18:35 = this lane.
Waiter: intel2 ~/tl-slc1xt8-watch.sh appends result.json lines to $D/watch.out every 15 min.
NEXT: when fA2/fB2/fC5 reach route, check gates DRC0/setup>=-42/hold>=0; pass -> AUTO-RESIGN row + export + RESULT. Fail GRT overflow at u_bound.u_ist_leafdn_o2_1 -> structural fix, ASK COORD Fable review after 2 rounds.
