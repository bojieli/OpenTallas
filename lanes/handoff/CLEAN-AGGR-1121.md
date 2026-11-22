# CLEAN-AGGR-1121 handoff to CLEAN-AGGR-R2 (2026-11-21 ~20:0x PST)

Owner order 11-21 19:1x: "apply all the aggressive cleanup rules". Rails kept: ot-delete only, guard, floors, admission, OOM.
Lane scratch: /srv/opentallas-scratch2/claude/clean-aggr-1121/tmp on every host (scripts + logs). Lane clone: epyc7 /srv/opentallas-scratch2/claude/clean-aggr-1121/w.

## Done
1. Guard protection set (main 1326932a95 + 2095d6a53d, ot-push-main, tests tools/fleet/test_guard_record_scope.py). Builds on FLOW-OPS-1300 item 13/13b.
   - build_protected_live.RecordScope: tree_switch markers + handoff/candidate/tree-check json protect a source tree only if it is current (kit_wave die config) or the record was written after the die adopted its current tree; a wave attempt only if a live/queued row lists it.
   - kit_wave bound_trees protect a tree only while a RUNNING/LAUNCHING/RETRY-INFRA/WAITING row is bound to its plan sha (ENQUEUED/ROUTE-HELD read their attempt kit).
   - prov cache honours 72 h (11-17 cache dropped). current_trees adds <die>_ prefix (qwen_compute_*, s81_head_* snaps).
   - ot_delete_guard: kw45/snap_<die>/<tree> = whole trees; routed-unsigned refusal only within 2 h grace (OT_GUARD_ROUTED_GRACE_H).
   - rt/current = 2095d6a53d on all hosts except epyc10 (was on 7b6af7dd0449; rt sync skipped it at <50 GB; now 850+ GB, next ot-tools-follow should copy - VERIFY).
   - Hub list rebuilt (fleet-ops-r/refresh_guard_live.sh cron */30): ~2244 roots (was 3175).
2. Batches (ot-delete, guard decides, idle >= 2 h): wave attempt dirs not listed ~23,800 deleted (epyc10 4229, epyc8 3701+, epyc2 3589+, intel1 3673, epyc7 1948+, epyc9 3256, intel2 446); kw45 old trees (kwbatch.sh); idle lane dirs (lanebatch.sh: nothing modified 12 h, no git repo inside, guard decides). Some batches may still run (detached; logs kwbatch/attbatch/lanebatch.*.log). Note: first lane batch (before the git skip) deleted ~10 small dirs (cbc-*, cland-macro-1, clean-all-1115, ccache-key-cardinal, codex-kv-prompt-1551, adopt-census-1800, astra-s81-h9r1-1120); manifests in ~/.local/state/delete-manifests.
3. autopilot/closed: units whose SIGNED records are in hub-coord/signed-store retired (intel2 9, epyc2 35, epyc10 16; script closed.py). ~2 LOCAL_PASS_NEEDS_PARENT units per host were deleted before LOCAL_PASS was treated as signed (checked: sstn_base566 and hd_mesh_e are in rtx INDEX). Kept: intel2 65 + epyc10 26 signed-not-in-store. Export: auto_export.py drain --scan (OT_AUTO_EXPORT_WINDOW_H=240) started on hub (log tmp/export_scan.log); rerun closed.py after it lands.
4. flow-canary (intel2): old sources (kept die_sha/last_sha + newest 3) and runs > 2 h deleted; KEPT runs/baselines/, the 7 runs named in baselines/*.json, latest run per die.
5. intel2 old dirs kw27, kw41, i2root-moved-1114, flow-fix-2045, s81-typemerge-gh, s81-resign-deep retired (log tmp/i2old.log). kw43 live, kw35 active: kept.
6. FABLE-FLOW-1900 (3): kit_wave cancel-rows --old-plans-only --per-block on 23 QC superseded-plan ENQUEUED rows with a queued current-plan row (tmp/cancel.sh, cancel.log on intel2; may still be running). 21 S81 + 2 KV superseded ENQUEUED rows have no current-plan row: kept.
7. Undrained epyc8 (coord 1b834321b4) and epyc2 (5620b60d51); host_drain is empty.
8. Step 5 STANDING: ot-autoclean.timer ENABLED + active hourly (:30) on all 7 gen hosts (intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10): ExecStart = CLEAN-2 args incl --live-refs-only --aggressive --apply; drop-in ~/.config/systemd/user/ot-autoclean.service.d/zzzz-clean-aggr-1121.conf sets OT_AC_CURRENT_EVENTS (update it at each plan event). First passes started 19:2x; check journalctl --user -u ot-autoclean for ALERT / exit 3/4. Localhost ot-autoclean-push.timer (:10) supplies the snapshot.

## Free GB scratch2 at ~20:0x
intel2 549, epyc10 857, epyc8 574, epyc2 381 (scratch3 811), intel1 799, epyc7 598, epyc9 645.

## Left
- epyc2 scratch2 target 450 (381 now): kw43-wave-1109 on scratch2, remaining closed units, lane dirs; epyc2 scratch3 (811 free) not targeted by kwbatch beyond symlinked kw45/kw43-wave-1109n.
- intel2 flow-canary runs: re-apply keep rule (canary.py in tmp) as new failed runs accumulate; ask FLOW-CANARY-R2 to self-retire.
- tap-grid-r5/kv (48 GB, live process) and mq1 (live merge-queue worktrees): owner lanes TAP-GRID-R5 / merge queue to trim.
- 40%-free target not met on 7.4 TB hosts; next big holders: kw45 trees still listed, ot-jobs, ot-store (intel2 422 GB), autopilot/closed signed-not-exported.
- Gap: private kits under a die work_root (.../kit-wave/<die>/<ev>/private/<lane>/<kit>) are still protected by the work_root ancestor (item-13 skip covers only attempt_N); small.
- auto_retire refusals "named in a hub post of the last 24 h" dominate lane candidates on intel2 (89); not changed.
- Post free GB every 30-60 min with bin/post.sh.
