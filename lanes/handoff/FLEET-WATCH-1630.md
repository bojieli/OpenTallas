# FLEET-WATCH-1630 handoff (11-20 ~16:50 PST)
Succeeds FLEET-WATCH-1400. Clone: epyc7 /srv/opentallas-scratch2/claude/fleet-watch-1400c (deletable; waiter /tmp/fw1630_del.sh on epyc7 retries ot-delete of 1400c then 1400, log /tmp/fw1630_del.log).

## Landed on main
- Item 1 (CANCELLED marks, earlyoom waiter adj, start canary): all three on main (5365832890c, 8be8f420531), landed by 1400 before I started.
- AUTOSTAGE-1630 (0e48f03cb9): ot-run spill_plan; when the lane-root spill is refused as too big / too many lanes / symlink out / ../ above lane and the waiter has waited 300 s (OT_RUN_AUTOSTAGE_AFTER_S), --dir alone becomes the --stage path and the spill is planned again (any host that admits, copy, run, copy back). Existing machinery already did spill with --stage; the gap was --dir jobs in a big lane (claude/wt). Test: tools/fleet/test_ot_run_autostage.py.
- TREESYNC-1630 (ceedd940a3): plan apply already synced+verified the tree on all current gen_hosts (ensure_tree_on_hosts, verify_tree_on_all_hosts). Added: hosts outside gen_hosts that hold the die's current tree (e.g. hand copies) join the sync set. Tests in test_apply_reviewed_tree_marker.py.
- ISOLATE-1630 (0b7c9148c7): ReapRetry test order dependency = wave_jobs.BAD_HOSTS left set by test_kit_wave_guard_kill.py (module global); test now resets it.
- Rt/current on hosts is NOT refreshed: AUTOSTAGE and TREESYNC take effect after the next flow refresh.

## Trees
- gen_hosts already include epyc7 for s81 (J5), qwen_kvsys and qwen_compute (QC). Trees present on epyc7 (kv tree dir exists).
- s81_head r11b_s0: replicate from epyc9 still running (epyc7 .part 22 GB at 16:45, ot-run pid 2569337 on epyc9). Waiter ~/fw1630_head.sh on epyc9 waits for that pid, verifies (src_manifest hosts, hash 73f4bb9a...), then kit_wave_edit adds epyc7 to s81_head gen_hosts; result in ~/fw1630_head_verify.log (EDITED / VERIFY-FAILED). If VERIFY-FAILED, re-run replicate.

## Skew measurements (16:10)
- TOOLS-LAG (git rev-list main since pin): qwen_kvsys 413 commits (missing r708); s81_head 904 (r698 r708); s81 UNMEASURED: tools_sha is the literal "j5tree", not a sha (bad revision 'j5tree..main').
- TOOL-SKEW pin mode UNMEASURED for qwen_kvsys and s81_head: rt/a2fb7e625dd8.manifest.json and rt/385f61b5582a.manifest.json exist on no host (not hub, not epyc7, not epyc9). Fix open: write manifest at pin time; or set s81 tools_sha to a real sha.
- tool_skew.py check vs main (closure 1034 modules): qwen_kvsys 132 differ, s81 56 differ (unallowed, refused count).

## Launches/h (KIT-WAVE LAUNCH lines): hour 13 181 (J5 apply), 14 36, 15 31, 16 11 in 14 min (~47/h pace). After-change figure not measurable yet: refresh not adopted.
## Open
- Next hour: confirm head EDITED, 1400/1400c deleted, rt refresh adoption; re-count launches.
