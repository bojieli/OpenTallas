# DIE-S81-21 (2026-10-29): S81 global clock geometry FAIL root cause + plan-of-record estimate

No build, no route, no shared-tool change. Diagnostic only.

## 1. Codex global clock GEOMETRY job (epyc2 unit 546691) — collected FAIL
- `epyc2:/srv/opentallas-scratch2/claude/codex-s81-2340/global_clock_src/geometry01.log`: die_trial `tree_netlist`
  ValueError "body home allocation broke physical clock reach; re-plan before build" (~02:09). No ctree/kit.
- Diagnostic rerun (same args, same tool snapshot, raise -> collect): `epyc2:/srv/opentallas-scratch2/claude/die-s81-21/geomdiag`
  (docker python:3.14-slim, 96 GB cap, `run_diag.sh`, `geomdiag01.log`). Output `reach_diag.json` (copied here).
- RESULT (CHECKED, own run): **9 legs > 405 um, all global FEED legs** (non-DME, kind straight, `feed` key), every one
  already > 405 BEFORE physical_pack (pre 406.74 / 7 x 457.308 / 462.388; post-pack delta <= 0.36 um).
  So body-home packing is NOT the cause; the cause is the known gap: shared `physical_leg` reach repair is applied to
  region-DME legs only, feed legs keep the evenly split rep-um 250 chain and one repeater per leg snaps off a blocked span.
- Fix (shared tool, CLK-TOOL-4 owns "global FEED physical_leg pricing"): build feed legs with `physical_leg` (paired inv2
  insertion) when `--rep-actual-max` is set, price the repaired delay in the feed balance, regenerate CA.

## 2. Estimate of the fix (UNCHECKED, analytic, local 2W2S late fit bk_stage_cal_2w2s_late.json, +2 paired inverters, even split)
| leg um | TT delta ps | FF delta ps |
|---|---|---|
| 406.7 (node 29) | +15.3 | +12.2 |
| 457.3 (7 nodes) | +11.1 | +8.4 |
| 462.0 (node 1161) | +10.7 | +8.0 |
Lower bound (a legal detour can be longer). Intra-region hold/setup unaffected (feed is above the region roots);
inter-region CA: go16 plan-mode worst lo/hi to guard 109.4/132.3 ps -> ~94-98 lo if left unbalanced (< 100 gate) ->
the feed balance must absorb the delta (siblings/mirrors), not a pad.

## 3. "Broad hold failure" reading (go16, CHECKED from go16/per_region_spice_edge.json + go16.status)
- Declared FF hold -288.93 with 397/397 regions negative is the LABEL effect (DIE-S81-17 (a)): declared mode counts the
  designed core-tap earliness as skew. Kit-contract hold (W 180) is the real intra-region number:
  **396/397 regions PASS, min +55.13 (s_0N_L1); only bk_sel FAIL -59.2 (window 239.2, 68 pairs).**
- bk_sel TT02 native-body 2W2S coupon (Codex, measured): window TT 62.18 / FF 81.44 -> bk_sel kit hold ~ +98.6 FF (UNCHECKED est).
- View gate FF hold -570.61 / TT setup +18.66: fail-closed on the 1696 early core taps without signed views (CORES-EARLY lane).
- reach17 view TT -100.64 / FF -680.05: post-hoc paired inverters unpriced by DME; geometry01 path prices them (physical_leg).

## 4. Plan of record (global real clock)
1. CLK-TOOL-4: feed legs via physical_leg + priced feed balance (test vector = reach_diag.json, 9 legs).
2. Rerun Codex `global_clock_geom.sh` args (plan_s13r2, map398, feed_sb6, late fit, early .9324 merge, 405/405) — NOTE the
   `inputs`/`physical` symlinks in global_clock_src point at the removed epyc2 wt/die-s81-18 (gone by 02:37); re-point to a
   sparse checkout of the same source before rerun.
3. Render + view + independent GEOM, then native 2W2S GRT TT/FF, die_sta_related (spice_edge, inverter-only tree) + CA bind.
Expected (UNCHECKED): kit hold >= +55 all regions, bk_sel ~+99; CA >= 100 only if the feed delta is balanced.
