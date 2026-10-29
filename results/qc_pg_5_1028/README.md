# QC-PG-5 (2026-10-28): 75-um A0 power-bump field in the QC plan PG (OWNER 19:58 option (c))

OWNER decision 2026-10-28 19:58: per-tile ICG on every A0 tile + 75-um power-bump field over the whole A0 array
including streets; the rest of the QC die stays at 150 um. This lane puts the field into the QC plan and checks it.
The ICG RTL is handled by the sub-lane QC-PG-5-ICG on its own branch.

## 1. Plan delta (for the QC plan owner, DIE-QC-23)
Basis plan: DIE-QC-23 `ev_qc23.json` (intel2 die-qc23-1028/plan; sha in plan_sha256.txt). The partitions and the 768
A0 outlines are identical to the R35 plan behind the QC-PG-MAP/QC-PG-3/QC-PG-4 solves (CHECKED: 768/768 A0 rects and
377/377 partition rects equal).
Delta = `qc_pg_delta.json` (`die.pg`), applied with `tools/pg_activity/qc/a0_bump_field.py PLAN OUT [155]`:
- `die.pg.bumps` = base 150-um pitch / 70-um pad + one field `a0_p75`: 75-um pitch / 37.5-um pad / keep 75 um, over
  the union of the 768 A0 outlines dilated by 155 um (= the QC-PG-4 MEp75 field; streets covered). The union is 2
  rectangles: [1495.24, 0, 31216.32, 10531.64] and [1495.24, 15733.96, 31216.32, 26265.6] (626.0 mm2).
- `die.pg.grid` M9 width 0.48 -> **0.672** (M8 0.48@8.64 and M9 pitch/offset unchanged). Every QC PG number since
  10-27 (30.403, QC-PG-MAP, QC-PG-2/3/4) used M9 .672 (COORD 10-27 15:24 adopted it provisionally), but ev_qc23 still
  carries 0.48. Without it the numbers below do not hold.
Bump counts (CHECKED, tool output bump_counts.txt): before 35,070 (point sources, 150 um); after **118,011** =
110,678 field bumps (37.5-um pads) + 7,333 base bumps (70-um pads) kept outside the field; VDD/VSS 59,006/59,005;
3.37x (QC-PG-4 ESTIMATE ~119k). Renders (viewed): field_die.png (field, A0 array, IO windows, kept base),
field_edgeN.png (field N edge at the su_c band, pads to scale), field_west.png (field W edge at the SerDes windows:
field pads stay out of the IO windows; 150-um base continues west of x 1495).

## 2. Shared tool change (opt-in, default byte-identical) -> ROOT-MERGE
The plan schema had only a uniform bump pitch. New opt-in `die.pg.bumps.fields[]` {name, pitch_um, pad_um, keep_um,
rects_um[], note}:
- `die_trial.bump_contract` validates fields (pitch > pad, keep >= (pad + base pad)/2, non-empty rects).
- `die_trial.bump_grid(..., pads=False)`: with fields, the field lattice is anchored on the base lattice origin (a
  75-um field lands on every 150-um base site), field bumps inside the rects with the complete pad outside channels/IO
  windows, base bumps within keep_um (Chebyshev) of a field bump dropped; `pads=True` returns (net, x, y, pad_um).
  No fields: output unchanged (test).
- `die_trial.bumps_tcl`/`_pad_bumps_tcl`: per-bump pads (`ot_pad net k x y pad`), OT_BUMPS line lists pads by size.
- `infra_pg.pg_bumps/window_kit/die_kit`: carry the per-bump pad through window crops.
- `schema.py` + `die_plan.schema.json` (dump-schema).
Tests: new test_pg_bump_fields.py (12: unchanged without fields, keep distance, parity, lattice anchoring, IO windows,
6 validation mutants, schema, mixed-pad Tcl on the mock M9 with real contact boxes); test_die_trial_*, test_pg_*,
test_schema, test_check: 201 pass + 13 subtests (pytest_die_plan.log; the one FAIL there was test_schema_file_in_sync
before dump-schema, 15/15 after). G0 check.py on ev_qc23 vs ev_qc23+delta: findings identical (168, same 3
pre-existing hard_pinreg lib ERRORs), CHECKED (g0/).

## 3. PDNSim on the measured map, bumps emitted FROM THE PLAN (VDD + VSS)
Method unchanged from QC-PG-4 (exact class superposition, a0_superpose.py, VDD drop + VSS bounce co-located per
load block, 450-um window edge excluded, + 4.597 mV below-M7 A0 budget), but the kits now come from the plan:
`tools/pg_activity/qc/plan_psm.py` -> infra_pg.window_kit with the plan's die.pg (bumps from the field contract,
per-bump pads). Classes A (A0 at 1 W/mm2), F (flattened logic), S (signed cores own W), U8 (su8) from QC-PG-MAP
loads. 6 solves, all EXIT 0, PG_CHECK OK VDD+VSS, PSM OK, pad_fallback 0 (CHECKED as run outputs, solve/).
A0 basis (QC-PG-3/4, CONFIRMED by NUMBER-CHECK): ICG-gated floor 0.012, token 0.151, gate/up window 0.868,
burst 1.448 W/mm2; F 0.27 W/mm2.
| window (die um) | basis | upper mV (VDD+VSS) | total mV | QC-PG-4 (mixbump) | verdict |
|---|---|---|---|---|---|
| A0 26352,3456 (interior) | ICG floor 0.012 | 2.50 | **7.10** | 7.29 | PASS |
| A0 | token 0.151 | 3.18 | 7.78 | - | PASS |
| A0 | window 0.868 | 14.36 | 18.96 | 18.90 | PASS |
| A0 | **burst 1.448 (static-IR gate)** | 23.96 (13.21 + 10.75) | **28.56** | 28.46 | **PASS** |
| SU 26352,9504 (field N edge + su_c) | burst, F 0.27 | 24.08 | 28.67 | 28.37 | PASS |
| SU | burst, flat F 0.5823 (edge band) | 29.36 | 33.95 | 33.95 | PASS |
| SU su8 node u_b39_33 | ICG floor, su8 12.56 mW | 17.74 | 22.34 (+6.60 su8 below-M7 = 24.35) | 22.35 | PASS |
A unit 16.544 mV per W/mm2 (QC-PG-4 16.48). The plan-emitted map reproduces the QC-PG-4 solve within 0.3 mV.

## 4. M8/M9 track check against the clock and long hops (12.13 / R35)
- PG share (infra_pg.tracks_of, CHECKED): M8 14.58 % (unchanged), M9 14.58 % -> 40.10 % with .672 (as all PG solves).
- Long hops: die layers M8/M9 carry no signals (ruling 9.3, G0 m89_signals), so the field and the M9 width do not
  touch any hop channel (M4-M7 untouched). The bumps touch no metal class (pads land on existing M9).
- Clock: DIE-QC-23 trial15 die clock GRT (c15_TT, inv2 tree, 43,857 nets) rerun with the M9 PG obstructions at 0.672
  (7,225 stripes, same centres): M9 resource -5.6 %, usage 0.44 % -> 0.47 %, 0 overflow on M8/M9, total wirelength
  identical (5,287,636 um), route guide and TT arrivals BYTE-IDENTICAL (sha256 in grt/). CHECKED. No clock impact.
- The R35 M9 spine pair-col phase is unchanged (same pitch/offset).

## 5. Open / UNCHECKED
- Package: mixed 150/70 + 75/37.5 pads on one die needs one fine-pitch-capable bump process (Cu pillar on a fine-line
  substrate or an interposer/RDL); no package rule deck in the repo (UNCHECKED; OWNER accepted the field).
- Window solves have open edges (no feed from outside) -- conservative, same as every QC PG number.
- Full-die PSM not run (a 307-mm2 full-die PSM segfaulted at 119 GB, 10-24).
- The su_c band between the halves stays 150 um (OWNER: rest of die 150); su8 window unchanged.
Run data: intel2:/srv/opentallas-scratch2/claude/qc-pg-5/{kits,c15w672_TT,g0a,g0b,ev_qc23_pg5.json}.
