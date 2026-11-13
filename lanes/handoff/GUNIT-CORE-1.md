# GUNIT-CORE-1 lane handoff (S81 dsdv_gunit_l1f_bf / gunit__t1) -- gf4 builds RUNNING 2026-11-13 12:2x PST

## 1 Scope
Give S81 hard core dsdv_gunit_l1f_bf a routed source (unblock gunit__t1 KIT-WAVE WAIT-CHILD), then get it to sign-off.

## 2 Done
- Cause: S81 hard cores are lane-kit builds and have no wave rows by design (DIE-S81-88 11-12 08:18). gunit__t1 waited
  on prov_require_cands because no prov_view_sources entry pointed at the routed lane kit
  epyc8 /srv/opentallas-scratch2/claude/die-s81-85/bfpad/kit_gf3ds60 (routed 11-12 18:58 PST, DRC 0, NOT SIGNED).
- View dir: epyc8 /srv/opentallas-scratch2/claude/gunit-core-1/view_gf3ds60/dsdv_gunit_l1f_bf (lef, _tt.lib = tc, _ff.lib = BC,
  provenance.json with sha256). Check: epyc9 /srv/opentallas-scratch2/claude/gunit-core-1/provcheck (prov_view.py make on the
  wave plan: dsdv_gunit_l1f_bf = routed).
- kit_wave.json dies.s81.prov_view_sources[dsdv_gunit_l1f_bf] + note_gunit1_1113; backup autopilot/kit_wave.json.bak-gunit-1113;
  coord/state commit 89b1ce0f009. Revert: delete that prov_view_sources key.
- 12:03 KIT-WAVE LAUNCH s81/gunit__t1 attempt 14 (event 7073a6b4a59), unit kw-s81-gunitt1-14-191, work
  epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/gunit__t1/attempt_14.

## 3 Waiter notes
- Watch ~/coord/autopilot/kit_wave/s81_gunit__t1_b7aa3666d0f6c/a14/prov_views.log (11-10 copies there are STALE; check mtime):
  expect PROV_JSON ... "dsdv_gunit_l1f_bf": "routed". Then place; attempt 12 died on OT_NATIVE_CELL_CAP 976,402 > 400,000
  (KIT-OPS-1 class, not this lane).
- When the core is signed later: replace the provisional entry with the signed view (export_view.py) so the type re-signs.

## 4 Core sign-off: BLOCKED on an RTL form (ASK posted, recommendation A)
- kit_gf3ds60: TT -95.94 / 355 ep, drv 293 slew + 4 cap, FF hold -49.66 port-only (NEEDS_PARENT). 5 forms all fail setup.
- My STA (epyc8 /srv/opentallas-scratch2/claude/gunit-core-1/an/sta/o/ends.txt, units x1e12 = ps; placement dump
  an/final.csv): l1r->c1r -95.9/82, l0b->c1r -51.7/225, l0r->c1r -42.2/20, arc->sc -30.8/11, c1r->o_d -18.5/13.
- Cause: fold u_m0 compares A lane i (S face) with B lane 7-i (N face) -> mirrored pairs ~270-520 um apart, 14 logic cells
  in the stage. R-RTL-1/4b/5: depth item, needs +1 register stage (pre-approved); no settings/ECO.
- Form A (recommended): define OT_GUNIT_BF_C1REG, register c1 compare bits + ab/w data at the compare site, retime c1r
  through u_m1 first exchange; +1 cycle on all o_* (total +2 vs gf2). Bench N=2 + mutants, latency row, die-owner reschedule.
- RTL: src_s81_main_7073a6b4a5 rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f.sv (bf module, M1REG define),
  dsdv_gunit_sel_n32.sv (dsdv_seln_fold_cx, dsdv_seln_x2, cx8_2); recipe physical/die_plan/s81/cores/legacy/recipes.json
  [dsdv_gunit_l1f_bf], profile cores/legacy/profiles/bf_m1reg_1108 (bench, pin_cycles.json).

## 5 Running jobs
epyc8 kit_gf4 + kit_gf4ds60 (ot-heavy tags gunit-core-1-kit_gf4*). Nothing killed.

## 6 COORD ruling 12:1x: form A APPROVED -> gf4 (OT_GUNIT_BF_C1REG) built 11-13 20:2x UTC
- Branch claude/gunit-core-1-c1reg-1113 (worktree epyc9 /srv/opentallas-scratch2/claude/wt/gunit-core-1, base origin/main 0a4b432de8):
  dsdv_gunit_l1f.sv bf `ifdef OT_GUNIT_BF_C1REG (inside M1REG): u_f0c fold compares + u_f0g candidate compares registered
  (f_c1q, f_gq) with records f_uq/f_wq; u_f0s exchange; u_m1c/u_m1g compares registered beside c1r (m_c1q, m_gq); u_m1s exchange;
  mfr2/gq2r2/gdr2/fltn2 extra delay. Mutant OT_GUNIT_BF_C1REG_MUT. sel_n32.sv appends dsdv_seln_x2g/x2s/fold_c/cx_c only.
- Define-off check: preprocessed dsdv_gunit_l1f.sv identical to main (blank lines only) for gf3 and gf2 define sets; sel_n32
  old text is an exact prefix (epyc9 /srv/opentallas-scratch2/claude/gunit-core-1/eqoff).
- Bench: profiles/bf_c1reg_1113/bench/run_bench.sh (gold = main bf as gf3; N1 PASS, N0/N2/MUT must FAIL).
- Ledger: profiles/bf_c1reg_1113/pin_cycles.json, physical/die_plan/s81/corelat/cycles_gunit_l1f_bf.tsv (o_* +2 vs plan),
  results/gunit_core_1/latency_rows.json (rows + gunit__t1 lane table, lane mapping read from names = UNVERIFIED).
  OWED by the S81 die owner: compiler/token reschedule of dsdv_gunit_l1c (u_l1c) for +2 on bf o_*.
- recipes.json dsdv_gunit_l1f_bf: suffix gf4, defines M1REG + C1REG, why_reform4.
- Builds (epyc8, ot-heavy 96G, GOAL finish): /srv/opentallas-scratch2/claude/gunit-core-1/kits/kit_gf4 (stock) and kit_gf4ds60
  (same + kit_gf3ds60 GPL-only density screen). Next: render at place (render_kit.py) -> GEOM-VIS verdict -> signoff.py; then
  export_view.py and replace the provisional prov_view_sources entry (keep it LIVE until then).

## 7 PLAN ITEM for the next S81 event (AFTER 11-15 04:00 freeze; COORD 12:1x)
- Real root cause = mirrored face order: fold pairs A lane i (S face s0a/s0b) with B lane 7-i (N face s1a/s1b) while BOTH faces
  run lanes left to right. Reverse the N-face lane order in the plan pins (s1a/s1b x order) so every compare pair is vertically
  aligned: 0 cycles; then gf4's +1 (and possibly gf3's +1) can be retired by a define-off form. Needs a plan event (pins of
  the bf core + gunit__t1 parent wiring) -> GEOM review -> rebuild.

## 8 Waiter notes (gf4, 2026-11-13 12:4x PST)
- Branch claude/gunit-core-1-c1reg-1113 @abef324ccc (NOT merged; merge after the gf4 route verdict). Bench NCYC 120: N1 PASS,
  N0/N2/MUT FAIL (bench/bench_short.out). Full NCYC 1500 still running on epyc9 in the worktree bench dir (bench_N*.log, slow
  iverilog ~30+ min); commit its result as bench_full.out.
- kit_gf4 CTS: "No setup violations found"; kit_gf4ds60 CTS: 6 setup endpoints repaired. CAUTION: gf3 also looked clean
  before route (GRT +7, routed -96) -- judge only on routed signoff.py TT/FF.
- Next per kit: route -> signoff.py verdict -> GEOM-VIS verdict on run/layout_review/{place,grt,route} -> SIGNED -> export_view.py
  -> replace kit_wave.json dies.s81.prov_view_sources[dsdv_gunit_l1f_bf] (backup first) so gunit__t1 re-signs with gf4 views.
  Pick ONE of the two kits (prefer stock kit_gf4 if both sign off). The +2 o_* cycles must be rescheduled by the S81 die owner
  before the gf4 view binds (corelat TSV is on the branch).
