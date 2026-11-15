# MERGE-QUEUE-1 handoff (successor, updated 2026-11-14 21:20 PST)

Task (OWNER 11-14): automatic merge queue for sha-pinned COORD approvals + kit wave on a pinned main tree. DONE, in operation.

## Live
- Queue: intel2 ot-merge-queue.timer (5 min). The service is TEMPORARILY pinned to the bootstrap copy ~/merge-queue/bin/ot-merge-queue
  (VERSION file), see the comment in ~/.config/systemd/user/ot-merge-queue.service. After 7fff3a1e0b1 lands, restore the ExecStart
  to the repo form (tools/fleet/systemd/ot-merge-queue.service: rt/current copy, bootstrap fallback) and daemon-reload.
- Log ~/merge-queue/log, state ~/merge-queue/state.json (re-queued false REDs listed under "requeued"); `ot-merge-queue status|parse`.
- Only COORD/OWNER-authored lines approve. Conditional rulings: proposed 'COORD APPROVED-IF:' (the queue ignores it).
- Gate: touched-path test selection under xdist; a new failure must also fail on a serial rerun of the branch and must not fail when the
  whole file runs on main (per-item base tree, same sparse set). Sparse: tools/, physical/common_flow, rtl/lib, rtl/common.
- Wave: autopilot.service drop-in zz-kw38-picker-runtime.conf + autopilot-aux.service run rt/current (backups ~/merge-queue/*.bak-mq1-1114).
  First tick on rt/76537ad08a5b 21:02-21:09 ok, run-items from rt/<sha>. kw38/rt is kept only for units still running from it.
- ot-tools-sync flips rt/current on hub + intel1 epyc2 epyc7 epyc8 epyc9 epyc10 after every push; ot-tools-drift.timer every 15 min.
- Per-host ot-run backends still differ from main (ADMIT-TUNE-1 owns them); drift lines list them.

## Open
- READY 7fff3a1e0b1 (whole-file baseline) waits for the COORD token.
- KIT-OPS-5 7d8520d56f32 (test_gpl_guard) and KITLOST 57ab6143d232 (test_wave_jobs) are real REDs, owned by their lanes.
- Local clone on rtx-pro: /home/ubuntu/wt/merge-queue-1-1114. Debug worktree intel2 mq1/wt/dbg-pga (can be removed).

## 11-14 21:54 update
- 2026-11-14 21:54 PST RESULT [MERGE-QUEUE-1 -> COORD; cc NEARMISS-FIX-1, NEARMISS-ECO, KIT-OPS-5] OWNER order done. claude/nearmiss-fix-1-1114 @966e3722ec6 was only in the hub clone ~/wt/nearmiss-fix-1, not on GitHub (21:45 tick: WAIT not fetchable). I pushed the sha to origin as that branch (new ref, no force); the 21:50 tick landed it first: MERGED main a88ea35f0fe -> 9adb525220f (GREEN, 10 tes
- 2026-11-14 21:54 PST READY [MERGE-QUEUE-1 -> MERGE-QUEUE (merge lane); cc COORD] branch claude/merge-queue-1-1114 head 868ecf1da24 (on GitHub): new tools/fleet/ot-src-refresh + test (3 pass), and an ot-merge-queue hook that runs the per-die refresh after each land and posts a STATE on CONFLICT/BUS
State: unit runs ot-merge-queue from rt/current; bootstrap ~/merge-queue/bin/ot-merge-queue = 7fff3a1e0b1; ~/merge-queue/bin/ot-src-refresh = 868ecf1da24 (manual: python3 -I ~/merge-queue/bin/ot-src-refresh refresh --from OLD --to NEW --dies qwen_compute,qwen_kvsys,s81,s81_head --apply). Open: approval of 868ecf1da24; ASK on catch-up apply.

## 11-15 00:39 update
- 2026-11-15 00:39 PST RESULT [MERGE-QUEUE-1 -> COORD; cc DIE-QC-103, HEAD-99, KV-102, WAVE-BALANCE-1] (1) QUEUE RUNNING AGAIN. 00:15-00:38 landed: kit-ops-6 ancestor-protect (50472807304, cf05598ef62), adoptguard 95e7edf8af6, plan-timing-audit (a5505562907, dea1a73bb3b5), s81-colgen-2 3cd0bf1b718, pg-pinband-1 6621b41723f, kit-ops-6 ca-chain 41835ce16ba, kit-ops-5 est5 df791a048f2, KV @426728e16ed -> main 973db049496. QC @a192501ee99b was already in main. wave-balance 7c617ca: MERGE-FAIL (orphan base, see 00:20 STATE); the rebased claude/wave-balance-1-1114-main @7766f2431cd needs a token. KV
Open: tokens for merge-queue-1 @850b1f53a81 and wave-balance-1-1114-main @7766f2431cd; QC gen_phys + HEAD check.py refresh conflicts with their owners; bootstrap ~/merge-queue/bin/ot-merge-queue = 7fff3a1e0b1 (fallback only), unit runs rt/current + drop-in src-hook.conf.

## 11-15 01:09 update
Gen breakage 00:26 fixed (cause: refresh wrote gen_host only; replicas mixed). Per-merge refresh OFF (drop-in MQ_SRC_HOOK=, now default empty in 453f6622a8d). Daily 06:00 ot-src-refresh.timer enabled on intel2 (needs 453f6622a8d on main; until then fails harmlessly). last good sha ~/merge-queue/src-refresh-last.json = 38ef0c93cdb. Replica sync scripts: /tmp/mq1-replica_sync.sh, /tmp/mq1-replica_add.sh on epyc9/epyc7 (one-off). Open: tokens for 453f6622a8d and wave-balance-1-1114-main @7766f2431cd; KIT-OPS-5 re-key of the 32 failed items; QC gen_phys + HEAD check.py 00:24 conflicts.

## 11-15 01:46 update
READY f9028d6ecf7 (daily all-copies + identical hashes + drift timer + put). Timers enabled on intel2: ot-src-refresh (06:00), ot-src-drift (:25); both run rt/current copy (need the sha on main). Code drift 0 on 4 dies after put of postcts_gate.tcl (+8 QC epyc2 files). QC 116 physical data files differ (flag only). Open: token for f9028d6ecf7, wave-balance-1-1114-main @7766f2431cd.

## 11-15 02:02 update
kit-ops-5-curplan-1114 @4c696027e0ef RED (branch alone fails test_kit_wave_composed_src refused_row: ROUTE-HELD vs FAIL/FLOW); posted to KIT-OPS-5. Waiter ~/merge-queue/curplan_wait.sh (pid 913804, log ~/merge-queue/curplan-wait.log) lands the next curplan token at once via tick --only and copies the MERGED/MERGE-FAIL line. Autopilot runs rt/current (no refresh needed). READY 26bd253bfdf (parser accepts the word branch).

## 11-15 02:42 update
19-token audit done (9 landed, 3 RED dly-spread/dly-spread-list/genbug-impl on kit byte-identity, 6 superseded marked REVOKED in state.json, curplan skipped). Parser fix 26bd253bfdf on main; daily refresh + drift timers now effective (rt/current has them). curplan waiter stopped.

## 2026-11-15 03:3x
- r64 genbug chain MERGED in order: fable-genbug 64d6a174f5d, genbug-impl def02ae19f6, dly-spread a7a198aeb79, dly-spread-list ad22c56cc3b (cherry-pick, 2 already in main).
- r65 s81-phypg-1 @e31f9ccd5c: was hub-only; fetched from hub + pushed to origin (no force); MERGED a55cbe3c34d.
- Open: 06:00 daily refresh (ot-src-refresh.timer) + hourly drift; QC gen_phys.py / HEAD check.py conflicts from 00:24 still with DIE-QC-103 / HEAD-99.

## 2026-11-15 04:0x
- ot-src-refresh installed at ~/.local/bin/ot-src-refresh on all 7 hosts. On intel2 it is a wrapper that runs rt/current's copy, falling back to ot-src-refresh.main. On the 6 gen hosts it is a wrapper that runs it on intel2 over ssh (kit_wave.json, ~/merge-queue and coord-commit live only there). Not on non-interactive PATH, so call it by full path.
- The 03:46 dry daily with the main tool failed the staged smoke on all 4 dies. Fix: branch claude/src-refresh-deps-1115 @33dde953101 (READY posted 04:0x): missing_deps() ADDs imported main modules; smoke allows odb/openroad. The dry run with the fix passes on every host.
- If it is not landed by 06:00, the daily swaps nothing (safe). After it lands, run it by hand: systemctl --user start ot-src-refresh.service on intel2 (only between waves).
- Die trees vs main list: intel2:/srv/opentallas-scratch2/claude/mq1/tmp/vsmain-0400.out (script vsmain.py beside it).

## 2026-11-15 06:1x
- put fix landed: claude/src-refresh-put-main-1115 @5dece1db8e7 -> main 782b88c3322. put reports gen host copy vs main; put --from-main writes main's version to the gen host and every replica. Cause of the KV gen_phys "SAME": put syncs the gen host copy and never read main.
- 06:00 daily APPLIED 38ef0c93cdb..782b88c3322 to every replica, identical after swap, smoke ok, no rollback:
  - QC: 6 hosts, ADD 4, MERGE 3, REPLACE 15.
  - KV: 6 hosts, ADD 6, MERGE 2, REPLACE 16 (+2 deps).
  - S81: 5 hosts, ADD 5, MERGE 3, REPLACE 16 (+1 dep).
  - HEAD: 3 hosts, ADD 11, MERGE 2, REPLACE 17 (+7 deps).
- Next daily: 11-16 06:00 (base 782b88c3322 in src-refresh-last.json). Drift check hourly at :25.

## 11-15 09:50 update (successor 2)
- Train since 08:00, all MERGED: core-bksel 4cb55d1bc58, mq-ready-gate a530ec0ae90, typemerge 10c9c1c2d55, stream-land f8702115908 (parallel gates, in-order land), rom-viamap a0402ec7083, taprows 0057d544543, oldplan-block ab284566664, kv-rawfix 6e938d93a48, leaf-t14-1115b 12f54cf1aec, wave-copyback 1faf0c24936. FAIL to lanes: flow-health a1992/5c0c (test_ot_run_direct Choose), epyc2-scratch3 (scratch_disk timeout), ca-band c9d1, kit-rtl-src-tree-1115-2 783923a5c86.
- READY claude/mq-ready-gate-skip-1115 @49b29925549 GATE main=358553fd3e6 pass=16/16 (skip settled READYs; fixes the live .strip() crash in the gate check). Needs COORD token.
- Hub (intel2 /home/ubuntu/OpenTallas) main stale at 22c217df54 + tmp/s81t14-main-fb7cf958; outside my rules, ASK to ROOT-MERGE-63/COORD (09:45 STATE).
- ot-src-refresh: put --from-main (782b88c3322) + missing_deps (ddb0624c3d4) on main, installed on all 7 hosts (gen hosts ssh-wrap to intel2). LOCAL branch claude/src-refresh-mergeguard-1115 (worktree /home/ubuntu/wt/merge-queue-1-1114, 2 unpushed WIP commits d320a4adc1b): closest-main-base 3-way merge + guard (clean merge that drops a main def/class/proc -> CONFLICT kept) + SMOKE attribute check + batch blob prefetch; 13 tests pass. Fleet dry run running on intel2: mq1/tmp/guard2-dry.out (ot-src-refresh.guard2). MUST land before the 11-16 06:00 daily (live daily still bases merges on the last-daily sha, which dropped full_area_hard_ip at 06:00 today). Next: squash the WIP commits, rebase on main, test, push, READY with GATE.
- Die trees: all 4 at the attribute-scan baseline; HEAD gen_phys HEAD-SERDES-SECONDARY hook re-inserted (stamp 20261115-170239).
