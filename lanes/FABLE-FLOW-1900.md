# FABLE-FLOW-1900: procedural / flow review, window 11-21 12:23 to 18:50 PST

Lane FABLE-FLOW-1900 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled, launched,
deleted or edited. Previous: lanes/FABLE-FLOW-1240.md (window 10:40 to 11:56).
Sources: autopilot/log.txt (12:23 on), autopilot/kit_wave_state.json and kit_wave.json (18:24), lanes/FLOW-HEALTH.tsv (18:07),
RELEASE_TREE.md failure block (18:17), `ot-run --status` (18:29 and 18:49), ~/.local/state/ot-run/signals.log, disk-rate.log,
per-host ~/.local/state/ot-auto-retire/log.jsonl and auto-clean/host.log (6 build hosts), ~/.local/state/ot-delete-guard/protected.txt,
rt/current tools/fleet/ot_delete_guard.py + build_protected_live.py, CODEX-LOG.md 18:11 handoff, posts of FLEET-WATCH-R8,
FLOW-OPS-1300, FLOW-CANARY-R2, FLEET-OPS-R. Size samples on epyc10, epyc8, intel2 were `ionice -c3 nice du/find` with timeouts.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Clocks: epyc7 to epyc10 log in UTC (PST + 8 h); intel1, intel2, epyc2 in PST.
Not done: no git history was read; kw45 total size on epyc10 did not finish in 400 s of du, so that one number is by subtraction.

## Headline

1. **The disk problem has moved to intel2, the only host that still admits.** intel2 scratch2 free: 1263 GB at 11:33, 861 at
   18:03, 576 at 18:50 (V, df). That is 62 GB/h over the afternoon and about 360 GB/h since 18:03. Writers at
   18:50 (V, /proc io, 10 s): three rsync pulls from epyc7 at 16 to 17 MB/s each (lane tree `s81-bksel-r7/tree_r6`, a src-manifest
   replicate, a kit-store snap) plus the die source trees FLEET-WATCH-R8 copied at 18:1x. Lanes and the wave are moving full
   copies of their trees to the one host with room. If the rate holds, intel2 is at the 100 GB ot-run floor between 20:00 and 20:30.
2. **The wave launched 57 rows at 18:22 to 18:40, none on intel2, all on the 9999-drained hosts** (V: 48 rows started in the
   last hour have gen_host epyc2 20, epyc7 11, epyc10 9, epyc8 9; intel2 0). epyc10 fell 72 GB (18:14) to 35 GB (18:43), under
   the 50 GB floor. `host_drain` stops new ot-run job dirs but not the wave's own gen / kit_rtl staging. Class (a).
3. **intel2 is in every gen_hosts list but is not usable by the wave.** SRC-INCOMPLETE for qwen_compute, qwen_kvsys and s81 on
   intel2 at 18:18, 18:30, 18:39, 18:49 with the same first missing file each time (V). The 18:1x rsync copied the die src
   trees, not the bind / postbind / macro trees the kits also read. The self-heal copies 100-file batches and has not converged
   in four ticks. Class (b).
4. **The delete guard fix (item 13, main 10b728cf8e3, 13:30) worked for attempt dirs and freed about 0 GB**, because old attempt
   dirs are not where the space is. What the guard still refuses is whole kw45 source trees and whole lane trees: 148 distinct
   kw45 trees and 260 lane top dirs carry at least one protected path (V, protected.txt 3,175 entries), while live wave rows name
   12 kw45 trees (V). Class (c) and the disk section.
5. **No kit-wave launch from 12:00 to 18:22 (6.4 h)** (V: launches per hour 75 at 11, 0 from 12 to 17, 57 at 18). 106 rows sat
   ENQUEUED. Fleet load at 18:29 was 437 of 736 threads (59 %); epyc9 29/96, intel1 36/112, intel2 45/112.
6. **Sign-off count: 524 any plan, 433 current plan (V 18:20), +14 / +9 since 11:49.**
7. E2BIG: 0 new FAIL lines in the window (15 in the last one). Class stopped. Canary: every verdict still FAIL. Class (f).

Trend against FABLE-FLOW-1240: FAIL lines 18 in 1.3 h then, 10 in 6.4 h now (9 disk not-run, 1 ssh timeout). Draining hosts 2
then, 6 at 18:29; at 18:49 epyc2, intel1 and epyc8 show DRAINING, epyc7 and epyc9 show no flag, epyc10 was not captured. STALE 109 then, 110 now.

## Classes

Fleet base: 159 running units (V 18:29). "Share" is the share of fleet thread-hours in the 6.4 h window, estimated (I).

### (a) Admission and drain do not agree with each other: 182 REQUEUE, 9 FAIL, 75 INFRA-RETRY, rising

- Count (V): `ot-run REQUEUE no host qualifies` 182 since 12:23 (hour 13: 48, 14: 59, 15: 11, 18: 63). Reasons: epyc10 scratch
  under the 100 GB floor 141, epyc8 same 28, intel2 ssh name resolution 5. `KIT-WAVE FAIL ... NOT RUN: no host with --dir has
  60 GB` 9 (all 12:25 to 12:55, QC). INFRA-RETRY 75 lines for 14 rows, now at requeue 6 of 8. RETRY-INFRA-STOP NO-HOST 11.
  LAUNCH-DISK-CAP 79 lines until 17:59, then none.
- Root cause (V for the facts, I for the mechanism): three separate disk rules decide one launch and they read different things.
  The wave disk cap passes a die when any host in its list has `free - 150 - in flight` room; adding intel2 at 18:1x made it
  pass for every die. The gen host is then picked from hosts whose source tree is complete and whose free space is above
  `gen_disk_min_gb` 70; intel2 is excluded (class b), epyc10 at 72 GB passed. The job dir is therefore on epyc10, and ot-run
  refuses it there (scratch floor 100, drain 9999). The row can only requeue. `host_drain` is not read by the gen-host pick.
- The 9999 drains are set and cleared by hand (R: r8watch undrains epyc10 only; epyc2/7/8 by FLEET-WATCH-R8 at > 200 GB). A
  manual hold with no release term over-holds: epyc7 sat at 266 GB free with a 9999 drain at 18:29.
- Structural fix (P): one function, used by the wave cap, the gen-host pick and ot-run admission, that answers "can host H take
  N GB for this row" from the same inputs (free, floor, in-flight peak, drain). A row is launched only with a host that passes
  it for gen and for place. Drain becomes a computed state with hysteresis (enter below floor + in-flight peak, leave above
  floor + 1.5 x in-flight peak for 30 min) so nobody undrains by hand. A row whose staged host stops qualifying is restaged once
  to a qualifying host instead of requeued in place. No floor changes.
- Owner: FLOW-OPS-1300 (code), FLEET-WATCH-R8 (operate until it lands).
- Share: about 40 % of fleet thread-hours idle for 6.4 h with 106 rows queued (I, from load 437/736 and zero launches). No
  compute was burnt by the not-run rows themselves.

### (b) Host added to a host list without its input closure: 12 SRC-INCOMPLETE, 44 SRC-SYNC, new

- Count (V): SRC-INCOMPLETE intel2 x 3 dies x 4 ticks. SRC-SYNC 44 lines (228 + 95 + 286 files named at 18:18). One
  `rsync error ... file IO (code 11)`. ADOPT-GUARD PLAN_MISSING on intel2 for all five dies once, then 33 ADOPT-GUARD alerts
  after 18:15; autopilot/ADOPT-GUARD-FAILED present at 18:27. Tick time 481 and 486 s (was 201 to 222 s), 444 s of it in
  kit_wave_step.
- Root cause: a host is made a gen host by editing lists. Nothing computes what a kit on that host reads (src tree, bind and
  postbind snapshots, macro trees outside kw45 such as `s81-j6/candC1n_pf`, plan file). The self-heal repeats the same batch
  without checking that the missing count fell: a retry on an unfixed cause.
- Structural fix (P): `kit_wave_edit add-host` refuses unless a closure probe (the list SRC-INCOMPLETE already computes) is
  empty on that host, and offers the one replicate command for the whole closure. Self-heal stops and posts after two passes
  with no drop in the missing count.
- Owner: FLOW-OPS-1300. FLEET-WATCH-R8 to finish the intel2 closure, or take intel2 out of gen_hosts until it is whole.
- Share: about 1 % (tick time doubled for the whole wave; no kit lost).

### (c) Guard and auto-retire refuse by reference, at whole-tree grain: about 2,000 refusals per host per 6 h, flat

- Count (V, per-host log.jsonl; intel1, epyc2, intel2 over 6 h, epyc7 to epyc10 over 14 h): "protected (kit_wave.json src/bind of
  record/marker/prov)" 782 to 1,918 per host, the largest class on every host. Next: "named in a hub post of the last 24 h" 7 to
  1,122, PROTECTED-DBS 84 to 924, FAILED 100 to 1,016 (epyc2), live input 3 to 586, "SIGNED unit not in the signed store" 13 to
  135. Deletes per 30 min pass fell through the day (epyc10 34 at 11:40 PST to 4 at 18:13; epyc2 45 to 14) with refused constant
  (epyc2 about 410, intel1 260, intel2 300, epyc10 95). Free space after a pass equals free space before it.
- What is refused now (V, guard decision replayed on the dirs refused in the last 2 h on epyc10 and intel1): attempt dirs only
  44 and 11, each listed itself or holding a listed `gen/<type>` or `rtl/kit_rtl.f`. kw45 trees 24 and 19: half listed
  themselves, half refused for one small file inside (`plan_of_record/latcheck.json`, `sidecar_new.json`, `plan_h2_2249.json`,
  `signed_view_sha_s81.json`). Lane trees: one protected child refuses the whole lane dir.
- Root cause: protection is granted by any reference and never bounded. 3,884 CANCELLED wave rows still in state name 42 kw45
  trees; `superseded_trees` lists hold 76 more names; prov cache 72 h; hub posts 24 h. The unit protected is a file of a few kB;
  the unit retired is a 30 to 60 GB tree. The log stores the reason cut to about 150 characters, so the protected path is
  usually unreadable; I had to replay the guard to see it.
- Structural fix (P): see "Retention rule" below (R1, R2). Log the full protected path.
- Owner: FLOW-OPS-1300 for the guard list builder and auto_retire candidates; new lane DISK-RETAIN-1 for the record pack and
  base + overlay source trees (too large for a fix lane that also owns the wave).
- Share: this is the cause of (a); counted there.

### (d) Stale rows on superseded events: 62 ENQUEUED and 113 ROUTE-HELD, flat

- Count (V): ENQUEUED 106, of them 62 on superseded events (QC 36, S81 23, KV 2, HBM 2), median age 13 h, oldest 19 days.
  ROUTE-HELD 118, of them 113 on superseded events; 34 older than 3 days, 40 between 1 and 3 days. RETIRE-SUPERSEDED prints
  "retired 0" on all 18 passes. STALE block: 110 (HBM 104 parked, QC 5 unowned, S81 1).
- Root cause: an un-started row of a superseded event has no terminal transition (owner 11-20: never start it). A ROUTE-HELD
  row waits for a visual verdict or a form change that no one will give for an old event. Both count as live or queued for the
  guard, so each keeps its item dir, two attempts and its source tree.
- Structural fix (P): ENQUEUED on a superseded event with a current-event row for the same type goes to CANCEL-SUPERSEDED on the
  next tick. ROUTE-HELD with a BAD verdict or WAIT-VISUAL older than 24 h on a superseded event goes to the same state, keeping
  reports and images. Running old-plan kits are untouched (owner rule).
- Owner: FLOW-OPS-1300. The 5 unowned QC types (4 `sle_hc0/slw_hc0` with no kit-wave row, `slw_hc3__clccfc3e6b__pv39aac7a1`
  SIGNED 13 h with count pending) go to QC-PLAN-R12.
- Share: 0 compute; it pins disk (source trees d8h, d8i, d8j5, d8j6, d25e3 are held only by these rows, V).

### (e) Tool and source skew: warn-only, rising

- TOOL-SKEW WARN (V 18:17): import-closure modules differing from the die pin: KV 349, S81 234, QC 161, HEAD 9, "launching".
  TOOLS-LAG: live die source trees are 185 to 380 commits behind main and all four report `missing r708` (nominal clock cap);
  at 12:25 KV read "97 commits / missing none". FLOW-HEALTH SKEW (18:07): 37 to 48 modules of the gen/bind closure differ from
  origin/main per live die tree; identical across hosts.
- rt/current differs between hosts (V 18:35): intel2 and epyc10 at 7b6af7dd0449, epyc8 and intel1 at 97321d8d0310. The guard
  file is identical in both. ot-tools-sync may have been mid-roll; it has failed before on hosts under 50 GB.
- Root cause: the source tree is pinned per event and the rule set (r-numbers) moves on main; the check warns and launches.
- Structural fix (P): a rule marked gate-relevant (r708 changes sign-off STA) makes TOOLS-LAG a launch condition for sign-off
  stages only: the measurement tcl is read from rt, not from the pinned tree (open since FABLE-FLOW-1000). ot-tools-sync posts
  when a host stays one snapshot behind for 30 min.
- Owner: FLOW-CANARY-R2 (which rules are gate-relevant), FLOW-OPS-1300 (the read path). Share: not measurable today; the risk
  is sign-offs on a stale STA basis, not lost time.

### (f) Canary: 17 verdicts in 6 posts since 17:00, 0 pass, flat

- V: s81_cl has no baseline and fails KIT_PREFLIGHT reset_tree_coherence before GRT, so it can never set one. hbm reports
  REGRESSION "not measured". STALE-BASELINE verdict and re-baseline landed (R, main 1a2f43e0ea).
- Structural fix (P): a canary whose inputs fail preflight is INPUT-BROKEN, not FAIL, and is excluded from the release verdict
  with one owner post; a canary on a parked die (hbm) is not scheduled.
- Owner: FLOW-CANARY-R2. Share: under 1 %.

### (g) Hub edited outside coord-commit, and alert noise: 11 HUB-SYNC-FAILED, 120 ADOPT-GUARD, flat

- V: HUB-SYNC-FAILED 11 alerts, 5 episodes (12:29 tools/signed_store_ingest.py, 13:32 lanes/posts, 15:32 NOPROG-ACTIONS.tsv,
  17:17 and 17:43 results/geom_review), still present 18:26. ADOPT-GUARD PLAN_MISSING hbm 60 + FIX 60, bind preflight hbm
  UNKNOWN 120 lines, DIE-OFF hbm 5: a parked die whose plan path was deleted prints every tick.
- Structural fix (P): writers of NOPROG-ACTIONS.tsv and geom_review commit through coord-commit in the same step (they are
  tools, not people). A die marked parked in kit_wave.json is skipped by adopt-guard and bind preflight.
- Owner: FLOW-OPS-1300. Share: 0; it hides real alerts.

### (h) Writer attribution is missing where the disk is worst: new

- V: lane quota alerts name intel1 only (harvest-eco-2350 36 to 58 GB per window, 4 alerts; kw45 186 and 191 GB per 6 h). The
  per-host scan timed out at 1,500 s on the 7.4 TB hosts in its last logged runs; `disk_eta_lanes` is empty on every host. The
  4-hourly "top writers" report last posted 11-18.
- Structural fix (P): writers record their own bytes at the end of a stage (ot-run job end, wave attempt end, replicate end)
  into a per-host ledger; no tree walk. Owner: FLEET-WATCH-R8 with FLOW-OPS-1300.

## Why the disk keeps filling

### Stock (V unless marked)

| Host | scratch2 size | free 18:50 | state 18:49 |
|---|---|---|---|
| intel1 | 3,520 GB | 126 | draining (< 250) |
| intel2 | 3,520 GB | 576 | admits, falling |
| epyc2 | 880 GB (+ scratch3 3,520, 385 free) | 107 | draining 9999 |
| epyc7 | 7,393 GB | 265 | no drain flag |
| epyc8 | 7,393 GB | 74 | draining 9999 |
| epyc9 | 7,393 GB | 199 | no drain flag |
| epyc10 | 7,393 GB | 35 | under floor |

epyc10 composition: wave run dirs 1,731 GB (kw43-wave-1109n 1,598: 4,103 attempt dirs in 2,382 items over 91 events, of which
3 events are current); ot-jobs 97; kit-store 95; ot-store 52; rt 51. That is about 2.0 TB of 7.34 TB used. The other 5.3 TB is
kw45 (205 trees: 139 src + 66 snaps, 107 of them created 11-19 to 11-21) and 285 lane dirs (I, by subtraction). epyc8 is the
same shape: wave 1,307, 158 kw45 trees. intel2 holds 250 GB in 10 kw45 trees after one afternoon.

### Writers per host per hour (GB/h)

| Host | net fall, window | named writers |
|---|---|---|
| intel1 | 21 to 51 (R disk-rate) | harvest-eco-2350 about 8/h; kw45 about 31/h (R lane quota) |
| intel2 | 62 average, about 360 from 18:03 to 18:50 (V) | rsync of lane and die trees from epyc7, 3 x 17 MB/s = 180/h visible (V) |
| epyc2 | 13 to 43 (R) | D27c mirror burst to 94 GB free at 15:0x (R FLEET-WATCH-R8) |
| epyc7 | 23; 130 at 14:4x (R) | two S81 donor transfers 112/h at 14:42 (R) |
| epyc8 | 20 to 36 (R) | git checkout burst to 85 GB free at 15:0x (R) |
| epyc9 | up to 51 (R) | not attributed |
| epyc10 | 11 to 15; 75 at 18:14 to 18:43 (V) | route ECO job dirs 23/h (V: 11.4 GB in 30 min, one job dir is 41 GB); 36 new wave attempts 8/h (V); rest not attributed |

Three writer kinds account for what could be attributed: (1) full copies of source trees, per plan event and per host and now
per lane move; (2) route and ECO job dirs, where each ECO iteration keeps four 1.9 GB ODBs (5_route, 5_3_fillcell, 6_1_fill,
6_final); (3) wave attempt dirs, small each (0.15 to 0.3 GB at gen) but never retired for old events with held rows.
Cleanup removes a few dirs per pass because everything large is protected by reference (class c). Inflow is 15 to 60 GB/h per
host; guarded outflow is near zero. The disks fill at the inflow rate.

### Retention rule (P), inside the owner rails: guard, floors and delete path unchanged

- **R1. Protect by need, not by mention.** The guard list builder keeps a kw45 tree only when it is (i) the src or bind of
  record of a die's current event or the one before it, (ii) named by a RUNNING, ENQUEUED or RETRY row, or (iii) under a live
  process. CANCELLED rows, `superseded_trees`, prov cache and hub posts stop protecting whole trees. On supersede, the small
  files those references need (plan_of_record JSONs, sidecars, latcheck, signed_view_sha, about MB per event) are copied once
  into a per-event record pack in the signed store, and the references are rewritten to it. Expected: 148 protected trees
  become about 15 per host.
- **R2. Retire below the protected child.** When a lane tree is refused for a protected child, auto-retire offers the lane's
  other children as candidates. The guard decides each one as today.
- **R3. One sealed base per die pin per host, events as deltas.** `publish_onbase --link-from` already exists; make it the only
  publish path and make lane "move my tree to host X" use it. Fix 3 of FABLE-FLOW-1000, not landed.
- **R4. Event quota in the wave.** Per die keep attempt dirs of the current event and of events with running rows. For other
  events keep signed attempts until archived and the latest routed-unsigned attempt (both already guard rules); everything
  else goes 12 h after supersede. Needs class (d) so that held rows stop counting as queued.
- **R5. ECO iterations keep 6_final.odb and the latest 5_route.odb.** The duplicate stage ODBs go at the end of each iteration,
  in the running job (SUBSTEP-1 does this only for terminal attempts). A 41 GB route job dir becomes about 12 GB.
- **R6. Budget per writer class per host**, enforced at admission by the function of class (a): wave runs, source trees,
  job dirs, lanes each have a GB budget; a writer over budget waits and the post names the largest guard-allowed and the
  largest protected holders in that class. Sizes come from the writer ledger of class (h).

Budget check for a 7.4 TB host (I, estimate): live route jobs 30 x 12 = 360 GB; wave attempts of 3 current events about
750 GB; 15 source trees as base + deltas about 300 GB; kit-store and ot-store 150 GB; lanes active in the last 24 h about
500 GB. About 2.1 TB, so more than 5 TB free against a 250 GB restore line. intel1 and intel2 (3.5 TB) fit the same budget.
epyc2 scratch2 (880 GB) does not fit wave + store together (R FLEET-OPS-R 11-18) and should hold job dirs only.

## For COORD now

1. intel2 is falling fast and is the only admitting host. FLEET-WATCH-R8: name the three rsync owners and decide whether lane
   tree moves to intel2 continue; apply the same 200 GB watch to intel2 as to the others.
2. epyc10 is at 35 GB with 9 new wave gen dirs on it. FLOW-OPS-1300: gen-host pick must read `host_drain` today (smallest form
   of class a).
3. intel2 closure for QC, KV, S81 is not whole after four self-heal ticks: complete it by one replicate or take intel2 out of
   gen_hosts so the die disk cap stops passing on a host the wave cannot use.
4. Open a lane for R1 + R3 (DISK-RETAIN-1); FLOW-OPS-1300 takes R2, R4, R5 and class (d).
