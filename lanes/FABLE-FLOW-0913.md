# FABLE-FLOW-0913: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE-FLOW-0913 (Fable). Read-only. Measured 2026-11-16 07:45-08:10 PST on hub intel2.
Window: autopilot/log.txt 05:48-07:48 PST (22 ticks). Sources: lanes/FLOW-HEALTH.tsv (07:40), tools/failure_breakdown.py
(07:51), `ot-run --status` (07:55), autopilot/kit_wave.json + kit_wave_state.json, lanes/handoff/tree_switch_*.json,
df/loadavg/kw45 on 6 build hosts (07:52), lanes/posts/*, rulings r291-r303. Previous: FABLE-FLOW-0713, -0513.
Scope: process and tooling only.

## Headline

1. The release path works again. Launches: 21 (06 h) and 46 (07 h), against 0-1 per hour at 04-05 h. Typed holds
   released 119 rows without a lane (95 on event_adopt:S4q6d). All four dies run the v2 trees. Kit FAILs: 9 in 2 h
   (7 are the HEAD private-path fails of 06:0x, closed by the _d1 tree).
2. Disk now removes two hosts from admission. epyc8 scratch2 has 17 GB free (100% used, 7.4 TB) with 24 openroad
   processes running; intel1 has 47 GB. `ot-run` REFUSES both. UNDER-USE now counts 416 threads, not 624. No cleanup
   lane has posted (lanes/posts/CLEAN-ALL-1115.md still does not exist).
3. A typed hold leaked. The `result:` matcher matched COORD ruling r297, which quotes the RESULT line. 16 of the 21
   S81 launches of the window (07:38) are svc kits released by that false match (HOLDGEN-1115 ALERT 07:53). 13 are
   non-pilot kits on a bind without the ref_1116 closure. They still run. COORD must decide to stop them.
4. Gen for QC, KV and HEAD is pinned to epyc10. The QC and KV v2 trees are on disk on all six hosts, but the markers
   list epyc10 only. Load now: epyc10 117/96, epyc9 106/96, epyc7 13/96, intel1 23/112.
5. The post-GRT repair step has a 12 h cap and no progress output. 3 jobs hit the cap in this window (06:32, 07:01,
   07:59), 8 since 11-15 15:42. Each used up to 12 h x 16 threads.

Fleet load at 07:52: about 390 of 624 threads (62%). Idle: intel1 89, epyc7 83, epyc8 49, epyc2 44.

## Fixes of 0713 and 0513

| Fix (owner) | Landed | Effect |
|---|---|---|
| typed `release_on` holds (KIT-OPS-5, HOLDGEN-1115) | yes, r294/r297; rt/current has it; dies.*.hold_items = 0 keys on S81, HEAD, QC, KV | 119 HOLD-AUTO-RELEASE; S81 launched after 7 h. One false release (headline 3) |
| UNDER-USE counts current event by queue status (KIT-OPS-7) | yes, r293 | `enqueued_not_held=311` gone; now q_fail 47-51, q_running 10-14 |
| retire superseded rows (KIT-OPS-7) | yes, r295 | 196 rows CANCELLED at 07:11-07:42 (QC 106, HBM 90); 52 superseded rows left |
| REPEAT-STOP ledger (FLOW-HEALTH-1) | yes, r292, repeat_stop.py in rt/current | ledger holds 15 items, 0 blocked. It started empty (see class 6) |
| bind preflight fails closed (KIT-OPS-7) | yes, r291 | S81 preflight UNKNOWN now holds 16 rows; the cause is open (class 5) |
| v2 tree switch, SELFCONT comment | yes (S81 07:10, HEAD _d1 07:00, QC/KV 06:07) | QC selfcontained passes on 3 fresh kits |
| smoke on a host without lane folders (TOOLS-CONVERGE-1115) | partly: bwrap smoke script exists on epyc10; S81 fails it at once; markers carry no `smoke_host` or `ext_source` field; not enforced | S81 and QC plans still in lane folders |
| auto fail-key release on merge; data-only trees | no. A third tree generation (S81 v3) is being built | fix latency unchanged |
| intel1 prune (CLEAN-ALL-1115) | no lane post. TOOLS-CONVERGE removed its own .building dirs (147 GB free at about 07:30) | back to 47 GB at 07:55 |
| history keys under `_history` (KIT-OPS-5) | no | `prev_treeswitch1116v2` printed as unread |
| NOPROG.tsv out of the hub checkout (0513 class 7) | no | HUB-SYNC-FAILED 8 alerts (06:22, 07:09) |
| 2-min tick | timer yes | tick body 178-481 s (kit_wave_step 96-397 s); ticks 10 min apart at 07:19-07:39 |

## Kit wave, 05:48-07:48

| | this window (2 h) | 0713 (2 h 27 min) |
|---|---|---|
| LAUNCH | 67 (HEAD 16, QC 29, S81 21, KV 1) | 8 |
| FAIL | 9 (HEAD 7 kit_rtl private path; QC 1 kit_topology; S81 1 KIT_INPUT_MISSING) | 10 |
| LAUNCH-REFUSED (same fail key) | 56, all HEAD at 06:0x, released by the _d1 tree | 9 |
| HOLD-AUTO-RELEASE | 119 | 0 |
| RELAUNCH-ON-FIX | 13 | - |
| EARLYOOM resubmit with unchanged memory | 0 | 7 |
| KIT-LOST | 1 (kv3_hub_Ei) | 3 |
| grt-timecap stops (12 h) | 3 | - |
| ALERT lines | 76 (hbm plan 44, HEAD plan sha 12, S81 plan 12, hub sync 8) | hbm only |

STALE: 118 current-event (+95 superseded); was 168 (+183). Unowned: S81 163 (was 196), HBM 7, KV 3, QC 1.

## Classes, ranked by waste

| # | Class | Count, trend | Share of fleet time | Owner |
|---|---|---|---|---|
| 1 | Disk removes hosts from admission | epyc8 17 GB, intel1 47 GB, both REFUSED; epyc7 root 117 < 150 (--dir only); worse | 208 threads out of admission, 138 idle now (22% of the fleet) | CLEAN-ALL-1115 (no sign of life), TOOLS-CONVERGE-1115 |
| 2 | Gen pinned to one host | QC, KV, HEAD gen_hosts = [epyc10]; new with v2 | epyc7 83 idle threads (13%) while epyc10 and epyc9 run above 1.0 x cores | TOOLS-CONVERGE-1115, KIT-OPS-7 |
| 3 | Post-GRT repair runs to a 12 h cap, silent | 3 cap stops in 2 h, 8 in 16 h, 53 in the log; kv_leaf__t2 silent 461 min; flat | estimate 5-10% (3-4 such jobs x 16 threads at any time) | new lane POSTGRT-STOP-1116 (with FLOW-HEALTH-1) |
| 4 | Hold release on prose match | 16 kits launched by a false match; new | 13 kits x 16 threads until stopped (about 2-3% per hour they run) | HOLDGEN-1115 |
| 5 | Stale or unpushed config, checks that read the wrong thing | HEAD PLAN_SHA_MISMATCH 6 ticks; TOOL-SKEW unusable on all v2 trees; FLOW-HEALTH 07 h row; preflight UNKNOWN; hub sync; flat | 16 S81 rows held by the preflight; the rest hides real findings | KIT-OPS-5, FLOW-HEALTH-1, MERGE-QUEUE-1 |
| 6 | Retry on an unfixed cause | slw_sc_v2 relaunched on "changed overlay", same fail; 2 cbn_q00 post-CTS; down | under 1% | FLOW-HEALTH-1 |
| 7 | Inputs outside the tree | S81 plan + asbuilt (PLAN_MISSING 6, SRC-INCOMPLETE intel1 25, epyc8 19), S81 1 + QC 6 kit input missing, hbm alert 22 ticks; down for HEAD | intel1 and epyc8 are not S81 gen hosts for this reason as well | TOOLS-CONVERGE-1115 |
| 8 | Unowned counters | TERM-UNREACHABLE=20 every tick (was 21); tree_switch=89 flat since 06:25; flat | none directly | KIT-OPS-5 |

## 1. Disk

Evidence. epyc8 /srv/opentallas-scratch2: 7,376 of 7,393 GB used. It was 242 GB free at 04:08, 33 GB at 07:42 and
17 GB at 07:52. 24 openroad processes write there. kw45 holds 164 entries, among them 6 full trees of 48-49 GB that no
die config names (src_kv_kvgeom7u, src_kv_e7d0118c2c_pgL, src_kv_main_40e22dd1d2, src_head_main_2dd0d8c9fd,
src_hbm_trainN_aaede, src_hbm_main_7073a6b4a5). Lane folders: vislayout3-s81-leaf 162 GB, s87bind 138 GB (du was cut
at 70 s; the list is partial). intel1: 47 GB, kw45 42 entries.
Root cause: cleanup is a lane, and the lane is not alive. A refusal is a log line that nothing acts on. The tree
builder adds a tree per version (v1, v2, _d1, v3) and removes none.
Fix:
- (KIT-OPS-7) a disk refusal triggers the cleanup. When `ot-run --status` shows REFUSED on scratch for 2 ticks, the
  autopilot runs the approved CLEAN rules on that host in the same tick (OWNER 11-14: apply automatically). It posts
  the freed GB once.
- (TOOLS-CONVERGE-1115) the switch step deletes the superseded tree on every host, once no queued or running job
  names it. A publish refuses when the tree count per die on a host exceeds 2.
- Now: COORD starts a Sonnet lane CLEAN-EPYC8-1116 today. epyc8 at 17 GB with 24 writers can fail running routes
  with ENOSPC within the hour. The 6 old trees are about 290 GB; check queue and waiter references first.

## 2. Gen pinned to epyc10

Evidence. tree_switch_qwen_compute.json and _qwen_kvsys.json list hosts [epyc10]. src_qc_pin_eb1e73448bd0 and
src_kv_pin_eb1e73448bd0 exist on intel1, epyc2, epyc7, epyc8, epyc9 and epyc10. HEAD _d1 exists on epyc10 only.
KIT-OPS-5 waits for TOOLS-CONVERGE to verify hosts; TOOLS-CONVERGE works on S81 v3.
Root cause: host verification is a hand step by one lane, placed behind that lane's next task.
Fix (KIT-OPS-7 + TOOLS-CONVERGE-1115): the marker carries the manifest sha only. Each tick the autopilot runs the
manifest and links check on every host of `hosts` (the SRC-HEAL step of r291 already copies missing inputs) and uses
every host that passes as a gen host. No host list in the marker, no lane step. Now: verify QC and KV on epyc7,
epyc2 and epyc9 and add them (OWNER 11-14: never pin kits).

## 3. Post-GRT repair

Evidence. CLASSIFY `STRUCTURAL (grt-timecap): post-route repair over 43259 s (cap 43200 s) hold_ws_ps=-147.50`
(cbn_q00__cl622f65d2, 07:01). REAP-DEAD SILENT s81|ot_s81sl_kv_leaf__t2: no output for 461 min, CPU growing, so
the watchdog reports it as progressing.
Root cause: the only stop is wall time, set to 12 h. The step prints nothing per pass, so "busy" and "converging"
look the same.
Fix (POSTGRT-STOP-1116):
- the repair loop prints one line per pass (pass, hold WS, violations, cells added);
- the step stops itself when WS or the violation count improved by less than 5% over 3 passes or 30 min, and
  classifies with the last line;
- the cap becomes 2 x the longest repair time of a signed kit of the same family, taken from the records;
- REPEAT-STOP gets the fingerprint `grt_repair|no-progress|<worst endpoint>`.
This is flow tooling, not a design ruling: a design that cannot be repaired is then known after 30 min, not 12 h.

## 4. Hold release on prose

Root cause: `result:` and `proof:` terms grep the post stream. Any line that quotes the wanted text releases the
hold. HOLDGEN's fix (2ffae09e946, gate running) limits the match to lines of type RESULT. That is still text.
Fix (HOLDGEN-1115): post.sh writes a record `state/results/<lane>/<tag>.json` (sender, time, post sha) for a RESULT
line with a tag. Terms read the record, never the text. A release of more than 5 rows in one tick logs
`RELEASE-BATCH <term> <record>` and HOLD-AUDIT checks that the record's sender equals the lane named in the term.
A pilot term (`pilot:<n>`) releases n rows first; the rest follow on the first pass.

## 5. Stale config and checks that read the wrong thing

- HEAD: `PLAN_SHA_MISMATCH declared 810a66fa536a != ddebc47fddd3` on every tick since the _d1 switch. The switch
  changed `src` and `plan` and left `plan_sha256`. Fix (KIT-OPS-5): the switch is one function that writes src, plan,
  plan_sha256 and src_sha from the marker; a config with a marker and a different sha is refused at load.
- TOOL-SKEW: `17138 of 17987 import-closure module(s) differ from pin eb1e73448bd0` for S81, HEAD, QC and KV. The
  earlier figure was 20-69 of 228. The check now walks the whole tree against the wrong base, so it says nothing and
  still prints "warn, launching". 30 more lines say UNMEASURED for trees no config names any more
  (src_s81_pin_e4b9ae9f1c1f, src_qc_pin_e594a73db756). Fix (TOOLS-CONVERGE-1115): compare the kit import closure
  with rt/<tools_sha> of the marker; a ratio above 50% is a check error and is posted once, not a warning.
- FLOW-HEALTH.tsv (07:40) shows 0 launches for hour 07; the log has 46 LAUNCH lines from 07:11. Cause not checked.
  FLOW-HEALTH-1 to verify.
- `bind preflight s81 UNKNOWN: ModuleNotFoundError kit_topology` (5 ticks): 16 S81 rows wait. The preflight imports
  from a path that lacks the module. Fix (KIT-OPS-7): the preflight runs with the die tree on its path, on a gen host.
- HUB-SYNC-FAILED on lanes/NOPROG.tsv: third review. Fix stands (untracked state/NOPROG.tsv). MERGE-QUEUE-1.
- History keys: fix stands (`_history`).

## 6. Retry on an unfixed cause

slw_sc_v2 was relaunched at 06:53 on "changed overlay" and failed at 07:01 with the cause it has had since 03:22
(`bit_route per_bit needs leaf_um`). The ledger counts 1, because it started empty at r292.
Fix (FLOW-HEALTH-1): backfill the ledger once from kit_wave_state attempt history and the log (48 h), so items with
3 or more identical past failures start as BLOCKED-REPEAT. A queued job keeps its runner dir (KIT-LOST, 1 case).

## 7. Inputs outside the tree

HEAD is closed by the _d1 pack. S81 (plan B6gG3b.json, asbuilt, sidecar, about 10 view dirs) and QC (die-qc-103
plan) are open; the S81 v3 pack is in work. One new S81 fail names `/work/run/results/.../1_synth.v` "on no die
host": a child view that names an original kit file. Fix stands from 0713 class 2. Add: data_pack.py (r299) follows
child view references, and the marker is refused while `ext_source_check --config` has findings.
hbm: the die is parked, yet prints 2 ALERT lines per tick. A parked die prints one line per day.

## 8. Unowned counters

TERM-UNREACHABLE=20 has no owner and no list. Fix (KIT-OPS-5): after 3 ticks, post the hold names once as
NEEDS-LANE. `tree_switch=89` has been flat since 06:25, after all four dies switched; which die holds these rows was
not checked.

## Not checked

- The full du on epyc8 (cut at 70 s) and whether the 6 old trees are named by a queued job.
- Whether the 13 leaked svc kits still run at the time of reading.
- Which die holds the 89 tree_switch rows; why FLOW-HEALTH shows 0 launches for hour 07.
- Thread-hours of the grt-timecap jobs (estimated from 16 threads per job).
- Whether CLEAN-ALL-1115 and FLOW-HEALTH-1 agents are alive (posts only; FLOW-HEALTH-1 last post 06:12).
