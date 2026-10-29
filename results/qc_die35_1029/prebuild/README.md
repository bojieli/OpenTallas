# DIE-QC-35 — QC fixed-tree clock prebuild (QC-001): root cause = stacked clock-cell M7 columns

All runs: intel2 `/srv/opentallas-scratch2/claude/die-qc34/`, Codex `fixed_tree_provider.py` (src_pc) around mesh5
`fixed_tree.py`, same inputs as DIE-QC-34 `run_prebuild.sh` except as listed. Each run ~6-12 min, 64 GB cap.

| run | change vs DIE-QC-34 | result (CHECKED, run_*.log / prebuild_*.json.gz) |
|---|---|---|
| DIE-QC-34 (2231204) | full PG access reserved (185,698 contacts) | 65,862 no_clock_track |
| ctl_noaccess (3680533) | no `--reserved-access` | **39,881** no_clock_track (36,905 nets) -> PG access is NOT the main cause |
| d1_nobackbone (3979495) | also no mesh5 `--backbone-plan` | **3,013** (2,266 nets) |
| d2_diag (738162) | d1 + instrumented `TrackRouter.place` | same 3,013; blocking-shape census `d2_diag.json.gz` |
| d3 what-if de-stack DY 1.6 (1020716) | d1 + clock-cell x de-stack | 125 |
| d3 what-if de-stack DY 4.4 (1020713) | d1 + clock-cell x de-stack | **0: fixed_wires PASS, 44,591 nets** (stopped later at review render: matplotlib missing in container) |

Diagnosis:
1. The backbone plan (mesh5 joint_groups, 89,180 M6-entry records, h800 geometry) pins every clock pin's M7 riser window to
   0.00-0.03 um around one per-pin M8 witness (Y-pin window widths: 0.03 x8,023, 0.02 x7,283, 0.01 x6,544, 0.00 x2,863).
   Each witness was proven for that pin alone; a trunk shared by many pins/nets must sit at one track inside the driver
   window, so trunks of neighbouring nets compete for the same witness track -> 36.9k of the 39.9k failures.
2. Without it, `clock_column_windows` still clips 13,644 / 89,180 pins: tree sites stack clock cells of different nets
   in the same M7 column (|dx| <= 0.064 um) two rows (0.54 um) apart, so the middle pins get a 0.444-um riser window
   (316/400 sampled failures; 88/400 windows lie entirely on the 0.48-um M8 PG strap, e.g. root ck_n0/ck_nr0 window
   12463.113-12463.557 on VDD strap 12462.96-12463.44). A shielded 0.08/0.32 M8 track does not fit -> 3,013 failures.
3. What-if (estimate before build, NOT legal placement): shifting 4,078 clock cells by +-2..6 sites (max 0.324 um) so no
   other-net clock pin shares their M7 column within 4.4 um (one M8 PG pitch) gives 0 no_clock_track. DY 1.6 (3,363
   cells, max 0.216 um) leaves 125.

Fix (QC-001, structural, no new check): re-site clock cells column-aware in the tree plan (no two different-net clock pins
in one M7 column within one M8 PG pitch, whole-site x shifts <= 0.33 um, legalized against the placed design), then
re-derive the M6-entry backbone records on the de-stacked sites with the per-pin witness replaced by the router's
trunk/driver track (clock tracks first), then plan PG access with `plan_access.py --joint-clock-reserved` of those
tracks (V-A), rematerialize, rerun prebuild. Live at park: d4 (de-stack DY 4.4, no access, full stages) and d5
(de-stack DY 4.4 + full PG access reservation) -> measures how much the current PG access still blocks.

## d4 (de-stack DY 4.4, no PG access, all stages; unit 1254018, exit 1) — CHECKED prebuild_d4_destack_full.json.gz
- Track stage PASS (44,591 nets, fixed_wires.json written; region render `d4_review_region.png` VIEWED: c_E2_bf_10 trunks
  in streets/over macros, M8/M9 continuous, no visible stray metal).
- Next stage FAIL `pin-access shorts`: encoder census 519 shorts / 89 spacing over 1,686,897 shapes, and 20,785 top
  (M8/M9) access conflicts; sampled 100: 58 M8 short vs PG strap, 9 spacing vs PG, 27 vs other clock shields, 6 vs tree.
  Example: ck_n0 VIA78 M8 landing pad at y 12463.36-12463.44 on VDD strap 12462.96-12463.44 (pin row under the strap).
  Same signature as Codex prebuild26_resume (21,394). This is exactly what the M6-entry backbone jogs solve -> they must
  be re-derived on the de-stacked sites with a WINDOW (not a single witness y) that the router's chosen trunk/driver track
  lies in, i.e. clock tracks first, then entry jogs, then PG access (V-A order).
- d5 (de-stack + full PG access reservation, unit oth-ubuntu-1254019) LIVE at park: collect prebuild_d5_destack_access/
  run.log + prebuild.json -> no_clock_track count = how much the CURRENT PG access still blocks after the de-stack.
