# FABLE-FLOW-1900: procedural and flow failures, 15:45-17:48 PST (2026-11-17)

Reviewer: FABLE-FLOW-1900 (Fable). Read-only: no kills, no deletes, no config edits.
Measured 17:43-17:50 PST on the intel2 hub and the 6 build hosts. Sources: autopilot/log.txt 15:45-17:46,
failure_breakdown.py (17:43), `ot-run --status`, kit_wave.json, kit_wave_state.json, rt/history.log, origin/main log,
lanes/posts 16:50-17:44, tools_refresh log and units, per-host ps / docker images / df. Previous: FABLE-FLOW-1700.
Shares are estimates from live-job counts and idle threads.
Not checked: AGIdock, thread-hours per job, whether an old-event plan block equals the current one (class A),
the cause of the one QC KIT_NOT_SELF_CONTAINED at place (C3).

## Headline

1. The wave launches again: 60 launches in hour 16, 49 in 17:00-17:46 (QC 60, KV 47, HEAD 2, S81 0). SIGNED: 2.
   UNDER-USE 17:42: 341 of 624 threads idle (45% used).
2. 24 of the 28 KIT-WAVE FAIL lines are procedural or infra, none of them a design result: 11 disk full (epyc9),
   7 partial bind copy (KV), 5 missing docker image (epyc7), 1 QC kit input. The other 3 are one known plan error
   relaunched through a leaked hold (class D).
3. 38 of 103 live kit items (37%) run on a superseded plan event: QC 28 of 63, HEAD 10 of 10, KV 1 of 30 (class A).
4. tools_refresh still applies nowhere. The KV refresher is now a loop: 9 starts today, every one AP_RC=1, 2 units
   alive at once at 17:48 (class B).
5. S81: 0 launches in the window, 127 current-event rows in FAIL FLOW, 17 enqueued. It waits for the D6z tree.

## 1. Fixes since 17:00 and the 1700 "do now" list: live and working?

rt/current = main 41129805aac4 on the hub and all 6 hosts (17:37-17:38). r641 is approved, not yet on main.

| Item | Live | Working |
|---|---|---|
| r626 QC preflight frame pairs | rt 7/7 | yes: QC 39 launches in hour 16 (0 before) |
| r628 tools_lag by ancestry | rt 7/7 | yes: TOOLS-LAG now lists r407..r640 per die; HEAD shows r618-r640 |
| r629 tree_has release term | rt 7/7 | unused: 0 tree_has terms in kit_wave.json (class B) |
| r630 apply replicates, no narrowing | rt 7/7 | yes for HEAD NF15f (17:23, tree on 4 hosts, ADOPT-ROWS line). QC N1B was applied before it: tree on epyc8 + epyc9 only, gen_hosts = [epyc8] |
| r632 event lineage | rt 7/7 | yes: HOLD-TERMS "no producer" (NF15c) stopped after 16:36 |
| r633 ot-run NOT-RUN exit 78 | rt 7/7 | not exercised: 0 NOT-RUN lines |
| r634/r635 kit self-containment | rt only | not in any die tree (class B) |
| r636 KV pc keepout | rt only | not in a KV tree; goes with D22 |
| r637 whole bind_out | rt 7/7 since 17:37 | prevention not exercised (0 SRC-INCOMPLETE lines). State is right now: kv-r3/d16gate/bind has 29 entries, 630 MB on all 6 hosts. Last fail of the class 17:19:29 |
| r638 serdes H-form part 1 | rt only | no, and DEFECT posted 17:37: serdes_boot_release_local.tcl has t13 coordinates hardcoded; wrong for the other 10 types |
| r639 host requires + place_prefer | rt 7/7 | derive_gen_hosts ran: KV 4 hosts, HEAD 3, QC 1 (epyc8) |
| r640 flow image keep list | rt 7/7 | yes: flow_images.txt present; opentallas/orfs:asap7lock-grtoff on 6/6 hosts (17:47). The 5 items that failed are still not relaunched (C1) |
| r641 family hold margin | no | not on main at 17:44 (FABLE-FIX-QC-N found 0 occurrences in rt) |
| 1700 F: COUNT-REVOKED sd9f | yes | row present (sha256 e4f6d7f4...) |
| 1700 C: retry-probe | yes | 3 probes per class run. Release rule still wrong (C2) |
| 1700 B2: one refresh per die per hour | no | worse (class B) |
| 1700 H: second term on S81 serdes holds | partly | term added, but it is a `result:` term again (class B) |
| 1700 I: quota stop | no | still "alert only, nothing stopped"; epyc9 reached 0.5 GB (C3) |

## Classes, ranked by fleet time wasted

### A. Work on a superseded plan event (37% of live kit items; trend up, was "90 rows" at 1700)

- Count: live processes by event (ps on 6 hosts, 17:46): QC L2 18, Q6D 9, S2 1 against N1B 35; HEAD NF15d2r1 9 and
  NF13a 1 against NF15f 0; KV kvgeom4 1 against HG5 29. State: 63 old-event rows ENQUEUED (QC 37, HEAD 18, KV 5,
  HBM 2), ages 1-94 h; UNDER-USE line: "superseded-event rows 99".
- Second effect, an over-hold: LAUNCH-KEEP "one live attempt per item" is keyed by item, not by event. HEAD NF15f
  has 0 launches 25 min after apply: the pilot hd_lep0N is kept out by its NF13a attempt 3 (a 33-h GRT on epyc10),
  hd_mesh by its NF15d2r1 attempt 2 (HEAD-PLAN-R4 BLOCKER 17:41). Last tick: 6 QC and 3 KV items kept out the same way.
- Root cause: adoption does not judge the live rows of the replaced event. RETIRE-SUPERSEDED reports "retired 0,
  relaunch-on-current 2" each tick.
- Fix (WAVE-FLOW-R2): at adopt, in the same tick, every live old-event row gets one of two outcomes by plan block sha:
  block unchanged in the new plan -> REKEY (keeps running, counts on the new event); block changed -> the old attempt
  is stopped and the item launches on the current event. LAUNCH-KEEP compares block sha, so an old-block attempt never
  keeps out a current-block launch. ADOPT-ROWS prints `rekeyed n, stopped n, launched n` and alerts on a rest.
- Now (HEAD-PLAN-R4, QC-PLAN-R3): decide the 10 HEAD and 28 QC old-event jobs by block sha; I stopped nothing.

### B. Fixes do not reach kits (about 25%; flat, fourth review in a row)

- TOOLS-LAG 17:40: s81 674 commits behind, qwen_compute 889, hbm 1986, s81_head 48. HEAD NF15f went live 17:23 on
  main 8569788b and is already 22 rulings behind (r618-r640). No tree holds r634-r641.
- KV refresher loop: starts 16:21, 16:40, 17:25, 17:32, 17:40, 17:46; all earlier ones AP_RC=1. The attempt key
  contains the main sha, so each new main commit is a new attempt. No single-flight: units ...6006 and ...6360 ran
  together at 17:48. 8 dry trees `_d16_t<sha>` exist (276 MB each, on up to 6 hosts). 17:43 it posted NEEDS-LANE:
  strict bind cannot run because the delta touches bind.py's import closure (60 modules). It will start again anyway.
- Release on merge: both S81 serdes holds (11 + 6 items) wait on `result:FABLE-FIX-S81-SERDES2:rail-gen` (posted
  17:10) and `result:S81-SERDES-GEN:h-form`. When that post comes, 17 items launch on tree d5e, which has neither r620
  nor r638, and r638 has an open defect.
- Fix (WAVE-FLOW-R2): (1) refresh is single-flight per die (flock), keyed by die + tree, target = rt/current at start,
  at most one per hour; a NEEDS-LANE or COMPOSE-FAIL result stops restarts until the lane answers; the previous dry
  tree is removed when the next one publishes. (2) hold validation refuses a `result:` term for a generator fix
  without a `tree_has:` term. (3) publish_gate refuses a tree whose tools base lacks a ruling that names its die.
  S81-TYPES-R3 now: add `tree_has:r638` (and the defect-fix ruling) to both holds.
- End state (unchanged since 1300): kits take tools from rt/current; a tree pins rtl + plan only.

### C. Self-inflicted infra failures (23 of 28 fails; about 4%)

- C1 image prune (5 fails, 17:05-17:26, FLEET-OPS-R). Prevention works (r640). Two gaps: (a) the fail is classed
  FLOW[design:place] "unclassified", and LAUNCH-REFUSED "same fail key" has no host part, so restoring the image at
  17:31 released nothing: kv3_hg_v1p3, v1p4, v1p5, kv3_pv_v8, kv3_hgi_v1__cl42bc8b12 are still FAIL at 17:46.
  (b) FAIL-ROUTE asked 4 owners in 30 min for the same two classes (17:08-17:38) although KV-R3 (17:18) and
  FLEET-OPS-R (17:31) had answered. Fix (WAVE-PILOT-FIX): "image missing", ENOSPC and PUBLISH FAILED are INFRA (one
  free retry on another host); the fail key includes the host-requirements digest; FAIL-ROUTE closes a class on a
  RESULT that names one of its items. Now: retry keys for the 5 items.
- C2 partial bind copy (7 fails, 16:51-17:19, KV-R3). r637 covers gen hosts. Gaps: (a) the breaker released the
  class twice on "preflight passes again" (17:00:36, 60 s after opening, and 17:20:28) while preflight could not see
  the cause; the ContractError class closed at 17:19 on "probe passed gen" for 9 families at once. (b) die bind_out
  still points into lane dirs: kv-r3/d16gate/bind, and the D21 candidate fable-fix-kv-hg2/d21gate exists on epyc10
  only. One lane cleanup breaks every KV kit. kv3_hgi_v1__cl141fc26e is still FAIL.
  Fix (WAVE-FLOW-R2): apply copies bind_out into the tree (`<tree>/bind_out`), kit_wave reads it tree-relative,
  publish_gate refuses a bind_out outside the tree. A class releases only on a probe that passed the failing stage.
- C3 disk (11 ENOSPC fails at 17:19 on epyc9, FLEET-OPS-R). GEN-DISK-LOW fired at 16:46 (52 GB); the quota alert
  (kw45 306 GB in 6 h) stopped nothing; 0.5 GB at about 17:15. Recovery was good: all 11 relaunched on epyc8 by 17:20.
  One more QC item (slw_fe_v1__cl95cd1d0c, epyc9, 17:12) failed as KIT_NOT_SELF_CONTAINED at place and is refused on
  the same fail key; probably the same event, not verified.
  Now: epyc9 149 GB, epyc8 141 (62 GB/h at 17:00), epyc10 70 (the gen floor), localhost REFUSED (112 < 150).
  QC generates on epyc8 alone. Fix (FLEET-OPS-R): floor ETA under 1 h holds the host for new jobs and starts the
  cleanup pass by itself; a lane over quota loses new launches on that host. QC-PLAN-R3 now: N1B tree to epyc10,
  intel1, epyc7.

### D. Hold leak (3 attempts, under 1%)

- QC slw_st_a_v1__clfc5867a6 x2: MPL-0034 known since 10:50. Commit bcec53b re-pointed the QC holds in bulk to
  `event_adopt:s29q103S4Q9N1B`; the fix is only in N2B. 16:00:20 HOLD-AUTO-RELEASE, launches 16:17 x2 and 16:34
  ("changed overlay", 16 min after the previous launch), fails 16:46 and 17:05, hold back at 17:05.
- Fix (WAVE-PILOT-FIX; QC-PLAN-R3 for the records): a hold carries the fail key of its cause; auto-release needs the
  term AND a changed input of that key. For PLAN fails the key is the error signature (macro, coordinates, core box),
  compared across events. "changed overlay" relaunches an item only when the overlay part that item reads changed.
  A bulk re-point of release terms is refused; each hold is re-pointed with a reason.

### E. Hub and hand edits (about 1%)

- `ot-gate-remote` has no argument check: `$1` goes straight to `gate "$1"`, so `--help` starts a gate; on the hub it
  runs locally (line 45). A second hub gate ran at 17:43 (head-xo-hop). Hub load 23.7, 91 sessions.
  Fix (FLEET-OPS-R): argument must match `claude/<branch>@<sha>`, else usage and exit 2; refuse on the hub unless
  OT_GATE_HUB=1.
- HEAD pilots were set by a direct kit_wave.json commit (3c531443) one minute after the atomic apply. Fix: apply takes
  `--pilot`.
- ALERT HUB-SYNC-FAILED 17:11, 17:39, 17:44: cron-written lanes/STALE.tsv and NOPROG.tsv are tracked files with local
  edits. Fix: generated tables are committed by their writer (coord-commit) or untracked.

### F. Stale and unowned (flat)

STALE current-event 121 (1700: 122): S81 5, QC 16, HBM 107 (parked). Unowned 15: QC 4 (3 FAIL kit_rtl since 06:21,
1 superseded), HBM 11. NOPROG-DRIFT: noprog_stage.py differs from main on 7 hosts (unchanged).

## Do now

1. WAVE-FLOW-R2: adopt-time rekey-or-stop by block sha, LAUNCH-KEEP by block (A); refresher single-flight (B).
2. HEAD-PLAN-R4, QC-PLAN-R3: judge the 10 HEAD and 28 QC old-event jobs; N1B tree to 3 more hosts.
3. WAVE-PILOT-FIX: retry keys for 5 KV image items + kv3_hgi_v1__cl141fc26e; INFRA classes; breaker release on the
   failing stage only; hold release needs a changed cause.
4. S81-TYPES-R3: `tree_has:r638` on both serdes holds before S81-SERDES-GEN posts h-form.
5. FLEET-OPS-R: disk ETA hold + quota stop; ot-gate-remote argument check; tracked cron tables.
6. KV-R3 + WAVE-FLOW-R2: bind_out inside the tree.
