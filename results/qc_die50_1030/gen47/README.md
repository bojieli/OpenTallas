# DIE-QC-50/gen47: START/reset provider re-emitted on the gen47 die clock tree (2026-10-30)

Tree: gen47 `tree.json` 4bad7469 (48,296 CKINVDCx16, 19,467 nodes + 28,828 repeaters, 7,889 taps). Plan: plan_qc49
9deec4c7. Proof: the DIE-QC-49/gen47 GRT-routed arrivals with planned-NDR M8/M9 RC (`grt_TTN`/`grt_FFN`, epyc2
die-qc-49/g47src). Main tools only for plan/bind/emit; Codex provider-import scripts copied read-only for placement
(`scripts/codex_provider_import_copy`). Data: epyc2 `/srv/opentallas-scratch2/claude/die-qc-50/gen47`.

Purpose: freeze-gate step (a). The old 2249 provider bound 3,266 stage clocks to old-tree node ids, which are invalid
on gen47 (317 gone, rest moved). This directory re-derives the START graph and the provider on gen47.

## Verdict
Step (a) is done through placement proposal + islands. It is not yet imported into an ODB. QC is NOT FROZEN; steps
(b) and (c) are not started.

## 1. START plan (`scripts/start_plan47.py`, recipe = Codex qc26_retime.py / reprice.py)
- Rows: the 2,525 CA crossings. All ports exist in plan_qc49 and the part map matches (0 mismatches). Old d/p values
  are discarded; each row is reset to the gen47 `sta_port_intervals` hull (spice_edge, CPPR-LCA, AOCV table, shared
  droop, FF core latency 202.5).
- Node-only proof (`startplan_nodeonly_FAIL/run.log`): FAIL. 421 of 811 START edges exceed 400 um. The default
  node-path proof skips the 28,828 repeaters, so there is no retime site between branch nodes. This failure is kept.
- Physical-path proof (main `trial_tap_arrivals.py --physical-paths --node-cell-names`, 48,608 nodes): PASS
  (`startplan/run.log`).

| item | result |
|---|---|
| regions | 3,682 = 313 data regions + 3,369 virtual stages (3,192 retime, 177 branch, 1 root) |
| START edges | 3,681, all clean |
| start_fail / reach_fail | 0 / 0 (max hop 399.6 um at node positions) |
| START width | median 23.9 ps, max 180.3 ps |
| min sync distance | 150.7 ps |
| CA data plan | fail 0; 2,525/2,525 depth 4; worst margin lo 104.8 ps (sl_E4_hc3__cws3__3) |
| bind | PASS |

## 2. Emit: main `start_stage_emit.py emit --reset-wave --path-encoding base36` on the gen47 kit ctree
`emit/check.json`, `scripts/check_emit.py`:
- 3,369 stages, 23,230 FF, 313 outputs.
- Clock cells are byte-identical to the input ctree (48,296).
- All 3,369 `t_st_*__clk` ports are present.
- 1,372 stages take the node cell's A net (inverting polarity).
- Max START hop between actual stage sites is 401.76 um (0 over 405).

Render `emit/render_start47.png` (viewed): stages follow the trunks; 147 edges are over 380 um, all local.

## 3. Synth (Codex reset_wave2 `synth.ys`, main `rtl/common/ot_dp_clk_landing_ca.sv`)
`synth/yosys_stat.txt`:
- 50,020 cells = 23,230 FF + 26,790 comb, 8,098.88 um2.
- `check -assert`: 0 problems.
- FF count equals the emitted count, so no reset FFs were pruned (the reset_wave1 failure mode).

## 4. Placement proposal (Codex provider-import scripts, new inputs; diagnostic policy 18x4.32 um windows, root 32x8.64)
- Constraints exported from gen47 `build2/clock_native.odb`: 48,296 existing cells, 1,602 hard rectangles, 97,280
  rows.
- First try (`place/boxes_first_try_30over405.log`): 30 whole-stage all-FF boxes over 405 um, max 407.97.
- Fix: Codex wave2_compact form, 3-column/3-row FF windows inside the same stage budgets for those 30 stages. Then
  b1038/b1039 FF windows toward each other. No RTL, cycle or rule change. Final `place/`:

| item | result |
|---|---|
| placed | 50,020/50,020, 0 failed |
| max anchor displacement | 10.854 um |
| registered arcs | 33,364, max 402.21 um, 0 over 405 |
| whole-stage interstage | 6,733 edges, max 404.73 um, 0 over 405 |
| islands | 111 types, 18,302 windows, 0 hard-core hits, 0 outside |

Crops `place/render_place_root.png` and `place/render_place_b1038.png` (viewed): FF rows sit on R0 rows next to the
grey clock cells, with no overlaps.

Open items:
- 50,020 of 50,020 cells overlap partition soft OBS. 3,346 of 3,369 stages sit inside partition outlines (12.2a1
  pushdown), so the abstracts need the type-union island holes.
- 313 native outputs and the root `rst_raw_n` are not yet bound to native pins (11 boundary arcs / 1 bit).

## Next (in order)
1. Fresh native target with island-holed abstracts (`die_trial.abstract_lef` minus `island_windows`), then
   `native_clock_source` graft (same ctree, plus the 3,369 `t_st_*` ports from `emit/ctree.v`).
2. Bind the provider outputs to native START pins (Codex `plan_boundary_pins`/`project_pins`) and the root reset.
3. Import (`apply_cells.py`), then leaf drivers (`tools/clk/provider_clock_loads.py`) and access
   (`plan_provider_clock_access.py`).
4. Proof the stages with `start_stage_emit proof` on measured arrivals.
5. Steps (b)/(c): fixed NDR prebuild, PG access, GRT 50 iterations, RCX, then `die_sta_related`. Every (b) input in
   the Codex 2249 chain is old-tree specific and must be regenerated for gen47:
   - the E1 prebuild `fixed_wires`
   - `islands119 cell_windows`
   - `census119_h800` geometry
   - `clock_base_resite_v2` A/Y stacks
   - native M7 landings
   - the `backbone_native` plan
