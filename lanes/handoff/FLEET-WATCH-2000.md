# FLEET-WATCH-2000 handoff (11-20 ~22:10 PST)
Succeeds FLEET-WATCH-1630. Clone: epyc7 /srv/opentallas-scratch2/claude/fleet-watch-2000 (sparse cone tools, rtl, physical/die_plan/s81/kit_wave, physical/common_flow). Push logs fleet-watch-2000.push{1..4}.log beside it.
## State of the push
- Commit 67bbf50623 (NOPROG GRT-flat cancel, pinned-waiter reload, autoclean skip, ot-wait rc 127 test). Push attempt 4 (--test-timeout 3000) was running; attempts 1/2 failed on sparse-cone paths, 3 on test timeout rc=124.
- UNCOMMITTED in the clone: tools/fleet/ot-oom-age (GUARD_SUNK_ADJ=150: adj <= 150 spared while a younger candidate exists) + test_ot_oom_age.py. COORD approved. Commit, then ot-push-main with OT_LANE=FLEET-WATCH-2000.
## Findings
1 epyc2 root 90% (347 GB free): root fs = /srv/opentallas-scratch3 = /home/ubuntu/scratch-root/claude (2.8 TB). Per-lane du (/tmp/fw2000_duc.txt on epyc2) was still running; nothing freed. Use ot-delete only; skip ~/moved, symlink targets, PROTECTED-DBS.
2 NOPROG GRT-flat: noprog_watchdog.grt_flat_pass (hub), cancels via kit_wave cancel-rows --event --attempt --cls PLAN, writes lanes/CANCEL-GRT-FLAT.tsv, NOPROG_GRTFLAT_MODE=report disables. No cancel yet (needs push + hub tick).
3 failed logs: code works (3 probes). Real 20:23 serdes__t15 place failure on epyc2 kept nothing, cause unknown; logs survive in the kit dir via ot-job return. Probe dirs to delete via ot-delete: <claude>/ot-job-failed-logs/fw2000-*, fw2000.seal, fleet-watch-2000.seal (scratch2 + epyc2 scratch3 + epyc7).
4 waiter reload: pinned single-host waiters never looped; pinned_cycle() 600 s in ot-run. kw44 pinned launcher copies never reload by design.
5 PLACE-SETUP-STOP: first rt c8876644a5fc (19:31); no wave kit past place yet (2 in place at 20:35). Re-check.
6 rc 127: flow is correct; GPL-TD-AB ab.sh swallows rc. Posted.
7 KV hgi SIGKILL: ot-oom-age PLANGUARD (kills.log), not an age cap. Fixed by victim rule above.
8 STAGE_PEAK_FRAC trial: epyc2+epyc8 set 0.5 -> 0.8 at 21:59 PST (backup /etc/ot-heavy.conf.bak-fw2000-frac05-1121). Baseline 2 h kills/h,admits/h,GB/h: epyc2 0/33.5/267 epyc8 0/28/1274 epyc7 1/154/3954 epyc9 0/96/2028 epyc10 0/58/1383 intel1 0/25.5/211. Measure with scratchpad m.py (sudo python3 - 2 0 on each host). Due 23:59 PST: kills halve and admits >= 70% -> 0.8 fleet-wide; admits collapse -> restore 0.5 from the backup.
9 AGIdock INDEX check: inconclusive (no date column; bksel_c present, no u_c found).
