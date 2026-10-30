# DIE-QC-50/gen47b: gen47 START/reset provider imported into the die database (2026-10-30)

Freeze-gate step (a), continued from DIE-QC-50/gen47 (c10d9a572). Plan plan_qc49 9deec4c7. Die clock tree gen47
4bad7469 (kit ctree.v 15f44729). Provider = the gen47 emit (3,369 stages, 23,230 FF) synthesized to 50,020 cells,
placed by the gen47 pimpC2 proposal. Run root: epyc2 `/srv/opentallas-scratch2/claude/die-qc-50/gen47b`.
Tools: main 4a5ce2f96 (`tools_main/`, die_trial / native_clock_source / provider_clock_loads /
plan_provider_clock_access / start_stage_emit / die_sta_related). Codex provider-import scripts are copies
(`gen47/pimp_src`, unmodified). QC-IMPORT-2 `preflight.py` (main) is used for the reset-on-bound-net check.

## Verdict
Step (a) is done: the provider is imported (all 50,020 cells), its clock leaf loads and lower access are planned, and
the stages pass the measured START proof on pre-import arrivals (loaded GRT readout is invalid, see 5). QC is NOT FROZEN. Step (b) (drawn fixed-NDR prebuild, PG access) and step
(c) (GRT 50 + RCX + related STA) are not done. COORD 16:0x ruling: Route A (drawn fixed prebuild rebuilt for gen47)
is the default measure for this lane. Route B (clock DRT + RCX) belongs to sibling [DIE-QC-50/gen47ndr].

## 1. Fresh native target with island holes (`scripts/sites47b.py`, `fresh_target47b.py`, `run_target_graft.sh`)
- Island sites: the 48,296 gen47 clock bodies plus the 50,020 provider bodies, each with its actual bbox (QC-IMPORT-1
  recipe, main `die_trial.island_windows` with the per-site `cell_um` opt-in). `islands/island_census.json`:

| sites | types | windows | in hard core | outside partitions |
|---|---|---|---|---|
| clock 48,296 | 118 | 13,888 | 0 | 24 (channel sites) |
| provider 50,020 | 111 | 18,302 | 0 | 0 |
| combined 98,316 | 118 | 32,190 | 0 | 24 |

- Abstracts: all 119 regenerated with `abstract_lef(islands=combined, landing_infra, reset_infra)`. 118 of them
  carry holes. Hard-core OBS is kept (12.2a1, type-union).
- route.v is regenerated and is byte-identical to DIE-QC-49 target49. grt.tcl, obs.tcl and tracks.tcl are copied
  unchanged.
- Graft: main `native_clock_source.py` with the gen47 kit ctree.v and tree.json, the same inputs as DIE-QC-49 build2.
  Result: CONNECTED_UNROUTED, 48,296 cells, 7,889 native M7 taps, root (17007.84, 12463.2).
- Hashes: native_target.odb ede56846, clock_native.odb da2473dd.

## 2. Boundary bindings (`scripts/bind47b.py`, QC-IMPORT-2 recipe)
The fresh source already has the native signal nets from route.v, so nothing is copied. The script removes only the
313 pinless `pst_*` placeholder BTerms, which leaves the provider as the only driver.

Bindings: 3,683 of 3,683 ports (`bound/bindings.json.gz`, `bound/bind_report.json`):
- 3,369 `t_st_*__clk` -> `ck_<clock_net>`. Each net has a single CKINV Y driver, and the node cell's `clock_from` pin
  sits on that net. 1,997 stages use the Y tap and 1,372 use the A tap (equals the emit). Every binding matches the
  emitted ctree.v assign.
- 313 `pst_*` outputs -> their `<dst_part>/cland_tstart_in` pin.
- `rst_raw_n` -> `rstw_sl_E0_fw_rst_o_0` (driver sl_E0_fw/rst_o_0, 2 ITerms).

Clock cell and ck_* net hashes are unchanged. The remaining BTerms are root and rst_n. source_bound.odb c2b70379.

## 3. Preflight and import
- Preflight (`bound/preflight.json`): READY_FOR_REVIEW, issues {}. That means 0 OBS/keepout/PG hits (gen47 had
  50,020), 0 overlaps, 0 mapping mismatches and 0 unbound ports. Fresh lower OBS: 609,621 rects over 377
  partitions. CHECKED.
- Review crops (`review/review_b1038.png`, `review/review_b0.png`, viewed): provider and clock bodies sit inside the
  holes. The b1038 hole spans a partition seam and is cut from both abstracts. Type-union windows also open in
  neighbour instances, as 12.2a1 intends. Self-review only: PASS-COND, independent GEOM review still owed.
- `apply_cells` (`import/receipt.json`): ALL_MAPPED_CELLS_IMPORTED. CHECKED.
  - 50,020 cells (23,230 FF / 26,790 comb)
  - 100,040 new PG terms
  - 48,673 native cells and 541,054 net records preserved
  - provider.odb 850002a6

## 4. Leaf loads and lower clock access (main tools)
- `provider_clock_loads.py`: ACTUAL_M1_ENDPOINTS_UNROUTED. 23,230 FF CLK terminals on 2,489 unchanged ck_* nets, max
  added fanout 14, 0 cells added. The plan is FF-only, so there are no leaf-driver inverters. The graph is the
  ODB-derived clock connectivity (`access/graph_raw.json`), not the fixed-tree prebuild graph. The fixed-tree graph
  will be extended again in step (b). CHECKED.
- `plan_provider_clock_access.py`: LOWER_ACCESS_GEOMETRY_PASS, 23,230 of 23,230 selected, 0 failed, 12 M3 jogs.
  It was checked against every actual signal pin, OBS and supply pin (`access/access_summary.json`). CHECKED.
  - Caveat: gen47 has no PG plan yet, so no `--reserved-power` was given. Access must be re-qualified jointly with
    the step (b) PG access plan.

## 5. Measured stage proof (`scripts/mk_stage_arr.py`, `run_stage_proof.sh`)
Recipe:
1. Each stage pin arrival is the measured driver-pin arrival (N/M rows) of its bound ck_ driver. Slew is that
   driver's max(rise, fall).
2. main `start_stage_emit proof` on gen47 `proofP` adds 3,369 measured `__st__` taps.
3. main `die_sta_related` runs with DIE-QC-45/49 args and `--count-align` = gen47 `startplanP/bind.json`. Every start
   port is re-timed on the measured stage pins.

- `stproof_pre`, arrivals from DIE-QC-49 grt_TTN/grt_FFN (GRT + planned-NDR RC, PRE-import tree, so no FF loads):

| corner | crossings | worst lo / hi | CA fail | start-skew fail |
|---|---|---|---|---|
| TT | 2,525 | 107.1 / 191.8 | 0 | 0/3681 |
| FF | 2,525 | 101.0 / 292.5 | 0 | 0/3681 |

  Verdict PASS, CHECKED log. TT intra setup +33.19 (0 neg), seam +155.17. Hold is BLOCKED(kits) = UNMEASURED (12.19).
- `stproof_load` (diagnostic, NOT a gate measure; kept as `stproof_load_INVALID/`): same chain on a 50-it GRT of the
  imported DB (`grt_prov.tcl`, NDR RC, `grt_load/`). GRT: 48,297 clock nets, 0 overflow, 4:51 wall, 20 GB.
  Result: COUNT-ALIGN TT worst lo 107.1 fail 0 but start-skew fail 2,711/3,681; FF start-skew fail 2,959/3,681; TT intra setup +32.23.
  Why it is not a measurement [CHECKED `grt_load/clock_layer_census.json`, census_*.json]:
  1. GRT `-clock` M8-M9 is not honoured on clock nets that carry M1 FF CLK pins: 2,480 of 2,489 FF-loaded ck_ nets route
     only on M1-M5 at 1x RC (example ck_n3750: M1-M5). Those stages read 300-820 ps per inverter (pre-import 75-97 ps),
     slew up to 277 ps. The drawn design lands leaves via M7 riser -> M8/M9 NDR, which GRT does not model here.
  2. The arrival readout becomes ambiguous: 26,171 (TT) / 41,876 (FF) ambiguous edge pins vs 0 pre-import.
  The loaded measure needs the drawn fixed prebuild (Route A, step b) or clock DRT + RCX (Route B, gen47ndr).

## Next
- Step (b), Route A: rebuild the 2249 fixed-NDR prebuild inputs for gen47. These are the E1 fixed_wires, the
  cell_windows (use `islands/combined_island_windows`), the census geometry, the clock A/Y stacks, the native M7
  landings and the backbone_native plan. Then run `fixed_tree_provider.py` with `access/plan/clock_loads_access.json`
  and `bound/bindings.json`.
- PG access plan for the 100,040 new PG terms, joint with the clock access.
- Independent GEOM review of the import.
