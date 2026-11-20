# FABLE-FLOW: flow and procedural review, 13:55 to 17:50 PST 11-19 (FLOW-REVIEW-18xx, read-only)

Sources: autopilot/log.txt (2,773 lines in the window), kit_wave_state.json / kit_wave.json (17:46), lanes/FLOW-HEALTH.tsv,
ot-run --status (18:0x), user journals + ot-auto-retire log.jsonl on intel1 epyc2 epyc7 epyc8 epyc9 epyc10,
~/.local/state/ap-src-sync/ss-*.log, rt/history.log, lane posts (S81-DIE-R3, KV-D23-COMPOSE, FLEET-OPS-R, FLOW-HEALTH-2,
WAVE-PILOT-FIX), FABLE-FLOW-1355.md. failure_breakdown.py is not in rt/current or ~/OpenTallas on the hub: NOT RUN; the
STALE view below comes from kit_wave_state instead.

Context: all LLM lanes were down 14:30-17:47. Fleet 624 threads x 3.9 h = about 2,400 thread-hours. Shares are estimates.

## What ran unattended, and what did not
- The autopilot ran every tick: 26 ticks, 398-429 s each, no tick killed (so 1355-B did not recur). rt/current stayed
  37a098acb4e8 from 13:58 to 17:49 (no tool change without lanes).
- KIT-WAVE FAIL 10 (283 at 1355): 4 design (MPL-0020 x3, OT_XSTN_STRETCH x2, boot path 1), 3 INFRA OOM, 1 BIND_STALE.
  The low count is not health: LAUNCH fell to 26 (14h 14, 15h 5, 16h 6, 17h 1; FLOW-HEALTH.tsv), and S81 + KV
  current-plan launches were near 0 (A, B below). QC N46C took 20 of the 26 launches.
- Fleet busy 87-90%, mostly on 111 ENQUEUED + 5 RUNNING S81 rows of the OLD event 3fa87b84b18 and 97 QC rows (they count
  under the any-plan rule, so the machine time is not lost; current-plan progress is).
- Self-heals that worked alone: src-sync to epyc2 (the detached copy failed on its first run and passed on its rerun at
  14:10, AP_RC 0; SRC-INCOMPLETE stopped after 14:49), EARLYOOM resubmits, ORPHAN-DEAD resubmit, REAP-REVIVE.
- Fixed only after lanes returned: disk auto-prune on intel1/epyc2 (FLEET-OPS-R, 17:51-17:52).

## Status of 1355 fixes (rt eba61e219525, 17:54)
- TICK-KILLED (ExecStopPost): NOT landed (no string; TimeoutStartSec=3000, no ExecStopPost). No kill in this window.
- PREFLIGHT-MISS / bind check from tree switch: NOT landed. Same disagreement still blocks S81 (A).
- INFRA fails feeding REPEAT-STOP: partly. Host fails already skip the ledger (kit_wave.py:12196), but OOM still counts:
  s81/dsdv_slice_lepw_mu_C__t1 BLOCKED-REPEAT gen_lint|INFRA|OOM at 15:34 after two kills on over-packed hosts.
- Self-heal reads unit RC: NOT landed; moot this window (rerun succeeded). The ss-*.log files keep 1,092-1,200 tar
  "Cannot mkdir" lines from the failed first run with AP_RC=0 from the rerun appended to the same log.
- Host packing (prefer hosts under cores): NOT landed. See C.
- Hub sync ExecStartPre from rt: landed 18:00 (FLOW-HEALTH-2 T4, drop-in), next tick verifies.
- Auto-prune unit in lane dir: landed 6fb6ab14e83 (FLEET-OPS-R). The same fault remains on ot-retire-superseded (E).
- Lane-dir deletion guard: b3aaf1a353 (enclosing lane dir named in a post keeps its subtree) is in rt eba61e2;
  a6ae56f851 (superseded src_ run() refuses live/queued job paths) is on main but NOT in rt/current yet.

## Ranked by time wasted

### A. S81 current plan d8h stalled on KIT_TOPOLOGY_BIND_STALE: 46 rows FAIL, 0 current-plan relaunch since 14:52.
   Schedule loss about 3 h of S81 current-plan throughput; machine loss small (old-plan rows filled the hosts).
- kit_wave_state: s81 event b4bb6a8b1e9 has 47 FAIL rows (46 PLAN|kit_topology BIND_STALE, updated 13:20-15:34, 1 OOM)
  and no ENQUEUED/RUNNING row. Only 2 S81 current-plan launches in the window: svc_hi_dsdv_svc_rs__t6 (14:22) failed
  BIND_STALE again 14:38; dsdv_slice_lepw_mu_C__t1 (14:52) OOM twice.
- bind_stale_items.s81 = [] and no WAIT-BIND line: the preflight still calls the d8h bind green while the stage calls it
  stale, so the rows sit as FAIL instead of parking, and nothing regenerates the bind. Trend vs 1355: fail COUNT down
  (107 -> 1) only because nothing launches; impact up (whole current plan stopped).
- S81-DIE-R3 is now building D8i (C4 bind r8 started 17:5x on epyc8, about 1.5 h), which supersedes d8h.
- Process root cause: two checks, two answers (1355 C), and a stale-bind verdict has no automatic consumer: the canonical
  bind regenerate waits for a lane, and during the outage there was none.
- Structural fix (self-healing, no hold): (1) a kit_topology BIND_STALE result is authoritative: it writes the tree into
  bind_stale_items and logs PREFLIGHT-MISS once per tree with both inputs; (2) the wave starts the canonical bind
  regenerate for that tree as an ot-run job (the stage's own message names the action) and relaunches the stale rows on
  its result, as the KV "POST-APPLY, kits relaunched on its result" path already does.
- Owner: WAVE-PILOT-FIX (preflight + auto-regen); S81-DIE-R3 (D8i bind).

### B. KV-D25d: 0 launches since the tree switch at 13:08 (4.7 h), and no log line says why.
- 13:08 ADOPT-ROWS switched KV d25c -> d25d4; 13:09 REKEY moved 4 live rows to KV-D25d. kit_wave_state still shows those
  4 rows on KV-HG6 / KV-D23H (REKEY not persisted, or REAP-REVIVE overwrote it; UNVERIFIED). OWNERS has 28 KV rows in
  take states (FIX 12, GEOM-REQ 12, REVIEW 2, KIT-PLACED 1, PLAN-STRUCTURAL 1); state has 0 rows with event KV-D25d.
- The UNDER-USE "rows not launching" breakdown (q_running 41-65, WAIT-FORM 25, KW-FIX-45 8) has no KV entry: KV rows
  are dropped before they become rows. After 14:39 (SRC-INCOMPLETE + SRC-SYNC of the d25d4 postbind, healed) no KV-D25d
  line at all. Postbind is complete on epyc8 and epyc10. Candidates (UNVERIFIED): KV bound_trees still names only the
  d24c tree (src_incomplete_last keeps "__bound__0" d24c missing on epyc2/intel1); or the r712 "POST-APPLY" gate waits
  for the d25d4 bind result without logging. KV-D23-COMPOSE has moved on to D25e (bind started 01:49Z on epyc10).
- Process root cause: "silent no-launch": a die can have eligible rows and launch none with no reason in log.txt.
- Structural fix (self-reporting, no gate): each tick, for every enabled die with take-state rows > 0 and launches = 0,
  one line "KIT-WAVE NOT-LAUNCHING <die> <event>: <n> rows; <reason histogram>" covering every drop point in plan_dies
  (bound tree, bind wait, src incomplete, only_items, plan block). Also persist REKEY into the row.
- Owner: WAVE-PILOT-FIX; KV-D23-COMPOSE checks why d25d4 rows were not selected before D25e applies.

### C. Host imbalance: 75 idle threads on average (12%, about 290 thread-hours) while 2-3 hosts admit 0. Unchanged.
- UNDER-USE idle 45-95 of 624 every tick. Idle on epyc10 (up to 30), epyc7 (21-24), intel1 (14-27); epyc8 load
  146-212/96 and epyc9 127-155/96 with ot-run "admits 0 GB", threads asked epyc9 579/96, epyc2 524/128, epyc8 353/96.
- Rows waiting on epyc8/epyc9 stay bound to their gen/place host; ot-run picks a host per new job only ("next 16-thread
  job -> intel1"). epyc8 was BAD-HOSTS (stop/reap ssh skipped) in 6 ticks.
- Process root cause: placement is fixed at submit; nothing moves a waiter when its host admits 0 and another admits.
- Structural fix (no cap; rails kept): (1) ot-run moves a WAITING (not running) job to the host with the most admit when its
  own host admitted 0 for 2 polls; (2) the wave pick prefers hosts under their cores (1355 A3/F). Choice of host only.
- Owner: FLEET-OPS-R (ot-run waiter re-pick), WAVE-PILOT-FIX (pick).

### D. OOM and kills on the over-packed hosts. About 1-2%. Same root as C.
- 3 INFRA OOM FAIL (svc_hi_dsdv_svc_rs__t6, dsdv_slice_lepw_mu_C__t1 x2), 3 EARLYOOM-RESUBMIT, 2 REPEAT-STOP x1.5 memory,
  1 BLOCKED-REPEAT on OOM (A). 11 PREGRT_HOLD_FALLBACK "tool rc 137: 4_cts.odb unchanged": the pre-GRT FF-hold step was
  killed and the row went on WITHOUT it (silent quality fallback; hold work moves to later ECO).
- Structural fix: C; plus an OOM on a host above its cores never counts toward BLOCKED-REPEAT, and a PREGRT_HOLD rc 137
  reruns that step once on the next pick instead of falling back.
- Owner: WAVE-PILOT-FIX.

### E. Systemd units running out of a deleted lane dir: auto-prune fixed, ot-retire-superseded still dead. 0% now.
- ot-disk-autoprune: 72 (intel1) + 69 (epyc2) 203/EXEC fails in the window; re-installed from rt 17:51-17:52. Disk is
  fine: intel1 773 GB free (642 at 13:55; the 6 h floor estimate did not play out), epyc2 484, epyc7 2,244, epyc8 1,068,
  epyc9 1,375, epyc10 791.
- ot-retire-superseded: ExecStart=/srv/opentallas-scratch2/claude/clean-all-1115/ot-retire-superseded-run.sh on ALL 6
  hosts; the dir is gone on intel1 and epyc2, so it has failed 203/EXEC there since the last success (intel1 11-19
  01:52, epyc2 11-18 18:48); on epyc7-10 it works only while that lane dir survives. wt-reaper is also in failed state
  on intel1 and epyc2 (cause not read).
- Structural fix: as for autoprune, install from rt/current tools/fleet; one hourly scan of every host's user units for
  ExecStart under /srv/*/claude/<lane>/ and for status=203/EXEC, one post line per unit.
- Owner: FLEET-OPS-R.

### F. Live lane inputs deleted (KV-D23-COMPOSE gatein/): cause found, 0 lane-dir deletions in this window.
- ot-auto-retire deleted /srv/.../kv-d23-compose8/gatein on epyc8 (15:38 UTC = 07:38 PST, idle 17.9 h) and on epyc10
  (19:40 UTC = 11:40 PST, idle 21.9 h): before the 24 h floor; the post named "gatein/" not the full path. The lane
  restored it from epyc9. auto-retire log.jsonl on all 6 hosts: 0 kind=lane DELETED since 13:55.
- Also S81-GEOM-OPUS d8h tree removed by the superseded src_ path run() (FLOW-HEALTH-2).
- Fixes: b3aaf1a353 (in rt), a6ae56f851 (main only; reaches hosts at the next rt switch). Root cause: idle measured by
  mtime, so read-only inputs look idle. Remaining structural step: a lane dir with a live ot-run job, an open lane, or a
  path in any 24 h post is never "idle", whatever its mtime.
- Owner: FLOW-HEALTH-2 (verify a6ae56f851 on hosts after the next rt switch), CLEAN-ALL successor = FLEET-OPS-R.

### G. Self-heal loops that never stop. Under 0.5%.
- ITEM-SYNC qwen_compute/phy_serdes_b intel1->epyc2 rc=2 every tick (25x, plan_s29_qc103_phyb.json; input
  a0_nk_pins_ck1109.json missing on the source too). 3 KIT-LOST QC attempts ("run_kit.sh missing on the hub"; the attempt
  dir exists, the runner lives on the gen host), each regenerated.
- Fix: after 2 identical rc!=0 the heal logs one SELF-HEAL-STOP line with the error and stops until an input changes;
  KIT-LOST checks the gen host's copy before calling the attempt dead. Owner: WAVE-PILOT-FIX.

### H. Long silent stages on S81 svc rows. Size UNVERIFIED (up to about 2% if stuck).
- 7 HUNG-WATCH POST (svc_hi/lo_dsdv_svc_rs t3-t7, w__t1): log frozen 360-369 min, CPU busy, 22-29 processes each on
  epyc2/intel1/epyc10; WF-1 keeps them. Probably slow design stages (svc rows also fail MPL-0020), not procedural.
- Owner: FABLE-FIX-S81-SVC (judge whether to stop them).

### I. Noise and skew
- HUB-SYNC-FAILED 33 alerts (root FABLE-FIX-QC.md in the hub checkout, ahead 0 / behind 0, since 11:48): MERGE-QUEUE-1.
- ADOPT-GUARD PLAN_MISSING hbm 50 alerts (parked die). TOOL-SKEW WARN unchanged (s81 368, qc 357, kv 2); s81_head pin
  manifest rt/385f61b5582a.manifest.json missing, seventh window (MERGE-QUEUE-1). hbm TOOL-SKEW now refuses launches
  (NEEDS-LANE 18:01, DIE-HBM-101).
- TOOLS-LAG "missing r708": not a gap; rt applies OT_NOMCAP at sign-off for all dies (FLOW-HEALTH-2 T3).
- STALE (kit_wave_state): s81 old event 3fa87b84b18 111 ENQUEUED + 5 RUNNING; 149 superseded-event rows not counted.

## Candidate class names (FLOW)
- "stale verdict with no automatic consumer" (A): a stage result that names its own repair (regenerate bind) starts it.
- "silent no-launch" (B): every die with eligible rows and 0 launches prints why, each tick.
- "submit-time placement" (C/D): a waiting job follows the admitting host.
- "service code in a lane dir" (E): second unit of the same class after the autoprune fix.
- "idle by mtime" (F): read-only inputs are live while a job, lane or post names them.
