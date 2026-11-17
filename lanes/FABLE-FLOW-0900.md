# FABLE-FLOW-0900: procedural and flow failures, 05:43-07:53 PST

Reviewer: FABLE-FLOW-0900 (Fable). Read-only: no deletes, no kills, no git in owner checkouts. One ALERT posted
(epyc10 disk, 07:52). Measured 2026-11-17 07:43-07:53 PST on hub intel2 and the 6 build hosts.
Sources: autopilot/log.txt 05:43-07:43 (23 ticks), lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py (07:45),
`ot-run --status` (07:44), disk-rate log, auto-retire journals on 6 hosts, merge-queue log, rt/current on 7 hosts.
Previous: FABLE-FLOW-0700. Clock: hub PST; COORD event times ("0700", "0900") run about 60-70 min ahead.
Scope: process and tooling only.

## Headline

1. Fleet use fell: median 38% over 23 ticks (range 30-56%), 42% at 07:41, 51% at 07:51 with epyc10 out of the
   table. 0700 was 49%. Nothing is waiting for admission (0 waiters; 0700 had 15 on intel1). The fleet is idle
   because the wave has almost nothing it may launch.
2. The wave is QC-only and QC failed every result. 13 LAUNCH in 2 h (0700: 42), all qwen_compute. 26 of 26 FAIL
   results are one class, the kit_rtl filelist escape. Last wave launch per die: S81 11-16 19:55 (12 h ago),
   KV 11-16 21:28 (10.5 h), HEAD 11-16 17:15 (14.5 h), HBM 11-13.
3. All ten approved fixes are merged and in rt/current (e251fda2da5b) on hub and 6 of 6 hosts. Approval to
   merge took 1-5 min and merge to synced runtime 2 min: there is no merge-queue lag. Three are live but not
   deployed or not used yet: r558 (no schedule), r562 (no tree made with it), the hook half of r548.
4. Disk still falls about 56 GB/h per host (0700: 87-91 on the two hosts scanned). The --lanes retire freed
   real space once (438 lane dirs), and full-tree copies took it back: epyc10 is at 27 GB, hub root at 64 GB.

## Are the fixes live

| Fix | In rt/current | Working? |
|---|---|---|
| r546 floor clamp | yes; frontends exec rt/current ot-run on hub + 5 hosts (epyc10 has no ~/.local/bin/ot-run) | not exercised: no FLOOR-OVERRIDE line found |
| r548 ot-lane-clone | yes | tool: yes. 5 sparse worktrees since 06:36 (1-6 GB each, epyc2 and epyc9), 0 raw clones born after the merge; warm repo exists on epyc2 and epyc9 only (made on first use). Hook: NOT installed. rt block_raw_rm.py has the clone rule; ~/.claude/hooks/block-raw-rm.py on localhost is the 02:57 copy without it. The rule also lets `--depth` through |
| r549 rt host prune | yes | yes: 19 snapshot dirs per host (0700: 203) |
| r550/r551 live-only list + --lanes | yes; cron every 30 min | list 1,383 roots (was 8,685). First --lanes pass deleted 438 lane dirs on 6 hosts. The disk-rate retire of kw45 trees still reports "deleted 0" and REFUSED on `src_s81_pin_3c913dbdfb23_` (message still cut) |
| r554 relaunch needs a named changed file | yes (06:50) | yes: RELAUNCH-ON-FIX 3 in 2 h (0700: 21), 0 tool-only after the merge; the 3x rule blocked 2 rows |
| r555 wave_balance sealed waiters | yes (06:55) | not exercised: 0 waiters, 0 RESTAGE lines |
| r556 no single-pilot family hold | yes (07:07) | partly seen: 9 LAUNCH-HELD, all FLOW-GUARD class breaker, 0 pilot holds. HOLD-AUDIT TERM-UNREACHABLE is 236 at 06:31 and at 07:40; the 6 h expiry cannot show before 13:05 |
| r557 nested child admission | yes; ot-heavy is a symlink into rt on 6 of 6 | waiters 15 -> 0 (the 14 intel1 children were admitted by hand at 07:1x, so the code path itself is not yet proven) |
| r558 lane quota alert | yes (07:12) | NOT deployed: no cron line, no autopilot/lane_quota_state.json, no state dir on any host. No alert can fire |
| r562 delta publish | yes (07:42) | not used: 0 trees with .link-base on 6 hosts. QC D4 (made 07:21) is a full 57.5 GB copy |

Merge queue: 18 merges 06:00-07:40, 18 syncs, 1 sync failure (06:02, epyc7 4 GB free).

## Classes, ranked by fleet time wasted

### A. The wave has nothing to launch (about 11% of the fleet: the fall from 49% to 38%)

A1. QC kit_rtl filelist escape. Count: 20 fails in hour 06, 5 in hour 07, 2 more by 07:49 (0700 brief: 21/h).
27 QC rows sit in kit_rtl. Trend: falling only because launches stopped; the pass rate is still 0.
Root cause: a D-step tree is a renamed copy and its filelists keep absolute paths of the base tree
(`.../src_qc_pin_eb1e73448bd0_s4q9l2/rtl/...` inside `..._s4q9l2_d2`). The bind check added on main refuses
them. D2 (05:19) broke every row; D3 (06:22) did not fix it; D4 switched at 07:38. Each tree was switched in
with no kit_rtl run on it. This is the third run of the class (11-15 22:00: 10 fails; 11-16 20:00: 33; today 27).
Process faults around it:
- The class breaker reopens a probe on every input change (06:22, 06:55, 06:59, 07:45), so 9 launches went to
  trees already known broken; each took 9-32 min to fail.
- Two rows launched on D3 at 07:36 and 07:40, during the fix, and failed at 07:44 and 07:49. The QC hold did
  not cover them.
- The first D4 launch (sle_ctl__cl67434795, 07:45:38) had no result at 07:53. D4 is not yet proven.
Fix: a publish canary. Before TREE-SWITCH, run bind kit-rtl for one type per family on the new tree on the gen
host (minutes), and src_manifest verify fails a tree whose filelists name any path outside it. A tree that
fails is never switched in. Owner: WAVE-PILOT-FIX (canary), QC-PLAN-R3 (D4 result).

A2. S81, KV and HEAD wave silence (12, 10.5 and 14.5 h). Live attempts exist (ENQUEUED: S81 31, HEAD 27, KV 6)
but no new launch. I did not find one cause. Facts: S81 has 28 rows in kit_rtl and the same escape class shut
its breaker on 11-16 20:00; KV gen_hosts is epyc10 only and epyc10 is under the gen floor; the under-use line
counts only 84 rows not launching (WAIT-FORM 25, q_running 25, q_signed 12, KW-FIX-45 8, q_fail 6), while the
breakdown has 320 stale current-event rows with no job. The gap between 84 and 320 is rows the wave no longer
considers. Fix: the under-use line must account for every unsigned current-event row with a reason, and a die
with no launch for 2 h posts NEEDS-LANE once. Owner: WAVE-FLOW-R2; new lane WAVE-SILENT-DIES to name the cause
per die.

### B. Disk (about 5%, was 15%; one host lost, hub writers held)

Count: free scratch2 after the 07:04 retire pass was 852 GB on 6 hosts; 587 GB at 07:51 (intel1 128, epyc2 82,
epyc7 111, epyc8 137, epyc9 101, epyc10 28). That is 338 GB/h, 56 GB/h per host. GEN-DISK-LOW 21 lines (0700: 41).
Refusals: epyc10 out as gen host from 07:31 (it is KV's only gen host); HUB-DISK launch refused from 07:39
(hub root 64 GB = floor); localhost REFUSED (109 < 150 GB); epyc7 root 40 GB (only `--dir` scratch2 jobs).
Root cause, unchanged: whole trees are still copied.
- QC D2, D3, D4 are three unshared 57.5 GB trees made on epyc8 in 2 h 45 min (172 GB) for a one-file change
  (tools/die_plan/bind.py). This is the epyc8 swing.
- `src_manifest.py replicate --hosts epyc7,epyc9,epyc2,intel1` has been copying KV D16 (48 GB) by full rsync
  from epyc10 since 07:21: 192 GB on the receivers.
- epyc10 fell 93 -> 55 -> 27 -> 21 GB (07:04, 07:47, 07:52, 07:53) under a tar extract (fable-fix-head-reset), a HEAD
  republish (head-die-r hr4) and a new S81 d5e tree.
- Hub root: /home/ubuntu/skyhum-work 179 GB (not this project) and scratch-root 96 GB of 468 GB.
Fix: r562 is the fix; make it the only path. publish and `replicate` refuse a full copy when a published base
of the same pin is on the target host and send the delta instead; TREE-SWITCH logs the unshared GB of the new
tree. Deploy r558 (cron) so the lane writers alert. Owner: FLEET-OPS-R; COORD for skyhum-work on the hub root.

### C. Single-host pins and gen-host lists (about 3%; epyc10 load 22-25 of 96 all window)

Count: 42 clients carry one `--hosts` (0700: 50): epyc8 23, epyc2 5, epyc10 5, epyc7 4, epyc9 3. QC gen_hosts
is still [epyc8] and KV [epyc10]. Committed threads are 238/96 on epyc8 and 232/96 on epyc9 at load 45 and 70.
Root cause: gen_hosts follows where the one full tree is; class B makes a second copy too costly.
Fix: with delta trees, TREE-SWITCH requires at least 3 gen hosts per die before it switches. Owner: FLEET-OPS-R
(staging), WAVE-FLOW-R2 (rule).

### D. Relaunch without a fix (under 1%, was 1%)

Count: 3 RELAUNCH-ON-FIX (21), 2 BLOCKED-FLOW after 3 identical fails. Fixed by r554. The remaining waste is
the breaker probe of A1. Owner: WAVE-FLOW-R2.

### E. Stale and unowned rows (no compute)

Count: 320 current-event stale rows (0700: 284), 181 on superseded blocks. S81 338 (FIX-S81-COL-STALE 203),
HBM 107, KV 34, QC 21, HEAD 1. Unowned 21 (22). RETIRE-SUPERSEDED retired 0 on 3 runs. Trend: worse by 36.
Fix as at 0700: one retire pass for the 203 dedup and superseded rows. Owner: FIX-S81-COL-STALE, COORD.

### F. Log noise and tick time

Count: tick median 137 s (149), max 555 s (216), 3 ticks over 280 s, so 23 ticks in 2 h. Per window: TOOL-SKEW
110 lines (hbm "241 of 241" every tick), ADOPT-GUARD hbm 46, SRC-INCOMPLETE epyc8 s81 22 (same path since
11-16 22:00), REAP-DEAD SILENT 22, HUB-SYNC-FAILED 5 (NOPROG.tsv, STALE.tsv dirty in the hub checkout).
Trend: flat. Fix as at 0700 (parked flag for hbm, one line per key with a counter). Owner: WAVE-FLOW-R2.

## Known issues from the brief

| Issue | 0700 | Now | Fell? |
|---|---|---|---|
| QC kit_rtl escape | 21/h | 5/h, pass rate 0, D4 unproven | no |
| QC full source trees | 56 GB each | 57.5 GB each, 3 in 2 h 45 min | no |
| epyc8 disk swing | 39-97 GB | 43-152 GB, 137 now | no (same cause) |
| QC gen_hosts epyc8 only | yes | yes; KV is epyc10 only | no |
| Lane clones slow or empty | 3 of 10 empty | 5 worktrees, 0 raw, 0 empty since 06:36 | yes |
| Dead-lane release term | open | r556 live; 236 unreachable terms still listed | not yet visible |
| Admission waiters | 15 on intel1 | 0 | yes |
| Tool-only relaunch | 21 | 0 after 06:50 | yes |
| rt snapshots per host | 203 | 19 | yes |

## Do now

1. COORD: epyc10 is at 27 GB (ALERT posted 07:52). KV has no other gen host.
2. FLEET-OPS-R: add the lane_quota cron (r558), install the rt block_raw_rm.py as the localhost lane hook
   (r548), and route the next D-step and the running KV D16 replicate through delta-apply --link (r562).
3. WAVE-PILOT-FIX: publish canary before TREE-SWITCH; report the first D4 kit_rtl result.
4. WAVE-FLOW-R2 or a new lane: name why S81, KV and HEAD have had no wave launch for 10-14 h.
5. COORD: hub root 64 GB; skyhum-work holds 179 GB of it.
