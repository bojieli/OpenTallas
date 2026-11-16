# FABLE-FLOWCLASS-KITPACK-2030: missing inputs and kit packaging

2026-11-15 ~21:15 PST. Read-only review. Basis: every `result.json` under `~/coord/autopilot/kit_wave/*/a*/` of the last 24 h (2,585 attempts), the live `autopilot/kit_wave.json`, runtime `rt/774e46503301/tools/autopilot/{kit_wave,kit_store,src_manifest,export_view,prov_view}.py`, and `tools/die_plan/hard_landing.py` in the QC tree `wt/qc-s29-tree2` (epyc8). Counts are regex buckets over the result text: good to a few percent, not exact.

## 1. Verdict

The fix for this class is already written and is switched on for one die of five. `kit_snap` (content-addressed closed input snapshot, required input absent = stop before any queue wait) is `True` only for `s81_head`. In 24 h HEAD had 3 fails in this class; QC had 682, S81 138, KV 125. The remaining gap is two things nobody built: exported views are not closed (they point back into the lane's build dir), and lane-built cores are registered as host:dir, never published.

## 2. Wasted share (measured)

| window | attempts | FAIL | this class | share of FAIL | wall hours in class |
|---|---|---|---|---|---|
| last 24 h | 2,585 | 2,172 | 948 | 44% (37% of all attempts) | ~257 of ~1,108 failed-attempt hours (23%) |
| last 2.2 h | 97 | 67 | 14 | 21% | 5.9 |

None of the 948 reached placement. By sub-class (24 h, attempts / distinct items / stage):

| sub-class | attempts | items | stage | named example |
|---|---|---|---|---|
| HDL file missing | 454 | ~97 | kit_rtl, kit_topology | 361 x one path: `die-qc-103/treeA/physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_*`; 38 x `rtl/qwen_dv/headprep13/corepub39/...`; 20 x `qfd_dv_redstn2_gsafe.sv` |
| tool module missing | 209 | ~114 | place, gen, kit_topology | `signoff_profile` (KV 66), `ot_store` (QC 19), `core_view_sha` (QC 22) |
| view missing / `core_view_sha` gate | 214 | ~120 | gen, prov_views, kit_topology | S81 `core_view_sha.py line 46 gate` 88; QC `sle_cland_w517_n_s10_1` missing under `epyc10:die-qc-103/rk2` 50; S81 `dsdv_gunit_l1f_ba0` candidate on **epyc4** (terminated host) 8 |
| view points into a build dir | 44 | 12 | gen | 33 x `tl-qcstav2/rk/sta_cland_w1574_e_s26/kits/..._synth0/signoff/signoff.json`; 11 x `die-qc-103/rk2/{sle_cland_w2104_s_s34,sta_cland_w1574_n_s26}/.../signoff.json` |
| stub view | 5 | 1 | gen | `cbn_q00__cldbcda913`: `qc_cland_w515_n_d8_local32_codex/provenance.json` has `export: {}` |
| other missing file | 22 | 9 | prov_views, kit_rtl | `plan_of_record/cores/st_a/sta_cland_w1574_e_s26_pins.json` 17; `sink_bins/hf1c/slw_su_c__cl19bb38ef.json` 3 |

The last 2 h: the 11 "KIT_NOT_SELF_CONTAINED" are all the fourth row (6 items). `slw_st_a_v2__cl9f076a5c` ran attempts 9 to 14 on the same path; that directory exists on epyc2 only, and epyc2 is not in the item's roam hosts (epyc7/8/9/10, intel1), so no attempt could pass. The `rk2` half is already cured: `rk2/.../signoff` is now on all five roam hosts (QC-SRC-CLOSE restage).

Not this class, do not count it here: `sle_ctl__cl372cea1c`, `sle_ctl__cl503337ff`, `slw_st_a_v2__clf4365a62` now fail `hard landing actual child proof failed: shared rst_xn[i]: 8-9 loads` (9 attempts). They got past the missing file and hit a real reset-ring proof failure. Owner: DIE-QC-103 / the cland RTL.

## 3. Root cause in the process

**R1. An input is a host path, not content.** One QC launch spec names five private lane trees by absolute path: `wt/qc-s29-tree2` (src and views), `die-qc-103/treeA` (plan, asbuilt manifest, clock sidecar, HDL), `qc-s28-hf1c/bind/bind_s29q103S4Q3CBQ` (bind out), and through the views `die-qc-103/rk2` and `tl-qcstav2/rk`. Each tree reaches each gen host by a separate hand rsync. Nothing states the whole set, so nothing can check it.

**R2. An exported view is not closed.** `export_view.export()` writes `provenance.src = <kit dir>` and `export.signoff = <abs path>` and copies only lef/lib/pins. At the parent's gen, `hard_landing.capture()` follows those pointers and reads `signoff.json`, `face_guard.json`, `face_guard.py`, `land_slots.json` and the netlist from the child's build dir. The closed form exists (`<view>/landing_evidence/`, which `hard_landing.emit()` prefers), but `export_view` never writes it; `prov_view.carry_landing_evidence` only copies one that is already there. So every cland view dies with the lane dir that built it.

**R3. Five partial mechanisms, each opt-in, each advisory by default.**

| mechanism | what it closes | state today |
|---|---|---|
| `kit_snap` (KIT-FIX-F) | plan, bind, HDL, sidecars; MISSING stops before queue | on: s81_head only |
| `kit_store` (KIT-INPUT-STORE-1) | same, hardlink form | S81, one pattern `ot_s81sl_leaf__t42*` |
| `kit_snap_view_refs: strict` | paths the child views name | on nowhere |
| `src_manifest` (SRC-TREE-1115) | die src tree = sha + overlay | QC spec: `verify` with `src_manifest_hash: ''` = not judged |
| `kit_self_contained: copy` | abs paths left in the finished kit | all dies, but it runs **after** gen |

Every fail in section 2 is at kit_rtl, kit_topology, prov_views or gen. The one check that is on everywhere runs after those stages, on a kit that was never produced.

**R4. Lane-built cores are registered, not published.** `lanes/AUTO-RESIGN.tsv` (119 rows) holds host + dir. `s81p_slice_station__t51_ot_s81_station_t51_native_w` is row 56: signed 11-13, `epyc7:/.../die-s81-85/t51pin/eco_wf_scope21b_1113/i1`, and its parent has waited on "no routed view" since. The view exists only where the lane left it; signed export goes to AGIdock and rtx-pro (archive), which the wave does not read. Candidates still name epyc4. When a file was needed to get past an exists-test, a stub was written (`qc_cland_w515...`, KIT-OPS-3 11-14, `export: {}`), which moved the failure one stage later.

**R5. Detection is late, one file at a time, and retried.** The miss is found on the gen host after ot-run admission and names the first file only (SRC-TREE-1115: one named ROM file hid 398 missing inputs). `HOST_GAP_WHY` treats `KIT_NOT_SELF_CONTAINED` as a host gap and relaunches elsewhere; nothing asks whether any roam host has the path. Result: 361 attempts on one PHY HDL path.

**R6. Tools come from two trees.** The wave runs `rt/<sha>/tools/autopilot` but gen/place import from the die src tree, which predates `signoff_profile`, `ot_store`, `core_view_sha` (209 attempts). Same root as R1: the tool set is a path, not a pinned content.

## 4. Structural fix, and the four proposals assessed

| proposal | verdict | form |
|---|---|---|
| content-addressed input manifest per kit, staging copies every input | **ADOPT, already built** | `kit_snap: true` + `kit_snap_view_refs: strict` on all five dies; snap id is the manifest |
| preflight that resolves every path and refuses with a named list | **ADOPT, at the event, not per item** | F3 |
| automatic view publishing at sign-off for lane-built cores | **ADOPT** | F1 + F4 |
| cleanup guarded by the manifests | **REJECT as a guard on lane trees** | F5: protect one root instead |

**F1. Publish closes the view.** `export_view.export()` runs `hard_landing.capture()` into `<view>/landing_evidence/` and copies `signoff.json` into the view; provenance paths become history, never read. `hard_landing.emit()` loses the follow-the-pointer fallback: no `landing_evidence` = `VIEW_NOT_CLOSED <view>`. Backfill once, on a host that still holds the build dir: epyc2 for `tl-qcstav2/rk/*`, any roam host for `rk2/*`. That alone releases the 12 items of row 4.

**F2. One closed input set per item, all dies.** Turn `kit_snap` on for QC, S81, KV, HBM. Extend the snap closure to what section 2 shows it misses today: the child views with `landing_evidence`, `plan_of_record/cores/*_pins.json`, `sink_bins/*`, every `preferred` HDL path the asbuilt manifest names, and core kits and prep binds (`kit_store_applies` excludes both). Pin the die src tree: adoption writes `src_manifest_hash`, mode `require`. Gen, bind and kit_rtl then read snap paths only.

**F3. Preflight at adoption.** `adopt_guard` builds the snap for every wave row of the event on one host and prints the complete missing list (all paths, grouped by tree), then refuses the switch. One refusal per event replaces N items x M retries. At launch, an item whose snap is absent on a host is `WAIT-INPUT`: no attempt number, no ot-run slot.

**F4. Sign-off publishes.** The sign-off step for `kind=core` rows and for every AUTO-RESIGN.tsv row runs the F1 export into `kit-store/views/<die>/<module>/<lef sha>/`, replicates it to all gen hosts, and the registry row carries module + view sha. `prov_sources` resolves by module + sha in the store, never host:dir. A provenance without `export.signoff` is refused by F3 with the module name; the module then gets an auto core row (WF-1) unless `auto_core_hold` names it **and** its lane is alive. QC `auto_core_hold` lists 7+ cland modules today; check each has a live owner.

**F5. Cleanup protects one root.** OWNER ruling KW-FIX-45 stands: a job that needs a file outside its folder is a kit fault. A manifest-guarded cleanup would keep the path model alive and add a second thing to keep in sync. After F2, `kit-store/` (snaps, blobs, views) is the only protected input root, with its existing referenced-set GC; lane trees are free to delete. Interim, per die until its `kit_snap` is on: CLEAN-ALL keeps every absolute path in that die's `kit_wave.json` block (src, plan, `kit_rtl.*`, `type_args`, `item_inputs`) and never runs `rsync --delete` into a plan dir.

**F6. No retry on a missing input.** A fail in this class sets the item to `HOLD-INPUT` keyed on the path; release is a probe that the path (or snap) resolves on a roam host, not a timer. Remove `KIT_NOT_SELF_CONTAINED` from `HOST_GAP_WHY` when no roam host holds the path. This is the same key FLOW-HEALTH-1 was given in r216; one implementation.

Order: F1 backfill and F6 today (hours); F2 per die with a 3-row smoke each, QC first; F3 and F4 next; F5 follows F2 per die.

## 5. Owners

| item | lane |
|---|---|
| QC now: F1 backfill of `sta_cland_w1574_e_s26` from epyc2 and the `rk2` views; hold the 4 items below until done; restage `qwen_missing_phy/nface_tall_1017`, `corepub39`, `qfd_dv_redstn2_gsafe.sv`, `cores/st_a/*_pins.json`, `sink_bins/hf1c` | QC-SRC-CLOSE-1115 |
| F1, F2 closure coverage, F3, F4 code; one branch, all dies | **new Sonnet lane KITPACK-CLOSE-1115** |
| flip `kit_snap` / `kit_snap_view_refs` / `src_manifest_hash` per die after the smoke | KIT-OPS-5 |
| F6 | FLOW-HEALTH-1 (already holds the r216 retry key) |
| F5 | CLEAN-ALL-1115 |
| R6 tool modules (`signoff_profile`, `ot_store`, `core_view_sha`) | TOOLS-CONVERGE-1115 |
| publish t51 native_w and the QC n9 cores through F4 (hand-run the F1 export today) | S81-CORES-1115, QC-SC-ROWS-1115 |
| a signed build of `qc_cland_w515_n_d8_local32_codex` (stub today) | DIE-QC-103 names the lane |

KIT-OPS-5 is not the code owner: it carries HEAD adoption and went 8 h without a post today.

## 6. Stop list

1. Stop relaunching `slw_st_a_v2__cl9f076a5c`, `sle_st_a_v2__pv30dda31f`, `sle_st_a_v2__pv4242de79` until the F1 backfill; their input is on epyc2 only.
2. Stop relaunching `cbn_q00__cldbcda913`; it needs a signed cland w515 view, not a retry.
3. Stop writing stub `provenance.json` or placeholder views to pass an exists-test.
4. Stop single-file or single-dir rsync after each first miss. Restage from the full list (F3) or not at all.
5. Stop adding per-path self-heals (`sync_item_inputs`, `view_sync_missing`, KW-FIX-45, KW-FIX-46, FIX-SELFCONT: five so far, class still 44% of fails).
6. Stop registering lane-built cores as host:dir, and stop accepting candidates on epyc4/5/6.
7. Stop `rsync --delete` into any `plan_of_record` or `runtime` dir.
8. Stop counting the `rst_xn` shared-load proof failure as a missing input.
9. Stop calling a restage done on `src_incomplete: {}`; done = the snap of every row builds on every roam host.

## 7. Not verified

- The six tables come from result text, not from the wave's own class field; sub-class boundaries (HDL vs other file) can shift by a few attempts.
- Wall hours are attempt start to result write, so they include queue wait.
- I did not test that `kit_snap` builds cleanly for QC/S81/KV/HBM rows; HEAD is the only proof. The smoke in F2 is the test.
- I did not read CLEAN-ALL-1115's current rules, nor confirm QC-SRC-CLOSE-1115 is alive (it has no posts file).
