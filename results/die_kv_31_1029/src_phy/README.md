# KV VDDPHY source fix + std-cell PG access (DIE-KV-31-SRC), 2026-10-29 10:26 PDT

Continues claude/die-kv-30-src-1029@51516afac (KV-006). Runtime `intel1:/srv/opentallas-scratch2/claude/die-kv-31-1029/src_phy`
(Codex PG helper tools copied read-only to `../pgh`; Codex inputs mounted read-only).

## 1. VDDPHY 0 ITerms: root cause + fix (CHECKED)
- The only macro over die.pg.domains `phy_sys_c_ucie` (VDDPHY/VSS, 5140.8,26058.24..5935.68,26853.12) is `sys_c` (kv3_sys_c_part).
  No master in the source had a VDDPHY MTerm (all 268 masters: VDD/VSS only). kv3_sys_c_part.lef (die_trial.abstract_lef via
  codex rebuild_abstracts.py) exported one full-body CORE VDD M7 pin (294 straps) straight through the PHY window, so
  `add_global_connection -pin_pattern ^VDDPHY$` matched nothing. pg_regions.resolve_loads rejects exactly this
  ("CORE VDD pin metal enters ... PHY region"); the source/pdn path never ran that check.
- Fix in the source step (no ODB edit): `scripts/phy_pg_abstracts.py` applies the repo's existing planned PHY split
  `pg_regions.prototype_lef` (same as `gen.py mockview --planned-phy-pg`) to all 56 abstracts: only kv3_sys_c_part changes
  (VDD 294->386 M7 pieces, cut with 0.096 um gap; VDDPHY 92 M7 pieces inside the domain; VSS 295 unchanged; OBS + signal text asserted identical).
  MODELED PHY interface per HBM PHY ruling (a) default; no licensed-IP/analog claim.
- Full rebuild (`scripts/run_src_phy.sh`, ot-run intel1 units oth-ubuntu-2527784-1793293119, oth-ubuntu-2552237-1793293234):
  check_native identical to DIE-KV-30 except masters.kv3_sys_c_part.pg_pin_shapes; constraints identical except source sha;
  preflight READY_FOR_REVIEW 0 issues; actual reach PASS 15,271 arcs max 355.326 um 0 >405; PG readback 38,127 cells,
  31,845 block OBS, non-PG sha cce6226e... unchanged; supply ITerms VDD 38,127 / VSS 38,127 / **VDDPHY 1 (sys_c/VDDPHY)** (was 0);
  shapes VDD 1,711,367 / VSS 1,700,546 / VDDPHY 8,648 unchanged.

## 2. PG access (CHECKED)
- compare_grid: rebuilt top grid M8/M9 VDD/VSS 19,798 rects == codex-kv-pg-0834 grid3_bbox/pg_rects.json (0 only-old, 0 only-new),
  so that export is reused under export_overlay.py (non-PG sha cce6226e, 75,934 owned terms unchanged, 13,073 PG reservations).
- plan_access --native-overlay (7m34s, 9.6 GB): **INCOMPLETE_NO_MATERIALIZATION**. 45,190 rail groups:
  ok 15,280 (30,234 contacts), failed 29,910 (45,700 contacts). Per net: VDD ok 7,399 / fail 15,196 groups (15,181 / 22,786 contacts);
  VSS ok 7,881 / fail 14,714 (15,053 / 22,914). VDDPHY: no std-cell rails in the domain; sys_c VDDPHY M7->M8 macro contacts are
  outside plan_access scope (pg_regions ot_pg_connect_pins is the repo hook), not planned.
- Blocker: 3,908 die BLOCK OBS on M7 = die_trial.band_share_obs ft-band share stripes (8.1/5.4 um wide, 10.8 um pitch, die-height,
  220 mm2 = ~74% of the die on M7): rejections obstacle_M7 361,338; 25,014 failed rails lie fully under one, 3,900 partially.
  review/access_fail_map.png (viewed): failures under the orange stripes, successes in the 2.7 um gaps. These are a GRT capacity
  model, not metal, but plan_access treats every BLOCK OBS as hard.
- DIAGNOSTIC what-if (not adoptable): same plan without the M7 band-share OBS -> ok 35,970 groups (60,453 contacts), failed 9,220
  (VDD 4,433 / VSS 4,787); remaining rejections obstacle_M8 197,204: die M8 BLOCK 0.40-um-tall segments (~7,977, 22.5-319.7 um long;
  owner = band-share/clock reserve, UNCHECKED) next to the M8 landing.
- apply_access NOT run (requires 0 failed). review/access_render.png = stock render (successes only).

## 3. Loaded die GRT0 incl clock: NOT LAUNCHED (access not clean). `scripts/grt_loaded.tcl` + `run_grt.sh` ready
  (read access.odb, liberty + create_clock root, signal M4-M7 / clock M8-M9 as source.tcl, 50 it, ot-run --mem 256).

## Next
Owner of plan_access/die_trial decides how band-share capacity OBS interact with PG access (e.g. cut them at island windows /
clock-cell rails the way partition M7 PG is cut, or exclude die band-share OBS from the PG-access blocker set and keep them for
GRT only), same question for the M8 0.40-um segments; then re-plan, apply_access, render, launch grt.
No IR, DRC, route, timing, sign-off or freeze claim. 0 cycles added.
