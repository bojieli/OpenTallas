# DIE-QC-30 — QC native clock landings 7,889/7,889: (b1) parent M7 stubs for the 4 PHY clock pins; growth plan event

Plan/estimate packet. No shared tool, RTL or canonical PG edit. Base: claude/die-qc29-1029@e6156ab3b (form (a), COORD-adopted).
Data: intel2:/srv/opentallas-scratch2/claude/die-qc30 (b1/, b2/), run in docker `--memory=24g` (`run_b1b2.sh`).

## Inputs (form (a) census, DIE-QC-29)
census `die-qc29/formA/census_full/landing_plan.json` (7,885 landed / 4 fail: io_serdes, io_serdes_1, io_serdes_2, ucie_kv),
canonical PG `census119_h800/pg_rects.json`, landing-first reserved power `formA/reserved_power_new.json` (89,180 contacts + 1,690 bridges),
clock M8 witnesses `joint_groups_actual/repair_plan.json`, clock NDR spacing 0.32. sha256 in `plan_event_qc30.json`.

## (b1) parent M7 clock stub — PASS_GEOMETRY, 7,889/7,889 (CHECKED, own run)
`phy_stub_plan.py`: for each failing pin, nearest M8 row OUTSIDE the pin whose VIA78 M8 patch (.192x.080) clears every M8 shape
(canonical PG, reserved power, witnesses, the 7,885 accepted landings) at 0.32, and whose M7 stub (pin width .032, pin metal -> row
incl. VIA78 M7 enclosure .027) clears every other-net M7 shape at .032 (macro OBS/pins/supplies from the source ODB export
`geometry.json` within 3 um = `near_phy.json`: none except the pin itself and the BLOCK M8 strap; reserved-power M7).

| pin | strap (VSS M8) | landing row | stub beyond pin |
|---|---|---|---|
| io_serdes   | 15171.60-15172.08 | 15171.24 (below) | 0.171 um |
| io_serdes_1 | 3481.68-3482.16   | 3482.52 (above)  | 0.211 um |
| ucie_kv     | 9633.36-9633.84   | 9633.00 (below)  | 0.211 um |
| io_serdes_2 | 1157.52-1158.00   | 1157.16 (below)  | 0.275 um |

Render `b1_stubs.png` VIEWED: each stub leaves the pin across/away from the full-width VSS strap; the 0.32 keep box of every patch
ends at the strap edge, nothing else nearby. Die-local, no PG change, wire added 0.87 um M7 total (~0 ps).

## (b2) VSS M8 notch what-if (run in parallel per COORD 06:2x) — FAIL 7,888/7,889, loser
`phy_notch_plan.py`: 0.832-um notch per pin, remainders fed by M9 VSS at 768.96/786.24 (380.16/397.44 for ucie_kv);
in-pin census on the notched grid still fails io_serdes_2 (no clear in-pin row; cause likely the extra clock witness DIE-QC-29 noted on that pin, UNCHECKED). b1 wins (12.17(3)); b2 stopped, no shared PG change proposed.

## Plan event (QC die owner) — `plan_event_qc30.json`
Adopted for the QC native physical plan: form (a) `tap_pin_heights_um` growth (29 types/327 pairs/3,217 pins, centres fixed, 0 cycles),
landing-first clock-cell PG access, and the 4 b1 stubs. NOTE: main `physical/die_plan/qwen_compute/die_plan.json` (68-type PLAN-QCv2)
carries no native tap pins; the event lands with the native h800 plan + fresh native provider import (QC-001).

## Not done (blocked)
fixed_tree prebuild/materialize need a source ODB whose abstracts carry the grown M7 pins, i.e. the fresh native provider import
(Codex packet handoff/codex_qc_20261029_0511.md: fresh native abstracts for 111-type provider islands + native reset outputs, explicit
bindings, 22,365 provider FFCK local branches not routed by the fixed encoder). Strict bind (QC-001) -> die GRT0 incl clock (QC-002)
-> clock check (QC-005) stay BLOCKED on that import. No freeze.

## NK A0 floorplan item (COORD 06:3x, pre-freeze)
QC-A0-KITS-12 NK GEOM FAIL (r2r 634.61 / 124 > 405; NODE in the 65-um east FF column) is a QC plan change and is part of this plan
event (`nk_a0_floorplan`). Die-owner DEFAULT = V1 (move the NODE off the east column; NK keeps the NL east FF column, no macro
pitch/outline change); flip to V2 (re-pitch macro columns) only if the QC-A0-KITS-13 estimate finds no legal NODE site with legs <=405 um.
Status PENDING_ESTIMATE; GEOM plan review before any re-place.

## BTAB F2 clock pin move (COORD 06:4x, pre-freeze)
Same plan event (btab_f2_clock_pin): qfd_dv_s8x_btab core clock pin x 167.916 -> 158.22, parent tap x 833.196 -> 823.5 (dx -9.696 um).
Adopted only on the QC-FIX-2 routed F2 PASS (TT 230-270 / FF 182.5-222.5, pair <=80, measured-frame FF hold, DRV/DRC 0); then re-run the
landing census + landing-first PG replan for the moved tap(s). Status PENDING_ROUTE.
