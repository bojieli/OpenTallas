# FABLE-FLOW-1600: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 15:43-15:50 PST on hub intel2.
Window: autopilot/log.txt 13:45-15:48 PST, lanes/FLOW-HEALTH.tsv, kit_wave.json + kit_wave_state.json (15:35/15:37),
failure_breakdown.py (15:43), `ot-run --status`, df / free / ps on 7 hosts, queue rulings r152-r177.
Scope: process and tooling only. Previous review: FABLE-FLOW-1350.

## Headline

1. The wave launched 4 items in the 80 min from 14:25 to 15:44 (3 HEAD, 1 KV). The fleet had 2.6 TB of admissible
   memory and about 140 idle threads (epyc2 53/128, epyc7 52/96, epyc8 76/96) the whole time. This is the largest
   waste of the afternoon, and it is a hold, not a failure: the die-level `*` holds on S81 and QC waited 88 min for
   one merge (kitrtl-fail-1115, ETA 14:35, landed 15:35).
2. KV cannot launch on kvgeom7u on any host. Since the 15:24 switch every one of the 5 KV gen hosts is
   SRC-INCOMPLETE (15 lines, 3 ticks). The one KV launch failed at kit_rtl. No lane has posted on it.
3. S81 is 88% held by item: 352 of 398 items carry a hold (249 from the 13:32 B6gE adopt, 88 for the tap-offset
   tables, 11 signed). The die-level lift at 15:37 frees about 48 S81 items only.
4. The `--src-tree` class is closed in code (main 3813f569afe, rt/current 85738b82470d equal on 6 hosts). First
   post-lift tick started 15:44: 36 launches in 3 min (S81 28, QC 8) at 15:47:48, still launching; 0 fails, no
   kit_rtl result yet.
5. Three fixes of 13:50 are still not on main: class breaker + hub disk precondition (flow-health-1115b, green at
   15:41, first in the train), signed-terminal (MERGE-FAIL 15:09, r2 in gate), watchdog exclusion (no code).

## Kit wave, 13:45-15:48

| 10-min bucket | 13:4x | 13:5x | 14:0x | 14:1x | 14:2x | 14:3x-15:3x (70 min) | 15:44-15:48 |
|---|---|---|---|---|---|---|---|
| LAUNCH | 10 | 56 | 92 | 0 | 0 | 4 | 36 (tick running) |
| FAIL | 55 | 0 | 110 | 77 | 14 | 3 | 0 so far |

2 h totals: FAIL 259, LAUNCH 162 (13:50 review: 120 / 212). FLOW-HEALTH.tsv hour 14: launches 92, fail before
P&R 187, passes 0.

| Count | Die | Stage | Class | State at 15:45 |
|---|---|---|---|---|
| 177 | S81 | kit_rtl | `--src-tree`, logged as "KW_ROAM kit_rtl: ran on X, outputs copied back to Y" | closed by merge 15:35 |
| 74 | S81 | kit_rtl | `bind.py: unrecognized arguments: --src-tree` (B6gE/src) | closed |
| 5 | QC | kit_rtl | same (qc-s29-tree2) | closed |
| 1 | KV | kit_rtl | same, on the new tree src_kv_kvgeom7u, 15:33 (2 min before the merge) | closed; see class 2 |
| 2 | HEAD | resume | "relaunch refused: every kit input ... equals the previous attempt" | correct refusal; see class 6 |

257 of 259 fails are one procedural class. No ENOSPC, no GEN-DISK-LOW, no GEN_LINT, no KIT_NOT_SELF_CONTAINED,
no design-class wave fail in the window. 0 fails since 14:25 other than the 3 above, because nothing was launched.

## Is the wave under-launching? Yes, from 14:10 to 15:44; it is recovering now, partly

Eligible versus launched, from kit_wave.json (15:37) and kit_wave_state.json (15:35), items of the current event:

| Die | Event | Items | Held by item | Free, no row | Free, failed kit_rtl | Running/queued | Launched 14:25-15:44 |
|---|---|---|---|---|---|---|---|
| S81 | B6gE 3fa87b84 | 398 | 352 | 5 | 37 (+4 retry-infra) | 2 free, 38 held | 0 |
| QC | S4Q3C | 130 | 46 | 89 | 7 | 0 (33 run on S4Q3B) | 0 |
| KV | kvgeom7u | 89 | 41 | 49 | 1 | 0 | 1 (failed) |
| HEAD | rp21z20NF6 | 26 | 5 | 6 | 2 refused | 13 | 3 |
| HBM | pEv11c | 154 | 107 (+ die `*`) | 88 | 0 | 5 | 0 (parked, owner) |

"Free, no row" is an upper bound: it includes items already signed on an equal type block (QC 6, KV 5 signed).

Reasons, in order of size:
- S81 + QC die-level `*` holds 14:07-15:37: about 48 S81 and 96 QC items were launchable and waited 88 min.
  Running attempts past kit_rtl were not touched, which was right. The hold was right at 14:07; it was 60 min too
  long because its release term (merge of kitrtl-fail-1115) sat behind a serial merge-queue gate (class 3).
- KV: 50 free items, 0 launchable hosts (class 2).
- S81: 352 item holds. 249 of them say "13:32 B6gE adopt" with release on Event F/G/G1d plan events. These are
  design holds and outside this review, but the wave count must be read with them: S81 volume cannot return
  before G1d adopts, whatever the flow does.
- Launch rate inside a tick is about 13 per minute (one launch per 4.5 s, serial). 140 items need 11 min. This is
  not a limit today; it adds to the tick length (229 s at 15:36, 873 s on the 13:4x adoption tick).

There is no launch cap in the config (max_launch_per_tick 100000) and no admission refusal on a build host.

## Summary, ranked by waste

| # | Class | Count | Trend vs 13:50 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Die-level hold waits on a merge that waits on a serial gate | 2 dies, 88 min, about 144 launchable items | new (follows class 1 of 13:50) | about 20% of fleet threads idle for 1.5 h; zero new S81/QC kits for 2.5 h | MERGE-QUEUE-1, WAVE-HOLDS-1115 |
| 2 | KV switch to 7u: bind report names origin-host paths; no gen host is whole | 5 of 5 gen hosts, 15 SRC-INCOMPLETE lines, 50 items | new at 15:24 | KV wave at 0 since 15:24 (and at 2 launches in the 2 h before) | KIT-OPS-5 (staged by WAVE-HOLDS-1115) |
| 3 | Merge queue gate throughput | 14 READY in hour 14, 4 MERGED; 7 waiting at 15:1x; lanes hand-gating 35-90 min | worse, then fixed 15:1x-15:40 | under 1% CPU; it set the length of class 1 | MERGE-QUEUE-1 |
| 4 | `--src-tree` tool skew | 257 fails, 2 h | 118 -> 257, then 0 after 14:25 (hold) and merged 15:35 | 0 CPU; one more hour of S81/QC kit_rtl loss before the hold | KITRTL-FAIL-1115 (closed) |
| 5 | No-progress watchdog cannot fire | EXCLUDED 66 of 109 rows; openroad over 6 h: 38 | flat (83 of 106; 43) | about 8% | new Sonnet lane (WAVE-PREPNR-1115 silent) |
| 6 | Signed type relaunched | 13 SIGNED-UNVERSIONED lines, 7 items; hd_spn_eshim_tx and hd_turn_a relaunched then refused | falling (20 items); 14 held by name | under 1% in this window | SIGNED-TERMINAL-1115 (fix red at 15:09) |
| 7 | Test leaves `lec_async.sh watch` processes | 15 on the hub (oldest 8.7 h), 16 on epyc8, 3 on epyc9, 2 on epyc2 | new finding | 0 CPU; cause of the 2400 s gate timeouts with class 3 | FLOW-HEALTH-1 |
| 8 | Copied kit carries the source kit's gate logs and signoff.json | 2 cases (HEAD v1f, S81 hwC) | new finding | 2 false results; one lane-hour each | KIT-OPS-5 |
| 9 | Class breaker and BLOCKED still not on main | 28 BLOCKED lines, kit_wave_blocked.tsv has 0 rows (file of 08:14) | open, third review | under 1% CPU | FLOW-HEALTH-1 |
| 10 | Scratch disks at the floor | hub 131 GB (97%, 165 at 14:00), epyc7 114 GB (99%), epyc2 115 GB, epyc8 140 GB, localhost REFUSED (139 < 150) | worse on the hub: minus 17 GB/h | 0 now; hub reaches the 64 GB launch stop in about 4 h | CLEAN-ALL-1115 |
| 11 | Bookkeeping | STALE 141 current (+108 superseded); S81 unowned 144; PLAN-CORE-NOT-IN-ONLY hbm 22 cores every tick | flat (136; 150) | none | FLOW-HEALTH-1 |

Closed since 13:50: adoption without a tool test (adopt_guard.tool_smoke merged 14:34), typed hold release
(apply_hold_release_on is in rt/current, r165), sparse-gate false timeouts (mq-gate-deps merged 15:40), config
drift (kit_wave.json equals origin/coord/state; rt/current equal on 6 hosts).

## 1. A die-level hold that waits on the merge queue

Measured: 14:07 WAVE-HOLDS set `*` on S81 and QC with release on merge:claude/kitrtl-fail-1115 plus a smoke
result. KITRTL gave ETA 14:35. The branch was approved in r175 at 15:19 and merged at 15:35 through a manual
`tick --only`. The config lift is 15:37; the first launch is 15:44:42. From 14:25 to 15:44 the wave launched 4
items. ot-run at 15:43: epyc2 admits 605 GB, epyc8 584, epyc10 418, epyc9 400, intel1 319, epyc7 299.

Root cause in the process: a fix that unblocks two dies had the same queue position as 13 other READY lines, and
the 14:15 tick spent 19 min gating 114 files for one branch. The hold itself has no priority link to its release
term. r165 auto-release would have saved the last 2-9 min only (it needs the merge).

Structural fix:
- MERGE-QUEUE-1: a branch named in any `hold_release_on` term of kit_wave.json is gated and landed first. The queue
  reads the config; no ruling is needed. With parallel gates (r175) this is an ordering rule, 10 lines.
- WAVE-HOLDS-1115: a die-level `*` hold must carry a number: launchable items behind it. The loop-gap line prints
  "die hold S81: 48 items, 52 min, waits on merge X (queue position N)". Over 30 min it is a COORD line.
- KITRTL-FAIL-1115 form for the next time: the same-hour bypass existed (the lane's main-tool-on-tree form could run
  from the branch through `die_gen_env` for two dies). Rule for COORD: a wave fix that unblocks a die may run from
  its branch tree behind the hold for a 3-item smoke, so that the smoke term is met when the merge lands.

## 2. KV on kvgeom7u: no whole gen host (new, open, unowned)

Measured at 15:45 on the hosts:

| Host | src_kv_kvgeom7u | kw45/kvbind_kvgeom7u/out | kv-102/kvgeom7/out4_kvgeom7u/bind/out/rtl |
|---|---|---|---|
| epyc7 | present | missing | 167 files (origin) |
| epyc8, epyc9, epyc10, intel1 | present | present, rtl 167 files | missing |
| epyc2 | missing | missing | missing (not a KV gen host) |

The wave reports on epyc8/9/10/intel1 "kv-102/kvgeom7/out4_kvgeom7u/bind/out/rtl/bind_cells.sv missing" and on
epyc7 "kvbind_kvgeom7u/out/bind_report.json missing". So the bind report (or the manifest the completeness check
reads) names the files by the absolute path of the host where the bind ran, and the staged copy sits at another
path. Every gen host fails the check; the die has none. The 15:24:39 launch of kv3_pc__cl254f2e73 came 16 s
after the first SRC-INCOMPLETE lines and failed at 15:33 (kit_rtl, `--src-tree`, before the merge). The 2 hg/hgi
pilots of r168 have not launched. WAVE-HOLDS posted "staged epyc7/8/9/10/intel1" at 15:24.

This is the 10-25 class again (bind manifest with absolute paths of a frozen worktree).

Fix now (KIT-OPS-5, one step): make the bind out exist at the path the report names, or rebind the report to the
staged path: copy epyc7 `kv-102/kvgeom7/out4_kvgeom7u/bind/out` to `kw45/kvbind_kvgeom7u/out` on epyc7 and rewrite
the rtl paths in the staged bind_report.json to the kw45 path with the tool that stages it (not by hand per host).
Structural fix (new test in the staging tool, FLOW-HEALTH-1 or KIT-OPS-5): the stage step ends with the wave's own
`src_incomplete` check on every gen host and refuses the config commit when fewer than 2 hosts are whole. A wave
switch that leaves 0 gen hosts must not be committable. Bind reports store paths relative to the bind out root.
adopt_guard (r154) checks tool flags; add this data check to the same guard.

## 3. Merge queue throughput

Hour 14: 14 READY, 4 MERGED, 2 BOUNCE. Hour 15: 6 READY, 7 MERGED, 2 MERGE-FAIL, 1 BOUNCE. The two BOUNCE lines at
14:35 and 14:40 are the same sha bounced twice. GENBUG's hub gate for drt0255 was silent 1.5 h. At 15:45 the hub
runs three `gate claude/signed-terminal-1115*` processes (23, 21, 6 min old), two of them for the same r2 sha.
The fixes landed: gate deps (15:40), parallel gates + remote runner + land on a green record (r175).

Remaining structural items for MERGE-QUEUE-1:
- One gate per (branch sha, main sha): a second `gate` call for a sha that is in gate attaches to the first run.
- A superseded sha leaves the queue when its branch gets a new head (7 waiting at 15:1x included superseded shas).
- Lanes stop hand-rolled gates: READY without a GATE stamp enters the remote runner instead of a BOUNCE. The
  BOUNCE-for-stamp rule costs a lane 35-90 min per branch and the queue re-gates anyway.
- A gate run kills its own process group at exit (see class 7).

## 5. No-progress watchdog (third review, no code)

NOPROG-TABLE 15:30: EXCLUDED 66, YOUNG 34, NO-DATA 4, KEEP 3, PROGRESS 2. 15:45 run: 0 flagged, 0 cancelled.
openroad over 6 h: intel1 7, epyc9 9, epyc2 8, epyc10 7, epyc7 4, epyc8 3 = 38. Still YOUNG: epyc2
col_h9_r0_p2 at 25.5 h, kv3_hgi_v2 GRT at 13.0 and 16.5 h with best = last ("series started inside the last 6 h").
r169 merged the stage-aware GRT metric; the exclusion on command text and the series-restart reset are unchanged.
REAP-DEAD SILENT prints QC glue and native59 every tick (no output 1034 min) and correctly keeps them.

Fix as before: exclude on the declared priority in the unit environment; evidence age runs from the best value
across series restarts and is bounded by process age. Owner: WAVE-PREPNR-1115 has not posted since 08:33. COORD:
start a new Sonnet lane NOPROG-EXCL-1115 from this section; do not wait for the old lane.
This is a stop for jobs with no progress evidence; it adds no limit on a run that improves.

## 6. Signed types relaunched

13 SIGNED-UNVERSIONED lines since 13:45, 7 items (HEAD hd_tile, hd_turn_a, hd_turn_b, hd_spn_eshim_tx; QC
sle_su_l0, slw_su_l0; KV kv3_io_ft_v1). HEAD launched hd_spn_eshim_tx (14:34) and hd_turn_a (15:04) after their
sign-off; both ended 9 min later in "relaunch refused: every kit input equals the previous attempt". The refusal
works, the launch should not exist. 14 items are held by name (r152). signed-terminal-1115 failed 2 tests at 15:09;
r2 @8ee6a2d068c is in gate. QC sle_su_l0__cl086d85ba signed at 15:42 on S4Q3B and is the next candidate for a
relaunch on S4Q3C if its type block is equal. Fix unchanged; MERGE-QUEUE-1 lands r2 after flow-health.

## 7. Tests leave `lec_async.sh watch` processes

Hub, 15:44: 15 `lec_async.sh watch` processes. 4 from wt/flow-health-1 and /tmp/fh_pt* (485-522 min), 8 from
/tmp/fh_main2 with /tmp/otst-* kits (296-306 min), 2 from fh_pt61/fh_pt71, and 2 from the merge queue's own gate
trees (mq1/wt/gc-b91c191fd6, 84 min; gc-954e9e3302, 10 min). Every one belongs to
`test_missing_proof_reference` or an otst kit route1 test. epyc8 has 16 pytest/watch processes over 1 h old,
epyc9 3, epyc2 2 (the remote runner hosts). So the leak is in the test, on every run, on every host that gates.

Root cause: the test starts the watcher detached and its proof never arrives, so the watcher polls for ever. A
watcher that holds the pytest worker's stdout keeps `pytest -n` from returning; that is the likely form of the
three 2400 s kv-pvgen timeouts after the sparse-tree fix (not proven here; I did not read that gate log).

Structural fix (FLOW-HEALTH-1, it owns lec_async r128):
- lec_async.sh watch exits when its kit dir is gone and takes a deadline from the caller in tests
  (`LEC_ASYNC_WATCH_MAX_S`, unset in production).
- conftest fixture: each test runs in its own session id; teardown kills the session. The merge-queue gate runs
  under `systemd-run --scope` (or setsid + kill of the group) so that a gate cannot leave a process.
- CLEAN-ALL-1115 removes the present ones by exact pid after an owner check (no pattern kill; hook rule).

## 8. Copied kits carry old results

Two cases today (HEAD v1f, S81 hwC): a lane copied a kit dir to try a variant; the copy kept the source's gate
logs and signoff/signoff.json; the lane's report read them as the variant's result. Same class as the 10-27 stale
sign-off log.

Structural fix (KIT-OPS-5): one tool `kit_fork` is the only way to copy a kit. It copies inputs and the chosen
resume ODB and nothing under signoff/, logs/, reports/, gate records; it writes `FORKED_FROM` with the source
path and time. The result readers (classify, signoff reader, lane summary script) refuse a signoff.json whose
recorded input digest does not equal the kit's current digest; the digest is already computed for the relaunch
refusal (class 6 shows it works). Then a stale result cannot be read as current even after a plain `cp -a`.

## 9. Class breaker

28 BLOCKED lines 13:45-14:20 (S81 kit_rtl 3x), each followed by more launches until the die hold at 14:07. With
a breaker of 10 per hour per (die, stage, class) the 13:4x S81 burst stops after 10 fails, not 251.
flow-health-1115b @954e9e33029 has a green gate record (193/193) and is first in the train since 15:41. COORD:
check MERGED by 16:15; this is the third review that lists it.

## 10. Disk

Hub scratch2 131 GB free, 97% (165 GB at 14:00, 204 at 12:35): minus 17-20 GB per hour; 140 rt trees (128 at 14:00,
118 at 12:00; each merge adds one, 7 merges per hour now). The 64 GB precondition of flow-health will stop all
launches at about 19:30 at this rate. epyc7 114 GB (99%), epyc2 115 GB, epyc8 140 GB; gen floor is 70 GB.
localhost is REFUSED by ot-run (139 GB < 150 GB floor).

Fix (CLEAN-ALL-1115, this hour): prune rt trees on the hub to the ones named by a live unit, a queued job or the
last 10 merges; run the aggressive pass on the hub, epyc7 and localhost. Structural: ot-tools-sync deletes an rt
tree when no process or unit references it and it is not one of the last 10; the tree count then stays flat.

## 11. Bookkeeping

STALE 141 current-event (+108 superseded): S81 165 (unowned 144), most of them DEDUP/SUPERSEDED rows of 11-14 on
col types that are held for Event F/G. They are not launchable work; failure_breakdown should not count a row
whose item has a `hold_items` entry with a plan-event release as STALE unowned (FLOW-HEALTH-1, one filter). Then
"unowned" shows real gaps only: today S81 kit_rtl 12 rows, QC "other flow error" 7 and "kit input missing" 2.
PLAN-CORE-NOT-IN-ONLY hbm prints 22 cores every tick (12 lines in 2 h); HBM is parked, print once per change.

## For COORD, in order

1. KIT-OPS-5 now: KV 7u bind out path (class 2). KV has 0 gen hosts; r168 pilots cannot start.
2. MERGE-QUEUE-1: land flow-health-1115b @954e9e33029, then signed-terminal r2; add "hold release branches first".
3. Read the 15:44 tick result: if S81/QC kit_rtl passes, class 4 is closed; if any `--src-tree` or new kit_rtl
   class appears, the breaker is not there yet, so WAVE-HOLDS re-holds by hand the same tick.
4. CLEAN-ALL-1115: hub rt trees and scratch2 (131 GB, minus 17 GB/h).
5. New Sonnet lane NOPROG-EXCL-1115 (class 5, about 8% of the fleet, third review).
6. FLOW-HEALTH-1 after the merge: lec_async watcher deadline + gate process scope (class 7); KIT-OPS-5: kit_fork
   and digest check on signoff.json (class 8).

Not checked: the content of the kv-pvgen gate logs; whether the QC 89 no-row items include items signed on an
equal block beyond the 6 counted; the result of the 15:44 tick beyond its first 3 min.
