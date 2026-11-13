# GUNIT-CORE-1 lane handoff (S81 dsdv_gunit_l1f_bf / gunit__t1) -- STOPPED 2026-11-13 12:06 PST, ASK posted

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
None of mine. Nothing killed.
