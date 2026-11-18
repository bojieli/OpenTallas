# FABLE-FLOW-1000: procedural and flow failure review (Fable, advisory, 11-18 09:43-09:55 PST)

Read-only review of 07:40-09:45 PST. Sources (intel2): autopilot/log.txt, autopilot/jobs/*/a1.log, kit_wave.json, lanes/FLOW-HEALTH.tsv,
tools/failure_breakdown.py, `ot-run --status`, ~/merge-queue/log, lanes/posts/, and a glob probe (no find) of kits and launch trees on 6 hosts.
No new holds or gates are proposed (r703). Host rails stay (r709). Counts are measured; "share" is my estimate of kit-hours lost of about 1,200 in the window.

## Headline
- Kit FAILs 216 in 2 h (79 / 96 / 41 by hour 07:40-, 08, 09-:45); 147 in the previous window. Launches 344, stage SUBMITs 100.
- 115 of the 216 FAILs (53%) are two stale-copy classes: RESET "refuses empty explicit buffer set" 104 (46 / 53 / 5 by hour) and relay_mid
  hook coverage 11. Both were fixed on main before most of the fails. The rate fell to about 3/h after 09:20 only because S81-COL-FLOW-1118
  patched 1,297 kit copies and 21 launch trees by hand on 7 hosts.
- The per-stage flow refresh (2757cb783bb) is on main and in rt, but it has NEVER RUN. 41 stage jobs carried the new chain; 0 printed
  KIT_FLOW_REFRESH; 0 flow_refresh.jsonl exist on any host. Cause: the stage job runs under bwrap, where /srv is empty except declared inputs,
  so rt/current/tools/autopilot/kit_flow_refresh.py is not a file there and flow_refresh() returns None without a line.
  The tool itself is right: a dry run on live kits would replace 4 files (epyc8) and 31 files (epyc9), tt_setup_repair.tcl among them.
- epyc2 scratch2 (880 GB disk) went 200 GB (08:11) -> 0 GB (09:3x). 30 stage jobs died "OSError: [Errno 28] No space left on device" in the
  09 hour, all on epyc2, all recorded "CRASH -> structural.tsv". epyc2 and epyc10 (33 GB) are refused by ot-run and skipped by rt sync, so they
  hold old runtimes: epyc2 c860f199a9c6, epyc10 edd8d74c3b0d; the rest 0c3fb152c30a. Every sync still ends "SYNC FAILED exit 4".
- Tick is longer again: 696, 790, 859, 1274, 1328, 754, 907 s (median 859 s; 640 s at 0800).

## Did the fixes take?
| fix | verdict |
|---|---|
| per-stage flow refresh from rt (TOOLS-DECOUPLE 2757cb783bb) | NOT LIVE. Never executes (bwrap hides rt/current; silent skip). Also by design it covers only autopilot stage jobs (route/finish). The wave gen + place stage is not covered at all, and that is where all 115 stale-copy FAILs happened. |
| tt_setup_repair.tcl line 134 (922c27887ac, 09:26) | On main and in rt 0c3fb152c30a. Reaches no existing kit: 1,965 of 2,476 kit attempt dirs touched in the last 6 h hold a copy other than the fixed one (intel1 233/283, epyc2 194/652, epyc7 64/64, epyc8 665/666, epyc9 199/201, epyc10 610/610); 134 of 139 launch trees hold the pre-fix blob e2363090. The bug lived on main 03:36-09:26. The setup-repair step is silent when it dies, so there is no FAIL count; the cost shows as timing misses at sign-off. |
| orphan units stopped on own FAIL (b516b6f7bac) | NOT SEEN FIRING. 2 ORPHAN lines in the window, both the old reason ("older than attempt 7"). The 61 units were stopped by hand by WAVE-FLOW-R2. 5 S81 leaf jobs still print "kit busy (container: False, logs 517-621 min old)", 29 lines. |
| stage-scoped SKIP-SAME-INPUT (c3e97ccccf) | NOT SEEN: 0 lines. REPEAT "unchanged relaunch after a repeated failure" rose 21 -> 50 lines. The 53 RESET fails of the 08 hour were relaunches released by hand retry keys onto kits that still held the old Tcl. |
| reap_dead off the tick path | TOOK. reap_dead is gone from the step timers (was 386-740 s); REAP-PROBE runs in the background. The tick did not get shorter: collect 116-170 s, poll_running rose 17 -> 134-191 s, reap_stale_attempts 123 s (2 ticks), wave_balance 253 s (1 tick), and "kit_wave_step+admit" exceeds the step total by 37-665 s (08:47: 1,158 s against 492 s) with no timer. |
| stale admission lock (7c54d9c198c) | In rt since 09:23 on 5 hosts; NOT on epyc2 and epyc10 (sync skipped; "ot-heavy differs from main" alert). The epyc7 stall (16 waiters, 70 min, dead holder pid) ended 09:07, before the fix arrived; no stall after it. Unproven. |
| host lists from gen_hosts | PARTLY. 15 GEN-HOST-TREE re-picks work ("epyc7 lacks tree; launching on epyc8"). KW_RT_TOOLS "die tree missing on tolerant-swine" still fails KV place: 7 at 07:42, 2 at 09:19. The place stage still lands on the hub, which is not in the KV gen_hosts. |
| epyc7 docker/IO hang | Diagnosed (overlay unmount waits on the fs journal under IO pressure from two metadata scans). docker ps answers in 0.07 s now, but IO pressure "full" is still 10% avg60. Cause class (fleet-wide scans of 3 TB) is not removed. |
| disk: KIT-SLIM, bind_sinks not copied (53f46fcb3c) | TOOK where run: intel1 +591 GB (572 free), epyc9 +334 GB. Not run on epyc2/7/8. epyc10 3 -> 51 -> 33 GB: it refills faster than the pass frees. epyc8 175 GB, falling 209 GB/h at 08:10. |
| export split | TOOK. 3 records RTX-FULL-AGI-META since 08:17; archive_gate.py now accepts the status. Open: signed-store-ingest.timer is still active and still copies whole units to AGIdock. |
| kit_wave.json "dirty edit" | Clean at 09:50, but the cause is unchanged: 12 lane commits to the file in 45 min, retry lists S81 336 / QC 251 / KV 59 keys, 257 RETRY-IGNORED and 106 RETRY-RELEASE lines, one reported uncommitted wave edit at 09:01 that dropped 21 keys. |

## Classes

### A. Fix on main does not reach kits - 115 FAILs, share about 11%, plus the silent setup-repair loss
- Root cause: three copy layers (rt -> launch tree chosen at launch -> gen dir -> attempt dir), and relaunch restores from items/<item>/gen.
  No layer is refreshed; the one refresh that exists cannot see rt.
- Structural fix: kits stop holding copies of main flow scripts. gen writes a link (or a one-line `source $OT_RT_FLOW/<file>`) and each stage
  job gets rt/<sha>/tools/die_plan as a declared read-only input, the way preflight and lec are staged today. Then a fixed file reaches every
  stage that has not started, including place, with nothing to patch. Until then: stage kit_flow_refresh.py + the blob index through
  admission_tools, call it from the wave place launcher too, and print a line when it is skipped.
- Owner: TOOLS-DECOUPLE (staging, place stage), WAVE-FLOW-R2 (launcher call). S81-COL-FLOW-1118 keeps hand patching until it is live.

### B. Disk floor on tree hosts - 30 job deaths, epyc2 and epyc10 out, share about 5% and rising
- Root cause: epyc2 scratch2 is 880 GB and received 440 units; cleanup frees less than the wave writes (238 GB/h at 08:10). A host under the
  floor keeps its running jobs, which then die mid-write. ot-auto-clean has not completed a pass on epyc2 ("for ever"), epyc10 (100 min), epyc7 (92 min).
- Structural fix: job output size is known per type from earlier attempts; the launcher subtracts in-flight bytes per disk (LAUNCH-DISK-CAP does
  this for the wave, not for stage SUBMITs, which went to epyc2 at 170 GB free with 105 running). ENOSPC must class INFRA with a free retry on
  another host, never "CRASH -> structural.tsv". rt sync: a host under the floor is "skipped", exit 0 (asked at 0800, not done).
  KIT-SLIM as a timer on every host, not a one-off lane pass.
- Owner: FLEET-OPS-R (epyc2/epyc10 now, cleanup timers), WAVE-FLOW-R2 (ENOSPC class, SUBMIT disk accounting), TOOLS-DECOUPLE (sync exit).

### C. Relaunch onto an unchanged failing input - 50 REPEAT lines, 53 re-fails, share about 4%
- Root cause: hand retry keys override the input comparison, and the comparison does not include the kit's flow-script copies, so "fixed on
  main" looks like a changed input while the kit is byte-identical.
- Structural fix: the input hash of a stage is the hash of the files that stage will execute in the kit. Class A makes that equal to the rt sha.
  Then delete dies.*.retry: a relaunch is a state command (rearm), not a config key.
- Owner: WAVE-PILOT-FIX.

### D. Wave writes the config file that lanes edit - the kit_wave.json confusion
- Root cause: the wave consumes retry keys by editing kit_wave.json; lanes edit the same file under git through kit_wave_edit.
- Structural fix: the wave never writes kit_wave.json. Consumed keys go to kit_wave_state.json; with C done the keys disappear entirely.
- Owner: WAVE-PILOT-FIX.

### E. Tick length - median 859 s, multiplies every class
- Structural fix (unchanged from 0800, not built): one per-host snapshot per tick read by collect, poll_running, wave_balance and under-use;
  an "other" timer for the 37-665 s outside the step.
- Owner: WAVE-FLOW-R2.

### F. Dead attempts keep units; place lands on a host without the tree
- 5 "kit busy" jobs at 517-621 min; own-FAIL orphan stop not observed. KV place on the hub: 9 INFRA fails.
- Structural fix: the collect call that writes FAIL stops that unit in the same call; the place job declares the die tree as an ot-run input,
  so ot-run itself can only pick a host that has it (stage SUBMITs already do: "INPUT HOLD: spec inputs exist only on ...").
- Owner: WAVE-FLOW-R2.

### G. STALE and non-design rows
- STALE 57, all HBM (parked; 9 unowned), unchanged. S81 "no host" 46 rows (disk, class B). QC cancelled (superseded) 16, up from 9.
- 5 dies show TOOLS-LAG against the pinned trees (hbm 2,259 commits, QC 1,162, S81 350); it no longer matters for tools taken from rt, and the
  line should be dropped or it will be read as a real lag.

## Do now (ranked)
1. TOOLS-DECOUPLE: make the refresh run (stage it through admission_tools or declare rt tools as a job input), cover the place stage, print on skip. Proof = flow_refresh.jsonl count > 0.
2. FLEET-OPS-R: free epyc2 and epyc10 above the floor; get ot-auto-clean passing on epyc2/7/10; KIT-SLIM on epyc2/7/8.
3. WAVE-FLOW-R2: ENOSPC = INFRA free retry (30 rows sit in structural.tsv as CRASH: re-class and relaunch); SUBMIT uses the disk cap.
4. TOOLS-DECOUPLE: rt sync exit 0 on skipped hosts; push the admission-lock fix to epyc2/epyc10 once they have room.
5. WAVE-PILOT-FIX: stage input hash from executed kit files; delete retry lists; the wave stops writing kit_wave.json.
6. WAVE-FLOW-R2: per-host snapshot and "other" timer; KV place declares the tree as input.
7. AUTO-EXPORT-1118: turn off signed-store-ingest.timer (the gate accepts RTX-FULL-AGI-META now).
