# FABLE-FLOW-1400: procedural and flow failure review (Fable, advisory, 11-18 13:43-14:05 PST)

Read-only review of 11:40-13:50 PST. Sources (intel2): autopilot/log.txt (5,034 lines in the window), autopilot/jobs/*/a1.log, tick_hosts.tsv,
kit_wave.json, kit_wave_state.json, lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py, `ot-run --status`, lanes/posts/, and one glob probe
(no find) on the 6 build hosts. No new holds or gates are proposed (r703); host rails stay (r709). Counts are measured. "Share" is my estimate
against about 1,100 job-hours in the window (520-600 running jobs x 2 h).

## Headline
- Kit FAILs 37 in the window (216 in the 1000 window). By hour 10/11/12/13: 12, 20, 5, 25. Launches 136 (9 / 22 / 105 by hour), stage SUBMITs 53.
  Sign-offs classified in the window: 4.
- Stale-copy FAILs: 0 (115 at 1000). RESET "empty explicit buffer set" 0 since 09:19; relay_mid hook 0.
- ENOSPC job deaths: 41 logs in the 10 hour, 1 in the 11 hour, 0 after. Admission / disk refusal lines: 0. Rows waiting on disk: 27 (constant).
- Tick: 397-671 s, median 521 s (859 s at 1000). kit_wave_step is 280-525 s of it; collect 42-99 s, launch_safe up to 112 s.
- Fleet 93-96% of threads used. The idle part is all epyc7 (19-41 threads idle, load 45-78 of 96, admits 512 GB) while intel1 carries
  138-192 waiters (3.3-6.0 TB asked).
- The main loss in this window is not tooling failure. It is two config facts that lived in a lane's head or a post, not in the data the wave
  reads: QC did not launch for 3.2 h (asbuilt pointed at an old clock table), and 58 col_h9_r1 kits were launched on a plan known not to route.

## Did the fixes take?
| fix | verdict |
|---|---|
| per-stage flow refresh incl. gen and place (TOOLS-DECOUPLE) | TOOK. 2 h records in KIT/flow_refresh.jsonl on 6 hosts: gen 284, place 190, route 10; hub job logs: 68 of 98 stage jobs print KIT_FLOW_REFRESH (lec.py, stage_odb_cap.py, hold_guard_grt.tcl, relay_mid.tcl replaced). All 190 place refreshes replaced at least one file, 0 of 284 gen refreshes did: gen still writes old copies from the die tree and the place refresh repairs them. Stale-copy FAILs 0. Not on epyc7 (0 records: no wave gen there). |
| executed-file stage hash, SKIP-SAME-INPUT (5394ba84c2) | PARTLY. SKIP-SAME-INPUT 38 lines (0 at 1000). But 38 of 54 RELAUNCH-ON-FIX lines say only "changed env", and those rows fail the same way again (class C). |
| CANCELLED rows relaunch without keys | TOOK, with a side effect: a lane cancel is undone in 8 min (cbx_q10, class D). |
| non-HBM retry lists deleted | NOT DONE. retry keys: S81 338 (336 at 1000), QC 275 (251), KV 59, HEAD 11. RETRY-IGNORED 89 lines; a new retry commit at 13:29 (S81-COL-FLOW). |
| stale-ENQUEUED retire (0b982e36ea) | TOOK. 10:44: 66 rows retired in one pass (not 9-10). The named rows (slice_station t14/t30/t44/t50/t6/t7 on e9eda32d41c, hd_turn_a l48ui) are CANCELLED SUPERSEDED; kw26 / kw24 / kw41src are gone from epyc2. 0 new since. |
| ENOSPC classed INFRA (f59cb55fdd0) | UNPROVEN. 0 "infra-disk" CLASSIFY lines all day; the 41 ENOSPC logs of the 10 hour were classed before rt carried it. No ENOSPC since, so it has not fired. |
| stage disk cap (8df70a17c67) | TOOK. 550 of 1,401 ot-run clients on the hub carry --disk (kit_peak_gb.json p90 5.94 GB, n 24, 13:34). |
| resumed-stage host re-pick (96e72f648d6) | TOOK. 29 RESTAGE lines (epyc2 -> epyc8) with gen_hosts-only picks; 0 KV "die tree missing on tolerant-swine" in the window. |
| ot-job ref drop + reaper (f8647ef9e5) | PARTLY. rt 4815c737fdbe on all 6 hosts. job-* refs older than 6 h: epyc2 3, epyc10 109, epyc8 147, epyc7 201, epyc9 214, intel1 265. epyc7 runs 48 jobs and holds 231 refs, so at least 180 are dead refs the reaper did not take (its rule needs "no job dir left"; dead job dirs remain). ODB-free publish: epyc2 ot-store is still 374 GB of a 944 GB disk (old objects; only a gc frees them). |
| flow ODB dedupe + log gzip (36f8b7312e) | Dedupe runs (stage_odb_cap.py is in 35 refresh lines). gzip NOT SEEN: 0 run_*.log.gz under the kit attempt dirs on 6 hosts (my glob; treat as not observed, not as proof). |
| tick length | Better: median 521 s. The per-host snapshot (tick_hosts.tsv) is written each tick. |

## Classes

### A. A config pointer disagrees with the artefact it is used with: QC launch stop, 56 rows, 09:40-12:53 (3.2 h)
- Count and trend: BIND-STALE lines 17 today; 39 rows at 09:40, 56 from 11:22 to 12:53; 0 after 13:00 (57 QC launches 13:00-13:07).
  The 11:36-13:06 figure is the part after the N3 jobs drained; the first line is 09:40.
- Root cause: kit_rtl.asbuilt (asbuilt_n4_portable.json) was hand-made at the N4 publish and still named the N2BBR clock landing table
  (d080395e); the bind DBQ was built on the N4DBQ table (dcdadbc1). Three files (asbuilt, bind, plan) each carry their own copy of the clock
  table reference, and the only check that compares them is the wave's launch-time preflight. The publish chain (advisory gate, apply) does
  not run it, so a mismatch that is fully known at publish time is found one tick later and repeated every tick with no owner.
- Structural fix (makes it impossible): the asbuilt is not written by hand. publish_apply derives it from the bind it publishes
  (bind INPUTS_ISOLATED already lists the clock table sha; write asbuilt from that), or simpler: kit_topology.bind_matches reads the clock table
  sha from the bind record only and the asbuilt carries no second copy. Until then, publish_apply runs kit_topology.bind_matches for all types
  of the candidate as part of apply (8 s for 133 types, measured by QC-PLAN-R3) and refuses its own apply on stale > 0: that is the apply
  failing its own input check, not a new launch hold. Second: a BIND-STALE line that repeats on 2 ticks posts once to the die owner lane with
  the differing key (here "clock_table_sha256 only"); the line today lists 56 names and no cause.
- Owner: TOOLS-DECOUPLE (apply check, derived asbuilt), QC-PLAN-R3 (N4.1p uses it). Share: 0% compute (fleet stayed 93%+ busy on S81), 3.2 h of QC
  schedule, 19 keyed QC types and 56 rows late by that much.

### B. Launch list and stop list are two hand-edited lists: 58 col_h9_r1 kits on the d8t plan
- Count: 58 launches 09:15-11:2x (16 / 5 / 4 / 5 / 5 / 15 / 8), 0 after 11:23. State now: 34 RUNNING + 26 ENQUEUED on event 3fa87b84b18;
  route SUBMITs for them still go out (13:36, onto epyc2). One was 3.7 h in GRT without reaching DRT.
- Root cause: "do not build col_h9_r1 on d8t" was a sentence in a strategy post; the launch came from an only_items base entry a lane added
  at 09:15. The wave reads only kit_wave.json. The known verdict (GRT-0116 from frame_int_o0 stations at y 1226.88, fixed by the D8e plan)
  was not attached to the type's input, so nothing compared the two.
- Structural fix (self-stopping, no hold list): a structural verdict is recorded against the plan-block hash of the type
  ("col_h9_r1__t1 @ block X: GRT-0116, needs plan change") in the same fail_keys store SKIP-SAME-INPUT reads. A relaunch on the same block is
  then skipped by the existing rule and released by the D8e apply with no lane edit. A force (only_items base entry, retry key) names the
  attempt and the input hash and is consumed once; it cannot widen to a family. The 60 live kits: S81-COL-FLOW should cancel the 26 ENQUEUED
  ones that have not reached GRT and let the 34 finish only if any is past GRT.
- Owner: WAVE-PILOT-FIX (verdict as fail_key by block hash, one-shot force), S81-COL-FLOW-1118 (the live kits).
  Share: about 10% of the window (60 jobs x 2 h of 1,100), plus about 100 job-hours before 11:40.

### C. SKIP-SAME-INPUT released by "changed env": 38 relaunches, same failure again
- Count: RELAUNCH-ON-FIX 54, of which "changed env" only 38 (S81 28, QC 5, KV 5). Example: sle_su_l1__cl5ea486db fails kit_topology 13:23,
  SKIP 13:26, "changed env" 13:35, launches, fails identically 13:41. Same for the 4 S81 LP types ("2 tree files declare it with different
  headers": 13 FAILs, attempts 21-26), serdes t2/t3 OT_BOOT_RELEASE, kv3_hub_C (772,806 cells, 3 launches), kv3_hub_Wo.
- Root cause (inferred from timing, not read in code): the releases come in bursts at 11:45, 12:54, 13:05, 13:16, 13:25, 13:35, each right
  after an rt sync or a config commit of another die (QC had no config change between 13:26 and 13:35; rt moved to 4815c737fdbe at 13:33).
  So the env part of the stage hash still holds a value that moves with every rt sha or die-global edit, not only keys the failing stage reads.
- Structural fix: the hash for a stage is built only from the env keys that stage's scripts read (a static list per stage family, checked by
  a test that greps the scripts for $::env / os.environ names). The log line names the changed key ("changed env: OT_X a -> b"); without
  that this cannot be audited. Delete the retry lists as planned (683 keys); they are the other way past the rule.
- Owner: WAVE-PILOT-FIX. Share: about 2% (most die in gen / kit_topology within minutes; the kv3_hub_C and serdes ones reach place).

### D. A lane cancel is read as an OOM kill and relaunched bigger: cbx_q10, 4 kits
- 13:09 QC-PLAN-R3 BIND-FAIL-CANCEL stops 4 cbx_q10 kits (strict bind / LATCHECK failed). 13:10 classify: "exit 143, stopped from outside"
  -> CRASH -> structural.tsv. 13:15: "OOM kill; the resubmit runs with place memory x1.5". 13:17 all relaunched, unchanged, on the bind
  that failed; cl94a12200_h again at 13:35 via "changed env".
- Root cause: publish_apply bind-fail cancels units but writes nothing to the row. The wave then guesses the cause from the exit code.
- Structural fix: bind-fail writes the row itself: FAIL, class BIND, input key = the bind id. SKIP-SAME-INPUT then stops it until a new bind
  is published, with no hold. `ot-run --cancel` records who and why next to the unit, and classify reads that before any guess; exit 143
  with no OOM line is never OOM and never gets x1.5 memory.
- Owner: TOOLS-DECOUPLE (bind-fail writes the row), WAVE-FLOW-R2 (cancel reason, OOM rule). Share: about 1% (4 kits x 48 replicas, running now).

### E. epyc2 scratch2 at 46-94 GB: the wave measures one disk and writes to another
- epyc2 scratch2: 46 GB free of 944 GB, falling 13-49 GB/h; scratch3 on the same host: 1,596 GB free of 3,779 GB.
  kw43-wave-1109n and kw45 on scratch2 are symlinks to scratch3, so kits do not fill scratch2. What fills it: ot-store 374 GB and ot-jobs
  (58 dirs). ot-run reports "scratch 52 GB", disk_rate alerts every hour, AUTO-RETIRE deletes 0.
- Root cause: the store and job dirs default to the first scratch disk; the disk gate reads free space of the path as written, not of the
  filesystem the job will write to.
- Structural fix: ot-job picks store and job dir on the scratch filesystem with the most free space per host (one line in default_store),
  and every free-space read uses the realpath of the work root. The ref reaper drops a ref whose pid is gone whether or not the job dir is
  still there (class above: 180+ dead refs on epyc7), then store gc frees the published ODBs that f8647ef9e5 no longer needs.
- Owner: FLEET-OPS-R (store gc, move), TOOLS-DECOUPLE (default_store, reaper rule). Share: under 1% now (29 restages off epyc2); the risk is
  a repeat of the 30 ENOSPC deaths, since epyc2 runs 100 jobs.

### F. epyc10 dropped with "not a manifest tree": the apply replicates from the hub, which holds no tree
- apply_reviewed_tree_marker.py runs `src_manifest.py replicate <tree> --hosts <extra>` with bash on the hub. The hub is not a tree host,
  load_manifest fails there, and every host that is in the die's gen_hosts but not in the candidate's list is dropped, even when it already
  holds the verified tree (epyc10 held n4_s1 with the right manifest). derive_gen_hosts put it back at 13:07, about 10 min later this time;
  the worst case is 1 h. epyc7 holds n4_s1 too and is still not in the QC gen_hosts.
- Structural fix: verify first (`hosts --expect`), replicate only on a mismatch, and run replicate over ssh from a host of the candidate.
  A source-side error is an apply error, never a host drop. After an apply, run derive_gen_hosts once instead of waiting for the hourly cron.
- Owner: TOOLS-DECOUPLE. Share: small this time; it is the reason the roomiest hosts keep falling out of gen_hosts.

### G. Host imbalance: epyc7 half idle, intel1 queue 138-192 deep
- S81 gen_hosts = epyc10, intel1, epyc2, epyc8 (not epyc7, epyc9); QC = 5 hosts (not epyc7). epyc7 has 1,581 GB free and 512 GB admit.
  Its inbound link is about 3 MB/s, so a tree takes about 2 h to arrive.
- Structural fix: tree replication to all 6 build hosts starts when a candidate is published (before apply), chained host-to-host;
  gen_hosts is derived, never typed. Owner: TOOLS-DECOUPLE. Share: about 7% of threads idle (41 of 624) against a 3-6 TB memory queue on intel1.

### H. Late ECO dies in under 2 s: "prd_mk.sh t10 failed (pass dir not staged)"
- 3 in the window, 12 today: slice_station__t26 (FF hold -3.47 ps), hd_ctl (FF -5.59 ps), col_h9_r2 pvea45273b (TT -44.75 against -42).
  These are the nearest sign-offs on the fleet and the ECO never ran. A fix for a read-only staged copy is on main
  (test_prd_mk_readonly); the kits still fail, so either the kit copy of post_route_drv is old (check that kit_flow_refresh covers that
  directory) or the cause is a second one. Not verified further.
- Owner: WAVE-FLOW-R2. Share: under 1% compute, 3 probable sign-offs per 2 h.

### I. STALE and non-design rows
- STALE 105 current-event: HBM 104 (parked, 11 unowned), QC 7 (CANCELLED SUPERSEDED 04:25, 9.3 h, owner KIT-WAVE-1: with auto-relaunch of
  cancelled rows live, these 7 should have relaunched; they did not). S81 non-design: other flow error 3, global_place error 5.
- TOOLS-LAG still prints (hbm 2,284 commits, QC 1,187, S81 375): drop the line, tools come from rt. TOOL-SKEW WARN 43 + UNMEASURED 17 lines,
  CELL-BIG 3,434 lines (68% of the log), REAP-DEAD SILENT 128 "reported only": log noise that hides the 37 FAILs.
- "ARCHIVE FAILED 3054c87a89d6 (x19): probe rc 1: Traceback" at 12:21: 19 repeats, no owner line.
- The hub checkout alert at 13:02 is a false one ("ahead 3, behind 0").

## Do now (ranked)
1. TOOLS-DECOUPLE: apply runs bind_matches on the candidate and refuses itself on stale > 0; asbuilt derived from the bind (class A).
2. S81-COL-FLOW-1118: cancel the 26 ENQUEUED col_h9_r1 kits on d8t that are not past GRT. WAVE-PILOT-FIX: structural verdicts stored as
   fail_keys by plan-block hash; forces are one-shot (class B).
3. WAVE-PILOT-FIX: env part of the stage hash = keys the stage reads; print the changed key; delete the 683 retry keys (class C).
4. TOOLS-DECOUPLE + WAVE-FLOW-R2: bind-fail writes the FAIL row with the bind id; exit 143 is never OOM (class D).
5. TOOLS-DECOUPLE: apply verifies before it replicates and never replicates from the hub; replicate to all 6 hosts at publish (F, G).
6. FLEET-OPS-R: epyc2 store gc and move to scratch3; reaper takes dead refs with a job dir left (E).
7. WAVE-FLOW-R2: late-ECO pass-dir staging (H); log noise: CELL-BIG once per type, drop TOOLS-LAG.
