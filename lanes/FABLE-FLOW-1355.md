# FABLE-FLOW: flow and procedural review, 11:45 to 13:55 PST 11-19 (FLOW-REVIEW-14xx, Opus successor, read-only)

Sources: autopilot/log.txt (2,273 lines in the window), tools/failure_breakdown.py (13:51), ot-run --status (13:50),
ot-oom-age kills.log, ot-auto-retire log.jsonl and user journals on intel1 epyc2 epyc7 epyc8 epyc9 epyc10,
~/.local/state/ap-src-sync/*.log on the hub, rt/current on all hosts, lanes/posts (WAVE-PILOT-FIX, FLEET-OPS-R,
FLOW-HEALTH-1, S81-DIE-R3), rt kit_wave.py, FABLE-FLOW-1150.md.

Window totals: KIT-WAVE FAIL 283 (s81 280, qc 2, kv 1). By hour 11/12/13: 20/106/157. Of the 283, 274 are procedural:
copy timeout 150, BIND_STALE 107, rt_tools 14, OOM 3. Design fails: 9.
LAUNCH by 10 min: 25 at 11:5x, **0 from 12:00 to 13:10**, 59 at 13:1x, then 1-2 per 10 min (LAUNCH-KEEP 219: one live
attempt per item; not launching: q_running 38-41, WAIT-FORM 25).
Threads used 90-96%. Guard kills: epyc2 8, epyc7 1, others 0. Count: signed any plan 471 (405 at 11:50); current plan 406.
Waste shares are estimates from capacity and hours (624 wave threads, 2.2 h); none is measured exactly.

## Status of 1150 classes
- A epyc7 copy storm: ENDED about 13:07. rsync servers on epyc7 now 0; load 40-73/96; ot-run admits 108 GB; rt/current
  is 55cdd618512a on all 6 hosts (epyc7 caught up). Last copy fail 13:07:54.
- B tick time: 421 / 648 / (stall) 1,331 / 513 / 454 s. Better after 55cdd61851.
- D BIND_STALE: fix landed (probe imports rt kit_topology, kit_wave.py:9160). The class GREW. See C below.
- E tar to epyc2: fix landed 12:12. It does NOT work. See E below.
- H AUTO-ECO: now prints reasons (130 candidates: 74 no record, 31 probe ssh failed, 6 LANE, 5 host gone). Closed.
- Hub gitshim deletion: 24 h + post-name guard is live ("REFUSED: named in a hub post of the last 24 h": 45 on epyc10,
  70 on epyc2). 0 lane-dir deletions in the window. Before it: 38 lane dirs deleted 08:38-11:40 at idle 12-22 h, incl.
  live s81-die-r3-e8/tools+gitshim (second time), kv-d23-compose8/*gate, s81-geom-opus-d8h-l4.

## Ranked by fleet time wasted

### A. epyc7 copy-storm tail: 150 copy fails, 69 items, 6 REPEAT-STOP on INFRA. About 11% of the window, now 0.
- 150 fails (80 old form "mkdir ... epyc7", 70 new form "flock push-epyc7.lock timeout 2400"), snapshot 3cb1702b 143.
  12:00-13:07 only. S81 col_h9_r1 42, col_h9_r0_p5 30, _p3 24, _p6 23.
- epyc7 (15% of threads) was off the fleet until about 13:05, then under-used: idle 47 / 49 / 29 of 96 at 13:16 / 13:27
  / 13:37, while epyc8 had load 213/96 and 703 threads asked, epyc2 202/128 and 836 asked (admits 0 on both).
- Residue that still costs: REPEAT-STOP on INFRA keys: STALLED:pipeline|INFRA 2+2, STALLED:rt_tools|INFRA 2+1,
  BLOCKED-REPEAT:route|INFRA 2. These rows now wait for an unblock line or a changed input, although the cause was the
  host and the host is fixed. CLASS-BREAKER open on "kit snapshot copy timed out" and "KW_RT_TOOLS".
- Process root cause: INFRA fails count toward the per-item repeat stop and the class breaker, and nothing re-arms them
  when the host recovers. The pick never re-fills a host that comes back (no rebalance from over-2x hosts).
- Structural fix (no new hold): (1) INFRA-class fails never feed REPEAT-STOP / BLOCKED-REPEAT; a CLASS-BREAKER on an INFRA
  key closes by itself when the named host is back under 2x cores and readable for 2 ticks. (2) Rows stopped on an INFRA
  key re-arm in the same pass. (3) The pick prefers a host under its cores over one over 2x (it already reads both).
- Owner: WAVE-PILOT-FIX.

### B. Launch stall 12:00-13:10: the 12:00 tick was killed at TimeoutStartSec=3000. About 3%, fixed.
- No TICK-TIMES from 11:59:41 to 13:16:31; 0 LAUNCH lines for 70 min. The fleet stayed 92-96% busy (deep queue), so the
  loss is mostly latency: idle threads rose from 25 (11:59) to 52-61 (13:16-13:37), part of it epyc7.
- Fixed by 55cdd61851 (cancel-stop skips bad hosts). The first tick after it still spent poll_running 615 s.
- Process root cause: a tick killed by systemd writes nothing; the stall was found by a lane 65 min later.
- Structural fix: ExecStopPost writes "TICK-KILLED <phase> <elapsed>" to log.txt when the tick ends by timeout, and the
  next tick runs the wave launch step before the poll phase when the previous tick was killed. Self-reporting, no gate.
- Owner: WAVE-PILOT-FIX.

### C. KIT_TOPOLOGY_BIND_STALE: 107 fails, 76 items, rising (11h 8, 12h 27, 13h 72). About 2%.
- By launch tree: d8g 54, d8h 49, d8f 3, KV d25c 1. Launch to fail: median 63 min (was 8), 100 rows, about 170 row-hours
  of wall time (mostly queue wait; compute is the stages before kit_topology).
- s81 switched d8g -> d8h at 13:02/13:08 (apply_reviewed_tree_marker). 49 rows launched on d8h then failed BIND_STALE
  13:20-13:40, e.g. slice_station__t27: LAUNCH 13:13 on d8h, FAIL 13:31. So the live tree was adopted without a bind
  that the kit stage accepts, and the preflight (bind_preflight 2x per tick) still let the rows launch.
- Fix D landed (preflight imports rt kit_topology). Two checks still give two answers. UNVERIFIED cause, two candidates
  seen in the code: (1) PROBE_BIND_SIG walks at most 4,000 stat entries and BIND_PREFLIGHT_TTL_S is 12 h, so a change
  past entry 4,000 of a bind_out tree keeps an old green verdict; (2) the probe runs with `asbuilt` = None when the row
  has none, the stage uses the full plan/asbuilt context ("regenerate the canonical native bind for this full
  plan/asbuilt context").
- Structural fix: (1) the tree switch (apply_reviewed_tree_marker) runs the same PROBE_BIND over the new tree's rows and
  writes the stale list into the switch record; stale rows go to BOUND-FALLBACK in that tick, no launch. (2) the probe
  signature hashes the bind manifest file, not a capped stat walk. (3) a kit_topology BIND_STALE after a green preflight
  logs PREFLIGHT-MISS with both inputs, once per tree, so the next disagreement names its cause.
- Owner: WAVE-PILOT-FIX (preflight + switch), DIE-S81-92 (canonical native bind for d8h).

### D. Disk auto-prune is dead on intel1 and epyc2: its script dir was deleted. 0% now; risk of disk refusals in ~6 h.
- ot-disk-autoprune.service fails every 10 min: "Failed at step EXEC spawning
  /srv/opentallas-scratch2/claude/clean-all-1115/autoprune-run.sh: No such file or directory". epyc2 since 11-18 19:00
  (114 fails), intel1 since 11-19 02:06 (71). The dir is gone on both, though it is listed in
  ot-delete-guard/protected.txt on epyc2. Who deleted it: UNVERIFIED. epyc7/8/9/10 run it fine (12 Finished each).
- intel1 scratch2: 642 GB free, falling 91 GB/h (FLEET-OPS-R DISK-RATE 13:00), floor in about 5.8 h; kw43-wave-1109n
  wrote 277 GB and kw45 231 GB there in the last window. epyc10: 428-652 GB free, falling 135 GB/h, 2.8 h to floor
  (its prune runs).
- Process root cause (same class as gitshim): a systemd service runs a script out of a lane scratch dir, and every
  cleanup is free to delete lane dirs. A unit that fails with 203/EXEC is silent: nobody reads user journals.
- Structural fix: (1) services install their scripts under ~/.local/lib/<service>/ (copied from main by ot-tools-sync),
  never ExecStart into /srv/.../claude/<lane>/. (2) the hourly host report greps each host's journal for
  "status=203/EXEC" and failed ot-* units and posts one line per unit. (3) re-install autoprune on intel1 + epyc2 now.
- Owner: CLEAN-ALL-1115 (FLEET-OPS-R is its successor and is active).

### E. Source self-heal to epyc2 still fails every tick, now silently. Under 1%.
- 12 SRC-SYNC passes, the same 191 (QC n46_s0 postbind) + 119 (KV bindcopy_kv_d25d4) files each time; SRC-INCOMPLETE
  epyc2 every tick (bind_cells.sv, cbf_q00__*.sv, kv_hard_models.sv). Hub unit logs: ss-560d8dbd35e7 AP_RC=2 on all
  3 runs, 800 "tar: ... Cannot mkdir / Cannot open: No such file or directory"; 4 of 12 recent logs RC 2 (the epyc2
  ones), 8 RC 0. On epyc2 the target dir under kw45 -> scratch3 was created 12:08 and holds 1 file.
- The 12:12 fix (readlink + --transform) changed the error from "Invalid cross-device link" to "No such file or
  directory"; it did not cure it. Since the copy went detached (FLOW-1150 B), the autopilot logs "copying in detached
  unit (next probe verifies)" and never reads the unit RC, so heal_blocked never counts a failure: the second failed fix
  is invisible in log.txt.
- Effect: epyc2 cannot take QC n46 or KV d25d rows (it is over-packed anyway, so little machine loss).
- Structural fix: (1) the next probe reads the ss-<hash>.log AP_RC and feeds heal_tries (stop after 2 identical, one
  line with the tar error). (2) a test that extracts into a dir whose top is a symlink to another filesystem, run on a
  real host pair, before the fix is called done. (3) or write on epyc2 to the realpath directly (tar -C <realpath of
  kw45> with members made relative to kw45).
- Owner: WAVE-PILOT-FIX.

### F. Over-packed hosts: epyc2 8 guard kills, epyc8 load 2.2x, while epyc7 idles. About 1-2%.
- epyc2: 836 threads asked / 128, MemAvailable 92 GB of 1,007, 8 SIGKILLs in the window (svc_lo_dsdv_svc_rs__t1/2/4,
  col_h9_r2, col_h10_r2 x2 at 13:45-13:46). 3 OOM FAIL lines; 2 REPEAT-STOP on OOM (x1.5 memory resubmit).
- The rails work (keep them). The waste is the re-run of killed place/route jobs on a host that the pick keeps filling
  while epyc7 has 625 GB available.
- Structural fix: same as A(3); no cap, only the choice of host.
- Owner: WAVE-PILOT-FIX.

### G. Unowned procedural lane: FLOW-HEALTH-1 has not posted since 08:51 (5 h). 0% direct.
- Its open items are stuck: the repo fix for terminated-host lists (lane commit f6ef5e021c on epyc9, not on main),
  the 12 h idle threshold of ot-auto-retire for lane dirs not named in a post (38 deletions this morning).
- Fix: a new Sonnet lane FLOW-HEALTH-2 takes FLOW-HEALTH-1's open list, plus D(1-2) if CLEAN-ALL is busy.
- Owner: COORD (assign FLOW-HEALTH-2).

### H. Tool/source skew. 0% measured; correctness risk.
- TOOLS-LAG: owner rule r708 (nominal clock cap) is missing from every die's pinned tree (s81 123 commits behind, kv
  183, s81_head 434 + r698, qc 1,441, hbm 2,538). Signoffs in this window ran on those trees. UNVERIFIED whether the rt
  launch tree applies r708 at the STA stage regardless of the die pin; if not, these signoffs lack an owner rule.
- TOOL-SKEW WARN: qc 357 / s81 368 / kv 2 import-closure modules differ from pin, "warn, launching". s81_head UNMEASURED
  (pin manifest missing on hub), sixth window.
- Structural fix: TOOLS-LAG names, per missing owner rule, whether the rt tree supplies it at launch; a missing owner
  rule that the rt tree does not supply re-pins the die tree at the next tree switch (switch already happens hourly).
- Owner: MERGE-QUEUE-1.

### I. Noise and small state issues
- HUB-SYNC-FAILED since 11:48 (10 alerts): a lane wrote FABLE-FIX-QC.md (root level, not lanes/) in the hub checkout
  directly. ahead/behind stayed 0/0 except two moments with "ahead 1" (kit_wave.json + tree_switch_s81.json at 13:02),
  so no stale read. Fix: lanes post via post.sh; hub_git_sync APPEND_RE also covers root *-FIX-*.md, or the lane moves
  the file under lanes/. Owner: MERGE-QUEUE-1.
- The autopilot's ExecStartPre runs hub_git_sync.sh from ~/OpenTallas on intel2, which sits at 22c217df540 (11-14) with
  2 uncommitted edits (hub_git_sync.sh APPEND_RE +auto_resign.tsv; kit_wave.py +52 lines). Live config not on main.
  Fix: ExecStartPre reads rt/current like ExecStart; commit or drop the two edits. Owner: MERGE-QUEUE-1.
- derive_gen_hosts (13:07) put epyc7 back into qwen_kvsys gen_hosts 26 min after KV-D23-COMPOSE committed "COORD: no
  epyc7" (12:41). An automatic writer overrides a lane's explicit host choice. Fix: a per-die "exclude_hosts" key that
  derive_gen_hosts honours. Owner: WAVE-PILOT-FIX.
- failure_breakdown STALE 110 (HBM 104 parked, flat; KV 6: 5 KIT-WAVE-1, 1 unowned core qkd_pv_fin_s8_pin CANCELLED
  SUPERSEDED 11.7 h). NOT SEEN: intel2. ADOPT-GUARD PLAN_MISSING hbm epyc2: 6 alerts, same text, still (parked die).
- PLAN-CONFIG-DRIFT kv / s81_head: item_env keys for items no longer in the plan (kv3_astk, kv3_head_eighth_*, hd_host).
- REAP of already-CANCELLED QC rows sends ot-run --cancel-dir every tick (35 signal-15 lines at 13:50, units []).
- ot-run spill_pending holds 597 entries, newest 11-19 11:25; spill_stuck.log last line 11-14. Probably stale state;
  UNVERIFIED.

## Candidate class names for the rulebook (FLOW)
- "INFRA counted as design repeat" (A): a host failure must never stop a row.
- "silent background failure" (B tick killed, D unit 203/EXEC, E detached copy RC): every detached or timed job writes
  its RC where the next tick or the hourly report reads it.
- "two checks, two answers" (C): the gate before launch runs the same function on the same inputs as the stage.
- "service code in a lane dir" (D, gitshim): long-lived units run only from installed or rt trees.
- "tool default silently wrong for plan form" (crossing-chain rise vs fall since 11-17, fixed d08514486e): same family as
  E (fix changed the error, not the result): a fix is done only when a test on the real form passes.
