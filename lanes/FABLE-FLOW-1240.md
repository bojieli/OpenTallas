# FABLE-FLOW-1240: procedural / flow review, window 11-21 10:40 to 11:56 PST

Lane FABLE-FLOW-1240 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled, launched or deleted.
Previous: lanes/FABLE-FLOW-1000.md (window 07:47 to 10:02). Fix lane since then: FLOW-OPS-1000.
E2BIG and snapshot-copy counts are taken from 10:02 so the gap between the two reviews is covered.
Sources: autopilot/log.txt (769 lines from 10:40), autopilot/WATCHDOG.log, lanes/FLOW-HEALTH.tsv (11:07),
tools/failure_breakdown.py (run 11:49), `ot-run --status` (11:50), lanes/posts/*.md (332 posts in the window), hub systemd
journal (signed-store-ingest, autopilot), /proc cmdlines of the live wave units on the hub, rt/* snapshot contents.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Fleet base: 245 running units (V, ot-run status 11:50), 1.27 h, so about 310 unit-hours in the window.
Not done: no git was run, so commit shas are checked by snapshot content, not by history.

## Headline

1. **E2BIG is fixed in the code and still failing in the fleet.** 29 FAIL lines today (first 10:12:58, 19 in hour 10, 10 in
   hour 11, last 11:32:25). The fix (gzip in `flow_files_refresh_cmd`) is in rt d3a716bffef1 and later; rt 4f638b4e9f8d does
   NOT carry it (V: grep count 0 there, 4 in d3a716b, 457647e, b6934d7). A wave unit keeps the rt it was launched with, so
   every unit launched before 10:52 fails when it next reaches the refresh. 6 such units are still alive (V, list in class a).
2. **A job cancelled as UNSIGNABLE comes back labelled "OOM kill" and is launched again with place memory x1.5.**
   s81/dsdv_slice_lepe_mu_LP__t2: cancelled 09:01 (-891 ps, 4.8 h) and 11:01 (-423 ps, 3.8 h), relaunched 11:52:34 as
   attempt 3. Same label on qwen_compute/cbf_q11 at 11:51. Class (b), new.
3. **Disk is now the binding limit for launches.** 11:52: LAUNCH-DISK-CAP on every host of the QC, KV and S81 host lists;
   intel1 and epyc9 DRAINING; epyc2 138 GB free under its 150 floor. epyc9 runs at load 41 to 47 of 96 while UNDER-USE
   prints "idle 0 of 624 threads". Fix 3 of the last review (overlay private trees, sealed trees) did not land. Class (c).
4. **Signed-store ingest: 29 service timeouts since 11-20 05:00 (V journal).** The first chunked run started 11:30; at 11:46
   it had ingested 0 records on intel1 (4 fails) and intel2 (6 fails, "hash differs on 75 files") and was on epyc2 chunk
   1 of 6. 57 new records wait. Not yet shown to complete. Class (e).
5. **Flow canary runs again and every verdict is FAIL** (12 verdicts in 5 posts, 0 pass). The same hold numbers repeat at
   three different shas, so it is the baseline, not a regression. Tags wait for a canary release. Class (f).
6. **Sign-off count: 510 any plan, 424 current plan (V 11:49), +16 / +11 since 09:46.**
7. **Wave: 29 launches in hour 10, 74 in hour 11** (45 QC V2 rows in one tick at 11:46). 18 FAIL lines from 10:40: 15 E2BIG,
   1 snapshot copy, 1 drain refusal, 1 CLAND band. 15 of 18 are one tool fault. STALE 109 (104 HBM parked, 4 QC, 1 S81).

## FABLE-FLOW-1000 fixes 1 to 9: what landed

rt/current is b6934d7751d6 (V 11:44).

| Fix | State this round |
|---|---|
| 1 tick budgets, stack dump, TICK-DEAD (0ae8276b04) | Landed, live (V): `TimeoutStartUSec=15min`, autopilot/tick_stack.log written 11:49, 0 PHASE-OVERRUN / TICK-DEAD / TICK-KILLED in the window. Ticks 180 to 533 s; kit_wave_step+admit is 163 s of a 215 s tick. |
| 2 watchdog SUPERSEDED stops only the row's own unit (d3a716bffe) | Landed. **Class stopped (V)**: watchdog ticks 10:53, 11:13, 11:33 read `STOP 0`, REPORT 11 / 10 / 12. `~/.local/state/ot-run/stops.log` is empty on the hub: no stop has gone through the new path yet, so the sender line is untested. |
| 3 `chattr +i` at publish, overlay private trees | **Not landed (V)**: no `chattr` and no `--base/--delta` in rt/current tools; no post. The disk cost it was meant to remove is now class (c). |
| 4 git history shim (659810b5f7) | Landed on 8 hosts (R). epyc4 missing (ssh host key). Not exercised. disk-rate.log still names epyc7 pid 2832979 at 76.7 GB in its latest epyc7 line; whether the pid was stopped is not posted. |
| 5 ETA-STAGE on a disk-ETA hold (1a22da679a) | Landed 11:44. Not exercised yet. |
| 6 small-input tarball beside every delete manifest (fd27f03a3d) | Landed 11:44. The second half ("idle-tree retire only in drain state") is not in the post. |
| 7 run_kit resumed goal skips the 4_cts hooks (328c0a40a0) | Landed (R). Running kits keep their copied run_kit: see class (a) root cause. |
| 8 obs_gcell_cap.tcl refresh into old kits (89ed3a69db) | Landed (R); applies on relaunch. |
| 9 `ot-wait --digest` + waits.tsv ledger (b6934d7751) | Landed 11:46. The hub step that folds per-host ledgers into lanes/WAITS.tsv is not installed, so lane waits still cannot be measured here. |

Open from the 1000 list with no fix: measurement tcl read from rt and `remeasure` (class e there), KV pv struct-stop by type,
canary as a wave row.

## Known items, verified

| Item | Verdict (V unless marked) |
|---|---|
| E2BIG after 4f638b4e9f | 4f638b4e9f8d has no fix. Fix is in d3a716bffef1 (10:52). 8df26be75d and 257642da66 have no rt snapshot and I ran no git: not confirmed as shas. Fails have NOT stopped: 11:32 kv3_pv_v8 and kv3_pv; 6 pre-fix units alive. |
| INFRA snapshot copy timeouts | 6 today (5 in hour 10 per FLOW-HEALTH, 1 at 11:07:49 kv3_hgi_v5). Fix fd27f03a3d at 11:44 (copy error drops the host, sibling wait 600 s instead of 7200 under a 600 s ssh timeout). 0 since, on 12 min of data; units launched before 11:44 keep the old code. |
| Watchdog SUPERSEDED killed lane LEC | Stopped, see fix 2. |
| No-progress watchdog reads only end-of-iteration DRT counts | Fixed on main c2047d41cc at 11:16 (R). noprog runs from an installed copy (`~/.local/lib/noprog`); the FLOW-HEALTH drift table says SAME on 7 hosts but was taken 11:07, before the fix. Live state unverified until the next FLOW-HEALTH pass. NOPROG 11:52: 188 jobs, 3 NO-PROGRESS (advisory). |
| ot-run 10-min drain cache | Not fixed. `host_drain.py` CACHE_S = 600 (V). Two hits: FAM-KV-IOPC-R2 NOT-RUN 11:04, and wave row s81/slice_station__t45 attempt 9 FAIL "every target host is draining (epyc7, epyc9, intel1)" logged 11:44:45, 40 min after the 11:04 undrain. Class (d). |
| ENV-PROVENANCE rc 14 | 3 refusals in the window (LOCKUP-STATION-R3 11:01, 4 s; OPUS-FIX-QC-SLE-R4 about 11:05; S81-BKSEL-R6 try 4 about 11:20). Each was relaunched through `private-spec` in 10 to 30 min. Self-stopping, seconds of compute. Works as designed. |
| QC V2 wave on old rt/65f3f85d7c5f | Closed 11:50 (R QC-PLAN-R11): tools_sha 65f3f85d7c5f -> b6934d7751d6. Finding there, confirmed here (V): kit stages run the scheduler rt of the launch, not the die pin. The 45 live QC V2 units run rt a13768301176, 22 run c2047d41ccdf. The pin only fed TOOL-SKEW and prune protection. |
| Signed-store ingest timeouts before e3c8933051 | 29 timeouts. Chunked run in flight, not proven. Class (e). |

## Classes, ranked

### (a) A fix on main does not reach running wave units, and tool faults count against owner caps

- Count (V): 29 E2BIG FAIL lines since 10:12 (19 + 10), 15 in this window; 6 snapshot-copy INFRA fails. Trend: falling
  (19/h to 10/h, last 11:32) but not zero. Live wave units by rt (V, hub /proc): 45 on a13768301176, 22 on c2047d41ccdf,
  5 on d3a716bffef1, 1 on aaa1dcff0349 (all fixed); **6 on pre-fix rts**: kv3_pv_v1 (22c4c3c58376), kv3_hub_C
  (470792e6e485), kv3_hg_v1p2 (4f638b4e9f8d), kv3_pv_v3n, kv3_pv_v4n, kv3_pv_v5n (b8c28cb91890). Expect up to 6 more
  E2BIG lines.
- Retries on the unfixed cause (V): 21 `REPEAT ... unchanged fail key` lines from 10:40. Rows relaunched with the same
  fault: slice_station__t18 three times, kv3_hgi_v8, kv3_hub_Wo, kv3_hgi_v5, serdes__t14 twice each.
- Over-hold (V): 6 rows hit CAUSE-CAP or BLOCKED-CAP with the cause text `OSError ... Argument list too long: 'ssh'`
  (s81 slice_station t6cl0755c26e, t45, t29clc7772371; qwen_kvsys kv3_hg_v1p4, kv3_pv_v8; qwen_compute
  slw_st_a_v2clf4365a62). BLOCKED-CAP reads "PLAN item for the owner; released only by a new plan event or an unblock".
  A hub tool fault became a plan item on a die owner. Some were released by hand retry keys (RETRY-KEY-LAUNCH 7 lines).
- Misrouted ownership (V): FAIL-ROUTE-1115 sent this class to KV-PLAN-R6, DIE-S81-92 and S81-SERDES-PHY-1116:
  4 NEEDS-LANE and 2 NEEDS-ACTION posts (10:48 to 11:48), none answered, while FLOW-OPS-1000 posted the root cause at 11:10.
- Root cause (V): (1) the unit runs kit_wave.py from the rt of its launch for its whole life (hours); (2) the first fix
  attempt was declared from the sha, not from a check that the failing function changed in the rt that units run;
  (3) the 0900 ARGV-GUARD covered one call site; payload still travels in argv elsewhere; (4) CAUSE-CAP and BLOCKED-CAP
  count every failed attempt, whatever its class; SKIP-SAME-INPUT releases on an rt change, the caps do not;
  (5) FAIL-ROUTE routes by die and stage, not by class.
- Structural fix (P):
  1. One ssh helper for all hub code (`roam_sh`): any payload over 16 kB goes over stdin, always. A unit test greps the
     tree for `subprocess` calls with `ssh` outside the helper and fails. E2BIG cannot recur at a new call site.
  2. A unit re-resolves `rt/current` at each stage boundary for the hub-side orchestration code (kit stages keep their
     recorded tools_sha). A fix is then live for running units within one stage, with no relaunch.
  3. Attempts whose fail class is FLOW or INFRA at stage `pipeline` (the traceback is in kit_wave.py itself) do not count
     in CAUSE-CAP / BLOCKED-CAP, and a cap whose only cause is such a class is dropped when rt changes.
  4. FAIL-ROUTE: class FLOW/INFRA at `pipeline` goes to the flow lane, never to a die owner; a RESULT that names the fail
     text closes all classes with that text.
  5. A flow fix RESULT must carry "function X differs in rt Y; N live units run older rts" (the 11:16 post did this; make
     it the template).
- Owner: FLOW-OPS-1000. Now: KV-PLAN-R6 and S81 owners need do nothing for E2BIG; FLOW-OPS-1000 clears the 6 caps.
- Fleet time: under 1 percent of compute (attempts die in hub-side kit prep after 5 to 18 min). The cost is 15 rows
  delayed 0.5 to 1.5 h, 6 rows capped, and 15 of the 18 FAIL lines in the window hiding the other three.

### (b) UNSIGNABLE cancel is classified as OOM and relaunched (NEW)

- Count (V): 2 rows in the window. log.txt 11:50:02 and 11:50:08: `CLASSIFY ... -> CRASH (infra-stopped): exit 143, no
  OOM line in the run logs: stopped from outside`; 11:51:08 `REPEAT-STOP ...: OOM kill; the resubmit runs with place
  memory x1.5` for cbf_q11 and dsdv_slice_lepe_mu_LP__t2; 11:52:34 `LAUNCH s81/dsdv_slice_lepe_mu_LP__t2` (unit ...-3).
  The same pair of lines for lepe t2 at 09:41 / 09:51. The classifier's own text says "no OOM line", then the next
  step says "OOM kill".
- Trend: appears with the UNSIGNABLE watchdog acting (0db164c936). 3 cancels in the window (11:01 one, 11:46 two).
- Root cause (V, I): `ot-run --cancel` by FLEET-WATCH-1015 leaves nothing on the wave row. The row sees rc 143, maps it
  to CRASH, and the CRASH branch is the OOM resubmit. The GRT-ARM path does it right (11:31 sle_su_c: row CANCELLED class
  PLAN, "not resubmitted"). So the measured evidence (WNS -423 ps) is lost and the same input runs again for 3 to 4 h
  until the watchdog fires again, each time asking for more memory.
- Detection is also late (V): cbf_q11 ran 15.2 h at -675 ps and was first listed at 11:00; c1x_C t9 6.1 h at -860 ps;
  sle_ctl 7.4 h flat at -85 ps; sle_su_c GRT flat at 8.8 h. About 26 job-hours past the 3 h rule (I).
- Structural fix (P): (1) `ot-run --cancel --why <class>:<evidence>` writes `CANCEL.json` in the job dir; every watchdog
  uses it. (2) The classifier reads CANCEL.json before the exit code: UNSIGNABLE -> row STRUCT-STOP, class PLAN, owner
  named, released only by a changed plan block (the existing struct-carry). (3) rc 143 with no CANCEL.json and no OOM line
  is `STOPPED-UNKNOWN`: one alert, no automatic resubmit, never the x1.5 memory path. (4) The UNSIGNABLE scan runs from
  hour 3 on every job, including wave units, reading the newest setup number of any stage log.
- Owner: FLOW-OPS-1000 (classifier, cancel record), FLEET-WATCH-R7 (watchdog call). Now: someone with authority over the
  S81 wave decides whether lepe_mu_LP__t2 attempt 3 (event a9ed808a98d, tree d8j6r1: check whether the input changed
  since the -423 ps run) should run; I did not touch it.
- Fleet time: lepe t2 alone burned 8.6 job-hours today on two cancelled runs; with late detection about 26 job-hours
  past the rule, near 5 percent of the window's unit-hours as large jobs (I).

### (c) Disk caps hold launches fleet-wide; draining hosts sit half idle

- Count (V): LAUNCH-DISK-CAP 3 dies at 11:52:34 (QC, KV, S81) and s81_head at 11:40; each line shows every host of the
  die's list over `free - 150`. ot-run status 11:50: scratch free epyc2 138, intel1 164 DRAINING (cap 250), epyc8 180,
  epyc9 174 DRAINING (cap 250), epyc10 179, epyc7 382. epyc8 fell 293 -> 193 GB from 10:27 to 11:32 (R FLEET-WATCH-R7).
  Load: epyc9 47/96 with 240 threads booked, intel1 90/112 with 170 booked. UNDER-USE 11:53: "idle 0 of 624 threads".
- Trend: worse. At 09:55 only epyc10 was short. The 45-row QC V2 launch at 11:46 took the remaining room.
- Root cause (V, I): (1) private candidate trees are real copies (54 GB for S81) since f77c697efa, and the overlay fix did
  not land; (2) a host cap (`gen_host_min_free_gb` 250 on a host with 174 free) is a hold with no owner and no release
  term; nothing frees disk on a draining host because it drains, so the hold cannot end by itself; HOLD-AUDIT checks row
  holds only; (3) UNDER-USE counts booked threads, so a host at half load reads as full.
- Structural fix (P): (1) fix 3 of the last review: overlay private trees (`private-spec --base <sealed> --delta <dir>`).
  (2) A host cap carries owner and release term; HOLD-AUDIT prints HOST-CAP-UNREACHABLE when free space on a capped host
  has not risen for 2 h; auto-retire runs first on DRAINING hosts. (3) UNDER-USE reports `min(booked idle, load idle)`
  and names hosts with load under 60 percent. (4) A plan-event launch of N rows is paced by the disk room of the event's
  hosts, largest replica count first, so the wave does not fill the disk in one tick and then stall three dies.
- Owner: FLOW-OPS-1000 (1, 2, 4), FLEET-WATCH-R7 (3, and cleaning intel1 / epyc9 now).
- Fleet time: about 10 percent of fleet load capacity idle behind caps (I: 49 free load slots on epyc9 + 22 on intel1 of
  about 736). Largest number in this review.

### (d) Manual drain is a 9999 GB cap behind a 10-minute cache, and a drained host is a FAIL

- Count (V): 1 wave FAIL (slice_station__t45 a9, its ninth attempt), 1 lane NOT-RUN (FAM-KV-IOPC-R2 11:04). Drain window
  was 10:58 to 11:04 (6 min); effects seen until 11:44.
- Root cause (V): `host_drain.py` caches caps per host for 600 s; a unit that reads during the drain acts on it later.
  "Every target host is draining" raises RuntimeError -> class FLOW -> counts in caps (class a). Whether the unit held
  the caps in memory for 40 min or failed earlier and was polled late is not resolved (I).
- Structural fix (P): drain is pushed, not pulled: `kit_wave_edit` writes `drain_caps.json` with the kit_wave.json sha to
  every host in the same commit step, and readers trust only a file whose sha matches the hub's current one (one cheap
  ssh, no TTL). A heavy stage that finds all hosts draining waits 3 x 10 min with a fresh read, then ends as INFRA
  `DRAIN-WAIT` (not counted, relaunched automatically when a host admits). A manual drain entry needs an expiry.
- Owner: FLOW-OPS-1000. Fleet time: under 0.3 percent.

### (e) Signed-store ingest starves: one slow host or one hash mismatch blocks the count

- Count (V journal): 29 `Failed with result 'timeout'` since 11-20 05:00; the 10:35 run: 3 min CPU over 50 min wall.
  The chunked run (11:30): 15 min to scan 230,082 records, store 1,450 identities, 57 new inside 96 h; intel1 0 ingested,
  4 fails; intel2 0 ingested, 6 fails, "hash differs on 75 files, first .../closed/s81_head/hd_spn_eshim_tx__8569788b03/
  kit/.kw_inputs.json"; epyc2 chunk 1 of 6 (14.46 GB) at 11:46.
- Root cause (V, I): the ingest hashes the whole kit, including kit metadata that tools rewrite after close
  (`.kw_inputs.json`; I: kit_flow_refresh or a re-arm). Such a record fails on every run. Hosts are done in series under
  one service timeout, so the slowest host starves the rest. No alert: the count simply lags.
- Structural fix (P): (1) hash only the files named in the signed record's manifest (final DB, reports, signoff.json);
  mutable kit metadata is excluded by list. (2) Per-host budget with a checkpoint, hosts in round-robin, so a timeout loses
  one chunk. (3) `INGEST-STALE` alert when new-inside-96h > 0 and nothing was ingested for 3 h. (4) The scan keeps an
  mtime index so it does not walk 230k records each run.
- Owner: FLOW-CANARY-R2 (it owns e3c8933051). Fleet time: none. Cost: the sign-off count lags the real state.

### (f) The canary is permanently red

- Count (V): 12 verdicts in 5 posts (10:49 to 11:45), all FAIL. s81_head hold_ff -20.85 -> -68.1 ps at d032c72040,
  e338085d61 and c2047d41cc (identical); hbm_sram setup -30.71 -> -53.39, hold 8.26 -> -149.37 at two shas; s81 hold
  8.62 -> -54.58; s81_cl and s81_head_cl NO-BASELINE (fail at lint / synth, no metric).
- Root cause (I): the baseline comes from an older flow state (the nominal clock cap change r708 is a candidate), so
  every sha "regresses" by the same amount. A canary that is always red says nothing about a new commit, and 8bce6e7c35
  makes tag cuts wait for a release, so signed results stay SIGNED-UNVERSIONED (5 such rows in the 11:22 list;
  RETRY-UNVERSIONED waited on admission in all 9 ticks).
- Structural fix (P): verdict = change against the previous run of the same die, with the fixed baseline as a second
  column. The same failing value at 3 consecutive shas is `BASELINE-STALE`: one post, automatic rebaseline. A die whose
  canary cannot reach GRT is `CANARY-BROKEN`, a separate state that does not block tags of other dies. Tag cut waits
  for "no new regression", not for green.
- Owner: FLOW-CANARY-R2. Fleet time: about 1 percent (canary jobs on 6 dies each 15 min plus repeated re-sign) (I).

### (g) Carried, with numbers

- HBM is parked and still prints 2 ADOPT-GUARD alerts per tick (18 in the window), bind preflight, src_overlay, TOOL-SKEW
  279 of 279 and TOOLS-LAG 3,243. Third review. FLOW-OPS-1000: a `parked` flag that silences all five.
- TOOLS-LAG grows: QC 253 commits, HEAD 199, both missing r708 (was 208 and 154). KV 85, S81 58, none missing.
- Skew (V FLOW-HEALTH 11:07): cross-host compare ok on all 7 trees. Against main: s81 38 modules, KV 37, QC v1r6 40,
  HEAD 32 (pins, expected). The QC row still names tree v1r6; the live tree is v2r10 since 11:17: the skew check reads
  a stale tree name.
- Holds: `route_hold:SKIP-HELD=63`, `WAIT-FORM=42` (was 53), `KW-FIX-45=8`. S81: 301 rows on the J6 hold (was 319), 30
  eligible, 0 scheduled at 11:40. STUCK-STATE: s81 29 current-plan rows CANCELLED/SUPERSEDED with no successor for 60+
  min; s81_head 1 (hd_host_n, since 11-20 22:18). s81_head: 0 launches since 07:41; at 11:40 the reason finally printed
  (disk cap on epyc10 and epyc7, its only hosts).
- Unowned (V failure_breakdown): 4 QC types with no kit-wave row and no owner (sle_hc0 ...pv48712631, ...pv6e886d59,
  slw_hc0 ...pvd0aa3ddc, ...pvde134a90): QC-PLAN-R11 should say whether V2 retires them. S81 iqf__t1 ROUTE-HELD geom
  7.6 h (FAIL-S81-1). failure_breakdown's live check prints "NOT SEEN: intel2" when run on intel2 itself.
- V2 QC event: 45 rows launched in one tick; PRECHECK-1119 lists 53 of 130 types over the 300 um hop cap (worst 678 um)
  and 22 unregistered-read candidates. The precheck is an estimator, not a gate; QC-PLAN-R11 should expect that share to
  stop at PLACE-SETUP-STOP and have V3 rows ready.
- Lanes (V): 16 stand-downs from 10:40; 32 DIED posts (16 rc 1), 10 under 120 s. `ot-run --cancel` prints `epyc10:
  ot-heavy-stop: 0 scope(s) stopped` first for jobs on epyc7 and epyc8; both jobs did end (exit 143 classified 11:50).
  ot-run end times from epyc hosts are still UTC.

## Do now (ordered)

1. FLOW-OPS-1000: classifier reads a cancel record; UNSIGNABLE cancel -> STRUCT-STOP, never the OOM resubmit (class b).
2. FLOW-OPS-1000: tool-fault attempts do not count in caps; clear the 6 E2BIG caps; one ssh helper with stdin payload;
   units re-resolve rt at stage boundaries; FAIL-ROUTE sends FLOW/INFRA pipeline classes to the flow lane (class a).
3. FLEET-WATCH-R7: free disk on intel1 and epyc9 first; FLOW-OPS-1000: overlay private trees, host caps with owner and
   term, UNDER-USE on real load, paced event launches (class c).
4. FLOW-OPS-1000: pushed drain state with sha, DRAIN-WAIT instead of FAIL (class d).
5. FLOW-CANARY-R2: ingest hashes the manifest set only, per-host budget, INGEST-STALE alert; confirm the 11:30 chunked run
   ended with records ingested (class e). Canary verdict against the previous run, BASELINE-STALE rebaseline (class f).
6. QC-PLAN-R11: the 4 unowned QC types; V3 rows for the V2 types the precheck flags. KV-PLAN-R6: nothing for E2BIG; the 6
   pre-fix KV units fail once more and relaunch on the fixed rt.
7. FLOW-OPS-1000: HBM `parked` flag; skew check follows the live tree name; WAITS.tsv hub step.
