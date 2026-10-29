# CLK-TOOL-1 (2026-10-28): ot-clk P0 (per-die config replay) + P1 (fail-closed stage-model registry)

Design: CLK-TOOL-0 (claude/clk-tool-0-1028@955de5cf1d, results/clk_tool_0_1028/README.md). Base: origin/main 6a56d58118.
Everything is opt-in. No edit to die_trial.py, to any die plan, or to any die clock run. No gate and no rule change (12.14a).
Labels: CHECKED = run here on the named data; UNCHECKED = not measured by this lane.

## 1. What was built

| file | role |
|---|---|
| `tools/clk/ot_clk.py` | die-agnostic driver: config -> die_trial `kit` argv; `check` / `argv` / `kit` / `replay` / `register`. No die name in code (test). |
| `tools/clk/configs/{qc,s81,kv,hbm,head}.yaml` | one config per die = that die's current die_trial clock build (inputs, stack, top form, region form, residual tools) |
| `tools/clk/configs/s81_go16.yaml` | DRAFT for DIE-S81-18: go15 recipe + registry stage model `inv2_ndr_s81_go15` + early 1.0/1.0 (DIE-S81-17 ASK default) |
| `tools/clk/stage_registry.json` | P1 stage-model table `ot_clk_stage/1`: key (cell, polarity, clock_rc, corners, edges) -> leg/tap coefficients + source + `coeff_sha` |
| `tools/clk/test_ot_clk.py` | 25 tests incl. the mutant; PASS on intel2 python3.14 + PyYAML and in python:3.12 without PyYAML (built-in YAML subset reader, 5 PyYAML-compare tests skip there) CHECKED |
| `tools/clk/replay.sh` | P0 replay in a capped docker container (diagnostic probe, fleet host only) |

Config keys -> die_trial flags: `inputs.{plan,region_map,feed,views}`, `stack.{cell,clock_rc}`, `top.{form,leaf_um,rep_um,
site_legal,site_slide,opts}`, `region.{form: dme|none, dme_mode, only, early.{tt,ff,mode,merge_only}, workers}`,
`stage_model.{entry,corners,edge,coeff_sha}`, `residual.{snake,tap_pad,cell_paths}`. Region sets are lists of names or
bash brace patterns (`c_{E,W}{0..5}_{bf,bn,tf,tn}_{00,01,10,11}` = 192 names, bash order), `all`, or `{all_from_map: true}`.

## 2. P0 replay: does each config reproduce the die's current clock build?

Method: `ot_clk.py replay <die>.yaml` runs MAIN die_trial (6a56d58118) with the config's argv on the event's own inputs, then
compares `clock/tree.json` and `clock/ctree.v` byte-for-byte with the die's reference run. The reference runs used older
die_trial copies (frozen worktrees, e.g. DIE-QC-11 1465eff51c, wt/die-qc21-1028, wt/die-s81-16), so the replay also proves
main is default-identical for each die's flag set. Runs: intel2/intel1 `/srv/opentallas-scratch2/claude/clk-tool-1/replay_<die>`.

| die | reference run (event) | config argv source | replay result |
|---|---|---|---|
| HEAD | intel2 die-head-11/inv/inv2r200 (= g5_r200 = DIE-HEAD-14 base tree) | LAND-HEAD 09:25 line (not scripted) | **ctree.v byte-identical; tree.json identical except `meta.clock_cell`** (CHECKED) |
| KV | intel1 die-kv-15-1028/kit_fb_inv_r150 | results/die_kv_15_1028/kit2.sh fb_inv_r150 inv 150 | **ctree.v byte-identical; tree.json identical except `meta.clock_cell`** (CHECKED) |
| HBM | intel2 die-hbm-10/trial2b/kit | results/die_hbm_1027/hbm10/trial2b/chain.sh | RUNNING (container clktool1-hbm, single-thread like the original ~3.5 h kit) -> collect `replay_hbm/replay.json` |
| QC | intel2 die-qc21-1028/trial14 | results/die_qc21_1028/kit21.sh t13 (stage cal via the registry) | **tree_GENERATED.json + ctree_GENERATED.tcl + ctree.v byte-identical** (non-legacy: stage cal written from registry entry `inv2_ndr_qc_trial13b`; 71 min at host load ~170) (CHECKED). The trial14 `tree.json` itself was later rewritten in place by `clock_body_bays.py` (meta.body_overlay, 36,269 cells moved), so replay compares die_trial's own `*_GENERATED*` copy when present |
| S81 | intel2 die-s81-16/go15/kit | results/die_s81_16_1028/scripts/go15.sh (`--legacy`: stage check FAIL by design) | RUNNING (clktool1-s81, `--legacy --workers 24`; original serial 3:02 h) -> collect `replay_s81/replay.json` |

`meta.clock_cell` is a provenance key that main die_trial writes and the 1465eff51c-era tool did not; nodes, taps, sites,
parents and the netlist are identical. Verdict label: `IDENTICAL_EXCEPT_META`.

P0 findings:
1. **HEAD fb1_lat.json (die-head-3/cmp) is not replayable**: its hard-core `pins_file` is relative into the deleted worktree
   `wt/die-head-3-bind` (reset_tree ResetError, CHECKED, kept in `replay_head_fb1lat_FAIL`). The DIE-HEAD-11 copy
   `g5_r200/plan_rs_fb1.json` (pins via `wt/die-head-1`) reproduces the tree. Same class as the 10-25 frozen-worktree bind
   lesson: plan events that point into worktrees die with the worktree. Recommendation to die owners (no new check): copy
   pin tables into the event directory at the plan event.
2. QC trial15/16 (DIE-QC-23) used the unmerged `--region-dme-snake-cap`; it was rejected, and DIE-QC-24 returns to the
   stock trial14 form, so qc.yaml reproduces trial14.
3. HBM trial2b kit.json has no `clock_cell` key although chain.sh passes `--clock-cell inv2` (see the HBM replay row).

## 3. P1: fail-closed stage model

- Registry entries (CHECKED: coefficients copied from the files, `coeff_sha` recomputed by test):
  - `builtin_bufx24_1x_ladder`: die_trial STAGE_1X_TT (20.8281, 0.013984, 0.00033554), BUFx24, TT, ladder fit (DIE-QC-3).
    die_trial uses it whenever `--region-dme-stage-cal` is absent; in ot-clk it is an ordinary entry, valid only for BUFx24.
  - `inv2_ndr_qc_trial13b`: DIE-QC-21 fit, 12,626 routed legs (results/die_qc21_1028/inv2_stage_cal_trial13b.json).
  - `inv2_ndr_s81_go15`: DIE-S81-17 fit, 16,604 routed legs, rms 7.95 TT / 7.06 FF vs 30.77 / 21.57 for the go15 model
    (claude/die-s81-17-1028@9f3d9adcc0; reproduced by DIE-S81-18's fit_dme_stage_cal.py @9e0f2cfb03).
- `stage_check`: a region form that consumes a stage model (DME) must name an entry; the entry key must equal the stack on
  cell, polarity (buf / inv / inv2 pair), clock_rc, every corner and edge the config asks for; `coeff_sha` must match. No
  implicit default. `kit` exits before calling die_trial on FAIL; `--legacy` only for replays of history.
- Results (CHECKED, `ot_clk.py check`): QC PASS (its own inv2 fit); KV/HBM/HEAD PASS trivially (geometric forms consume no
  stage model; CLK-MODEL-SWEEP-1 shows they still carry 9-34 ps/leg geometric error, which P2/P3 address, not this check);
  **S81 go15 FAIL** ("no stage_model.entry ... BUFx24 1x ladder"), i.e. the check would have stopped the DIE-S81-17 build;
  s81_go16 draft PASS.
- Mutant (test_mutant_stale_bufx24_model_on_inv2_tree_is_rejected): S81 inv2 config pointed at `builtin_bufx24_1x_ladder`
  -> FAIL "stack cell=CKINVDCx16_ASAP7_75t_R but entry ... fitted on cell=BUFx24_ASAP7_75t_R". Further mutants rejected:
  single-inverter polarity, clock_rc 1x, fall edge, FF on the TT-only built-in, hand-edited coefficients, wrong pinned
  coeff_sha, unknown entry.
- Adoption on S81: no duplicate of DIE-S81-18's fitter. New fits enter the registry with
  `ot_clk.py register --cal <fit_dme_stage_cal.py output> --id ... --cell inv2 --clock-rc ndr`. go16 can be built as
  `ot_clk.py kit tools/clk/configs/s81_go16.yaml --out <dir>` once DIE-S81-18 sets the plan path (opt-in; the die owner decides).

## 4. kv_r7 / kv_r8 die_sta_related forks: no live gate uses them (CHECKED)

- `git grep` on origin/main: only `tools/die_plan/kv_r7/{run_mcp.sh,hb_count_r7.py}` and `kv_r8/{sta_b5.sh,hb_count_r8.py}`
  reference `die_sta_related_r7/_r8` (10-26 KV mesh-CPPR experiments). No die owner result script, no autopilot file.
- Fleet: no running process on intel1/intel2/epyc2 matches `die_sta_related_r[78]|kv_r[78]/`; no `.sh` under scratch
  `claude/`, `codex/` or `~/coord/autopilot` modified in the last 48 h calls them (the 3 grep hits were main
  `die_sta_related.py` with `r23`/`r8` in other paths).
- Recommendation: retire the 2 forks + 4 callers in P4 (after release) or earlier as a no-risk delete via ROOT-MERGE.

## 5. Design addendum (COORD 2026-10-28 22:0x): per-region TritonCTS benchmark after P1

A planner sanity check, information only (no gate, rule freeze 12.14a): for each region of a routed die trial, cut the region
into a stand-alone CTS problem and run TritonCTS with the OR-CTS-PROBE-1 settings; if our routed region spread (nominal,
arrival + declared insertion, same GRT RC) is more than 20 ps worse than the best LEGAL TritonCTS variant, flag the region
as a planner defect for the die owner (cause first: stage model -> `calibrate`, then structure). TritonCTS does not replace
the planner. Reuse claude/or-cts-probe-1-1028@76e78b8c01 `results/or_cts_probe_1_1028/scripts/{extract.py,gen.py,cts.tcl,
ours.py,summ.py}`; variants v4 (dist 250 + repair_clock_nets) and v6 (dist 150 + repair). Legality matters: on QC c_W2_bn_01
the repair step put 37-42 buffers inside A0 cores, so a variant with check_placement overlaps is reported but never counts as
"best". Would have caught go15 svc_12 (ours 215.0 vs TritonCTS v4 158.2 TT, CHECKED in OR-CTS-PROBE-1). Cost estimate
(UNCHECKED): CTS 6.6 s per region + GRT; ~400 regions/die -> run on a sample (worst 20 regions by our spread + 20 random).
Planned as P1b: `ot_clk.py bench-cts <config> <routed run> --regions ...` (~0.5 lane-day).

## 6. Next steps

1. ROOT-MERGE this branch (new files only: tools/clk/*, results/clk_tool_1_1028/*).
2. DIE-S81-18: optional go16 via s81_go16.yaml (set plan); registry entry for each new fit via `register`.
3. P1b TritonCTS benchmark (section 5), then P2 one-size-per-level + residual ledger, P3 single entry (CLK-TOOL-0 plan).
