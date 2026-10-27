# QC-KITS-1 (2026-10-27): QC partition-type work list against the pending plan event

Lane QC-KITS-1 owns the Qwen compute (QC) partition-type kits through sign-off. It also tracks the unsigned QC hard cores.

Label meanings: CHECKED = recomputed here from the data. UNCHECKED = taken from another lane's output.

## Inputs (read-only)

| input | sha | what it is |
|---|---|---|
| main QC plan | 54a1aeb5 | physical/die_plan/qwen_compute/die_plan.json, 68 types |
| candidate_oneqc0733 | e4829ce2 | base of the 43.2 delta, 88 types; epyc2 qc-mesh-r17/pkg/inputs |
| plan_d43 | f2c91d03 | results/qc_clk_mesh3/r17/plan_delta/plan_d43.json.gz, from claude/qc-mesh-r18-1027@a9ef417d20 |
| d43b top-tree island windows | 0fb327fa | epyc2 qc-mesh-r17/pkg/build/basekit/island_windows.json |
| R18 die STA, worst seam pairs | - | results/qc_clk_mesh3/r18/runs/f64/sta_cv_die_sta_related.json |

## Outputs

- `qc_kits_worklist.py`: the diff script. Running it writes `worklist.tsv` (88 rows, critical types first) and `worklist_summary.json`.
- `hardcores.tsv`: the 9 QC hard-core modules, with sign-off state, blocker and owner lane.
- `bind_d43_recipe.sh`: the strict-bind command, ready for the moment plan_d43 is adopted.

## Findings (all CHECKED unless marked)

1. **0 of the 68 main types are untouched by the plan event.**
   - 55 main types change content (`clock` + `cells`; 26 of them also `contents`/`buses`/`internal_stations`).
   - The other 13 main types are split into 33 cohort classes (`__cl*`, `_e2`, `_v1r`). Cohort classes are landing classes.
   - Taken alone, the d43 delta changes no type: partition_types and ports are byte-identical to candidate_oneqc0733, and only origins and channels move.
   - The plan event as a whole (ONEQC candidate + d43 + clock islands) touches every type. So under "kits skip types the delta changes", **the work list is empty**.
2. **plan_d43.json is not kit-ready.**
   - The d43b top-tree cells sit in 66 partition types, 8064 instance windows in all. For every one of those 66 types, the windows are absent from that type's `clock.die_islands_um` (0 overlap).
   - 0 types carry `clock.reserved_sites_um`.
   - gen_phys reserves only those two keys (gen_phys.py die_islands_tcl / reserved_sites_tcl). A kit cut from plan_d43 today would therefore place logic on the die clock-tree sites.
   - R17 already says this: "contents NOT re-cut".
   - The adopted plan must re-cut the islands from the final (R19) tree.
3. **12.7c:** neither plan carries `master_plan`, and no QC master-plan slices exist. A sign-off kit would have no frozen slice to consume.
4. **S81 BLOCKER A will hit 9 QC types.** These types have clock-kind landing-contract pins, so landing_contract.sdc emits `remove_from_collection`, `create_generated_clock` and `set_max/min_delay -ignore_clock_latency`, all of which sdc_lint rejects. The types are:
   - sle_fe_v1__clad8c146b, sle_fw_v1__cl3b7cacba, sle_fw_v2__clf90441df, sle_su_l1__cl15735621
   - slw_fe_v1__cl8ba3358f, slw_fe_v2__cle5354d4d, slw_fw_v1__cl82aac3aa, slw_su_l0__cl0cf5548e, slw_su_l1__cl8312485b

   Another 13 types have ctl-only contracts. Their SDC is unchanged.
5. **S81 BLOCKER B applies to every QC type.** Kit RTL comes from `bind.py kit-rtl` on the plan-event bind, which waits for QC.BIND.
6. **Critical types**, the seam pairs named in R18:
   - sle_hc0 (sl_E0_hc0)
   - cbn_q00 (c_E0_tn_00)
   - slw_su_c__cl77ab230a (sl_W1_su_c)
   - cbx_q10 (c_W1_bn_10)
   - slw_su_c__clbb0c543d and slw_su_l1__cl8312485b (the core-view FAIL pair)

   All six are touched. Their HB4 hold-buffer pushdown also depends on the R19 rebalance (R18 residual 1.30 M cells, UNCHECKED).
