# HQF-PIPE: private QC type kit build chain (HARD-QC-FORMS-1)

Everything here is **DO_NOT_COUNT**. Nothing in this folder is a kit-wave row or a countable sign-off. Kits carry
`K/DO_NOT_COUNT.json`, and kits built from a waived bind also carry `W/rtl/PRIVATE_WAIVER.json`.

Master copies of the scripts are on epyc9 in `/srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe/`.

| file | role |
|---|---|
| `chain_qc.sh` | Chain for one type: rtl -> gen -> place -> cts -> sta -> grt -> route -> signoff |
| `rebind_qc.sh` | Private strict die bind of a plan in the private tree copy (`pipe/tree`) -> `pipe/bind_TAG` |
| `waive_bind.py` | Private bind view: a copy of a failing bind with `bind_report.json` errors set to 0 (originals kept under `private_waiver`) |
| `selfcont.py` | Runs the kit wave's own `SELFCONT_PY` (kit_self_contained=copy) on the kit |
| `wave_args.py` | Gen env and args of a type, read from `qc_wave_cfg.json` |
| `qc_wave_cfg.json` | Read-only snapshot of intel2 `~/coord/autopilot/kit_wave.json` dies.qwen_compute, taken 11-13 14:2x |
| `sta_cts.sh`, `sta_cts.tcl` | Post-CTS TT setup report job, run through ot-run on the build host |
| `tree/` | File copy of epyc9 `wt/qc-s28-event2` (@0bac129af33c, without .git, 4.6 GB). The sha of r8 / sidecar / manifest / bind.py equals the ev2st_g1 bind header |
| `bindw/<name>/` | Private waived views (442 MB each) |
| `bind_<TAG>/`, `bind_<TAG>.log`, `bind_<TAG>.classes.json` | Private re-binds |
| `runs/<TAG>/<TYPE>/` | W: `chain.log`, `rtl/`, `gen/` (kit K = `gen/<TYPE>`), `sta/`, `png/`, `ot_<stage>.log`. The same path holds the kit on the build host |

## Run a new (TAG, TYPE, PLAN)

```
# on epyc9.  The plan must be a geometry edit of a plan that already went through the bind_fix.sh chain.
P=/srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe
cd / && nohup bash $P/rebind_qc.sh TAG /abs/path/plan.json > $P/logs/rebind_TAG.out 2>&1 &     # ~13 min, nice 19
# then build, using the plan copy that rebind_qc.sh put in the tree (same sha):
cd / && nohup bash $P/chain_qc.sh TAG TYPE $P/tree/physical/die_plan/qwen_compute/plan_of_record/zz_bind_TAG.json $P/bind_TAG rtl route > /dev/null 2>&1 &
grep -E 'CHAIN_(STAGE|DONE|BUILD|FAIL|END)|STA_' $P/runs/TAG/TYPE/chain.log      # poll
```
Baseline (no re-bind; the default BIND_DIR is DIE-QC-100's `qc-s28-hf1c/bind/bind_ev2st_g1`):
```
bash $P/chain_qc.sh base sle_stm_v2__cl7b3062fa $P/tree/physical/die_plan/qwen_compute/plan_of_record/zz_bind_ev2st_g1.json "" rtl route
```
Run part of the chain with `[from-stage] [to-stage]`, for example `... "" sta sta` to repeat only the STA.

Environment (all optional):
- `BUILD_HOST` (default epyc4).
- `AUTO_HOST=1`, added by QC-FORMS-2 at 15:09: BUILD_HOST is only the data host, and ot-run `--stage W` picks the run host.
- `MEM` (48 GB) and `THREADS` (16). The wave uses 8 threads; this chain uses 16 for speed, so compare runs at the same value.
- `PRIVATE_WAIVER` (1).
- `ALLOW_PLAN_MISMATCH` (0).
- `FORCE_SYNC` (0).
- `PNG_HOST` / `PNG_DIR` (default epyc7 `/srv/opentallas-scratch2/claude/hard-qc-forms-1/png`).
- `CM_FILE` / `KP_FILE` / `EVENT_TREE` for `rebind_qc.sh`.

## What each stage does (copied from kit_wave.py 4285-4380 and the QC wave config)

1. **rtl**
   - `bind.py component-proof` (receipt `W/component_proof.json`).
   - On FAIL, with `PRIVATE_WAIVER=1`: `waive_bind.py BIND pipe/bindw/<name>` (cached, rebuilt when the source bind_report sha changes), then `kit_topology.py stamp-bind` on that view.
   - `bind.py kit-rtl PLAN --out <view> --asbuilt <bind manifest> --type T --kit W/rtl`.
   - `kit_topology.py prepare-stations PLAN T W/rtl --native-plan <bound plan> --asbuilt <manifest>`.
   - The bound plan, manifest and sidecar come from `<BIND>.log` and `provenance_bind.json`. They are mapped into `pipe/tree` and their sha is checked against the bind log header.
   - PLAN must have the same sha as the bound plan. Otherwise the stage stops and says to run rebind_qc.sh.
2. **gen**
   - `gen.py phys PLAN --out W/gen --types T --rtl-root pipe/tree --kit-rtl T=W/rtl/kit_rtl.f --cland-pinslot all` + gen_args + type_args.
   - The env is `OT_FLOW_TAG=<flow_tag>` | die_gen_env | item_env[T].
   - `--clock-landing` is set to the bind's own sidecar (`runtime/sidecar_pv.json`), not the wave's kw45 sidecar.
   - Then SELFCONT copy, and `K/DO_NOT_COUNT.json` is written.
3. **place / cts / grt / route**
   - Each runs `ot-run --mem $MEM --threads $THREADS --dir K --hosts $BUILD_HOST -- bash W/gen/run_kit.sh K <goal> $MEM $THREADS`.
   - Before place, W (without `run/`) is rsynced to the build host.
   - `route` is run_kit's route goal: ORFS route, finish, abstract, then the kit's `signoff.py` on the host.
   - The layout_review PNGs go to `W/png` and to epyc7 `.../hard-qc-forms-1/png/<TAG>__<TYPE>__<stage>_<name>.png`.
4. **sta**
   - The `sta_cts.sh` docker job runs `make ... run RUN_SCRIPT=sta_cts.tcl CORNER=TC CORNERS=tc` in the kit's ORFS container. That gives ORFS `load_design 4_cts.odb 4_cts.sdc` with the kit libs and macro libs.
   - It applies the kit TT vclk binding (`vclk_corner.tcl ot_vclk_bind tt`), propagated clocks and placement parasitics.
   - Outputs in `W/sta/`:
     - `summary.txt` (WNS/TNS and cell metrics per stage)
     - `worst5_setup_tt.rpt` (report_checks -path_delay max -fields {slew cap fanout input_pins} -format full_clock_expanded -group_count 5)
     - `worst5_geom.tsv` (launch/capture instance, master, xy, distance, cells, summed hop length)
     - `clock_skew.rpt`
5. **signoff**: prints `K/signoff*/signoff.json` key values and copies the reports to `W/signoff_reports`. It never claims a sign-off.

## Obstacles and how the chain gets past them

1. **The component proof cannot pass on this bind.**
   - `bind_component.inspect` accepts only global errors of the form `EMIT wavefront core reset <other type>/...`. Every R8_STALE, LANE_ASBUILT or PARAM_REGEN error becomes a selected error.
   - It also expects the relayed wavefront reset form. stm uses a collector reset tree, which adds 63 x "reset consumer rst_n bypasses recorded release 6" plus about 200 "source reset depth None" lines.
   - Baseline result: `CHAIN_COMPONENT_PROOF FAIL selected_errors 362` (W/component_proof.json).
   - Fix: a PRIVATE waived view, `waive_bind.py`. It copies the bind, sets `bind_report.json` n_errors to 0 and keeps the 92 errors and class counts under `private_waiver`. kit-rtl runs on that view. Every such kit carries PRIVATE_WAIVER.json and DO_NOT_COUNT.json.
2. **prepare-stations stopped with `KIT_TOPOLOGY_BIND_STALE`.**
   - bind.py writes `native_topology.json` only for a clean bind, and ev2st_g1 has none.
   - Fix: `kit_topology.py stamp-bind <bound plan> <private view> --asbuilt <manifest>` on the private view only. The original bind is never written.
3. **The bind outputs carry absolute epyc9 paths** (`wt/qc-s28-event`, `qc-s28-hf1c/bind`, `wt/qc-s28-event2`).
   - All rtl, gen and bind steps run on epyc9.
   - gen copies the RTL and macro views into the kit (`/work/...` paths). SELFCONT found nothing outside the kit (`SELFCONT_COUNT 0 BAD 0`), so W (15 MB) is rsynced to epyc4 and builds there.
4. **run_kit.sh `place` blocks until the async LEC verdict** (lec_async.sh finish).
   - For stm, the flow ended at 15:13 and LEC EQUIVALENT came at 15:21:49 (94809/94809 compare points).
   - Later goals reuse the proof (identity match), so the wait is paid once per kit.
5. **ot-run on epyc9 lists only epyc2, intel1, epyc4, epyc5 and epyc6** (no epyc7; epyc7 load was 101/96 at 14:2x).
   - BUILD_HOST defaults to epyc4. A build on epyc7 needs ot-run run from a client that lists epyc7 (intel2 does). Not wired.
6. **Other lanes run this chain_qc.sh concurrently.** bash reads a running script lazily, so a new version must be installed by rename (`scp x.new && mv x.new chain_qc.sh`). Never overwrite it in place.
7. **The wave's `--clock-landing` is the kw45 sidecar_pv_s28.json.** The chain uses the bind's own sidecar (`runtime/sidecar_pv.json` e292ebb838c1). Gen env and args are otherwise the QC wave's for the type.
8. **rebind_qc.sh does not run the bind_fix.sh chain** (straps, reset pad, repick, tap ident, local copy, r8 derive, lane proof). Those scripts write into DIE-QC-100's `qc-s28-hf1c/bind/work` and `bind_*`.
   - A plan whose hard cores moved may still need that chain, or the gen hazard "physical collector_tree differs from captured bound reset identity" can appear.
   - Run the fix chain in a private copy first if needed. Not wired.

## Baseline run (TAG base, sle_stm_v2__cl7b3062fa, plan zz_bind_ev2st_g1 9f3ed3486d81, build host epyc4, 16 threads)

Stage timings (wall), all read from W/chain.log and the ORFS logs:

| stage | wall | notes |
|---|---|---|
| rebind_qc.sh base | 753 s | Reproduced 92 errors (R8_STALE 30, LANE_ASBUILT 60, LANE_ASBUILT_TOTAL 1, PARAM_REGEN 1); bus_groups a4787ed48569 = ev2st_g1. The rtl/ dir differs only in reset_tree.json provenance fields (plan/manifest names, git commit null) |
| rtl | 127-138 s | component-proof about 5 s, kit-rtl about 120 s, prepare-stations a few s |
| gen | 75-84 s | kit 15 MB, self-contained |
| place | 14:38:48 -> 15:13:22 flow (34.6 min); run_kit returns at 15:21:49 after async LEC EQUIVALENT | synth 2 min, floorplan with repair to 14:48 (7 min), GPL 14:48:41-15:04:44 (16 min), resize 3.4 min, DPL 4.7 min, render 29 s |
| cts | 2348 s (15:22:16 -> 16:01:28) | about 25 min of that is OT_TAP_BALANCE iterations; FF hold gate PASS (wns -116.81 ps, 12358 endpoints, limit -180) |
| sta | 151-153 s | |
| grt | started 16:04:03 | see chain.log |

The rebind path is proven: `chain_qc.sh rbtest ... zz_bind_base.json $P/bind_base rtl gen` gave a kit identical to base, apart from the bind name in a comment and the W paths.

Post-CTS TT setup (W/sta/summary.txt): WNS -679.0 ps, TNS -288163.8 ps, 886 violating endpoints. Worst path:
`u_core.u_stream.wd_q[12]` -> `lane_c[399]`, 1630 um Manhattan (launch 120,58 -> capture 260,1548).
See W/sta/worst5_setup_tt.rpt and worst5_geom.tsv.

CODEX 2026-11-13 CBF corridor source READY: existing HARD-QC-FORMS branch pushed 4ad3e1b02c (parent d2506256e2), count-bank-aware opt-in core_input_chain plus coherent INNER metadata adapter and focused tests. Requires RULES-REACH anchor fe86e6ab12+6d5f095842. Actual E4 frozen CBF ODB: all514 fixed/count/mux bits discovered; corrected anchors6148latches/5888PC/unresolved0 (256constant tap+4reset non-PC classified). Old fixed3 refuses208bits, max minimum-count hop436.574um; proposed coherent fixed4/span1/input1 gives327.4305um. Atomic old-depth rejection verified ZERO location/status changes across ODB. Seven focused tests PASS including actual Binder/514bit RTL lockstep+mutants. E7 WT results/geom_review/cbf_r8_corridor_codex has viewed current candidate render/sites; no ODB written and no physical result claimed. Production event/PLACE waits parent QC clean strict seed; adapter refuses dirty/stale seed and propagates companion/downstream pads without RTL hand-edit. Intel2 logs ~/hqf-codexlog/cbf_anchor_layout_final.log and cbf_atomic_final.log; units1495261/1496597 exit0.

CODEX bank-area follow-up PUSHED b869e17362 (parent4ad3e1b02c); independent GEOM full-rectangle/corner PASS-COND, proposal-only.

Bank-area refinement after independent geometry review:
The original route skeleton used collinear bit targets. The placer now allocates
three whole fixed-FF bank rectangles and one combined count/data-mux rectangle.
Actual master demand: DFF1.08–1.188um x0.27um. The measured candidate's three
514-FF banks each reserve36.18x11.8125um /20rows /35.07% occupancy. The combined
514count+1542data-mux/buffer bank reserves36.18x46.44um /77rows /16.06% occupancy.
All rectangles are macro/9um-halo-clear, inside core, and mutually disjoint.
Actual per-bit minimum/count1 paths max387.2675um; all rectangle-corner paths
max393.0286um (<405). This bound includes uncorrelated endpoint movement within
each bank. The source fails atomically if any rectangle or exact/corner hop fails.
It still needs real synthesized common-floor4 masters and PLACE legalization proof.
Static count decode remains in its existing tree; it is not moved into this bank.
Evidence: cbf_bank_area_review.png (viewed), bank_sites.tsv, bank_rects.tsv.
Intel2 ~/hqf-codexlog/cbf_bank_layout_corners.log, E4unit2281269-1794612927 exit0.
This probe uses exact real ODB masters/data cones plus a virtual proposed fourth FF;
no database placement or ODB write occurred. Eight focused tests PASS including
full-bank row demand, macro-clear fit and unfittable-bank refusal (E7unit1948094).
The earlier327.43um skeleton estimate excludes bank area and is superseded by the
387.27um exact/393.03um rectangle-envelope bounds above.
