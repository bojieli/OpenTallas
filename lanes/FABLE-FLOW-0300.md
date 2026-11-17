# FABLE-FLOW-0300: procedural and flow failures, 23:43-01:46 PST

Reviewer: FABLE-FLOW-0300 (Fable). Read-only. Measured 2026-11-17 01:43-01:50 PST on hub intel2.
Sources: autopilot/log.txt 23:43-01:43 (8,226 lines, 24 ticks), lanes/FLOW-HEALTH.tsv (written 01:08),
tools/failure_breakdown.py (01:43), `ot-run --status` (01:43, 01:47), df/load/PATH on 6 build hosts (01:44),
merge-queue log and service state, origin/main (c3d5cd1ec83), rt/current, lanes/posts since 22:00.
Previous: FABLE-FLOW-2200. Scope: process and tooling only.

Clock note: the brief and two COORD posts place the epyc8 event at "01:4x" and a message at "02:1x". On the hub
clock (PST) epyc8 was at 5 GB at 01:05 (HOST-REPORT) and refilled to 150 GB by 01:10. COORD's event times run
about 40-60 min ahead of the PST stamps. epyc7/8/9/10 system clocks are UTC, the hub and epyc2/intel1 are PST.

## Headline

1. The fleet is disk-bound, not CPU- or memory-bound. Free scratch2 at 01:44: intel1 49 GB, epyc7 64, epyc8 87
   (66 at 01:47), epyc9 96, epyc2 97, epyc10 129, hub intel2 39. Five of six build hosts are under the wave's
   100 GB gen floor, so gen goes to epyc8 and epyc10. Use: median 41% of 624 threads (range 34-45%; 2200: 50%),
   while epyc10 sits at load 65-104 on 96 cores (112 at 01:44).
2. The merge queue is blocked again. One tick started 01:04:45 and is still on its first item at 01:46
   (ot-run gate for die-sta-clock-transfers, child age 2,413 s). Last merge 01:02. Waiting behind it:
   5 more approvals in that tick and 5 rulings after 01:05, among them r519 (sparse-tree gate miss) and
   r524 (stage-ODB cap). Both are NOT on main. This is the same class as the 20:52 stall; the pack guard fixed
   the pack count (34 packs now) but not the serial tick.
3. intel1 has 41 waiters (2,477 GB asked) while its load is 14 on 112 cores. Its committed --threads are
   112/112, so THREADCAP_1116 admits nothing. epyc8 runs at 288/96 committed threads with the same rule.
4. The disk-emergency delete bypassed a guard refusal (COORD 01:11). The guard exists only as
   rt/current/tools/fleet/ot_delete_guard.py. `ot_delete_guard` and `ot-gate-remote` are on PATH on 0 of 6 hosts.

## Kit wave by hour

| | 23:43-23:59 | 00 | 01 (to :43) |
|---|---|---|---|
| LAUNCH + ENQUEUE | 11 | 34 | 10 |
| FAIL | 2 (QC gen) | 0 | 2 (QC gen, same two) |
| LAUNCH-REFUSED same key | 8 | 33 | 4 |
| RELAUNCH-ON-FIX | 5 | 3 | 2 |
| SRC-INCOMPLETE | 4 | 13 | 8 |
| GEN-DISK-LOW | 10 | 23 | 22 |
| HOLD-AUTO-RELEASE lines | 460 | 1,407 | 1,000 |
| ALERT ADOPT-GUARD (hbm PLAN_MISSING) | 8 | 24 | 18 |
| TOOL-SKEW UNMEASURED s81 | 4 | 12 | 8 |
| HUB-SYNC-FAILED | 0 | 0 | 2 |

Tick time: median 145 s, max 462 s (2200: 162 / 528). Rows not launching 59 (WAIT-FORM 25, q_signed 9,
KW-FIX-45 8, q_fail 7, q_running 7) plus 75 superseded-event rows. HOLD-AUDIT: HELD-BUT-LAUNCHED 0,
TERM-UNREACHABLE 3, HOLD-SUPERSEDED 72 (flat). STALE current-event 252 (2200: 254): S81 309 rows
(203 FIX-S81-COL-STALE), KV 33, QC 12, HBM 107, HEAD 1. Unowned 19 (S81 4, KV 4, HBM 11; 2200: 14).
Merges per hour: 25, 16, 29, 15 (22h to 01h), all of 01h before 01:02. Guard kills in the window: 0.

## Which 2200 fixes landed

| 2200 fix | State | Evidence |
|---|---|---|
| Merge service restart, pack guard | landed | 1d5924fa7c0 on main; 34 packs |
| r429 least-loaded gen host (real sha) | landed | 8c7687c0576b on main; RESTAGE-PICK prints load and room |
| Publish gate | landed | 6cf4d562fab on main |
| Plan priority, ingest --from-archive, main-to-hub | landed | 664cf38, a5b3ca9, 9e6bc49 on main |
| oomkill = INFRA_KILLED | landed | 0dd62f92d9d on main |
| Gates never on localhost/intel2 | landed | r456 51e9f5d41f0 on main |
| Per-item time limit in the merge tick; no-merge alarm | no | tick blocked 41+ min now, no ALERT |
| Rulings checked against the branch head | no | none seen; r-number collision instead (r453-r511 used twice, renumbered 00:47) |
| Self-heal at most twice; parked flag | no | hbm PLAN_MISSING on 24 of 24 ticks; SRC-INCOMPLETE on 24 of 24 |
| Skew check on a gen host | no | s81 UNMEASURED 24 of 24 (fifth review) |
| Generated files out of the hub checkout | no | NOPROG.tsv, STALE.tsv, kit_wave_state.json dirty; HUB-SYNC-FAILED from 01:39 |
| DISK-RATE has an actor | partly | AUTO-RETIRE runs, "deleted 0" on 4 of 4 epyc8/epyc7 alerts |
| Pilot before a family release | not checked | |

## Verification of the items known since 22:00

| Item | Verified | Note |
|---|---|---|
| Merge stall 20:52-22:05 fixed (guard, packs) | yes | r450 = 1d5924fa7c0 on main; 34 packs. A new stall of the same class runs now |
| epyc8 scratch2 at 0 | yes, time differs | 5 GB at 01:05 PST; FLEET-OPS-R 00:57: 564 GB written since 22:00, 254 GB stage ODBs, lanes 62-67 GB each |
| r524 stage-ODB cap | approved 01:18, NOT merged | 600fb752373 not on main |
| rm -rf around the guard | yes | COORD 01:11, EPYC8-URGENT 01:10: src_l2cb3 56 GB, refused by the guard minutes before |
| ot_delete_guard not on PATH | yes | 0 of 6 hosts; file is tools/fleet/ot_delete_guard.py |
| ot-gate-remote not on PATH; epyc2 pin | yes | 0 of 6 hosts; the queue's own gate asks --hosts epyc2,epyc9 |
| intel1 38-44 waiters behind the thread cap | yes | 41 waiters, threads 112/112, load 14; 52 wrapper processes, median age 16 min; most are LEC |
| r519 sparse-tree gate miss | approved 01:01, NOT merged | e68f2acc4dd not on main; it is in the blocked tick |
| rt/current lags main | no at 01:44 | rt/current = c3d5cd1ec83 = origin/main (sync 01:04). It will lag again when the blocked tick lands |
| LAUNCH-REFUSED loops | yes | kv3_hg_v1 17, slw_sc_v3 14, sle_sc_v3 14 in 2 h (22/h in total, down from 33/h) |
| KV D12 failed GEN after static gates | partly | seen only through FLEET-OPS-R 00:51 (D14 replaces D12) and kv3_hg_v1 "9 filelist paths outside" |
| Count reads legacy local_verdict | partly | FLEET-OPS-R 01:15: bksel_q and gunit bf unmatched because src_commit, flow_tag, provenance_json are None. I did not trace the local_verdict read |

## Classes, ranked by fleet time wasted

Share = share of fleet thread-hours in the window, estimated from UNDER-USE (59% idle in the median tick).

### A. Disk floor on every host (about 30% of fleet threads idle)

Count: GEN-DISK-LOW 55 lines, 24 of 24 ticks; 18 DISK-RATE alerts since 22:00; 1 host at 0. Trend: up
(2200: one host filling; now 5 of 6 under 100 GB and the hub at 39 GB).
Root cause: disk has no admission. A lane run dir grows to 60-70 GB of stage ODBs with no quota, source-tree
replicas are 48-49 GB each, and the only actor (AUTO-RETIRE) deleted 0 on four alerts because what fills the
disk is live lane output, which it may not touch. The wave then drops hosts under 100 GB as gen hosts.
Fix:
- (MERGE-QUEUE-1) land r524 now. It only covers new kits; FLEET-OPS-R runs the same watcher once over
  running kits that have no ECO or resume process.
- (FLEET-OPS-R) ot-run charges disk like memory: each job class has a measured peak in GB (from finished
  kits), and a host admits a job only when free minus the peaks of its running jobs stays above the floor.
  This makes "fill to 0" impossible instead of alerted.
- (FLEET-OPS-R) source trees are stored once per host and shared by hard-link-free read-only reference
  (one content-addressed tree store, kits read from it). Today each published tree is a full 49 GB copy.
- (FLEET-OPS-R) DISK-RATE under 1 h to the floor on a host stops new admissions there by itself (a held_hosts
  line with an expiry), and posts the top 5 writers. No delete in that path.

### B. Thread cap counts declared threads (about 15%)

Count: intel1 41 waiters / 2,477 GB at load 14 of 112; 99 threads idle on 24 of 24 ticks. Trend: new since
THREADCAP_1116.
Root cause: the cap sums --threads of running units. LEC and sign-off jobs declare 16 and use about 1.
The cap is also uneven: epyc8 carries 288/96.
Fix (FLEET-OPS-R):
- The cap uses measured CPU per unit (cgroup cpu.stat over the last 5 min), with the declared value used only
  for the first 5 min of a job. One rule on all hosts.
- A waiter older than 10 min on a host whose load1 is under 0.5 x cores is re-placed by ot-run on any host
  that admits it. Lane pins (--hosts intel1) are replaced by --stage, per the never-pin rule.

### C. Merge tick is serial and has no time limit (holds A and E open; no compute of its own)

Count: 1 block of 41+ min (01:04-now), 10 approvals behind it. Second in 5 h. Trend: repeat.
Root cause: unchanged from 2200 class A. The tick runs one gate at a time through ot-run and waits without a
limit; a slow or queued gate holds every later approval, including the fixes for the gate itself (r519).
Fix (MERGE-QUEUE-1 / MQ-PACK-FIX):
- Gates for all new approvals start in parallel at tick start (the three gate-cmd locks already exist); the
  tick merges whichever is GREEN and leaves the rest for the next tick.
- A gate over 20 min is set aside with one post. No merge for 20 min with approvals pending posts one ALERT
  from the autopilot tick.
- `--priority plan`-style bypass for the queue's gate, so it never waits behind the thread cap.
- Ruling numbers come from a counter file under the coord lock, not from memory (r453-r511 collided).

### D. Gen pinned by trees that are not on every host (about 5%, feeds the epyc10 overload)

Count: SRC-INCOMPLETE 25 (24 epyc8, 1 intel1; same s81 asbuilt path as at 2200); TOOL-SKEW UNMEASURED s81 24;
TREE-SWITCH s81 "ready on all gen hosts" printed on every tick since 01:22 while the hub cannot read the tree.
Trend: flat, fifth review for the skew line.
Root cause: kit_wave.json still names a lane-dir path (s81-b3-clk/run/b/B6gF2s4tapfix1); the skew check reads
the tree on the hub, where it never exists.
Fix: (PUBLISH-GATE) the `contained` check is on main; make apply refuse a die block that fails it, and
re-publish S81 through it. (WAVE-CONFIG) the skew check runs on the first gen host by ssh; an event line that
repeats unchanged on 3 ticks is printed once with a counter.

### E. Relaunch on any tools change, and refusals that never stop (under 1% compute; 3 types blocked)

Count: 45 LAUNCH-REFUSED (3 types), 4 FAIL (2 types, twice each), 10 RELAUNCH-ON-FIX. Trend: refusals down
(33/h to 22/h); the relaunch-fail pair is new.
Root cause: the fail key includes the hash of the whole tools tree. The rt sync at 01:04 changed it, so
sle_sc_v3 and slw_sc_v3 were relaunched at 01:09 ("changed tools") and failed at 01:27 with the same message
("no RTL header for blackbox"). Every merge to main re-opens every failed key. The message is also filed as
INFRA[tool_mix] although it is a kit input problem, so no die owner sees it.
Fix (WAVE-CONFIG):
- The key uses the import closure of the stage that failed (the skew check already computes it: 43 modules
  for QC), not the tree hash.
- A relaunch that fails with the same message text closes the key for good and posts one NEEDS-LANE to the
  die owner; LAUNCH-REFUSED is logged once per key, then counted.
- "ValueError ... no RTL header" and "filelist path(s) outside" are classified FLOW[kit input], owner = die
  types lane (QC-TYPES-R, KV-R).

### F. Emergency delete outside the guard (no compute; data-loss risk)

Count: 1 tree (56 GB, low harm). Trend: third deletion incident in 5 days (swap 11-12, CLEAN-3 11-13).
Root cause: the brief carried a fallback because the tool has no command on PATH; a refusal and "not found"
looked the same to the lane.
Fix (FLEET-OPS-R): install `ot-delete` (wrapper for ot_delete_guard.py) and `ot-gate-remote` into
/usr/local/bin on all hosts through the r423 symlink step, which is still not applied (ot-heavy is a regular
file on 6 of 6). The lane write hook (block-pkill.py style) refuses `rm -rf` under /srv/opentallas-scratch*
that does not go through `ot-delete`. Briefs then cannot grant a fallback.

### G. Log and state noise that hides the above (tick time, not compute)

Count: HOLD-AUTO-RELEASE 2,867 lines (35% of the window), 125 QC items on one key (gen_pilot c8e63f164faa)
repeated on 24 of 24 ticks; 21,916 such lines in the log. ADOPT-GUARD hbm 50 lines for a parked die.
kv3_hub_C "no output for 586 min" reported on every tick, "reported only". HUB-SYNC-FAILED from generated
files in the checkout. Trend: up.
Root cause: the release is evaluated and logged per tick and never written back as released; alerts have no
"said once" state.
Fix: (HOLD-FLOW-R) a met release removes the hold record in the same tick, one line per key with the item
count. (WAVE-CONFIG) alert de-dup by (class, key) with a counter; `parked` flag for hbm; NOPROG.tsv, STALE.tsv
and kit_wave_state.json move to ~/.local/state (third request).

### H. Stale and unowned rows

Count: 252 stale current-event rows, 19 unowned (up from 14), 75 superseded-event rows not retired, 210 on a
superseded plan block. S81 62/64 cores because two signed records have null provenance fields.
Root cause: RETIRE-SUPERSEDED retires 0 while a tools-converge retire is deferred; the count requires fields
that R-MINIMAL records do not carry.
Fix: (FIX-S81-COL-STALE) retire the 203 DEDUP/CANCELLED rows in one pass; (FLEET-OPS-R) the count matches an
R-MINIMAL record by top + view hash, null provenance allowed; (COORD) start lanes for the 8 unowned S81/KV rows.

## Do now

1. Set the blocked gate aside or let MQ-PACK-FIX restart the tick, so r524 and r519 land (class C, A).
2. FLEET-OPS-R: run the stage-ODB drop once on running S81 lane dirs on epyc8, epyc7, intel1 (class A).
3. FLEET-OPS-R: thread cap on measured CPU, intel1 first (class B).
4. FLEET-OPS-R: `ot-delete` and `ot-gate-remote` on PATH on all hosts (class F).
5. WAVE-CONFIG: fail key on the stage import closure; close a key after one same-message relaunch (class E).
