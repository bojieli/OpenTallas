# FABLE-FLOW-2000: procedural / flow review, window 11-21 17:45 to 19:50 PST

Lane FABLE-FLOW-2000 (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched, deleted
or edited. Previous: lanes/FABLE-FLOW-1900.md (window 12:23 to 18:50). This file replaces the 11-20 report of the same name
(kept in git history).
Sources: autopilot/log.txt (17:45 on, 1,038 lines), kit_wave.json and kit_wave_state.json (19:47), lanes/FLOW-HEALTH.tsv (19:10),
RELEASE_TREE.md failure block (19:20), `ot-run --status` (19:46), ~/.local/state/ot-run/signals.log, disk-rate.log, rt/history.log,
rt/current (5aab47bd4b12) kit_wave.py and host_drain.py, the auto-export spool, `docker ps` on intel2, posts of FLOW-OPS-1300,
FLEET-WATCH-R8, CLEAN-AGGR-1121/-R2, FLOW-LECGATE-R1/-R2, FLOW-CANARY-R2, KV-PLAN-R6 and the family lanes.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: no git history was read. "Share" is an estimate (I) of fleet thread-hours in the 2 h window unless marked.

## Headline

1. **Disk is no longer the limiter.** Scratch free at 19:46 (V, ot-run status): epyc10 1192, intel1 1197, epyc9 1170, epyc8 820,
   intel2 587 (797 by df at 19:50), epyc7 579, epyc2 374 GB. `host_drain` is empty. Admission refusals: 182 REQUEUE in the
   window, 175 of them 18:20 to 19:09, 8 after 19:10. Cause of the recovery: the guard list fix (1326932a95, f2e05fd6ee,
   2095d6a53d) plus about 13,200 idle attempt dirs deleted (R CLEAN-AGGR-1121). The inflow side (full tree copies per lane and
   per host) is unchanged.
2. **The cleanup that fixed the disk did damage in three places** (class C3): 60 closed units deleted against the signed store
   instead of the export index (2 signed records lost, 9 LOCAL_PASS deleted, R); two kit dirs deleted at 19:24 that
   FLOW-LECGATE-R2 tried to re-LEC at 19:35 (2 units rc 1 in 3 s, V); 25 wave rows cancelled as "superseded ENQUEUED", 6 of
   which had a live container (V).
3. **The structural fix for drained-host launches has not landed.** FLOW-OPS-1300 "computed drain + host-add gate" is committed
   in its clone; `ot-push-main` failed at 19:13, 19:28 and 19:44 (rc 4 after 278, 819, 925 s). The class stopped only because
   the hosts were undrained by hand.
4. **Pushing main is now a queue of its own**: 14 pushes rc 4 against about 20 real rc 0 in the window (V, posts), about 75 min
   of lane wall time in failed attempts. Class B1.
5. **Launches resumed**: 75 LAUNCH lines (62 in hour 18, 13 in hour 19), 3 FAIL lines. 67 rows started in the window are RUNNING.
   Tick time 420 to 595 s (kit_wave_step 378 to 495 s), one TICK-KILLED (19:18, no launch pass until 19:35).
6. **Sign-off count 527 any plan / 437 current (V 19:10), +3 / +4 since 18:20.** 23 LEC rows stand in COUNT-REVOKED.tsv.

## What FABLE-FLOW-1900 asked for: landed or not

| 1900 item | State at 19:50 |
|---|---|
| (a) gen-host pick reads drain; one admission function | NOT landed. Push failing (headline 3). Hosts undrained by hand 18:51 to 19:26 |
| (b) intel2 input closure | DONE by hand 19:32 (R: 3 bind dirs + 441 files copied, re-probe empty). SRC-INCOMPLETE intel2: last line 18:58 (V). Host-add gate NOT landed |
| (c) guard protects by need (R1) | LANDED. Guard list 3,175 to 2,244 roots (R). R2 (retire below protected child): not needed now. Full protected path in log: not landed |
| (d) superseded ENQUEUED / ROUTE-HELD get a terminal state | Applied once by hand (25 rows), not as a wave rule. RETIRE-SUPERSEDED still prints "retired 0". Left: ENQUEUED 38 and ROUTE-HELD 109 on superseded events (V) |
| (e) sign-off tcl from rt; gate-relevant TOOLS-LAG | NOT landed. All four live dies still "missing r708" (V 19:37) |
| (f) canary INPUT-BROKEN, parked die not scheduled | NOT landed. Class C1 |
| (g) tool writers commit through coord-commit; parked die skipped by adopt-guard | NOT landed. HUB-SYNC-FAILED 8 alerts / 4 episodes; ADOPT-GUARD 74 alerts, 34 of them hbm (V) |
| (h) writer ledger | Manual only (FLEET-WATCH-R8 15 min ledger on intel2). Tool not landed |
| R3 one sealed base per pin, events as deltas | NOT landed. See classes A4, A5 |
| R5 ECO iterations keep two ODBs | NOT landed |
| item 14 `ot-run --status <unit>`, ot-wait off-hub | LANDED main 3fd5ccccd1 (R). Not re-tested by me |
| intel2 heavy refusal | LANDED main 3b2f4d0447, rt/current on intel2 19:26. Verified: 22 containers on intel2 at 19:50, among them dpkit-hd_turn_a (16 min), dpkit-col_h10_r1 (23 min), so_*_tt/ff sign-off pairs; ot-run shows intel2 run 32, load 74/112, admits 261 GB (V) |

## Classes

### A. Admission, hosts, trees

**A1. Gen-host pick launches on drained hosts: 55 launches, stopped by hand, fix not landed.**
- Count (V, state rows by start time and gen_host): 18:20 to 18:59, 55 rows: epyc2 22, epyc7 17, epyc10 9, epyc8 7; intel2 0 (50 of them before 18:50).
  At that time epyc2, epyc8, epyc10 carried a 9999 drain and epyc7 until 18:51. From 19:10: 13 rows, epyc9 10 and epyc7 3,
  none drained. REQUEUE "no host qualifies": 182 lines over 36 job dirs; epyc8 floor 97, epyc10 floor 73, intel2 name
  resolution 5. Per 10 min: 19, 31, 37, 49, 39, then 7, then 1.
- Root cause (V, kit_wave.py 5514 to 5516 in rt/current): `res = [h for h in res if h not in _dr] or res`. The drain filter
  exists, but when every listed gen host drains it returns the full list ("ot-run then refuses the new dir"). It fails open.
  At 18:22 every gen host of S81, QC and KV was drained, so the filter did nothing. The wave disk cap had been lifted by
  adding intel2, which the pick then excluded as SRC-INCOMPLETE.
- Structural fix (P): the same expression must fail closed: an empty list means the row waits with one line per die per
  15 min. One function for cap, pick and ot-run admission (1900 class a) is the full form; the one-line change is enough to
  make the class self-stopping.
- Owner: FLOW-OPS-1300. Share: under 2 % compute (gen and kit_rtl ran, place waited); 36 rows delayed 20 to 50 min.

**A2. A hand-set drain has no release term: over-hold.** epyc7 held a 9999 drain at 265 GB free until 18:51; epyc9 a 250 GB
cap until 18:51; intel1 a 250 GB cap until 19:26; epyc2 9999 until 19:26 at 382 GB (V and R). UNDER-USE reported 96 % used
because drained hosts are left out of its base (528 of about 730 threads counted). Fix (P): drain is computed with hysteresis, as
proposed in 1900; UNDER-USE prints the excluded hosts and their threads. Owner: FLOW-OPS-1300 (code), FLEET-WATCH-R8 (operate).
Share: about 8 % (I: intel1 22 to 36 load of 112 threads and epyc9 33 of 96 for about 1 h).

**A3. epyc7 is admitted by memory only and is thread-saturated.** ot-run status 19:46: epyc7 load 159/96, 61 running,
threads 520/96, admits 0 GB (V). FLOW-OPS-1300 runs its push tests there, which is why they fail on timing (B1). Fix (P):
admission counts requested threads against cores with a cap (for example 3x) as it does memory; push tests run on the host
ot-run names as "next job". Owner: FLEET-WATCH-R8. Share: not measured; every job on epyc7 runs slower.

**A4. Lanes build private trees by hard-link copy, and a link can point into an event tree: 2 incidents, new.**
- V (posts 18:51 to 19:42): FABLE-FIX-KV-HUB-R4 ran `cp -al` on a path that was a symlink to the D27d3 event tree. Its
  privatising step then moved the gated bind_of_record aside and rewrote plan_c.json inside the event tree. KV-PLAN-R6 stopped
  three exact pids and restored the tree. Separately the D27d3 seal passed and `verify --ro` failed: 324,773 files with
  nlink 11, because the tree itself was composed by `cp -al` from older trees. KV-PLAN-R6 killed its own replica copy
  (rc 143; R CLEAN-AGGR-R2: no reaper involved), made a real copy, and verify passed at 19:42. About 50 min of the KV plan
  event lost, plus IOPC-R4 and HUB-R5 waiting on the seal.
- Root cause: there is no tool for "give me a private writable copy of tree T". Each lane writes its own cp, rsync or link
  chain; the seal rule (no shared inodes) is checked only at verify, after the compose.
- Structural fix (P): one command (`ot-tree-fork SRC DST`) that resolves SRC with readlink -f, refuses a DST inside any
  kw45 or sealed tree, and makes either a real copy or a recorded `.link-base` overlay that verify accepts. Event trees are
  made read-only (chmod a-w, or chattr +i where allowed) at seal, and compose writes only into a new tree. This is R3 of 1900.
- Owner: new (DISK-RETAIN-1 was proposed in 1900 and has no lane). Share: about 1 %.

**A5. Lane tree copies to the admitting host: flat.** 18:42 to 18:55 two identical rsyncs of one 56 GB tree from epyc7 to
intel2 by one lane (R FLEET-WATCH-R8). Same missing tool as A4. Owner: new, with A4.

**A6. Self-heal re-copies files that cleanup removed: 16 ITEM-SYNC, new.** V: 16 ITEM-SYNC lines 19:1x to 19:40 (none
earlier in the window), 4 with rc 2, re-copying parts of superseded QC snaps (n46r4_a4, n46v0e_s2, v1r6 bind) to epyc2 and
epyc10 for bound rows. SRC-INCOMPLETE appeared on epyc9 (19:10), intel1 (19:22) and epyc2 (19:38) for qwen_compute; the
named postbind dir is present on intel1 and epyc2 at 19:50 (V), so those healed or were transient. I: the kw45 old-tree
batch removed trees that queued rows still name. Fix (P): the guard and the wave must use one definition of "tree needed by a
row"; a tree a row names is either protected or the row is retired in the same pass. Owner: CLEAN-AGGR-R2 with FLOW-OPS-1300.

### B. Tooling used by lanes

**B1. ot-push-main: 14 failures in 2 h, rising.**
- V (posts): rc 4 FLOW-OPS-1300 8, FLEET-WATCH-R8 4, TAP-GRID-R5 1, FABLE-FIX-QC-COLL 1. Failed attempts cost 27 s to 925 s
  each, about 75 min in total. One cause found (R FLEET-WATCH-R8 19:05): a base test went through `repick_stage_hosts()`,
  which read the live ~/coord kit_wave.json; when intel1 left the S81 gen_hosts the test changed verdict. Fixed in the
  fixture only. FLOW-OPS-1300 names load-sensitive ot-run tests for its three later failures.
- Root cause: base tests are not hermetic (live config, host load, wall-clock timeouts), and every lane pays for each one.
- Structural fix (P): the test runner sets COORD_DIR to an empty fixture dir and fails any test that opens a path under
  ~/coord or calls ssh; a test that failed and then passed on the same sha is quarantined automatically with one post, and
  does not block the next push. The owner rule "never --no-test" stays.
- Owner: FLOW-OPS-1300 (FLOW-NOADV-R3/R4 stood down; base-test triage has no lane). Share: 0 fleet; it delays every fix,
  including A1.

**B2. private-spec takes defaults from the live wave, not from the tree it was given: 3 reports, new.**
- R: `--tree <J7>` without `--bind-out` keeps the J6 wave bind (FAM-S81-COL-H9R0-R4, two launches failed at kit_rtl); without
  `--rt` the spec takes rt/current, whose reset_replicate.py differs from the J7 bind; on the sealed J7 tree the in-tree bind
  is stale for kit_topology (FAM-S81-SLICE-R6). On an r16 HEAD tree the default rt writes no kit_env_provenance.json
  ("SKIPPED"), and `--rt 01fa4a7bcd90` fails on a missing `sink_bins_8.json` (HEAD-CTL-R1). The lane then wrote the
  provenance record by hand.
- Root cause: a private kit has four inputs that must agree (tree, bind, rt, plan); private-spec lets each default
  independently and checks none against the others. Same class as the 11-21 wave-env memory entry.
- Structural fix (P): with `--tree`, bind and rt default to what the tree's seal manifest records; a mismatch between the
  tree and an explicit `--bind-out` or `--rt` is a refusal with the one command that fixes it. ENV-PROVENANCE is written by
  private-spec itself from the hub rt, never by the kit's rt, so "SKIPPED" cannot occur.
- Owner: FLOW-OPS-1300. Share: about 1 % (failed kit_rtl runs are short; the cost is lane time).

**B3. run-item ends at geometry for private kits; lanes drive run_kit.sh by hand: 5 lanes in 2 h, flat.**
- R: FAM-QC-CB-R2/R3, QC-SLE-R5, FABLE-FIX-QC-STRAP-R2, HEAD-CTL-R1. Side effects seen: GOAL=cts skipped the pre-GRT hold
  check and was first read as a flow bug; an advisory GRT hit a 600 s wall (rc 137); one kit resumed on a host under its
  disk floor. Lanes also edit spec.json by hand to carry A/B keys (R, earlier posts; no new instance found by keyword in
  this window).
- Root cause: the wave has stage chaining, hold gates and retry rules; a private kit gets none of them after geometry.
- Structural fix (P): `run-item --goal route|finish` for private specs, using the wave's own stage chain, and
  `private-spec --set KEY=VAL --why` as the only way to change a spec (recorded as declared A/B in the provenance record).
- Owner: FLOW-OPS-1300. Share: about 2 % (I: reruns for a wrong GOAL and waits between hand-launched stages).

**B4. Sign-off chain side effects.**
- Routed LEC advisory (fixed e5429d32c55): 24 records revoked (R); 23 LEC rows in COUNT-REVOKED.tsv at 19:50 (V: QC 18,
  S81 3, HEAD 1, HBM 1); 1 re-credited after a new LEC; 9 QC records have no RTL left and need a rebuild (R). Root cause:
  a sign-off check could be marked advisory in the chain without the count noticing. Fix (P): the count reads the list of
  gate checks from one table, and a record lacking any of them is not counted at ingest. Owner: FLOW-LECGATE-R2.
  Share: 9 rebuilds, about 2 % of the next window.
- Auto-export queued a measurement run: spool 98caa81c2b8bc9fe.json, name "tt", die / element / kind null, from a lane dir
  `zh_candidate_signoff` (V, file read). Root cause: the sign-off script queues an export whenever it writes signoff.json.
  Fix (P): queue only when the verdict is SIGNED and die, element and kind resolve; otherwise write nothing. The entry is
  still in the spool. Owner: FLOW-LECGATE-R2 (same chain). Share: 0.

**B5. Waiter tooling.** Landed (table above). No open item.

### C. Background machinery

**C1. Flow canary: 28 verdicts since 17:00, 1 PASS, flat; disk now bounded by hand.**
- V: s81_cl 6 FAIL (NO-BASELINE, stops before GRT and can never set one), s81_head 5, hbm_sram 4, s81_head_cl 4, hbm 3,
  s81 2, qwen_kvsys 2 FAIL and 1 PASS, qwen_compute 1. A new run set starts about every 15 min, one source checkout per main
  sha. Sizes at 19:50: runs 53 GB (36 dirs), sources 37 GB (8). At 18:55 FLEET-WATCH-R8 measured 121 + 112 GB touched in
  20 min; CLEAN-AGGR-1121 retired 13 sources and old runs.
- Root cause: the canary runs on every main sha, and main moves every few minutes (about 20 pushes in 2 h); a verdict that
  cannot change (no baseline, parked die) is recomputed each time.
- Structural fix (P): run only when the import closure of the canary's stages changed; a canary that cannot produce its
  metric is INPUT-BROKEN and is not rescheduled until its input or baseline changes; hbm is parked and not scheduled; keep
  the baseline runs and the last two per die, and one source per sha in use.
- Owner: FLOW-CANARY-R2. Share: about 3 % (I: 4 to 6 canary jobs running most of the window on intel1 and intel2).

**C2. Wave rows called ENQUEUED hide three different states: new.**
- V: the 25 rows cancelled at 19:04 to 19:36 were all "ENQUEUED". 23 ot-run clients that had STARTED 9 to 34 h earlier were
  signalled by the cancel. 19 had no container (waiters, or dead). 6 had a live container. After the cancel 11 were classified "kit logs
  idle 11.8 to 40.3 h"; three of the six with containers are among them (13.7, 17.1 and 26.6 h idle): hung jobs that the
  2 h watchdog did not see (WATCHDOG.log: ACT 0 on every tick). The other three with containers (native59,
  slw_hc1__cl68f9248e__cle683a076, slw_sc_v1__cl64543eaf__cl4590432d; submitted 03:06 to 09:59) have no classify line
  yet and the containers are gone. Whether they were progressing when cancelled is not known.
- Root cause: the row status does not say whether the queue job is waiting, running or dead; the hung-job check watches
  RUNNING rows only. The owner rule (never cancel a running old-plan kit that can still sign) cannot be applied from this
  status.
- Structural fix (P): status WAITING / RUNNING / STALLED derived each tick from container presence and kit log age; the
  watchdog reads all three; `cancel-rows --old-plans-only` refuses a row with a live container unless its log is idle over
  2 h, and prints the idle time it used.
- Owner: FLOW-OPS-1300; CLEAN-AGGR-R2 to check the three unclassified rows in its damage audit.
- Share: the three hung containers held up to 72 GB requests each for 14 to 27 h. 38 superseded ENQUEUED rows remain
  (S81 22, QC 12, KV 2, HBM 2; 21 older than 24 h) and may be in the same state.

**C3. Aggressive cleanup deleted by store membership, not by need: 60 units, 20 lane dirs.**
- R (CLEAN-AGGR-R2 audit 19:40): 9 LOCAL_PASS units deleted (archived DBs exist for all); 2 SIGNED records lost with DB
  (QC sle_st_b_v2__cl14c98df5__pv41c959f3, rebuild requested; slw_st_b_v1__cl6357f1cc__pv6ace3e48, older export exists);
  2 worktree dirs with a .git pointer removed, no commits lost. V: FLOW-LECGATE-R2 re-LEC of fe76c313f9b4 and
  822d3873e2eb died rc 1 after 3 s at 19:35 because their kit dirs had been retired at 19:24. A broader flow-canary delete
  was started and stopped by exact pid before it reached a baseline run (R).
- Root cause: "record is in the signed store" was taken as "exported", and no check asked whether another lane had an open
  use of the kit. A guard rule changed at 18:58 and a fleet-wide batch ran on it within 15 minutes.
- Structural fix (P): retire of a closed unit requires an INDEX row for that exact record (R: landed as "INDEX or ledger
  record"); a lane that needs a kit writes a dated hold line that the guard reads and that expires in 24 h; any guard rule
  change runs dry on all hosts and posts its delete list one tick before the first apply.
- Owner: CLEAN-AGGR-R2. Share: 1 QC rebuild certain, 2 re-LECs lost.

**C4. Retries on an unfixed cause: 2 FAIL, 11 REPEAT, falling.**
- V: s81_head/hd_host_n failed twice more at kit_rtl ("bootstrap GEN failed") and was stopped at attempt 17; the stop line
  says "16 earlier attempts not in the ledger". 11 REPEAT relaunches at 18:23 with an unchanged fail key after
  "REPEAT-STOP RELEASE tools:pipeline-cap". kv3_hub_Wo: 1 preflight FAIL, then SKIP-SAME-INPUT held it correctly.
- Root cause: the repeat ledger counts from when it was introduced, and a tools release resets a cap whose cause was not a
  tool. Fix (P): the ledger is rebuilt from attempt dirs at start; a release names the fail key it claims to fix and frees
  only rows with that key.
- Owner: FLOW-OPS-1300; hd_host_n itself to HEAD-START-R17. Share: under 1 %.

**C5. Stale and unowned.** STALE block 106 (HBM 104 parked, S81 1, QC 1 unowned; was 110). ROUTE-HELD 120, of them 109 on
superseded events (S81 79, HBM 29, KV 1); 84 older than 24 h (V). Source skew warn-only: KV 349, HBM 280 of 280, S81 234,
QC 161, HEAD 9 modules; TOOLS-LAG 204 to 399 commits on the four live dies, all missing r708 (V). Base-test triage and the
tree-copy tool (A4) have no lane.

## Fleet time in the window (estimates)

| Class | Share |
|---|---|
| A2 over-held drains | about 8 % |
| C1 canary | about 3 % |
| A1 drained-host launches | under 2 %, 36 rows delayed 20 to 50 min |
| B3 hand-run stages, B2 private-spec defaults | about 3 % together |
| A4 tree copy incidents | about 1 % |
| B4 LEC revoke | 9 rebuilds in the next window |
| C2 hung containers | 3 jobs, 14 to 27 h each, before the window |

## For COORD now

1. A1 is one line (`or res` at kit_wave.py 5516). Ask FLOW-OPS-1300 to push that alone, ahead of the computed-drain change
   that has failed three pushes.
2. B1: name an owner for base-test triage; pushes fail more often than kits do.
3. C2: CLEAN-AGGR-R2 to state what the three unclassified containers were doing at cancel, and FLOW-OPS-1300 to run the
   idle-log probe over the 38 remaining superseded ENQUEUED rows before any further cancel-rows.
4. A4 + A5: open the tree lane (fork tool, read-only event trees). Two lanes have now written into or failed a seal on a
   KV event tree in one evening.
5. B4: drop spool entry 98caa81c2b8bc9fe (measurement, name "tt") through its owner.
