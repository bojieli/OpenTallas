# CLK-TOOL-2 (2026-10-28): HEAD event replay, P1b TritonCTS region benchmark, kv_r7/r8 STA fork retirement

Base: claude/clk-tool-1-1028@8ad34ae837 (QC + S81 replays byte-identical) merged with origin/main b6fd7043d2.
Everything is opt-in: new files under tools/clk plus 6 deleted unused fork files. No change to die_trial.py, any die plan or
any die clock run. No gate and no rule change (12.14a). CHECKED = run here on the named data; UNCHECKED = not measured.

## 1. P0 replay status (README sec 2 of CLK-TOOL-1)

| die | result |
|---|---|
| HEAD | **real event plan now replays**: `head.yaml` = die-head-3/cmp/fb1_lat.json + `inputs.pins_rebase` -> ctree.v byte-identical, tree.json identical except `meta.clock_cell` (CHECKED, `replay_head_fb1.json`) |
| KV | byte-identical ctree.v, tree.json except `meta.clock_cell` (CLK-TOOL-1, CHECKED) |
| QC | byte-identical (CLK-TOOL-1 @39f2f953fd, CHECKED) |
| S81 | byte-identical, legacy (stage check FAIL recorded) (CLK-TOOL-1 @8ad34ae837, CHECKED) |
| HBM | still RUNNING: docker `clktool1-hbm` on intel2 (from wt/clk-tool-1, started 22:06, single-thread like the ~3.5 h original; 1:16 h CPU at 23:2x). Collect `/srv/opentallas-scratch2/claude/clk-tool-1/replay_hbm/replay.json` |

HEAD `meta.clock_cell` is a provenance key main die_trial writes and the 1465eff51c-era tool did not (the reference dir has
no `*_GENERATED` copy); nodes, taps, sites, parents and the netlist are identical. Making it byte-identical would need a
die_trial edit, which this lane does not make.

`inputs.pins_rebase` (ot_clk.py `rebase_plan`): fb1_lat.json's hard-core `pins_file` points into the deleted worktree
`wt/die-head-3-bind`. The replay writes a plan copy beside the kit with each `pins_file` rewritten onto the pin table
committed in this repo (`physical/die_plan/s81_head/cores/elem{A,B}_pins.json`, blob-identical to the wt/die-head-1 copy
DIE-HEAD-11 used, CHECKED by git hash-object). It refuses a missing file, a path outside the repo, a pins_file not under
the declared prefix, and a plan with a `die_io.json` sidecar (a moved copy would lose it); the original plan sha and the
rewritten files (sha) go into `ot_clk_argv.json` / `replay.json`. The identical tree proves the deleted worktree's pin
tables equal the committed ones for this tree. 3 new tests.

## 2. P1b: per-region TritonCTS benchmark (`tools/clk/bench_cts.py`, INFO only)

`bench_cts.py prep|run|summ|all --plan P --tree tree.json --arr-tt A --arr-ff A --region R [--region-map M] --out D`.
Generalises OR-CTS-PROBE-1's hand-cut scripts (@76e78b8c01) to any die/region, no die name in the code (test):
- region = taps of the partitions mapped to R (`part_region`), else of partition R; root = lowest common node of those taps
  in OUR tree; declared insertion per tap from the shared plan model (`schema.core_taps` / `core_tap_insertion_ps`, others
  `common_latency_ps`), so core pins carry (core insertion - common latency) as liberty max/min_clock_tree_path;
- hard cores = CLASS BLOCK macros at their die-frame outline (plan `to_die`, any orient), OBS M1-M6;
- TritonCTS variants v4 (dist 250 + repair_clock_nets) and v6 (dist 150 + repair) in openroad/orfs:asap7lock (16 GB cap),
  TT builds, FF re-times; `tools/clk/bench_cts/cts.tcl` = the probe's cts.tcl with renamed sink files;
- a variant is LEGAL only if check_placement passes and no clock buffer lies inside a hard-core outline;
- verdict: PLANNER_DEFECT if our routed spread (arrival + declared, nominal, GRT RC) exceeds the best legal variant by
  > 20 ps at TT or FF; OK otherwise; NO_LEGAL_TRITONCTS if no variant is legal (nothing to compare).

Results (CHECKED, runs intel2 `/srv/opentallas-scratch2/claude/clk-tool-2/bench/*`, copies in `bench/`):

| region (routed run) | ours TT / FF ps | v4 TT / FF | v6 TT / FF | legality | verdict |
|---|---|---|---|---|---|
| S81 svc_12 (go15) | 215.0 / 211.4 | 158.2 / 136.0 | 168.4 / 145.9 | both legal | **PLANNER_DEFECT** (+56.8 TT / +75.4 FF vs v4) |
| QC c_W2_bn_01 (trial14) | 130.9 / 127.7 | 290.1 / 223.1 | 233.0 / 180.0 | 42 / 37 buffers inside A0 cores, check_placement FAIL | NO_LEGAL_TRITONCTS (ours already beats both illegal trees) |

Every number equals the OR-CTS-PROBE-1 table (independent reproduction through the new generic extractor), and the
render `results/or_cts_probe_1_1028/qc_v6.png` (viewed) shows the v6 buffers inside the grey A0 outlines. The S81 flag is
the known go15 defect (uncalibrated BUFx24 stage model on an inv2 tree, DIE-S81-17), which the P1 stage check already
refuses; DIE-S81-18 go16 should be benchmarked on the same region to close it. Cost: ~2-3 min wall per region for 2
variants x 2 corners (CTS ~6 s; host load ~90). 4 tests (`tools/clk/test_bench_cts.py`).

## 3. kv_r7 / kv_r8 die_sta_related forks retired

Deleted `tools/die_plan/kv_r7/{die_sta_related_r7.py,hb_count_r7.py,run_mcp.sh}` and
`tools/die_plan/kv_r8/{die_sta_related_r8.py,hb_count_r8.py,sta_b5.sh}` (1087 lines). One more grep on origin/main
b6fd7043d2 (CHECKED): the only references were these files themselves; `kv_r7/mesh_cppr.py` names the fork in a docstring
only; `explicit_mesh_signoff.py` and kv_r17/r18/s81_pd9 use `kv_r7/qc_clk_mesh2.py` / `kv_mesh_rec.py`, which stay. No
running process on intel1/intel2/epyc2; the only < 48 h `.sh` hits on scratch are whole-tools snapshot copies
(hbm-streets2-1027/tools_snap_die_plan, codex-head-landing-1410/tools), not callers. History stays in git and in
results/clock_kv_r8.

## 4. Tests
`tools/clk/`: 32 PASS in python:3.12 + PyYAML (28 ot_clk incl. CLK-TOOL-1's 25, 4 bench_cts). CHECKED.

## 5. Next
1. Collect the HBM replay (sec 1) and add its row.
2. Run bench_cts on DIE-S81-18 go16 svc_12 once routed (expect OK if the stage cal holds) and on a sample per die
   (worst 20 regions by our spread + 20 random) at each die's next routed trial.
3. P2 one-size-per-level + residual ledger, P3 single entry (CLK-TOOL-0 plan).
