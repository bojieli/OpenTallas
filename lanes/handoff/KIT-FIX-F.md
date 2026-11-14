# KIT-FIX-F handoff (Fable; build-kit fix; COORD is the coordinator)

Worktree: epyc8 /srv/opentallas-scratch3/claude/kit-snap-1, branch claude/kit-fix-f-1113 (inherited clone of KIT-SNAP-1). A second worktree on intel1 /srv/opentallas-scratch2/claude/kit-fix-f (same branch name in the intel1 repo) is spare.
Data: intel2 ~/kff_rows.json (the 173 rows), ~/kff_plan.txt (wave dry-run plan 17:46).

## STATE 1 (2026-11-13 17:5x PST): what the 173 really are
Source: the latest plan-current kit_wave_stages.tsv row per non-HBM type, the same rows failure_breakdown.py labels "other flow error" 113, kit_rtl 32, port mismatch 14, infra 14. Every row was read by its reason line.

| True cause | Rows | Dies | Tooling? |
|---|---|---|---|
| Wave stop artefact: stage units stopped by the controller when the QC hold went on (11-12 06:16-06:18, "FAIL @unit: KW_STAGE ...", systemd Stopping), plus RETRY-INFRA "restaged: unstarted waiter" rows that never restarted | 64 | QC 64 | No. Not a failure of the kit; mislabelled |
| Already past placement: ROUTE-HELD (visual / form / R-CAP / porous) 14, grt-timecap 5, DRT-0255/0073 route errors 6, place errors 3 | 28 | S81 12, QC 7, KV 5, HEAD 4 | No. Mislabelled |
| Design or plan content stops gen: S81 leaf "collector_tree differs from captured bound reset identity" 21, svc_hi memory_bits 8, svc_lo $fatal lint 8, S81 KeyError col_h10 pv (old event) 6, QC KIT_TOPOLOGY_BIND_STALE 3, QC landing-group override 2, KV kv3_phy clock tap 2 | 50 | S81 43, QC 5, KV 2 | Partly: needs a plan or bind event, already owned by die lanes |
| Real kit-input break: an input file is missing, outside the kit, or deleted | 29 | KV 15, QC 12, HEAD 2 | Yes |
| ssh transport | 2 | QC 2 | Infra |

Kit-input detail (29): KV kv3_pv x15 "preferred HDL source missing" (the kit_store pilot moved the asbuilt into kit_inputs without its rtl/ files); QC KNSC x9 (face_guard.json, sidecar_pv.json, failfast_rules.py, bind_report.json in other worktrees), QC kit_rtl.f names deleted qc-transport-fix-4 files x1, QC geom_run script gone x2; HEAD hd_mesh / hd_spn sink_bins_4.json outside the kit x2.

By die, what blocks a launch today (wave dry-run plan 17:46):
- QC 89 rows: 0 eligible. Every QC type is under the die hold WAIT-FORM / HF-1c (old floor). The rows are 11-12 06:16-06:59 leftovers. Nothing here launches until the s28 + HF-1c event, whatever the kit tooling does.
- S81 55 rows: 45 eligible; 23 leaf held DRT73-AOR-1113 (collector_tree class), 16 svc held SVC-MACRO-1113 (after the freeze), 12 col_h held.
- KV 22 rows: 27 eligible incl. kv3_pv x15, kv3_phy, kv3_pc.
- HEAD 6 rows: 8 eligible incl. hd_mesh.

## Why kits break (plain words)
A kit is not a package. It is a list of absolute paths into other people's work folders on one particular machine: the die source tree, the bind output, sidecars, recipe files. Four things move under it:
1. Cleanup or a disk swap deletes a folder the kit still points at (qc-vis-resite/srcs27, kw32/src_27db6, the epyc4 KV swap, qc-transport-fix-4/src_sw2).
2. The wave sends the item to a machine that never had the folder (1109 SRC-INCOMPLETE probe lines; bind_report.json on another host).
3. A plan event changes the plan while the bind of record stays the old one (KIT_TOPOLOGY_BIND_STALE, collector_tree identity).
4. A tool fix lands on main but the wave runs each die from a pinned source copy, so the fix never reaches kit generation until the next source switch.
A failed row is not retried unless someone lists item@attempt, and a held or stopped row keeps its last FAIL text, so the failure table keeps counting rows that are held by a die owner or were only stopped.

## STATE 2 (2026-11-13 18:1x PST): fix built, canaries running
- Branch claude/kit-fix-f-1113@64db7fb624 (origin; epyc8 /srv/opentallas-scratch3/claude/kit-snap-1). Files: tools/autopilot/kit_store.py (snap / verify / snap-gc, dry closure walk, 'tree'), tools/autopilot/kit_wave.py (option kit_snap, kit_snap_stage, donor copy, KIT_INPUT_MISSING rule), tools/autopilot/test_kit_store.py (25 tests pass). 89 test_kit_wave*.py files: all pass except test_kit_wave_otherfail.py::KilledIsInfra::test_own_cap_sigkill_247_is_not_made_infra_here, which fails the same way on origin/main 28cf407973 (not mine).
- NOT deployed to the live runtime (intel2 /srv/opentallas-scratch2/claude/kw38/rt). Canary copy: intel2 /srv/opentallas-scratch2/claude/kit-fix-f/rt/tools/autopilot (runtime *.py + my kit_wave.py / kit_store.py).
- Canaries (kit_snap on, own work root /srv/opentallas-scratch2/claude/kit-fix-f/canary/<die>/<event> on the gen host, control dirs intel2 /srv/opentallas-scratch2/claude/kit-fix-f/canary_ctl/<die>_<item>/a1, units kff-*): KV kv3_pv_v8 (intel1), S81 serdes__t2 (epyc9), HEAD hd_spn (epyc9), QC slw_su_l1__clcc9d0155 (epyc4), QC cbn_q11__cl49ae4555 (epyc8). Launcher: intel2 /tmp/kff_canary.py [item ...].
- First HEAD canary failed at kit_rtl: the script reads <plan dir>/native_domains/... by relative path; fixed by 'tree' (bounded plan / as-built directory moves whole), relaunched.
- Live wave (no kit_snap): KIT-OPS-2's R-MINIMAL release launched 25 items at 17:44; kv3_pv x15 passed bind + kit_rtl on the current runtime and hd_mesh reached place. The 17 launchable kit-input rows were stale failures that had not been retried.
- coord: tools/failure_breakdown.py relabelled (4e63bf853ab): stopped by the wave, held by die owner, placed / route rows, kit input missing, bind stale. New type table: QC 98 held by die owner; S81 42 held.
- Snapshots sit in <scratch>/kit-store/snaps, outside the ot-autoclean roots (<scratch>/claude), so cleanup does not touch them; kit_store.py snap-gc --snap-root <dir> [--apply] removes those unused for 14 days.

## FINAL (2026-11-13 19:1x PST): lane CLOSED on COORD order
- Code: main 157bec2e19a2 holds 64db7fb624 + 54a94f5577 (train G). Delta for train J (ROOT-MERGE-63): claude/kit-fix-f-1113@aeb5ab6463923adc739e06415b4ad6ee033370ab = b50308aba6 (original kit top-level files travel with face_guard.json) + aeb5ab6463 (repeat the view-reference fetch, max 3 rounds). test_kit_store.py 27 pass.
- kit_snap is OFF everywhere in the live runtime. Deploy + enable = KIT-OPS-2 after train J: copy main tools/autopilot/kit_wave.py + kit_store.py to intel2 /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot (keep backups), then kit_wave.json dies.<die>.kit_snap = [patterns] or true; revert = delete the key. Optional dies.<die>.kit_snap_view_refs = "strict".
- Canary result (kit_snap on): HEAD hd_spn PASS (place + geom). S81 serdes__t2, KV kv3_pv_v8, QC cbn_q11__cl49ae4555: through kit_snap, bind, kit_rtl, kit_topology, gen, preflight; in the place stage at 19:06, no result yet (units kff-* on intel2, results in canary_ctl/<die>_<item>/a1/result.json). QC slw_su_l1__clcc9d0155 FAIL at gen on aeb5ab6463.
- KNOWN GAP (not fixed, COORD: no more fixes here; the type is old QC floor, replaced by s29): gen's hard_landing reads the ORIGINAL signed kit of a child view (provenance.src): face_guard.json, face_guard.py, and the netlist kit/run/results/asap7/<design>/base/1_synth.v. The wave now copies face_guard.json and the kit's top-level files from the host that has them (intel1) to the gen host, but not the netlist: view_refs only follows face_guard.json "netlist" when it is an absolute path, and here the path gen opens was never in the missing list (one fetch round ran, 0 mentions of 1_synth.v; the file is 1.7 MB on intel1). Next step for whoever owns it: read how hard_landing.py builds the netlist path (tools/die_plan/hard_landing.py capture(), `net = Path(old['netlist'])`) and add that rule to kit_store.view_refs; or have export_view copy face_guard.json/.py + netlist into the view dir so no original kit is read.
- The missing-reference list of that type also holds paths gen never reads (/work/run/..., deleted trial dirs): keep the default advisory.
- Leftovers that are mine: intel2 /srv/opentallas-scratch2/claude/kit-fix-f (rt copy, canary_ctl); canary work dirs /srv/opentallas-scratch2/claude/kit-fix-f/canary on intel1, epyc4, epyc8, epyc9; snapshots under /srv/opentallas-scratch2/kit-store/snaps on those hosts; on epyc4 the files my canary copied under /srv/opentallas-scratch3/claude/codex-qc-sul1-qualified-1106 and codex-qc-su-trials-era paths (KW_VIEWREF_COPIED lines in canary_ctl/qwen_compute_slw_su_l1__clcc9d0155/a1/kit_snap_refs.log). All deletable once the three place canaries end. Worktrees: epyc8 /srv/opentallas-scratch3/claude/kit-snap-1 (clean), intel1 /srv/opentallas-scratch2/claude/kit-fix-f (unused).
- Commit 54a94f5577 has a subject-only message (shell quoting error); b50308aba6 carries its body.
