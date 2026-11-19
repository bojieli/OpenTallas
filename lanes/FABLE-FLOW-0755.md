# FABLE-FLOW: flow and procedural review, 05:43 to 07:55 PST 11-19 (FABLE-FLOW-10xx, read-only)

Sources: autopilot/log.txt (7,756 lines in the window), kit_wave_state.json (07:47), ~/coord/tools/failure_breakdown.py
(07:50), ot-run --status (07:45), rt/history.log, /var/tmp/ot-heavy/admit.log and /var/tmp/ot-oom-age/kills.log on
intel1/epyc2/epyc8/epyc9/epyc10 (epyc7 refused ssh), lanes/FLOW-HEALTH.tsv, ps on intel1, FABLE-FLOW-0555.md.

Window totals (last window in brackets): LAUNCH 444 (22): S81 427, QC 14, HEAD 3, KV 0. FAIL 247 (5).
CANCEL-SUPERSEDED 15 (6). Guard kills 0 on the 5 hosts read (1). REPEAT 63 (8). SRC-INCOMPLETE 41 (58).
Threads 92-99% used. Waste shares are estimates; none is measured exactly.

## Ranked by fleet time wasted

### A. Snapshot copy storm took epyc7 off the fleet. New. Largest. Estimate 15-20%, still rising at 07:52.
- 244 of the 247 FAILs are one line: "@pipeline TimeoutExpired ... ssh <src> ssh epyc7 mkdir -p
  /srv/opentallas-scratch2/kit-store/snaps/<id> && rsync -a ...". Destination epyc7 183, epyc9 61. Seven snapshot
  ids, three of them carry 223 of the fails (3cb1702b 93, 63392233 82, addb6f0b 48). Fails by tick: 07:08 88,
  07:21 58, 07:35 98. 55% of the window's launches ended here before using any build time.
- epyc7 load: 133 (06:43), 327 (06:57), 588 (07:15), 590 (07:27), 776/96 at 07:52 (15-min mean 691). It is not
  easing. ssh to epyc7 was reset or timed out in 3 of my 4 tries; ot-run --status prints "epyc7 unreachable";
  ORPHAN and STOP-SURVIVOR checks log "epyc7 not checked"; AUTO-RESIGN export to epyc7 timed out 6 times.
- Cause, seen in ps on intel1 at 07:51: 131 live rsync clients to epyc7, 74 of them copying the SAME 5.8 GB
  snapshot 3cb1702b, the oldest 3,793 s old (started 06:47). epyc2, epyc9, epyc10 each hold 42 and epyc8 38 more.
  About 295 parallel copies in all. tools/autopilot/kit_wave_roam.py ensure_snap() tests "<snap>/.verified on
  dst" and, if absent, starts its own full rsync. Each row does this alone, so N rows of one snapshot start N
  copies of it. The wave's timeout marks the row FAIL but does not end the rsync, and the relaunch (23 at 07:1x,
  86 at 07:2x) adds a new copy on top. The class feeds itself.
- The BOUND-FALLBACK fix from 0555 A (255a0c4245) released 103 then 155 S81 rows at once; that is correct and
  wanted. It only exposed that the copy has no sharing.
- cb448f6ac56 (skip hosts above 2 x cores in pick_gen_host) does not cover this path: the copies are not picked
  jobs, and the orphan copies keep running whatever the pick does. FLOW-GUARD CLASS-BREAKER opened on the class at
  07:08 and launches continued (stops are off, r703), so nothing ends it.
- Structural fix (no hold, no cap on launches):
  1. One copy per (snapshot, destination). ensure_snap takes a flock on dst at <snap>.copying; a row that finds
     the lock waits on it and then re-tests .verified. N rows then cost one rsync.
  2. The copy runs under `timeout` on the source host with the same limit the wave uses, so a row that the wave
     has failed leaves no rsync behind.
  3. The row's snapshot is copied before the launch is recorded, once per tick per (snapshot, dst), and a copy
     failure is an INFRA retry on another host, not a design FAIL. 244 rows now sit in FAIL with a Tcl-error class.
  4. One-time: the ~295 live rsync clients to epyc7 are leftovers of rows already failed. I did not touch them
     (read-only). FLEET-OPS-R decides; until they end epyc7 stays unreachable.
- Owner: WAVE-PILOT-FIX (1-3, kit_wave_roam.py), FLEET-OPS-R (4, and epyc7 sshd).

### B. Tools rollout: epyc8/9/10 ran a 77-minute-old rt; both new fixes reached the hosts only at 07:48. 2-4%.
- rt/history.log: 06:31 all 6 hosts on 67c25c671d91. The next four hub promotions (07:03 01900fe5, 07:08 4a861bec,
  07:18 7293a6df, 07:33 0ccfdf3d) list only intel1 and epyc2. epyc7 has no line at all in those four, not even a
  FAILED one, and epyc8/9/10 stayed on 67c25c671d91. At 07:48 59024a5e802d went to intel1, epyc2, epyc8, epyc9,
  epyc10 and logged "epyc7 FAILED ssh: kex_exchange_identification".
- So at 07:52: cb448f6ac56 and df9f0958284 are in rt/current on the hub and 5 build hosts (checked by ancestry of
  59024a5e802d and by readlink on each host). epyc7 is UNVERIFIED and almost surely still on 67c25c671d91.
  Neither fix was live anywhere before 07:48, so this window cannot show whether the load-aware pick works.
- Root cause (UNVERIFIED in code, read from the log shape): the per-host loop stops at the first host that hangs
  (the 300 s ssh timeout on epyc7) and the next promotion starts before it reaches epyc8/9/10. The 07:48 run got
  a fast reset from epyc7 instead of a hang and went on.
- Structural fix: ot-tools-sync pushes to all hosts in parallel with one result line per host every time
  (ok / FAILED reason), and a host that missed a promotion is retried on the next run before new work. The wave
  does not pick a gen host whose rt/current differs from the hub's (ordering only: it picks it again once equal).
- Owner: FLEET-OPS-R (ot-tools-sync), WAVE-PILOT-FIX (pick).

### C. Host load other than epyc7. 3-5%, easing.
- 07:45: epyc9 129/96 (was 290 at 07:27, 203 at 06:43), epyc10 124/96, epyc2 117/128, intel1 94/112 (198 at 07:15),
  epyc8 80/96, hub 56/112. Threads asked: epyc9 735, epyc10 568, epyc2 500 on 96-128 cores.
- 0555 B fix landed as cb448f6ac56, live since 07:48 only. Re-read next window.
- Owner: FLEET-OPS-R. No new fix.

### D. Source copy to epyc2 fails every tick: 16 of 16 (was 6 of 6). 1-2%.
- The 0555 fix "log the first stderr line" landed and gives the cause: "tar: .../kw45/snap_qwen_compute/
  qwen_compute_n43_s3_postbind_1119041444/_postbind/out/rtl/bind_cells.sv: Cannot open: Invalid cross-device
  link". On epyc2 /srv/opentallas-scratch2/claude/kw45 is a symlink to scratch3 (since 11-14). The copy writes
  hardlinks into a store on the other filesystem. It is not the disk floor (scratch2 148 GB, floor 150).
- Not landed: stop after 2 identical failures. epyc2 is still not a QC gen host (9 SRC-INCOMPLETE lines).
- Structural fix: SRC-SYNC resolves the destination with realpath and uses the store of that filesystem
  (5f45a94f549 gives the per-filesystem primary); on EXDEV it falls back to a plain copy. After 2 identical
  errors it posts once and stops retrying until the error text or the source changes.
- Owner: WAVE-PILOT-FIX (SRC-SYNC), FLEET-OPS-R (epyc2 kw45 link).

### E. KV still has no gen host: 0 launches, third window. Estimate 5% of wave output.
- SRC-INCOMPLETE 28 lines: bind_report.json missing for src_kv_pin_..._d25c on epyc7/8/9/10. 37 KV rows ENQUEUED.
- source-follow bind for KV fails every tick: 24 "bind.py bind ... --strict rc=N" with FileNotFoundError
  src/kv3/pv_col_pads_Nb.json (22), and 127 "cached elaboration source changed; fresh die elaboration required:
  physical/die_plan/qwen_kvsys/bind/kv3/group_r?c_native.sv" lines. Same input each tick, same error.
- BOUND-FALLBACK works for S81 but KV has no earlier tree with a green bind on the gen hosts, so it has nothing
  to fall back to.
- Structural fix: source-follow keys its retry on (src tree sha, error line); an unchanged pair is not rerun,
  one post goes to the die owner. The missing generated file (pv_col_pads) is a source-manifest row, so a
  tree without it is refused at publish_apply with the file named, not found by bind later.
- Owner: KV-D23-COMPOSE (bind of record), MERGE-QUEUE-1 (source-follow retry key).

### F. Unchanged relaunch: REPEAT 63 (8, 43: rose with the S81 release). 1-2%.
- SKIP-SAME-INPUT fired 170 times and REPEAT-STOP 9, so the 0358/0555 C fix does block most. RELAUNCH-ON-FIX 129
  shows rows released by a real change. cbn_q11 (OT_XSTN_STRETCH) is now stopped after 3 identical fingerprints.
- Still leaking: ot_s81sl_leaf__t56 and bk_sel__t2 relaunched 3 times each on an unchanged fail key (kit_rtl
  bind error "rst_n ... is not a bit of w_u_vp_u_rr_rst_n", attempt 24). hd_tile relaunched once more.
- hd_spn_eshim_rx: 252 "FileNotFoundError .../attempt_3/gen/.../base; retry next tick" lines, then 20 "backed off
  until". The directory is gone (cleanup or moved host); a retry cannot bring it back.
- Structural fix: "retry next tick" on a missing run directory is tried twice, then the row is re-queued from its
  last kept stage. The A fix item 3 removes the 244 copy fails from the repeat counters.
- Owner: WAVE-PILOT-FIX. Items: DIE-S81-92 (leaf t56, bk_sel t2), HEAD-100 (hd_tile, hd_spn_eshim_rx).

### G. Frozen job: fixed. Under 0.5%.
- s81 serdes__t15__cla2127225 (0555 G) got "HUNG-WATCH CANCEL ... relaunched as a free infra retry: no stage-log
  output for 225 min and CPU not grown" at 07:23. The both-tests rule acts now. REAP-DEAD SILENT 25 (63).
- Owner: FLOW-HEALTH-1. No new fix.

### H. Tick: 556-796 s (median 503 last window). Worse. Under 1% direct.
- 06:57 653 s, 07:15 796 s, 07:27 556 s. kit_wave_step+admit 427-537 s; poll_running 262 s at 07:15 (ssh waits
  on epyc7). The 400 s target is missed in every tick.
- Structural fix: every per-host ssh in the tick uses ConnectTimeout 10 and a host that fails twice in a tick is
  skipped for the rest of that tick (already printed as "not checked"). Fix A removes the cause.
- Owner: WAVE-PILOT-FIX.

### I. Noise and stale state (no fleet time)
- CELL-BIG: 1,620 lines of 7,756 (21%, was 77%): better, still not deduped.
- epyc4 (terminated 11-13) is still called: 74 "Host key for 185.189.44.212 has changed / Host key verification
  failed" lines, and failure_breakdown prints "NOT SEEN: intel2 epyc4 epyc7". Fourth window. Fix: the host list
  comes from derive_gen_hosts output in every tool; no tool keeps its own list.
- TOOL-SKEW UNMEASURED s81_head: rt/385f61b5582a.manifest.json missing, fourth window. S81 343 of 18,020 modules
  differ from pin 3c913dbdfb23 (warn). TOOLS-LAG QC 1,387 commits (1,365), HBM 2,484.
- PLAN-CONFIG-DRIFT QC only_items sle_ctl__cl503337ff__v1 / __cl67434795__v1: open, third window.
- failure_breakdown: STALE 104, all HBM (parked, flat): 11 unowned. S81 types 44/394 signed, 152 "other flow
  error" (these are the A rows), 198 running. KV types 6/56, 20 cancelled (superseded). QC not listed as failing.
- RESULT-RECLAIM: 246 "skip guard REFUSE: protected" lines. The delete guard works (rail kept); the reclaim sweep
  should not ask for protected paths each tick.
- tools/failure_breakdown.py is not in rt/current (it lives in ~/coord/tools); briefs that name the rt path fail.
- docker "openroad/orfs:asap7lock not found" 5 lines inside one stage log; the image is present on the 5 hosts I
  checked. epyc7 UNVERIFIED.
- Owner: WAVE-PILOT-FIX (CELL-BIG, reclaim), FLOW-HEALTH-1 (epyc4, failure_breakdown), HEAD-100 (pin manifest),
  DIE-QC-103 (only_items).

### J. Admission, kills, disk
- Admission or disk refusals in the admit logs of 5 hosts: 0. PLAN_BYPASS 14 (epyc8 6, epyc9 8; was 21).
  Guard kills in the window: 0 on 5 hosts (last ones 02:39-02:46 PST). RETRY-HOST 44 "killed on epyc7" at 07:25
  are rows lost to the epyc7 overload, cause A. intel1 admits 0 GB (avail 207).
- Disk: epyc2 scratch2 148 GB (floor 150, was 131, no longer falling). epyc10 scratch2 91%, 685 GB free (764).
  epyc8 87%, 975 GB. intel1 77%. hub 80%.
- Owner: FLEET-OPS-R (epyc10 trend), CLEAN-ALL-1115.

## Did the fixes from FABLE-FLOW-0555 land?
- A per-item launch on the newest green-bound tree: yes (255a0c4245, BOUND-FALLBACK 103 and 155 rows; S81
  launches 0 -> 427). Apply refusal without bind_report on every gen host: no (KV, class E).
- B load-aware pick: landed as cb448f6ac56, live 07:48 on hub + 5 hosts, not on epyc7. Effect not measurable yet.
- C compare against the last FAILED attempt: mostly (SKIP-SAME-INPUT 170); two S81 items still repeat.
- D SRC-SYNC error text: yes, and it names the cause (cross-device link). Stop after 2: no. df9f0958284 live 07:48.
- F stale-verdict cache: UNVERIFIED; tick got slower for another reason (epyc7).
- G watchdog on both tests: yes.
- H ot-run copies the script at submit: UNVERIFIED, no slip seen this window.
- I keep clock-of-record kits: 68ad9df0b11 is now an ancestor of rt/current (it was not at 0555).
- J epyc4 name, s81_head pin manifest, only_items drift: no.
