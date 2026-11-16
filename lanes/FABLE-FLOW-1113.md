# FABLE-FLOW-1113: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE-FLOW-1113 (Fable). Read-only. Measured 2026-11-16 09:43-09:55 and 13:22-13:35 PST on hub intel2
(the review was cut by the usage limit in between). Window: autopilot/log.txt 07:40-13:26 PST (64 ticks).
Sources: lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py (09:48), `ot-run --status` (09:48, 13:25),
kit_wave.json, lanes/handoff/tree_switch_*.json, df + kw45 + autoprune/autoclean journals on 6 build hosts (13:22),
ot_disk_autoprune.py as installed, lanes/posts/*, rulings r304-r343. Previous: FABLE-FLOW-0913.
Scope: process and tooling only.

## Headline

1. The fleet ran at 34-46% from 10:20 to 13:00. UNDER-USE: 337-414 of 624 threads idle on every sample. epyc10 ran
   at load 191-279 on 96 cores (99 jobs at 13:25); the other five hosts at load 13-50. Three of the four live dies
   generate on epyc10 only. This is the largest waste and it is a config fact, not a capacity limit.
2. epyc10 loses 290 GB per hour: 2,085 GB free at 09:48, 1,029 GB at 13:25. At this rate it is full at about
   17:00 PST. It is the only gen host of S81 and HEAD. epyc9 is HELD for disk (43 GB measured).
3. The autoprune cannot free anything, by construction. Three separate defects (class 2). It is not a tuning
   question.
4. The S81 run-copy incident: 105 SRC_MANIFEST fails in 14 min (08:51-09:05), then no S81 launch for 3 h
   (09:00-12:0x). The fails were cheap; the 3 h were not.
5. Usage-limit outage 11:20-13:20 (COORD report). The wave kept ticking (24 ticks, median 91 s), but launches fell
   to 2 in hour 11, because every release step was a step a lane had promised to do by hand.

## Fixes of 0913

| Fix (owner) | Landed | Effect |
|---|---|---|
| Disk refusal triggers cleanup (CLEAN-ALL, r307) | yes, timer on all 6 hosts | frees 0 MB every run (class 2) |
| Switch deletes the superseded tree; publish refuses above 2 trees per die | no | epyc10 holds 50 trees, 11 of them S81 pin trees; 20 dirs dated today |
| Gen not pinned to epyc10 | QC yes (5 gen hosts). S81 [epyc10, epyc9], KV [epyc9, epyc10], HEAD [epyc10]; epyc9 is HELD | epyc10 load 277/96 |
| Post-GRT repair self-stop (POSTGRT-STOP-1116) | no lane seen | grt-timecap stops: 1 each in hours 07, 09, 10, 12 |
| Hold release reads a record, not text (HOLDGEN) | partly: r304 limits the match to RESULT posts; 16 leaked kits cancelled 08:52 | no new leak seen; still text |
| HEAD plan_sha written by the switch (KIT-OPS-5) | fixed by hand | PLAN_SHA_MISMATCH 0 since 09:00, 1 at 11 h |
| TOOL-SKEW on the right base (r312) | yes for QC (OK 0 of 17987 at 13:2x) | S81 still WARN 6-12 lines per hour; hbm 228 of 228 |
| Ledger backfill (FLOW-HEALTH-1) | not seen; FLOW-HEALTH-1 last post 06:12 | 1 REPEAT-STOP in the window |
| TERM-UNREACHABLE owner (HOLDGEN) | yes, 20 -> 0 at 08:41 | closed |
| NOPROG.tsv out of the hub checkout | not verified | HUB-SYNC-FAILED 1 (12 h), was 8 |
| Parked hbm prints one line per day | no | PLAN_MISSING hbm 2 per tick all day (64 ticks) |
| HEAD count fallback (r313, plan search on marker hosts) | approved 09:44 | merge not verified |

## Kit wave, 07:40-13:26

| Hour | 07 (from :40) | 08 | 09 | 10 | 11 | 12 | 13 (to :26) |
|---|---|---|---|---|---|---|---|
| LAUNCH | 39 | 138 | 13 | 11 | 2 | 66 | 1 |
| of which S81 | 8 | 120 | 0 | 0 | 0 | 60 | 1 |

FAIL 07:40-09:43: 128 (S81 SRC_MANIFEST 105; QC kit_topology 12; S81 kit input missing 5; S81 tool_mix 4; other 2).
FAIL 09:40-13:26: about 15 (KV self-contained 3, KV bind path 3, S81 input missing 2, S81 gen interrupted 2, other).
LAUNCH-REFUSED same fail key: 113 (07:40-09:43), 49 (11-13 h). STALE 106 current-event (+112 superseded);
unowned: S81 173, HBM 7, KV 6, QC 1. The S81 173 are DEDUP and CANCELLED rows 37-52 h old.

## Classes, ranked by waste

| # | Class | Count, trend | Share of fleet time | Owner |
|---|---|---|---|---|
| 1 | Gen and launch pinned to one host | 3 dies on epyc10; third review; worse | 54-66% of threads idle for 2.7 h | KIT-OPS-7, TOOLS-CONVERGE-1115 |
| 2 | Disk: no working limit | epyc9 HELD, epyc2 26-90 GB, epyc10 -290 GB/h; worse | epyc9 out (96 threads, 15%); epyc10 next | CLEAN-ALL-1115, TOOLS-CONVERGE-1115 |
| 3 | Lane-held release steps (limit outage, S81 `hold_items['*']`) | 2 h + 3 h; new | S81 launches 0 for 3 h; fleet at 34% in hour 11 | KIT-OPS-5, new lane LIMIT-GUARD-1116 |
| 4 | Wave src pointed at a lane run copy | 105 fails, one event; closed by r311 if merged | under 1% in compute; cause of class 3 | KIT-OPS-5, MERGE-QUEUE-1 |
| 5 | Inputs outside the tree | KV 6, S81 7, QC 1 fails; svc as-built names lane folders; down | under 1% | TOOLS-CONVERGE-1115 |
| 6 | Post-GRT repair to the 12 h cap | 4 stops in 6 h; flat | about 5% (unchanged estimate) | new lane POSTGRT-STOP-1116 |
| 7 | Log and counter noise that hides findings | HOLD-AUTO-RELEASE 12,624 lines for 259 keys; hbm alerts; TOOL-SKEW | none directly; log is 50 MB | HOLDGEN-1115, KIT-OPS-7 |
| 8 | Unowned stale rows | S81 173 unowned, flat | none directly | KIT-OPS-7 |

## 1. Gen pinned to epyc10

Evidence. kit_wave.json: s81 gen_hosts [epyc10, epyc9]; qwen_kvsys [epyc9, epyc10]; s81_head [epyc10].
epyc9 is HELD (TEMP-DISK-EP9-1116). The S81 tree `src_s81_pin_3c913dbdfb23_f2s3_mainref_pg_d2` exists on epyc10 and
epyc9 only; HEAD `_d1` on epyc10 only. Load at 13:22: epyc10 280/96, epyc9 51, epyc2 33, intel1 22, epyc7 22,
epyc8 16.
Root cause: a tree is built on one host and copied by a lane step, 48 GB per copy, and the builder publishes a new
variant every 1-2 h. Copying to five hosts never catches up, so the host list stays at the build host.
Fix:
- (TOOLS-CONVERGE-1115) split the tree: one read-only base per tools sha, the same on every host, and a small
  data pack per plan line (plan, as-built, sidecar, views). A new plan line ships the pack only. See class 2.
- (KIT-OPS-7) the autopilot verifies the manifest on every host of `hosts` each tick and uses every host that
  passes. No host list in the marker. This is the 0913 fix; it landed for QC by hand only.
- (KIT-OPS-7) UNDER-USE above 40% idle with one host above 1.5 x cores for 3 ticks posts NEEDS-ACTION once.

## 2. Disk

State at 13:22 (scratch2 free; trees in kw45; lane folders):

| Host | Free | 09:48 | kw45 src trees | Lane folders |
|---|---|---|---|---|
| epyc10 | 1,047 GB (86%) | 2,085 | 50 | 204 |
| epyc9 | 119 GB (99%), HELD | 182 | 48 | 383 |
| epyc8 | 263 GB (97%) | 149 | 28 | 240 |
| epyc7 | 319 GB (96%); root 115 < 150 | 74 | 24 | 364 |
| intel1 | 95 GB (98%) | 67 | 33 | 270 |
| epyc2 | 26-90 GB (97%) | 118 | 20 | 250 |

Why the autoprune "referenced" rule keeps everything (ot_disk_autoprune.py as installed):
1. The text-reference list (40,653 paths from 72 h of handoff and autopilot text) contains a parent folder of
   kw45. `verdict()` keeps a tree when `tree.startswith(ref + "/")`. So one line that names the parent protects every
   tree on every host.
2. Without that, a superseded tree is still named in 72 h of autopilot text, because it was the wave src
   yesterday. 64 kw45 trees are named. The rule protects exactly the trees the tool exists to delete, for 3 days.
3. Candidates are only `src_<die>_pin_<sha>` trees whose sha is not a current tools sha: 3 of 48 on epyc9. The
   `_d1.._d6` variants share the current sha and are never candidates. Trees named `src_*_main_*`, `kvgeom*`,
   `qc_s2x` (most of the 48) are never candidates.
4. On epyc2, kw45 is a symlink to scratch3. Every tree returns "symlink/realpath".
5. It runs only below 65 GB free. The gen floor is 70-100 GB and intel2 refuses at 150 GB. Hosts sit at 90-120 GB,
   refused for gen and above the prune trigger. Exit 3 on a failed hub ssh (2 of 5 runs on epyc9).
ot-autoclean has the same shape: on epyc9 one run took 41 min and 60 GB of memory, deleted 4.4 GB and skipped
438 GB; 2,483 rows (253 GB) are kept as "diagnostics".

Growth. epyc10: 290 GB/h (measured, 3.6 h). 20 tree dirs dated today, 28 bind dirs; a tree is 48-57 GB
(7 measured), so trees and binds explain roughly 1,000-1,400 GB per day on that host. epyc8: 60 GB/h on route
output (0913, 24 openroad). epyc2: 26 GB/h. Per-lane folder sizes were not measured (a du on 7 TB is a heavy job).

Structural limit, in order of effect:
- (TOOLS-CONVERGE-1115) shared read-only base + data pack. Base `kw45/base_<tools_sha>` (48 GB, mode r-x, one per
  tools sha, at most 2 per host). Pack `kw45/pack_<die>_<plan>` (plan inputs, MB to a few GB). The manifest is
  (base hash, pack hash). No hard links: r311 and the nlink check stay. The bwrap smoke already mounts a tree this
  way. This removes about 9 of the 11 S81 trees on epyc10 (about 440 GB) and ends the copy lag of class 1.
- (TOOLS-CONVERGE-1115) the builder removes its own failed and superseded variants at publish: `_dN` is deleted
  when `_dN+1` passes smoke; publish refuses above 2 bases or 3 packs per die on a host.
- (CLEAN-ALL-1115) autoprune: delete the parent-prefix match; text never protects a tree that a marker
  supersedes (keep live process, queue, waiter, unit, exact provenance path); compare realpaths on both sides;
  candidate = every kw45 `src_*` that no marker, kit_wave.json, queue entry or provenance line names; trigger at
  200 GB; print the size; use cached markers when the hub is unreachable.
- (KIT-OPS-7) delete at result. SIGNED: export the record to AGIdock and rtx-pro (owner rule), then delete the
  run dir in the same step. FAIL: keep reports/, logs and bind inputs (owner 11-13); delete odb/def/spef at once.
  "diagnostics" keeps reports only after 24 h.
- (CLEAN-ALL-1115) per-lane quota: a nightly ionice du writes lanes/LANE-DISK.tsv per host. `ot-run --dir` refuses
  a lane folder above 150 GB; a lane folder with no live process for 24 h goes to the approved CLEAN rules.
Now: free epyc10 before 17:00 PST. The 9 older S81 pin trees and the legacy KV/HEAD trees there are the first
candidates; check queue and waiter references first.

## 3. Lane-held release steps and the limit outage

Evidence. KIT-OPS-5 09:15: "hold_items['*'] on s81 ... I switch src then and delete the key". S81 launches: 0 from
09:00 to 12:0x, then 60. Posts did not stop in 11:20-13:20 (6-9 per 10 min at 11:20-11:39, then 10-29); COORD
posted 16 rulings. I could not tell from the posts which agent wrote them. Launches were 2 in hour 11.
Root cause: the next step of a release lives in a lane's memory. When the lane stops (limit, crash, or it works on
the next variant), the fleet waits. All lanes share one account limit, so they stop together.
Fix:
- (KIT-OPS-5) a pending action is data. `autopilot/pending_actions.json`: "when the s81 marker names a tree with
  hash H and smoke passed, set dies.s81.src and delete hold key K". The autopilot runs it in the tick. A lane
  writes the action, then may die. A `hold_items['*']` without such an action or an expiry is refused at load.
- (new lane LIMIT-GUARD-1116, no LLM) the intel2 cron that writes COORD-SNAPSHOT also counts posts per 15 min.
  Fewer than 3 lanes posting for 2 samples writes `LIMIT-OUTAGE` to the log and the snapshot, lists every open
  pending action and every hold without one, and starts the Codex takeover from the snapshot.
- (COORD) spread lanes over the two accounts and stagger starts, so one 5-hour window cannot end all lanes in the
  same minute. Each lane ends every post with its next step, so a resume is mechanical.
Cost: 3 h without S81 launches and 2 h at 34% use: about 400 idle threads x 2 h = 800 thread-hours.

## 4. Wave src on a lane run copy

105 fails, 08:51-09:05, `tree is not main 7073a6b4a599 + its overlay manifest ... 65733 file(s) share an inode`.
The manifest check worked: every kit stopped at the first stage. FLOW-GUARD opened the class after about 100
fails, not after 3. r311 (marker must name dies.<die>.src, sha equal) makes the config impossible. No PUBTREE line
is in the log yet, so the merge and rt sync are not confirmed. Two findings remain:
- tree_switch has 2 marker files for s81 (one with tools_sha None, hosts [epyc10]) and 3 for KV. "Newest mtime
  wins" is a rule waiting to fail. Fix (TOOLS-CONVERGE-1115): one marker file per die; a second is a load error.
- Fix (KIT-OPS-7): a class breaker opens at 3 identical pre-P&R fails in one tick, and the launch loop of that
  die stops in the same tick.

## 5. Inputs outside the tree

KV: `KIT_NOT_SELF_CONTAINED` 3 and a bind path error 3 on `src_kv_pin_eb1e73448bd0_7yhr_d1`. S81: KIT_INPUT_MISSING
7, SRC-INCOMPLETE on intel1 and epyc2 until 09:xx (SRC-HEAL copied 654 files once). svc pilots: as-built
manifests name lane folders. All are the same class as 0913 class 7. The data pack of class 2 closes it when
`ext_source_check` gates the marker; that gate is still not enforced.

## 6. Post-GRT repair

Unchanged. 4 cap stops in 6 h. No POSTGRT-STOP lane exists. COORD: start it, or rule that the cap stays.

## 7. Noise

- HOLD-AUTO-RELEASE: 12,624 lines since 07:40 for 259 keys; 2,600-2,800 per hour. The release is logged every
  tick. Fix (HOLDGEN-1115): log once per transition; then delete the released key.
- hbm: 2 ALERT lines per tick on a parked die (fourth review). TOOL-SKEW hbm "228 of 228".
- failure_breakdown STALE prints "NOT SEEN: intel2 epyc4": the live check does not see the hub it runs on, and
  epyc4 is still in held_hosts.
- RETRY-IGNORED 93 (08 h) and 59 (13 h): not examined.

## 8. Unowned stale rows

S81 173 unowned rows are DEDUP or CANCELLED-SUPERSEDED rows from 11-14 on an old plan line. They are not work.
Fix (KIT-OPS-7): RETIRE-SUPERSEDED also retires DEDUP members whose owner row is retired, so "unowned" counts
only rows on the current line.

## Not checked

- Per-lane folder sizes and the split of the 6.9 TB on epyc9 (du too heavy for this review).
- Whether r311, r312 (S81), r313 are merged and synced to rt/current.
- Which agent wrote the 11:20-13:20 posts; the exact lane stop times.
- RETRY-IGNORED, REAP-DEAD (9 at 10 h), FLOW-HEALTH.tsv hour rows after 09:41.
- epyc10 growth split between trees, binds and route output.
