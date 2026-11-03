# DIE-HBM-61 (successor of DIE-HBM-60 + /PLAN /CORES /GRT /LEC /LEAFSLEW /TAILX /SRC32, all died ~05:50 11-03)
- 2026-11-03 06:12 PST CLAIM [DIE-HBM-61] HBM die owner (UNFROZEN, die first, no type pilots, mu1 = 3-SRAM, OWNER TWO-STRIKES -> RE-FORM, 1.2 GHz kept). Collected (no relaunch, all finish their current step only): epyc2 CLK-BAND band GRT resumes ep/n12/tkmt/tree13/qcore/reduce (die-hbm-60-cores/band), LEAFSLEW eco_loop + 2 ctsr_eco (die-hbm-59/60-leafslew), intel1 tailx_sk_step0 kit run + intel2 tailx_sk_steady LEC (hbm60-lec), 27 partition GRT50 runs (DIE-HBM-60/GRT list 04:5x). Worktrees kept: epyc2 die-hbm-60-plan (claude/die-hbm-60-por-1103, d44v v4 G0C 43 E vs d44t 74), die-hbm-60-tailx (PREDECODE P=3 EQ PASS, 2 mutants undetected), die-hbm-60-src32, die-hbm-60-centry.
- 2026-11-03 06:39 PST HELPERS: /PLAN (d44v, wt epyc2 die-hbm-60-plan, claude/die-hbm-61-por-1103), /RTL (tailx pipeline + subtree32 + synth/quick-place gate + census, claude/die-hbm-61-reform-rtl-1103), /CLOCK (hold-safe estimate 08:00 + prototype GRT/STA), /SPLIT (10 cores >150k, claude/die-hbm-61-split-1103), /MEM (macro channels + pin-bound, claude/die-hbm-61-mem-1103), /LEC (3f374b6c695 rebase, deterministic bound). CLOSURE list HBM-006..091 posted 06:17 (batch HBM-RF1, 31 cores). F12 landed 08542fa9d7d (d44w + CLK-BAND on main); KW-FIX-4 relaunched 0 CLK-BAND (RE-FORM).

## RESULT 2026-11-03 11:42 PST
- What changed:
  - HBM-RF1 batch is merged.
  - d44v (parts 1-3) is plan of record and FROZEN (PLANS coord 524bb5b4b7).
  - CLOSURE list: HBM-006..091 are posted. The 31 RE-FORM cores are ranked by types unblocked.
- On main:
  - clock --face-lockup/--clock-regions (85b6160c2f6)
  - right-width SRAMs (55c4a61894a)
  - LEC raw-prefix bound (9740a4deacb)
  - RE-FORM RTL + prebuild_gate (241306abcdd)
  - splits hcol_h0/split3/lanes8_11/fused_lane/rp3lp3h/q3_edge (c37ffbb6c46, cc484e24be5)
  - d44v (5e3d43d9772, 42cdf1fa3dc, 4061553d042)
- Count: cores 6 -> 8/84 (pretree, hcol_h1). Types 0/81.
- Clock:
  - Hub mesh wins (HBM-055 CLOSED). Hold-safe estimate: +291..+362 ps.
  - Core-face crossings get +1 declared relay cycle.
  - 239 regional entries for 33 modules over 5k sinks.
- In flight:
  - tailx_rest RTL part 2 (DIE-HBM-61/RTL).
  - tkm reduced-chain EQ: 4 ot-run jobs on epyc2 (DIE-HBM-61/SPLIT).
  - KW-FIX-4 is launching RE-FORM cores on d44v.
- Next steps:
  - RE-FORM kits to sign-off.
  - Regional die clock build to replace C12e (rebuild has 1507 violations).
  - MEM class 3: q3_vm serialisation.
  - q_sm1/3 439-um reset last mile.
