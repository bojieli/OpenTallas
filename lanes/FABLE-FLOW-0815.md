# FABLE-FLOW-0815: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 07:43-07:50 PST on hub intel2.
Window: autopilot/log.txt 05:00-07:43 PST (6,458 lines), ps and /proc/pressure on the 6 gen hosts, `ot-run --status`,
kit_wave.json, kit_wave_state.json, failure_breakdown.py, and today's queue posts.
Scope: process and tooling only. No physical-design judgement.

Fleet basis: 6 gen hosts, 624 threads (intel1 112, epyc2 128, epyc7/8/9/10 96 each).
Shares below are estimates from one sample at 07:46, except where a count is given.

## Summary

| # | Class | Count, 05:00-07:43 | Trend | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Long-running P&R with no stop and no owner | 76 openroad processes older than 6 h | flat to rising | about 13% of fleet CPU (83 cores busy, 598 threads requested) | new lane WAVE-LONGRUN-1 |
| 2 | epyc2 closed to new jobs by a full scratch2 | 1 host, 128 threads | unfixed | up to 20% of fleet threads as its jobs drain | CLEAN-ALL-1115 |
| 3 | epyc9 CPU oversubscription | load 291 on 96 threads, CPU pressure 45% | rising (255 -> 291) | about 5-7% | KIT-OPS-5 (replication) + FLOW-HEALTH-1 (host choice) |
| 4 | Pre-P&R kit input missing or source skew | 494 fails on 589 launches (84%) | classes rotate, rate still 85% after 07:00 | under 3% CPU, but about 2 h of calendar on QC and KV | FLOW-HEALTH-1, WAVE-QCFIX-0715 |
| 5 | Wave config edited but not live | 1 event, about 4 h (01:13-05:2x) | fixed for the push, not for detection | QC changed types idle for 4 h | FLOW-HEALTH-1 |
| 6 | S81 adoption with an incomplete source copy | 3 of 4 S81 gen hosts refused, 2 launches in 33 min | new at 07:25 | S81 release throttled to epyc7 | KIT-OPS-5 |
| 7 | Merge fails | 14 MERGE-FAIL today, 5 since 06:00 | flat | no CPU; 1-2 h delay per fix | MERGE-QUEUE-1 |
| 8 | Bookkeeping noise (STALE rows, log repeats) | 291 STALE, 4,227 repeat log lines | flat | none; hides real rows | FLOW-HEALTH-1 |
| 9 | Lanes edit the owner checkout / force-push | 1 each today | flat | none measured | MERGE-QUEUE-1 |
| 10 | Cleanup deleting live sources | 0 found today | none | none today | CLEAN-ALL-1115 |

## 1. Long-running P&R with no stop and no owner (about 13% of fleet CPU)

Measured:
- 76 openroad processes are older than 6 h across the 6 gen hosts. They use 83 cores and requested 598 threads.
  Per host: intel1 19, epyc2 9, epyc7 9, epyc8 10, epyc9 19, epyc10 10.
- Most are single-threaded global route at 100% CPU. On epyc9: ot_s81sl_leaf__t52 at 17.0 h, ot_s81sl_leaf__t47 at 17.6 h
  and a second ot_s81sl_leaf__t47 at 10.7 h, iqf__t1 at 10.7 h, cbf_q11 at 3.2 h.
- The wave state has 22 RUNNING rows older than 6 h (223 row-hours). 21 of the 22 are on a plan event that is no longer
  current: 18 on S81 7073a6b4a59 (S81 moved to b6gsl_rel2 at 07:1x) and 3 on QC s29q103S3R.
- 3 S81 rows (col_h9_r0_p6__t1 pv0012ba28, pv8d617470, pvbdbd69f2) have been RUNNING at stage preflight for 13.5 h.
  They produce a DEDUP line every tick.
- REAP-DEAD SILENT: 398 lines, 37 distinct units silent over 2 h, 22 over 6 h (S81 26, QC 7, KV 3, HEAD 1).
  Every line says "fleet probe unreadable (reported only)", so the watchdog cannot tell busy from dead and does nothing.

Root cause in the process:
- Adopting a new plan event does not decide what happens to running rows of the old event. KIT-OPS-5 cancels only
  pre-admission clients by hand, and "unchanged types finish" is asserted per adoption, not computed.
- Nothing prevents two attempts of one item from running at once.
- The owner removed the GRT early stop, so the only remaining stop is a watchdog that cannot read the fleet.

Structural fix:
- Make supersede part of adoption. In the same tick that switches a die's event, each RUNNING row of the old event is
  either re-keyed to the new event (block digest unchanged) or cancelled (digest changed). No row stays on an old event.
- One live attempt per item: launch refuses when a unit for the same die and item is active on any host.
- Fix the REAP probe so it reads CPU time of the unit. A unit with no CPU time for 30 min is dead and is reaped.
  A busy unit is not touched: this is a liveness check, not a new limit.
- A row at a pre-P&R stage for more than 1 h is closed as FAIL INFRA.

## 2. epyc2 closed to new jobs (up to 20% of fleet threads)

Measured:
- `ot-run --status`: epyc2 REFUSED, scratch2 has 6 GB free under a 50 GB floor. Its load is still 103 on 128 from jobs
  already running, so the loss grows as they finish.
- scratch2 holds 515 GB of claude trees and 297 GB of ot-store. The root disk on the same host has 2.0 TB free.
- CLEAN-ALL-1115 could delete only 1.8 GB there (kitwave-keep 218 GB, live, under 6 h) and posted that relocation is
  the real fix, not done.
- intel1 had the same refusal 05:00-06:10 (7 `no host qualifies` fails). Cause: a sticky ALERT stopped ot-autoclean for
  2 days. CLEAN-ALL-1115 cleared it and freed 481 GB.

Root cause: ot-run admits on one fixed scratch path per host, and cleanup is the only lever. The content store shares
that disk and has its own gc.

Structural fix:
- ot-run picks, per host, the scratch disk with the most free space instead of refusing the host.
- Move ot-store on epyc2 to the 2.0 TB disk (one relocation, with readlink proof on both ends).
- Merge claude/clean-all-1115-alert-nonsticky @8a777eb057 so one ALERT can never stop cleanup again.

## 3. epyc9 CPU oversubscription (about 5-7%)

Measured:
- epyc9 load 291 on 96 threads, 124 cores demanded, CPU pressure `some` 45% over 5 min.
  The other five hosts are at 0.1-3% pressure with load 72-104.
- 29 global routes on epyc9 requested 312 threads. 16 of the containers are QC core kits (kqc-sta_region_*).
- QC bind sources existed only on epyc9 (KIT-OPS-5 06:5x: 117 source dirs and files; WAVE-QCFIX: treeA/rtl 54 of 10,950
  files elsewhere), so QC plan binds and core kits could only run there.

Root cause: admission is by memory only, and host choice ignores CPU pressure. Plan inputs are not replicated when a
plan event is created, so one host becomes the only eligible one.

Structural fix:
- Host choice, not a limit: ot-run sends the next job to the eligible host with the lowest CPU pressure.
- Plan-input replication is part of every plan event (see class 4), so plan binds are eligible on every gen host.

## 4. Pre-P&R kit input missing or source skew (84% of launches)

Measured, 05:00-07:43: 589 launches, 494 fails. 282 of the 494 are the same item failing the same class again.
A failed attempt takes about 9 min at low thread count.

| Class | Count | Active | State now |
|---|---|---|---|
| QC kit_rtl: HDL source missing (treeA/rtl sparse off epyc9) | 214 | 05:30-06:39 | stopped |
| KV gen: schema.full_area_hard_ip missing (tree behind main) | 75 | 05:30-06:49 | stopped, KV held |
| QC gen: count frame files feed_s29/regions_s29 not found | 62 | 06:30-07:09 | stopped 07:03 |
| KV gen: gen_phys.tap_offset_table missing | 20 | 05:00-05:39 | stopped |
| QC gen: collector_tree differs from bound reset identity | 23 | 07:10 on | new, open |
| QC prov_view input not staged (treeA/physical sparse) | 17 | 07:00 on | open, 6 per 10 min |
| QC VIEW-MISSING: LEF never copied into views/ | 18 | 06:50-07:19 | copied on epyc10 |
| QC GEN_LINT: module not part of the design | 14 | 07:00 on | open |
| Other (disk floor 7, KIT_NOT_SELF_CONTAINED 3, topology 8, misc) | 51 | whole window | open |

Per hour: 05h 148 fails on 214 launches, 06h 246 on 323, 07h (43 min) 100 on 118. The fail rate did not drop: fixed
classes were replaced by new ones.

Root cause:
- Kits read absolute paths into lane-private trees. Adoption checked only the top-level bind json (KIT-OPS-5 06:5x),
  not bind.f, the as-built script, count frames, physical/ or child views.
- The die tree and the kit tools are versioned separately, so a tree can call an attribute its tools lack.
- The wave blocks an item after 3 identical fails, but it has no class-level stop, so a class with 60 items burns
  180 attempts first.

Structural fix:
- Merge claude/flow-health-1 @5044622648a first. It adds the per-host input preflight and the class circuit breaker
  (5 same-class fails in 30 min holds the class). It is READY, not merged; lanes/FLOW-HEALTH.tsv and the src skew check
  (flow_health.py SKEW section) therefore do not exist on the hub yet.
- Adoption writes a closure manifest (every path the kit follows, with sha) and switches kit_wave.json only after the
  manifest verifies on every gen host. The wave launches a row only on hosts whose manifest verified.
- A failed class is not relaunched until its preflight passes. No attempt is charged for INFRA classes.

## 5. Wave config edited but not live (about 4 h of QC)

KIT-OPS-5 05:28: the wave reads origin/coord/state, and the S4K switch sat uncommitted in the working tree from 01:13
to 05:2x, so no changed QC type launched on S4K. FLOW-HEALTH-1 installed a coord-commit.sh at 07:5x that always prints
PUSHED or FAILED. Checked at 07:48: HEAD equals origin/coord/state; only kit_wave_state.json is dirty.

Structural fix: each tick compares the working-tree kit_wave.json with origin/coord/state and posts one ALERT when
they differ for more than one tick. Config edits go through one command that edits, commits, pushes and reads back.

## 6. S81 adoption with an incomplete source copy

Measured: S81 moved to b6gsl_rel2 at 07:1x with 60 types released. Since 07:25 the wave logs SRC-INCOMPLETE for epyc8,
epyc9 and epyc10: B6gsl/asbuilt_run.json names src/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v,
which is missing there. Only 2 S81 launches on the new event by 07:48.
This guard is the right behaviour (it stops instead of failing 200 times), but the adoption post said "sha-verified on
all 4". Same root cause and fix as class 4: the adoption check and the wave check must read the same closure manifest.

Verified fixed: OT_TAP_MAX_SINKS is no longer in the S81 die_gen_env (kit_wave.json at 07:48). The class remains:
die_gen_env keys can override plan values without notice. Fix: gen refuses, or logs one OVERRIDE line per key, when an
env key overrides a value the plan declares.

## 7. Merge fails

Today: 14 MERGE-FAIL (9 red tests, 4 conflicts, 1 orphan base). 5 since 06:00.
Also: queue down 22:42-00:12 (one unfetchable sha crashed every tick), and 19 approvals unseen for about 2 h because
the parser rejected the word "branch". Both are fixed in main.
Three branches failed on the same test (test_kit_chan_identity), so lanes post READY without running the gate.

Structural fix: READY must carry a gate stamp (test result on the current origin/main, with both shas). The queue
rejects a READY without one. Approvals name the branch, and the queue takes the branch tip that contains the approved sha.

## 8. Bookkeeping noise

- STALE 291 (S81 230, 179 unowned). Nearly all are DEDUP or CANCELLED SUPERSEDED rows of old S81 events, not open work.
  Fix: failure_breakdown.py counts only rows of the die's current event.
- Log repeats in 2.7 h: RETRY-IGNORED 2,901, DEDUP RELEASE 928, REAP-DEAD SILENT 398. ARCHIVE FAILED repeats one sha
  (3054c87a89d6, path gone) 17 times. Fix: log a state once, and close an archive item whose source path is gone.

## 9 and 10. Owner checkout, force-push, cleanup

- One force-push note today (KIT-OPS-6) and 4 files edited by lanes in the owner checkout (rtl/dsrom_sys/s81_link,
  still dirty). Fix: deny non-fast-forward on claude/* at the remote, and make the owner checkout read-only for lanes.
- No cleanup deletion of a live source found in today's posts. The "pruned bind worktree" text on the 214 HDL fails is
  wrong: the files were never replicated (WAVE-QCFIX-0715). Fix the message so it does not point at cleanup.

## Order of work

1. Merge claude/flow-health-1 @5044622648a (classes 4, 5, 8).
2. Supersede-at-adoption and one live attempt per item (class 1).
3. epyc2 scratch choice or ot-store move (class 2).
4. Lowest-pressure host choice and plan-input replication in the plan event (classes 3, 6).

## Not checked

- Whether each of the 76 long-running processes is still making progress. Only age and CPU were read.
- lanes/handoff/FLOW-HEALTH-1.md does not exist, so the skew check location is taken from the lane's READY post.
- localhost (rtx-pro) and epyc4 (held for drain) were not probed.
