# FABLE-FLOW-2200: procedural / flow review, window 11-21 19:45 to 21:48 PST

Lane FABLE-FLOW-2200 (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched, deleted
or edited. Previous: lanes/FABLE-FLOW-2000.md (window 17:45 to 19:50). This file replaces the 11-20 report of the same name
(kept in git history).
Sources: autopilot/log.txt (19:45 on, 771 lines), kit_wave.json and kit_wave_state.json (21:45), lanes/FLOW-HEALTH.tsv,
`failure_breakdown.py` (21:43), `ot-run --status` (21:43 and 21:48), ~/.local/state/ot-run/signals.log, lanes/NOPROG-TABLE.md
(21:30), rt/current kit_wave.py (7c6e28945118, then 4dac1ad0b7b5 from 21:45), /proc and `docker ps` / `docker stats` on
intel1, epyc2, epyc7, epyc8, epyc9, epyc10 (21:47), posts of the last 3 h (FLOW-OPS-1300/-R2, CLEAN-AGGR-R2/-R3,
QC-RELAUNCH-R1, FLEET-EPYC7-R1, FLOW-RESTORE-AUDIT-R1, FLOW-TREEFORK-R1, FLOW-PRIVSPEC-R1, GEOM-UNHOLD-2200,
NOPROG-CANCEL-2105, FABLE-FIX-S81-COLROM-R5, FLOW-CANARY-R2, S81-J6-ASSEMBLY-R5, KV-WAITBIND-R1).
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: the 44 QC visual-held rows were not checked one by one for their AUTO-GEOM verdict; the cause of the three
QC-RELAUNCH-R1 geom rc 1 runs was not read; the drop of the current-plan count (headline 6) was not traced; the "specA vs
specA7" string-prefix guard case was not found as a landed fix. "Share" is an estimate (I) of fleet core-hours in the 2 h
window unless marked.

## Headline

1. **The fleet is not failing, it is not launching.** Launches per hour (V, FLOW-HEALTH + log): 62 (hour 18), 16 (19), 1 (20),
   3 (21). FAIL lines in the window: 0 until one infra kill at 21:45. Measured load at 21:42 (V): intel1 16/112, epyc2 37/128,
   intel2 44/112, epyc7 58/96, epyc8 53/96, epyc9 32/96, epyc10 68/96 = 308 of 736 cores, **42 % busy**. UNDER-USE printed
   "used 88 %" at the same minute, because it counts requested threads (epyc7 271/96, epyc8 283/96), not CPU.
2. **198 rows cannot launch a route** (V, UNDER-USE 21:42): SKIP-HELD 71, WAIT-VISUAL 51, WAIT-FORM 44, q_running 12, q_fail 10.
   On top, 274 S81 and 25 KV type rows are "held by die owner (plan event pending)" (V, failure block); S81 J7 applies at
   04:14 (R).
3. **WAIT-VISUAL came back through config, not code** (class H1): `review_before_route` with `required: true, all_items: true`
   is set on all four live dies (V). It was removed at 00:00 on 11-21 (coord b1a38f6fc0f, after FABLE-FLOW-2350) and put back
   at 03:07 (QC), 03:24 (KV) and 04:12 (S81 atomic apply). Fix landed 21:46 (main 94f0c2e4b8, R); effect not yet seen.
4. **epyc7 is refusing work again, for a different reason** (class A2): THREAD_CAP_FACTOR=1.0 was hand-set at 21:09 against a
   stall whose own diagnosis was I/O, and its owner stood down at 21:31 with no successor. 31 "not admitted on epyc7"
   requeues from 21:20 to 21:48 at load 50/96 (V).
5. **Docker stall itself: fixed for the symptom, not for the cause.** At 21:47 all six gen hosts show Dirty 0.0 GB,
   dirty_background_bytes 1 GiB, ot-docker-bdi-cap active, `docker ps` 0.05 to 0.09 s, dockerd D threads 0 to 1 (V). Raw
   tree copies continue: 6 seen at 21:47, 4 of them duplicates of each other (V, class A4).
6. **Count: signed any plan 527 / current plan 431 (V 21:43).** Any-plan is flat since 19:10; current-plan was 437 at 19:10.
   4 units were classified SIGNED in the window (QC sle_hc2 x2, sle_hc0, slw_fe_v1). 5 rows stand as "signed (count
   pending)", three of them for 14 to 19 h (class C5).

## What FABLE-FLOW-2000 asked for: landed or not

| 2000 item | State at 21:48 |
|---|---|
| A1 drain filter fails open | LANDED main 3504af932d 21:27 (R): computed drain, DRAIN-HOLD when every gen host drains, host-add gate. Took 17 pushes; the last ran 3051 s |
| A2 hand-set drain has no release term | Disk drains: computed now. The same class re-opened on threads (epyc7, headline 4) |
| A3 epyc7 admitted by memory only | Changed by hand on epyc7 only (/etc/ot-heavy.conf), not in main. See A2 |
| A4/A5 tree fork tool | LANDED main 19c436478b 20:50 (R): ot-tree-fork, private-spec --fork, writer names on a broken seal. Used by FABLE-FIX-KV-HUB-R5 (R). Not enforced: raw copies continue (V) |
| A6 guard and wave share one definition of "needed" | PARTLY: guard now lists every scratch path named in enabled die plans + gen_args (d82503914e, 86d1912318, R). Still a list built from sources; see D1 |
| B1 ot-push-main failures | Improved: 32 rc 0 / 4 failed (rc 4 x3, rc 3 x1) in the window, was 20 / 14 (V, posts). 1265 s lost in failed attempts, was about 75 min. Base-test triage still has no lane (one BASE-TEST ask to FLOW-NOADV-R3, which stood down) |
| B2 private-spec defaults | LANDED main 15db9fcd7a 20:35 (R); prov views 2c04073c53 21:04 (R) |
| B3 run-item to sign-off | LANDED with B2 (`--goal auto`). First end-to-end proof not run yet (R: the chosen kit failed place on design) |
| B4 LEC count / spool entry | Not re-read |
| C1 canary | NOT landed. 13 verdicts in the window, 2 PASS; s81_cl NO-BASELINE 3 more times; hbm and hbm_sram still scheduled (5 verdicts). New: STALE-BASELINE label on hbm_sram (R) |
| C2 ENQUEUED hides three states | NOT landed. 34 superseded-event ENQUEUED rows remain (S81 18, QC 10, KV 4, HBM 2; S81 median 26 h) (V) |
| C3 retire needs an INDEX row; guard changes dry-run first | PARTLY. A second delete incident surfaced (D1) |
| C4 repeat ledger | NOT landed. hd_host_n still "16 earlier attempts not in the ledger" (V) |
| 1900 (e) sign-off tcl from rt, TOOLS-LAG | NOT landed. All four live dies still "missing r708"; lag 240 to 435 commits (V) |
| 1900 (g) parked die skipped by adopt-guard | NOT landed. 45 ADOPT-GUARD hbm alert lines and 2 DIE-OFF hbm in the window (V) |

## Classes

### H. Holds that over-hold

**H1. Route held for a visual verdict: 50 live-die rows, 36 of them for 24 to 39 h. Fix landed 21:46, unverified.**
- Count (V): state 21:45: QC 44, S81 4, KV 2 (plus 1 parked HBM). First WAIT-VISUAL log line of the rows still held after
  19:45: 36 rows on 11-20 (06:00 to 23:00), 1 at 05:00 today, 11 at 20:00 to 21:00 today. Trend: was 0 after the 00:00
  unhold, 51 now. GEOM-UNHOLD-2200 and QC-RELAUNCH-R1 hand-posted 18 verdicts (21:25 to 21:33 and 20:02, 20:54); the 21:42
  tick still counted 51.
- Root cause (V, kit_wave.py 16440 to 16466 in rt 7c6e28945118): `required_route_hold()` returns WAIT-VISUAL whenever the die
  config has `review_before_route.required`; it runs before `visual_advisory()` and before `stops_off_die()`, so the owner
  rule ("visual never blocks") implemented at three other places did not apply. The key is plain config: two plan lanes and
  one atomic apply wrote it back 3 to 4 h after COORD removed it. Global config says `visual_gate: signoff` and
  `wait_visual: false` at the same time (V), so the file contradicts itself and nothing reports that.
- Fix landed (R, FLOW-OPS-R2 main 94f0c2e4b8): a row whose own AUTO-GEOM passed is no longer held by `required`,
  `route_hold_reason` or `visual_hold`. Hard holds kept: explicit BAD, PASS-COND, no geom record.
- Is it structural: partly. The code path is closed for AUTO-GEOM PASS rows. Still open (P): (1) `kit_wave_edit` and
  `apply_reviewed_tree_marker` should refuse to write `review_before_route.required` on an unparked die, so a plan apply
  cannot carry it back; (2) HOLD-AUDIT printed seven zeros every tick while 51 rows were held against an owner rule: add a
  counter OWNER-RULE-HOLD (any WAIT-VISUAL on an unparked die) that must be 0; (3) rows with PASS-COND stay held with no
  owner: list them in the tick line.
- Owner: FLOW-OPS-R2. Share: about 15 % (I: 36 routes waiting over a day while 58 % of cores were idle; each route is
  several hours at 8 to 16 threads).

**H2. A hand-set host cap with no release term and no owner: epyc7, again.**
- Count (V): signals.log "not admitted on epyc7 within N s": 1, 1, 1 per 10 min from 20:50, then 12, 12, 6 from 21:20 (31
  lines; FLOW-LECGATE-R1 relec 11, FAM-S81-COL-H10-R4 7, FAM-S81-IQF-R1 3, QC wave row 3). ot-run status 21:48: epyc7 load
  50/96, avail 575 GB, 5 waiters, threads 268/96.
- Root cause: FLEET-EPYC7-R1 first read the stall as CPU over-admission and set THREAD_CAP_FACTOR=1.0, then found the cause
  was I/O (68 GB dirty pages, R) and fixed that with the dirty cap, but left both caps and stood down with "successor none".
  The 268 committed threads are mostly requests, not use: 11 of the 27 running units are single-threaded GRT loops at 100 %
  of one core each (V, docker stats).
- Structural fix (P): every hand edit of /etc/ot-heavy.conf goes through one command that records owner, reason and an
  expiry (default 2 h) and the conf is rebuilt from main when it expires; thread admission charges measured CPU of units
  older than 30 min instead of their request. Same form as the computed disk drain that landed tonight.
- Owner: NEW (FLEET-WATCH-R8 to revert the epyc7 thread cap now; code to FLOW-OPS-R2). Share: about 5 % (I: half of a
  96-core host for the last 30 min and rising; the 2 h docker stall before it is counted in A4).

**H3. Jobs that cannot sign keep running: 19 containers, 7 to 51 h, verdict without an action.**
- Count (V, NOPROG-TABLE 21:30): 19 GRT-LABEL "DESIGN-FAIL GRT-0273" rows (epyc7 11, epyc10 3, epyc9 2, epyc8, intel1,
  intel2 1 each), 17 older than 21 h, overflow flat or rising (for example 62755 -> 49999 after 36 h). Their action column
  is empty. 3 more were cancelled by hand at 21:11 to 21:13 (R). Trend: flat; the label exists since 11-20.
- Root cause: the watchdog has an action for UNSIGNABLE and NO-PROGRESS but GRT-LABEL is report-only, and the owner rule
  (cancel jobs over 3 h measured unable to sign) is applied by a one-off lane. The design cause is not in scope here; the
  missing action is.
- Structural fix (P): GRT-LABEL DESIGN-FAIL with age over 3 h and overflow not down 20 % in the last two rounds gets the
  UNSIGNABLE action (notice to the owner lane, cancel on the next pass unless the lane posts KEEP).
- Owner: NEW (NOPROG-WATCHDOG has no live lane). Share: about 3 % of CPU (19 cores), but 268 committed threads on epyc7
  feed H2, and about 1.3 TB of memory requests stay reserved.

**H4. Cancel by name pattern hits bystanders: 3 cases.**
- V/R: NOPROG-CANCEL-2105 `ot-run --cancel` matched by substring and sent SIGTERM to two epyc7 waiters of other attempts;
  21:45 kv3_sys_c@6 was killed at geom_run by `ot-run --cancel KV-D26/items/kv3_sys_...` and took a free infra retry;
  CANCEL-STOP at 21:12 reported "epyc10, epyc7 not checked: rc 124 timeout" and went on.
- Structural fix (P): `ot-run --cancel` takes a unit id or an exact job dir; a pattern needs `--match` and prints the
  matched units first; an unchecked host makes the cancel result UNKNOWN, not done.
- Owner: FLOW-OPS-R2. Share: under 1 %.

### A. Hosts, trees, disk

**A4. Bulk tree copies on the docker disk: the stall is capped, the copies are not.**
- Count: epyc7 created no container from 19:10 to 21:14 (R, FLEET-EPYC7-R1): 2 h on a 96-core host. Writers were 6 tree
  copies, 3 of them duplicates (R). At 21:47 (V): epyc10 three rsyncs of one tree (s81-bksel-r5/w/tree_r6 from epyc7, two
  started 2 s apart, 78 min old) and two of fam-qc-cb-r3/bind3/tree; epyc9 a `cp -a` of the QC v1r6 snapshot into
  fam-qc-fefw. epyc10 docker was 14 s at 21:28 (R); `docker ps` is 0.05 s now (V; `docker run` not timed by me).
- The fix that landed (main 8082157602: 4 GiB per-device dirty cap + 1 GiB background, on all 7 hosts and in the host
  install script) is structural for the failure mode "one syncfs waits behind 68 GB". It does not reduce the write load:
  epyc7 and epyc8 scratch are 89 % and 83 % full consumer NVMe at about 70 MB/s sustained (R), and a capped writer now
  blocks itself instead of docker.
- Root cause: copying a 57 GB / 325,000-file tree is a lane habit with no queue. ot-tree-fork landed tonight but nothing
  makes a lane use it, and it has no cross-host form with a concurrency limit.
- Structural fix (P): `ot-tree-fork --host` and `src_manifest replicate` take a per-host copy lock (1 or 2 at a time) and
  reuse an existing identical copy by manifest hash; ot-copy-reaper (its timer already runs every 10 min on the hub, V)
  posts any raw cp / rsync / tar whose source is under kw45 or a lane tree, with pid and lane. Docker data-root off the
  scratch disk on epyc7/8/9/10 when the two new hosts are installed.
- Owner: FLOW-TREEFORK-R1 (tool), FLEET-WATCH-R8 (operate). Share: about 6 % (I: epyc7 starts and teardowns blocked 2 h;
  running jobs continued).

**A1/A2 disk admission.** REQUEUE lines per hour (V): 136 (18), 48 (19), 2 (20), 40 (21). The 21 h lines are epyc7 thread
cap (31), not disk, plus 3 naming epyc4. Scratch free 411 to 2646 GB. Disk is not a limiter. No open item.

### D. Delete guard and cleanup

**D1. The guard is a list of known reference sources; each incident adds one. 4 new cases.**
- R (CLEAN-AGGR-R3 21:18, 21:37): (a) s81_head_r4_s0 deleted on epyc7/8/9/10 at 19:13 to 19:16 by the hourly
  ot-retire-superseded timer while the r16 source plan still named its sink_bins paths: the guard knew kit_wave src and
  bind only; the 18:58 guard change turned a partial delete into a whole-tree delete one pass later. (b) Private-spec kits
  were protected by the kit-wave ancestor, so two failed QC-RELAUNCH-R1 kits could not be deleted. (c) Copied child-view
  sign-off records made a lane-private copy "signed". (d) Hub run-item command lines protected the same path on every
  host. All four have pushes on main (d82503914e, 86d1912318, eb170c1a34, 47a226faaa). Not found as fixed: path prefixes
  compared as strings (specA vs specA7).
- Also R: hosts ran a stale 11-14 ot-autoclean because an hourly timer on localhost re-pushed its own old copy; the epyc7
  timer had not finished a pass since 11-16; three kwbatch.sh loops of the stood-down CLEAN-AGGR-1121 were still running on
  epyc7/9/10 and were stopped before they reached snap trees. s81-die-r3-e8 (65 GB, about 355 signed views not exported)
  is undeletable under the KEEP rule until AUTO-EXPORT acts; its lane stood down without answering.
- Root cause: "is this path needed" is answered by scanning a growing set of files and command lines for paths. Anything
  that names a path in a place the scan does not read is unprotected (a); anything that sits under or contains a protected
  string is over-protected (b, c, d).
- Structural fix (P): leases. A consumer (wave row, bound plan, run-item, lane hold) writes one line `realpath, host,
  owner, expiry` into a lease dir on that host; delete needs zero live leases on the path or any parent, compared by path
  components after realpath. The plan-file scan stays as a second net and logs every path it protects that has no lease.
  Fleet tools installed on hosts carry the main sha in a header and the tick alerts when a host copy differs from
  rt/current (that would have caught the 11-14 autoclean in an hour instead of a week). A lane that starts a background
  loop registers its pid with the lane row, and stand-down.sh refuses while registered pids live.
- Owner: CLEAN-AGGR-R3. Share: 0 fleet; one HEAD tree lost (not restored, HEAD moves to r17a), about 1 h of two lanes.

### B. Kits and tools

**B5. Tool fixes cannot reach kits: pins and sealed trees.**
- V: kit_wave.json tools_sha: s81 a9ed808a98d5, qwen_compute 65f3f85d7c5f, s81_head 745c8f11e429 (tools_from_rt false),
  qwen_kvsys 47a226faaa96 (moved with the D27d3 apply at 21:39). TOOL-SKEW warn-only: KV 428, S81 234, QC 161, HEAD 9
  modules differ from pin; HBM 281 of 281.
- R: the restore-keep fix 650916ebb262 reaches wave kits only because every stage refreshes run_kit.sh from rt/current;
  HEAD gen skips that refresh. The seat fix 643ffb9932 lives in kit_istations.py, which is not in the refresh list, so the
  sealed J7 tree (tools = rt 404887a342b0) will launch S81 col kits at 04:14 with 52 to 140 plan seat keys matching nothing.
  SEAT-MISS was made a warning by COORD ruling (aa0cde9d13), so the kit will not stop on it.
- Root cause: a tree seal freezes design sources and flow tools together; the only way to carry a flow fix is a file-by-file
  refresh list.
- Structural fix (P): split the pin: design-generating tools stay sealed with the tree; kit-time flow scripts (run_kit.sh,
  kit_istations.py, the sign-off tcl) always come from rt/current, by directory, not by a list. Until then add
  kit_istations.py to the kit_flow_refresh ALWAYS list before the 04:14 J7 apply. That one line decides whether the J7 col
  wave is built with a known defect.
- Owner: FLOW-OPS-R2 (refresh list today), S81-J6-ASSEMBLY-R5 (J7). Share: at risk, not spent: all S81 col types of the J7
  wave.

**B6. Seat-key matcher matched nothing, silently: 58 placed kits (R), flat until tonight.**
- R (FABLE-FIX-S81-COLROM-R5): 58 placed kits with unmatched relay_sites keys; forms: leaf prefix (25 kits, fixed by
  RELAY-NORM 4dac1ad0b7), J7 station keys (88 of 140 fixed by RELAY-INST), and plan rows naming registers the kit does not
  have (bk_sel 594, QC cb 276 to 294 each, sle_ctl 15,996). The count is now in the kit log and in
  ot_relay_sites_unmatched.txt.
- Is it structural: no. A warning in a kit log is what existed before ("plan keys unmatched: 140 of 166" was printed, V in
  the post). The class stays silent at the level where it can be acted on.
- Structural fix (P): check at gen time, before place: gen fails when a plan seat key matches no register in the
  generated netlist, with a per-type waiver list in the plan (explicit, counted, visible in PRECHECK). Then a wrong plan
  row costs 5 minutes, not a routed kit.
- Owner: FABLE-FIX-S81-COLROM-R5 (matcher), PRECHECK-1119 (gen-time check). Share: design-adjacent; the 3 kits with stages
  moved over 50 um each lost a place-to-CTS run.

**B7. A step status masked by `| tee`: about 35 kits kept a worse DB; the pattern is still in the generator.**
- R (FLOW-RESTORE-AUDIT-R1): 259 kit dirs had a RESTORE verdict on the old flow, 40 (about 35 kits) kept the regressed DB,
  2 of them had passed the -42 ps gate before the repair (one recovery copy running on epyc8). Fix 650916ebb262 takes the
  status of tt_setup_keep.py itself.
- V: gen_phys.py in rt/current has 42 lines with `| tee` and 2 with `pipefail`. The instance is fixed, the class is not.
- Structural fix (P): the generated run_kit.sh sets `set -o pipefail` once at the top of every container shell, and a
  generator test fails on any `| tee` in a step whose status is used.
- Owner: FLOW-OPS-R2. Share: under 1 % measured (2 kits).

**B8. Re-sign NOT RECORDED.** R (FLOW-OPS-R2 main 5ce545eff0): nomcap receipts map to nomcap_dir(), sha-bound, fail-closed;
`refresh-coverage` re-derives without STA. 2 re-signs re-recorded; the other 37 NOT RECORDED are real failures. Structural
for this cause. Open (P): AUTO-RESIGN should print the gate that failed in the NOT RECORDED line so the next path-map
error is one grep, not a 7-host scan. Owner: FLOW-OPS-R2. Share: under 1 %.

**B9. Private kits outside the queue: 2 passes not taken, 3 geom rc 1, 2 synth fails.**
- R (QC-RELAUNCH-R1): pvcca9ff41 old-spec run-item passed geom at 20:3x and the autopilot queue never took it (0 rows);
  regenerated on main; its geom then died rc 1 at 21:39 (V, 98 s). pv41c959f3 geom rc 1 at 21:12. Two private slw_su_c kits
  failed synth for missing provisional views (fixed 2c04073c53). The wave did not relaunch the same types for 30 min.
- Root cause: an old-spec private kit ends at geometry and expects a queue that only reads wave rows; specs made before
  15db9fcd7a have no goal chain. Nothing tells the lane its spec is of the old kind.
- Structural fix (P): run-item refuses a spec without a goal chain and prints the regenerate command; a private kit that
  ends at geom PASS without a next stage writes result.json STOPPED-AT-GEOM, which the lane waiter reports.
- Owner: QC-RELAUNCH-R1 (instances), FLOW-PRIVSPEC-R1 (rule). Share: about 2 % (short failed runs; the cost is 3 QC rebuilds
  about 2 h late).
- Lane units that DIED in the window (V, posts, excluding pushes): 98. rc 1: 55 (FAM-QC-HCST-R3 12, HEAD-START-R18 5,
  FLOW-LECGATE-R2 4), rc 143: 25 (QC-PLAN-R12/R13 8), rc 11: 7. Not classified further.

### C. Lanes and background machinery

**C6. Lanes stand down for context against the owner rule: 8 in 2 h.**
- V (posts 19:52 to 21:21): FABLE-FIX-QC-COLL, FABLE-FIX-HEAD-LEP0N-R6, CLEAN-AGGR-R2, OPUS-FIX-KV-PV-R6, FAM-QC-CB-R3,
  QC-PLAN-R12, FABLE-FIX-S81-LEAF-R8, FLOW-OPS-1300 all give "context" as the reason. FLOW-OPS-1300 stood down with
  "successor none" while its push 17 was in flight and then said so itself. `bin/stand-down.sh` has no check on the reason
  (V: no match for "context" in the script).
- Cost seen: FLEET-EPYC7-R1 and FLOW-OPS-1300 left open items without an owner (H2, base tests); CLEAN-AGGR-1121 left three
  running loops (D1); S81-DIE-R5 left an unanswered export ask.
- Router: 4 redirect / filed-under lines in the window, all resolved to a live successor (V). The stale-name loss is fixed
  for chains with a successor; "successor none" still drops posts.
- Structural fix (P): stand-down.sh refuses a reason matching context / limit / compact and prints the owner rule;
  "successor none" is allowed only with `--done` and no open ASK addressed to the lane, no registered pid, no hand-set cap.
- Owner: FLOW-OPS-R2. Share: 0 fleet; about 20 to 30 min of lane time per chain, 8 chains.

**C1. Canary.** 13 verdicts, 2 PASS; unchanged class (table above). Owner: FLOW-CANARY-R2. Share: about 3 %.

**C4. Retries on an unfixed cause: low.** ITEM-SYNC phy_serdes_b epyc10->epyc2 rc 2 every tick (5 of 67 ITEM-SYNC lines; the
other 62 are rc 0 re-copies of bound dirs); kv3_hub_Wo held correctly by SKIP-SAME-INPUT; INFRA-RETRY slw_su_c "free requeue
8/8". ADOPT-GUARD hbm 45 lines. kv3_hub_C: "unit active, no output for 791 min", reported only, container alive (V).
Owner: FLOW-OPS-R2. Share: under 1 %.

**C5. Stale and unowned.** STALE 107 (HBM 104 parked; QC 2 unowned, S81 1). The three live-die rows are all "SIGNED count"
rows waiting 14.4, 16.4 and 18.7 h for the count (V), and the failure block shows 5 "signed (count pending)" in total.
Superseded-event rows: ROUTE-HELD S81 62 SKIP-HELD + 17 WAIT-FORM (median 26 to 32 h), ENQUEUED 34. 134 S81 rows unowned
(R, S81-J7-HELD-R1). Fix (P): a SIGNED row not counted after 2 h is an alert with the missing gate named (LEC, export,
visual), owned by the count owner. Owner: FLOW-LECGATE-R2 for the count rows; NEW for base-test triage, NOPROG actions and
host caps.

## Fleet time in the window (estimates)

| Class | Share | Fix | Owner |
|---|---|---|---|
| H1 visual route hold via config | about 15 % | landed 94f0c2e4b8; refuse the config key, OWNER-RULE-HOLD counter | FLOW-OPS-R2 |
| A4 tree copies / docker stall | about 6 % | dirty cap landed; copy lock + dedup by manifest, raw-copy alert | FLOW-TREEFORK-R1 |
| H2 epyc7 thread cap left behind | about 5 %, rising | revert now; caps with owner and expiry, CPU-measured threads | NEW / FLEET-WATCH-R8 |
| H3 unsignable GRT jobs | about 3 % CPU + reservations | GRT-LABEL gets the cancel action | NEW |
| C1 canary | about 3 % | closure-change trigger, INPUT-BROKEN, no parked die | FLOW-CANARY-R2 |
| B9 private kits outside the queue | about 2 % | refuse goal-less specs, STOPPED-AT-GEOM result | QC-RELAUNCH-R1 / FLOW-PRIVSPEC-R1 |
| B7, B8, C4, H4 | under 1 % each | pipefail; gate name in NOT RECORDED; exact-unit cancel | FLOW-OPS-R2 |
| B5/B6 pins and seat keys | at risk: J7 col wave | refresh list today, gen-time seat check | FLOW-OPS-R2 / FABLE-FIX-S81-COLROM-R5 |
| D1 guard, C6 stand-downs | 0 fleet, lane time | leases; stand-down reason check | CLEAN-AGGR-R3 / FLOW-OPS-R2 |

## For COORD now

1. H2: revert THREAD_CAP_FACTOR on epyc7 (`/etc/ot-heavy.conf.bak-fleet7r1b-1122`); the stall was I/O and the dirty cap
   covers it. 5 units are waiting at load 50/96.
2. H1: at the next tick check that WAIT-VISUAL on QC/S81/KV went to 0; any row left is PASS-COND or has no geom record and
   needs a named owner. Ask FLOW-OPS-R2 to make kit_wave_edit refuse `review_before_route.required`.
3. B5: add kit_istations.py to the kit_flow_refresh ALWAYS list before the 04:14 J7 apply, or the S81 col wave launches
   unseated.
4. H3: name an owner for the 19 GRT-0273 containers (11 on epyc7); they are the committed threads behind item 1.
5. A4: tell S81-BKSEL (three rsyncs of tree_r6 on epyc10) and FAM-QC-CB-R4 (two of bind3/tree) to keep one copy each.
6. C5: 5 signed rows are not in the count, three for 14 to 19 h; current-plan count fell 437 -> 431 since 19:10 with no
   post explaining it.
