HBM-R15 (2026-10-27) — C16 plan-delta TRIAL on Codex pin6_bundle (C15 3a73d67be12d + XQ 362.88x276.48 + HC pair E pins).
Data: intel2:/srv/opentallas-scratch2/claude/hbm-r15-1027 (chain16.sh, c16/, gates16b.sh). Not adopted; no P&R.

Delta (c16_delta.py, report c16_delta_report.json, render c16_render.png viewed):
- Q3 edge core re-lot 190.08 -> 216.00 x 1054.08 at same origin (both instances). Root cause of k3m GP divergence
  (overflow .9956 @38910 it): 12 SRAM 171.288x77.784 fixed 175.5k um2 of 189.7k core, 13.55k um2 movable std in 14.2k free
  (95.7 %). New free ~41k um2 (std ~33 %, UNCHECKED). Macro column re-centred x 22.356; E pins follow face (4443 moved);
  entry (108.00, 527.04) in the same SRAM channel. Gap to body core 95.04 -> 69.12 um. 0 collisions.
- EP 250.56x375.84 -> 241.92x397.44 (Codex crossing model: 336 nets vs 200 SRAM-gap capacity; 425 at 60 % taller);
  non-host y 1114.56 -> 1088.64; R12 W/E split pins (sha 5a4807c8) re-spread per face: E 1125 / W 1124 = 2.96 pins/um
  (old E 6.27). Entry centre (120.96,198.72); core owner places 4 SRAM 2+2 around it. 0 collisions.
- epall --fix: 210 endpoints of moved cores put on actual pins; relax_route 47 bad chains re-sited, count kept, 0 added,
  0 failing; relax_hop 0 added. PG contract unchanged (pin6_bundle current-main 150/70/35).

Pin-window census (pin6_capacity_c15.txt, from Codex c15_pin_windows.json, 47 violations): 16 PARTITIONS average <=5.4/um
on every face -> local clustering only, fixed by an even re-spread in the partition pin emitter; 31 CORES have >=1 face over
capacity even if perfectly spread -> need per-type outline growth or partner-side face split (xq_split pattern). XQ resolved
in pin6_bundle; EP resolved here.

C16r (final candidate, intel2 .../hbm-r15-1027/c16r, plan sha 732240f89458):
- incore_restation.py: 182 station registers left inside the grown cores (EP, q3 edge, XQ from pin6_bundle) moved to the
  nearest free 4.32 lattice point 2.16 um clear of cores (144 chains, max move 95.04 um, count kept); 13 chains then >405
  re-sited by relax_route (0 added cycles, 0 failing). EP clk pin put on the centre entry (120.984,198.744).
- apply_clk.py (HBM-MU-QUAD-6/CLK, COORD 10-27) on C16 --halo 0: renamed 0 / created 0 / moved 0 (C15 lineage already has
  the entry fix); it found 24 core taps != origin+orient(entry) (7 from C16 moves, 17 pre-existing) -> retap.py fixed all 24.
  clock_taps_die.json / clock_htree.json / entries.json are STALE (die clock tool owner regenerates).
- Gates (branch check.py codex-hbm-plan-1351): G0 PASS 0 errors; G0C FAIL 12 = core_faces only (q_hub_nw 6 / q_hub_ne 6,
  pre-existing hub away groups), 49/51 types clean (C15: G0C 20, 47/51).
- tools/die_plan/check.py: G0C clock_entry_macro ported from rescue e33799a17 (halo 0 per COORD ruling) + 6 tests.
