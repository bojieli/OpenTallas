# FABLE-FLOWCLASS-TOOLSKEW-2030: tool and source skew class (2026-11-15 20:45 PST)

Lane: Fable review, read-only. Implements: TOOLS-CONVERGE-1115 (Sonnet). Cc KIT-OPS-5, MERGE-QUEUE-1, PLAN-GATE-PRE-1115, FLOW-HEALTH-1, die owners.

MEASURED = read by me on intel2 / epyc7 tonight. POSTED = taken from a lane post, not re-measured.

## 0. Summary

1. The die trees are not "main + plan". They are loose directories (no .git, no manifest, writable, hardlinked) that five different writers change file by file. Every failure of this class today is two files of different vintages in one tree.
2. Almost all of the 227 differing modules are stale copies, not features (POSTED, TOOLS-CONVERGE 20:28: real die edits are S81 11, KV 5, HEAD 13, QC 9). So convergence is a rebuild from main plus about 38 modules to reconcile, not a 227-module merge.
3. The S81 60-of-60 class is already fixed on main. MEASURED: main `sdc_lint.py` (rt c34f6a980b1e) reads `tap_offset_ps` (R-CLOCK-7 lines 490, 929-952); the S81 B6gE tree copy has 0 mentions of "offset", is dated 11-13 04:28 UTC and has 56 hard links; the tree `gen_phys.py` (dated 11-15 18:09 UTC) writes the offset lines (l.1342-1345). One half of a main feature was copied into the tree.
4. The guard that would have stopped this exists and is not armed: `src_manifest.py` (SRC-TREE-1115) is on main, but MEASURED 0 of 5 live trees carry `.src-manifest.json`, and the default policy `verify` lets a tree without a manifest through.
5. Target: a wave tree = `git archive` of one main sha + a data-only overlay (plan, as-built, rows, generated RTL), published read-only with a manifest; a tool fix reaches a die only as a new sha -> new tree -> smoke -> pointer switch. KV is one step away from this today (c1), S81 next at G3b, then QC, then HEAD.

## 1. Root cause in the process

### 1.1 Why die trees carry tool copies at all

- By design the wave runs gen and bind from the die tree, not from rt. `ot-src-refresh` docstring (MEASURED): "Kit generation and plan binds read SRC/tools/die_plan ... of each die's own source tree, never the pinned rt/current tree". `kit_wave.py` l.5912 and l.5947 run `cd {src} && python3 tools/die_plan/bind.py ...`.
- A plan event needs tool behaviour that main does not have yet (a new schema key, a new SDC form). The merge gate was slow (POSTED: 88 min behind a serial gate at 14:35), so the die owner edits the tools next to the plan and binds there. The feature lives in the tree, not on a branch.
- The plan of record is not on main on any die (POSTED, census section 3 item 1). So main is never run against the plan the wave builds, owners have no proof that main works on their plan, and they keep the tree.

### 1.2 How the trees drift: five writers, all per file

| # | writer | evidence (MEASURED unless marked) | effect |
|---|---|---|---|
| 1 | Event chain by hard-link copy | S81: `chainB6e_92.sh` l.5 `cp -al ovl_b6d ovl_b6e`; `bandtap_compose.sh` l.7 `cp -a tools_<TAG>` + `cp -al physical`; private dirs tools_B6gE, tools_B6gF, tools_BANDTAP, 2, 3. B6gE `schema.py` 22 links, `sdc_lint.py` 56 links. Tree base = `git archive` of main 7073a6b4 from 11-13 04:46 (KITOPS1_OVERLAY.txt) | each event inherits the last tree; one write changes up to 56 trees |
| 2 | `ot-src-refresh` daily 06:00 (timer active, next run 11-16 06:00) | QC tree 24 log lines, HEAD tree 167; REPLACE when the copy equals an older main version, 3-way merge or keep when it is a local edit | a file the owner edited stays old, its neighbours move to main: mixed vintages by construction |
| 3 | Hand copy of single files and patches | KV 7u: `gen_phys.py` "main copy from 15:15" on the tree `schema.py` of 11-14 (POSTED KITRTL-FAIL 17:32); WAVE-PREPNR patch "KIT-OPS-5 please copy+mv into each die src"; COORD r207 fixed it in place in 3 trees x 5 hosts; KITOPS1_OVERLAY.txt hunks | no smoke, no record of which sha a file is |
| 4 | The wave itself | `kit_wave.py` l.5922-5946: `kit_tools` = tree `tools/die_plan` + main modules the tree lacks (`rsync --ignore-existing`) + main `bind.py` and `param_wrap.py`; l.5956 retries with the tree bind on an API error | a third and a fourth combination that nobody tested; this is the `--src-tree` class |
| 5 | Bind overlays kept apart from the tree | S81 `ovl_b6E` without `band_fixed_um` / `band_tap_windows_um` (POSTED, 17 G0 errors) | compose tools and bind tools of different vintages |

### 1.3 Why nothing stopped it

- No tree has an identity: no .git, no manifest (0 of 5: S81 B6gE/src, KV 7u, KV 7u_c1, HEAD c327, QC qc-s29-tree2), all writable.
- `src_manifest` policy default `verify` = "a tree without a manifest is noted". The first real switch never happened (pilot tree only).
- The checks added today are heuristics on symptoms: flag-level `--help` smoke, AST arity (1 false positive on KV c1: `sys.path.insert(tools/s81_head)`), API_SKEW regex. None compares bytes to one sha.
- The merge gate tests main on main's own fixtures, not on the four plans of record.

## 2. Target architecture

### 2.1 Three things, three owners of change

| thing | content | changes by | lives in |
|---|---|---|---|
| TOOLS | tools/, physical/common_flow, rtl/lib, rtl/common (the ot-src-refresh scope) + tools/autopilot | merge to main only | rt/<sha>, already on all hosts with `<sha>.manifest.json` (per-file sha256, MEASURED) |
| DATA | plan JSON, as-built, sidecars, rows, hard_params, landing tables, generated RTL, view lists | plan event (die owner) | event bundle `events/<die>/<event>/` + its own manifest |
| PIN | `dies.<die>.tools_sha`, `src_manifest_hash`, src pointer | adopt or tool roll (KIT-OPS-5) | kit_wave.json, one commit |

### 2.2 Tree form (phase 1, no tool code change; use tonight)

`src_manifest.py build` already does it: tree = `git archive <tools_sha>` of the scope + overlay files, fresh copies, never hard links, `publish` makes it read-only and switches a pointer, `hosts` verifies on every gen host. Three additions for TOOLS-CONVERGE:

1. Overlay path rule: an overlay entry under the TOOLS scope is refused. Only DATA paths (physical/die_plan/<die>/**, results/**, the die's generated rtl dirs, plans/**) may be overlaid. A temporary tool overlay needs an entry in `tool_skew_allow.json` with the module, the branch sha it comes from and an expiry of at most 12 h.
2. `tools_sha` must be an ancestor of origin/main and must have an rt/<sha> dir on the host. Equality test = the tree file sha256 against rt/<tools_sha>.manifest.json. No AST, no regex.
3. Policy `src_manifest: require` per die from its conversion on.

Phase 2 (after closure, optional): the tree's TOOLS dirs become symlinks into rt/<tools_sha>. Before that, TOOLS-CONVERGE must count the tools that find the repo root from `Path(__file__).resolve()` and then read die data (the epyc2 logical-path defect of today is this family). Not measured by me; do not start phase 2 without that count.

### 2.3 One sha per wave, and how a fix arrives

- The pin is per die and moves only at an adopt or a tool roll. It does not follow rt/current (rt moved 7 times 18:44-19:57, POSTED). Rule: at each adopt the new tree is built from rt/current of that moment.
- Tool roll (a fix on main that a die needs between events) = new tree dir from the new sha + the same data overlay -> `adopt_guard` (manifest on all hosts, per-family kit_rtl smoke, r196) -> pointer switch. Same path for an urgent fix; the pilot replicated 2150 files to 6 hosts and verified them (POSTED 11:04).
- This replaces `ot-src-refresh` daily, catchup and put. Per-file refresh is writer 2 above.
- Jobs record `tools_sha` and `src_manifest_hash` in spec.json. FLOW-HEALTH-1 keys the retry on them (not on the hub rt digest, which is why the key found 0 repeats, POSTED FABLE-FLOW-2000).

### 2.4 Die features on main behind plan keys

- A die feature is a code path on main selected by a key in the plan; the key's default keeps the old behaviour, so the other dies are not touched. Already true for `clock.tap_offset.per_port_ps`.
- To land this way (POSTED list, TOOLS-CONVERGE 20:28): S81 `band_fixed_um`, `band_tap_windows_um`, txl_mid face anchor; HEAD `phy_pg_floor_um`, secondary clock (today env `OT_GEN_SECONDARY_CLOCK` -> plan key), street_rule_st2; KV bound_r8_straps width; QC core_latency + tap_offset schema keys, `grt_pre` `OT_PG_TRACK_TRUTH` default (a die decision -> plan key `flow.pg_track_truth`, not a changed default in a private file).
- No env variable and no private default may select die behaviour: the plan is the only switch, so the plan sha plus the tools sha fully name a build.
- Fast lane in MERGE-QUEUE-1 for die-feature branches (tools/die_plan only): gate = die_plan tests + the plan matrix below, target under 20 min, not behind the serial train.
- Plan matrix in the gate: for each die's adopted plan, schema check + `plan_gate_pre check` + gen phys and sdc_lint and kit-rtl of one type per family (the r196 smoke list). This needs the plans on main: at ADOPT the event bundle is committed to main as a data-only commit (path check only, no test gate). This also closes census item 1.
- Trial before merge: the owner binds from a pushed branch sha published as rt/<branch sha> (immutable, same manifest). Never from loose files. The wave may run on a branch sha only through the expiring allowlist.

## 3. Migration order (no in-flight bind or kit is touched)

Common rules: a running job keeps the tree named in its spec; that tree is frozen (not patched, not deleted while a spec, waiter or queue row names it). Conversion happens only by pointer switch for new launches. A bind that is running finishes on its tree and gives the gate numbers; the adopt then needs one rebind on the new tree with the same result (errors, LATCHECK count, G0 count equal).

| order | die | state tonight | step | when |
|---|---|---|---|---|
| 1 | KV | 51 types on the die hold, 0 launches; c1 = `cp -a` of main 8989ba7b1755 (POSTED), G0 0, LATCHECK 2404/2404; 64 false HARD_CORE_PARAM_ALL lines from an empty registry record | Rebuild c1 with `src_manifest build` from rt/current (c1 has no manifest and `gen_phys.py` has 2 links, MEASURED), overlay = plan_c + asbuilt + PCC/PCF source rows only. Merge `-kv` @401b6a32a03 and the HCPARAM-ALL registry fix first. The 7p pvgen patch lands on main as a branch; it is not applied to c1. Flip KV to `tool_skew: refuse` + `src_manifest: require` at the switch | tonight; first die |
| 2 | S81 | 348 held, 2 running; G3/G3b binding on the B6gE lineage; `B6gG3/src` does not exist yet on epyc7 (MEASURED), so the release tree is still to be made | Build the G3b release tree from main, not by `cp -al` of B6gE. Before that: DIE-S81-92 + TOOLS-CONVERGE put the 9 divergent modules (gen_phys 178 lines, schema, bind, landing_contract, clock_landing_plan, clock_landings, postcts_gate, check, cap_estimate) and txl_mid.tcl on one branch; proof = G3b composes and binds on main+branch with the same report as the lineage bind, and the release list lints 0. 10-minute check first: run rt/current `sdc_lint` on one failed slice_station__t8 kit; if it parses, the 59 offset tables are a design question for S81-TAPROWS (do they match eventG taps), not a lint question | with G3b adopt |
| 3 | QC | 36 running; S4q6d and S4q7e adopt pending; tree has 28 local edits, 9 real (POSTED) | Do not hold S4q6d: allowlist the 9 modules until 11-16 08:00. Merge `-qc` @9f5470b182c + grt_pre plan key; convert at S4q7e or S4q7g, whichever adopts after the merge | next QC event after merge |
| 4 | HEAD | healthy: NF13a adopted 19:3x, 8/8 family smoke, 0 fails; 13 real edits incl. 3 private files | Leave the wave alone. Merge `-head` @809e3672add (secondary clock behind a plan key). Convert at the next NF event or by a tool roll once the 22 launched types are past gen; allowlist until 11-16 12:00 | last |
| - | HBM | parked, tree gone | starts in the new form, no allowlist | on resume |

After the last die converts: delete the `kit_tools` staging and the legacy-bind retry from `kit_wave.py` (writer 4), delete the `--src-tree` flag probe, stop `ot-src-refresh.timer`.

One thing before 06:00 tomorrow: `ot-src-refresh.timer` fires at 06:00 and writes per-file merges into every tree. On a converted read-only tree it will fail or break the manifest; on an unconverted tree it is writer 2. KIT-OPS-5 or MERGE-QUEUE-1 disables the timer tonight; unconverted dies get fixes by tool roll.

## 4. Launch-time guard

TOOLS-CONVERGE's `tool_skew.py` (READY 20:02, compares the closure to main, allowlist, warn mode) is the right place. Changes:

1. Reference = rt/<dies.<die>.tools_sha>.manifest.json, not "main" and not rt/current. The pin is the contract; without it every merge makes every tree "skewed".
2. Scope = the whole TOOLS scope of 2.1 (not only tools/die_plan + tools/autopilot: KV c1 imports tools/s81_head/fallback_land.py, and common_flow tcl is in the kit).
3. Three checks, per gen host, cached on (tree path, manifest hash, newest mtime in scope): (a) every TOOLS file equals the rt manifest; (b) no extra file in the TOOLS scope; (c) tree read-only and nlink 1 on TOOLS files. Any miss = REFUSE for that die on that host, class TOOL-SKEW, one post per die per changed set, no retry (it is deterministic).
4. `tools_sha` older than rt/current by more than one adopt is a note, not a refusal.
5. Unreadable tree: `unmeasured` in warn mode, REFUSE in refuse mode.
6. Same function called from three places: wave launch, `adopt_guard` (before the switch), and the bind chain wrapper (`ot-run --priority plan`), where it replaces the AST arity class of `plan_gate_pre` (exact, and removes the KV false positive).
7. Rollout: warn on all dies now (as the lane proposed); refuse per die at its conversion; allowlist entries expire, and an expired entry refuses. All four dies on refuse by 11-16 12:00.

## 5. Ban on in-place die-tree patches

Rule text for the rulebook (FLOW family):

- A published die tree is read-only and is never written again. This holds for lanes, KIT-OPS, MERGE-QUEUE and COORD (r207 was an in-place write too).
- A fix reaches a tree in one way: merge to main -> tree build from that sha -> adopt_guard with per-family kit_rtl smoke -> pointer switch. Handoff files of the form "*.patch, please copy into each die src" are not accepted.
- `cp -al` is not used for anything in the TOOLS scope. Event data may be hard-linked only inside one event dir.
- `ot-src-refresh` daily, catchup and put are retired (2.3).
- Enforcement is by the guard, not by the rule: `chmod a-w` at publish, hash check at launch, adopt and bind. A patched tree stops launching and names the file.

What the bind.py incident would have looked like: the prepnr change merges to main with its test, KIT-OPS-5 rolls the tools pin, the kit_rtl smoke fails with NameError on the first family, nothing is switched. Cost 10 minutes on one lane instead of 1 h 40 on four dies.

## 6. Owners

| item | owner | due |
|---|---|---|
| Overlay path rule, pin-based guard (section 4), calls from adopt_guard and the bind wrapper | TOOLS-CONVERGE-1115 | tonight, before KV switch |
| Reconcile branches: -kv, -s81 (+ the 9 divergent modules with DIE-S81-92), -qc (+ grt_pre key), -head (+ secondary clock key) | TOOLS-CONVERGE-1115 with each die owner | KV tonight, S81 with G3b, QC and HEAD by 11-16 08:00 |
| Each die owner names any module it still needs that is not on those branches; no answer by the die's conversion = main is taken | KV-102, DIE-S81-92, DIE-QC-103, HEAD-100 | at COMPOSED of the next event |
| Tree build, publish, replicate, pointer switch, `tools_sha` + `src_manifest_hash` in kit_wave.json, `require` and `refuse` flags, tool roll procedure | KIT-OPS-5 | per die at conversion |
| Disable `ot-src-refresh.timer`; fast lane for die-feature branches; plan matrix in the gate; data-only plan commit at ADOPT | MERGE-QUEUE-1 | timer tonight; rest 11-16 |
| `plan_gate_pre` TOOLS class = manifest equality | PLAN-GATE-PRE-1115 | after the guard merges |
| TOOL-SKEW = deterministic, no retry; retry key on tools_sha + manifest hash + plan sha | FLOW-HEALTH-1 | 11-16 |
| HCPARAM registry record ot_qwen_tp8_pv_join_t RESET_PIN=1 | HCPARAM-ALL | before KV strict bind on main |
| Rulebook line (section 5); no in-place fixes by COORD | COORD | now |
| Remove writer 4 from kit_wave.py | TOOLS-CONVERGE-1115 | after HEAD converts |

## 7. Wasted share (POSTED numbers from FABLE-FLOW-1350/1800/2000, not re-counted)

| window | launches | fails | of this class |
|---|---|---|---|
| ~12:00-14:00 + the 14:01 tick | - | - | 118 + 110 (`--src-tree`) |
| 15:45-17:45 | 99 | 88 | 80 (S81 sdc_lint 56, KV tree 24) |
| 17:45-19:45 | 119 | 72 | 60 (S81 sdc_lint) + the kit-rtl NameError share of the other 12 (not split) |

- 15:45-19:45: 140 of 160 fails (88%) and 140 of 218 launches (64%) are this class. Day total in the windows read: at least 368 failed launches, plus 28 S81-TAPROWS col kits killed by the NameError.
- Held behind it: KV 51 types (die hold since 17:35, tree rebuild), S81 slice_station/serdes families (59 types wait on G3b, which exists partly because of the lint).
- Lane time on symptoms today: KITRTL-FAIL-1115 (a, b, c), SRC-TREE-1115, TOOLSMOKE, WAVE-PREPNR patch + fix, KV-102 tree rebuild, PLAN-GATE-PRE TOOLS class, COORD r207.

## 8. Stop list

1. Copying a single tool file from main (or from another tree) into a die tree. This is the S81 gen_phys/sdc_lint and KV gen_phys/schema failure.
2. In-place edits of any published tree, by anyone, including "copy+mv" installs of handoff patches.
3. Building a new event tree by `cp -al` of the last event's tree or overlay (S81 G3b, KV 7p).
4. Applying the 7p pvgen patch to KV c1, or any `-kv/-s81/-qc/-head` branch content to a tree by hand: merge, then build.
5. Flipping `tool_skew` to refuse on a die before its conversion (all four differ today; every launch would stop).
6. Relaunching S81 slice_station/serdes on B6gE: 60 of 60 fail and the result is known.
7. Widening or bypassing `sdc_lint`, and adding more adapters in the wave (staged sets, legacy retries, API_SKEW patterns): they hide the skew.
8. Merging 227 modules "die -> main". Only the about 38 real edits are reconciled; the rest is stale and is dropped.
9. Changing a tool default or reading an env variable to get die behaviour; use a plan key.
10. Letting the 06:00 `ot-src-refresh` daily run.
11. Converting HEAD mid-wave tonight; it is the one die that launches cleanly.

## 9. Limits of this review

- I did not run main `sdc_lint` on an S81 SDC; item 3 of the summary is from reading both files (the 10-minute check in section 3 confirms it).
- Module classes (BEHIND, AHEAD, counts per die) are TOOLS-CONVERGE's inventory, read from its post, not from cls_<die>.json.
- Trees were inspected on epyc7 only; the census reports the cross-host copies identical.
- Phase 2 (symlinks) is not audited.
- Fail counts per window are from the FABLE-FLOW posts.
