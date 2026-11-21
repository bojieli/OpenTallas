# FLOW-CLKGRT-R2 handoff (Opus 5.5; successor of FLOW-CLKGRT-1121). CURRENT 2026-11-21 ~11:2x PST
Goal: clock nets keep near-CTS routes through congestion GRT. Work dir epyc8 /srv/opentallas-scratch2/claude/flow-clkgrt-1121
(h/ harness, out/ results); lane clone epyc10 same path /repo.

## Done
- main 6eeda31903 (predecessor): kit_wave.py private-spec --rt SHA.
- main e338085d61: clock-first GRT opt-in, gen env OT_GRT_CLOCK_FIRST=1 (tools/die_plan/grt_clock_first.tcl, gen_phys
  grt_clock_first_cfg/install, allow_congestion re-armed after the merge read_segments; test_grt_clock_first.py). Off = kit unchanged.

## A/B (KV hroot D25d a5 4_cts_pre_tt copy, 30 it; read from .seg via h/sta_seg.tcl + h/ff_seg.tcl, no re-route)
| arm | overflow | clock-net len vs clock-only | t9 spread | max ins | TT setup/hold | FF internal hold |
| nondr | 385 (10/4) | 46 nets >20um, max +148 | 266 | 655 | -644/-402 | -177, 759 viol |
| clkfirst (no reserve) | 336 (6/3) | +0 | 170 | 410 | -770/-331 | -87, 541 |
| hook (reserve) | 385 (8/3) | +4 um total | 170 | 409 | -624/-331 | -86, 542 |
| base | pending (it ~24/30 at 11:20) | | | | | |
- Remaining t9 170 ps is not a GRT detour (clock routes equal the clock-only route).
- Harness note: arm.tcl usage-report step died GRT-0116 on clkfirst/hook r1 (allow_congestion reset by read_segments); fixed in
  h/arm.tcl; hook r2 rerun = oth-ubuntu-2522200-1795285340 (log out/hook.log; r1 kept as hook_r1.log/.seg).

## Next
1. base done (waiter) -> summ.py out base; resaware same. Default-on only if hook/clkfirst overflow <= base and FF hold not worse.
   If clkfirst (no reservation) beats hook on overflow at equal clock, push OT_GRT_CLOCK_FIRST_RESERVE=0 as the recommended form.
2. Proof on FABLE-FIX-KV-HUB-R2 b1 kit (not generated yet; bind B2): A/B copy via private-spec --ab OT_GRT_CLOCK_FIRST=1 --rt e338085d6155.
