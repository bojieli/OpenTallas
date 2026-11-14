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
