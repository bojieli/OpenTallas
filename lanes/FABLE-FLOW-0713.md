# FABLE-FLOW-0713: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE-FLOW-0713 (Fable). Read-only. Measured 2026-11-16 05:49-06:20 PST on hub intel2.
Window: autopilot/log.txt 03:50-06:17 PST (27 ticks). Sources: lanes/FLOW-HEALTH.tsv (05:36), tools/failure_breakdown.py
(05:59), `ot-run --status` (06:02), autopilot/kit_wave.json + kit_wave_state.json (06:04), df/loadavg and kw45 listing on
6 build hosts (06:04), lanes/posts/*, rulings r288-r290, lanes/handoff/tree_switch_*.json. Previous: FABLE-FLOW-0513.
Scope: process and tooling only.

Timing note: FABLE-FLOW-0513 was committed at 05:40 and this review started at 05:49. The owning lanes had about
30 minutes, not 2 hours. "Not landed" below mostly means "not started yet", except where a lane has no post at all.

## Headline

1. The fleet is 64-69% idle and getting worse: used threads 59% (03:45) -> 47% (05:35) -> 37% (05:59) -> 31-36%
   (06:10-06:15). Launches per hour today: 22, 19, 15, 13, 1, 0, 7. The 7 launches at 06:03 (HEAD) all failed in 4-10
   minutes.
2. The "318 unheld rows that do not launch" of 0513 is a counting error, not a launch bug. The wave status ENQUEUED
   means "handed to the ot-run queue after place". Of the 312 rows now counted: 264 have a finished queue result FAIL,
   25 are SIGNED, 21 are RUNNING, 2 ORPHAN; 291 belong to superseded events (QC efdb36e864 alone 118, last update
   11-06). No row is waiting for a slot. The explain step as specified would explain nothing; the counter must change.
3. The autopilot switched S81 and HEAD to the v1 pin trees at about 05:57 (kit_wave.json src = src_s81_pin_e4b9ae9f1c1f,
   src_head_pin_e594a73db756; old values under prev_treeswitch1115). The markers still name v1 (written 03:31); no
   marker names eb1e73448bd0. HEAD: 7 of 7 first launches on the pin tree failed kit_rtl bootstrap with
   `FileNotFoundError /srv/.../head-97/pd/native_domains/head_serdes_primary_3place_1113.json` on epyc10, a private
   lane path. The marker smoke ("kit_rtl 12/12 RC0") ran where head-97 exists. S81: still 0 launches, 6 h 45 min
   (last 11-15 23:34), now held by prose holds, not by the tree.
4. Of the six 0513 fixes: one is installed (2-min tick), one is approved but not in the runtime (r290: SELFCONT
   comments + private-path check in REPORT mode), four have no code and no post (REPEAT-STOP, explain step, intel1
   prune, data-only trees).

## FABLE-FLOW-0513 fixes

| Fix (owner) | Landed | Class effect |
|---|---|---|
| REPEAT-STOP ledger (FLOW-HEALTH-1) | no. Last FLOW-HEALTH-1 post 02:46; no REPEAT/STALLED code in rt/current (cd1b8dbc54b, 05:56) | not shrunk. kv3_pc_v1 x2: 4 earlyoom resubmits each at `--mem 48 unchanged` (03:42-04:52), then 72 GB by the older infra-oom rule, then KIT-LOST 05:22-05:24 (runner missing). autopilot/kit_wave_blocked.tsv is still header-only (11-15 21:45) |
| explain 318 rows (KIT-OPS-7) | no. Last KIT-OPS-7 post 03:51 | the class is a counter artifact (headline 2) |
| 2-min tick (KIT-OPS-7) | yes. autopilot.timer OnUnitInactiveSec=120. Tick starts 05:35, 05:40, 05:45, 05:50, 05:55, 05:59: every 4.5-5 min (150 s tick + 120 s), was 10 min | fail-to-refusal delay halved. Tick body is still 150 s, of which loop_gaps 59 s and kit_wave_step 71 s |
| intel1 tree prune (CLEAN-ALL-1115) | no. No lanes/posts/CLEAN-ALL-1115.md exists | flat: intel1 scratch2 51-56 GB free, kw45 still 37 entries, GEN-DISK-LOW on every tick (18 lines). intel1 is out of gen |
| refuse private-lane paths at config load (TOOLS-CONVERGE-1115) | partly. r290 (06:03) approved ext_source_check --config, REPORT mode only; not in rt/current | not shrunk, and it fired: 7 HEAD kits on head-97; ADOPT-GUARD PLAN_MISSING hbm (kit-ops-1 path) on every tick since 05:32. The check FAILS for all 5 dies today (plans, asbuilt, sidecars in s81-b3-clk, head-99, die-qc-103, kit-ops-1) |
| data-only trees (TOOLS-CONVERGE-1115) | no; the lane plans a v3 delta for 4 trees instead | not shrunk. Tool skew unchanged: S81 69, HEAD 53, KV 20, HBM 95 of 228; QC UNMEASURED |
| SELFCONT comment false positive (TOOLS-CONVERGE took it) | approved r290 06:03 (comment line removed in main, checker ignores # comments); not in rt/current; v1 and v2 trees of all 4 dies still carry the line | 6 QC items still refused (class c344a406fe); FAIL-ROUTE escalated it to COORD at 05:48 |
| v2 tree switch | no. v2 complete only on epyc10 (S81, HEAD, KV, QC); S81 v2 also on intel1, epyc8, epyc9; epyc2 and epyc7 have none. Smoke 46/46 RC 0 on v2 per the lane | the autopilot switched to v1 instead (headline 3) |

## Kit wave, 03:50-06:17

| | this window (2 h 27 min) | 0513 (2 h) |
|---|---|---|
| LAUNCH | 8 (HEAD 8; S81 0, QC 0, KV 0) | 31 |
| FAIL | 10 (HEAD 7 kit_rtl private path; QC 2 SELFCONT comment; KV 1 ssh 255 at place) | 26 |
| LAUNCH-REFUSED (same fail key) | 9 to 05:50, then HEAD rows from 06:08 | 15 |
| EARLYOOM-RESUBMIT with unchanged memory | 7 (2 items) | - |
| KIT-LOST (runner missing on hub) | 3 | - |
| ALERT ADOPT-GUARD PLAN_MISSING hbm | 2 lines per tick since 05:32 | - |
| HUB-SYNC-FAILED | 0 | 1 |
| used threads | 47% -> 31-36% | 59% |

Disk and admission: no ot-run memory refusal (every host admits 476-787 GB). The only refusals are GEN-DISK-LOW on
intel1 and epyc7 root 118 GB < 150 floor (--dir jobs only). epyc4 HELD (drain). STALE: 168 current-event (+183
superseded); was 149 (+182). S81 unowned 196 (was 193).

## Classes, ranked by waste

| # | Class | Count, trend | Share of fleet time | Owner |
|---|---|---|---|---|
| 1 | Die release depends on prose holds and on a tree that needs a lane | S81 0 launches 6 h 45 min; rows: WAVE-HOLDS-1115 172, DIE-S81-92 156, tree_switch 89, PARKED-OWNER 56; worse | most of the 64-69% idle | KIT-OPS-5, DIE-S81-92, TOOLS-CONVERGE-1115 |
| 2 | Tree published with inputs outside it (private lane paths) | 7 of 7 HEAD launches; hbm plan alert every tick; all 5 dies fail the check; new as a launch-killer | 7 kit gens lost; blocks HEAD refill of ~60 idle threads | TOOLS-CONVERGE-1115 |
| 3 | UNDER-USE counts finished rows as waiting | 312 rows, 0 real; flat | none directly; it sent 0513 and COORD after a bug that does not exist | KIT-OPS-7 |
| 4 | Retry on an unfixed cause (no fingerprint, OOM resubmit unchanged) | 7 unchanged OOM resubmits, 3 KIT-LOST; not shrunk | ~1-2% (2 x 16 threads x 1.5 h on epyc7, plus earlier route repeats) | FLOW-HEALTH-1 |
| 5 | Tree disk on intel1 | 51-56 GB, flat, no prune | intel1 gen unavailable (112 threads at 48-58 load) | CLEAN-ALL-1115 |
| 6 | Approved fix not in the runtime or the trees | r290 at 06:03; 6 QC rows still refused; each fix needs merge + rt + tree delta + marker | 6 QC types idle since 03:22 | MERGE-QUEUE-1, TOOLS-CONVERGE-1115 |
| 7 | Config history keys printed as unread | `prev_treeswitch1115` added a new one at 06:02; same | none | KIT-OPS-5 |

## 1. Release by prose

Evidence. S81 current event 3fa87b84b18: FAIL 130, ROUTE-HELD 90, ENQUEUED/FAIL 43, RETRY-INFRA 22, running 2.
dies.s81.hold_items has 483 entries. The DIE-S81-92 entry says "Release on B6gG3c = the same G3b plan + RTL on the
TOOLS-CONVERGE S81 tree, checked on one fresh kit (M7 offset 8.448)". That is text; no typed term reads it. The tree
term fired (src switched at 05:57) and nothing launched, because the release still needs DIE-S81-92 to edit the
config, and DIE-S81-92 has no post file and no post today. HOLD-AUDIT reports TERM-UNREACHABLE=21 every tick and
nobody owns that number.
Root cause: a hold can be written without a machine-readable release. A tree switch and a hold release are two
separate hand steps by two lanes.
Fix (KIT-OPS-5): the config load refuses a hold_items entry without `release_on` (typed terms only: tree_ready:<die>,
event_adopt:<key>, proof:<id>, probe:<item>:<check>). For this case: `probe:slice_station__t46:pdn_m7_offset=8.448`
launches one held item on the new tree, and a pass releases the pattern in the same tick. TERM-UNREACHABLE > 0 for
3 ticks posts one NEEDS-LANE with the hold names. Convert the 328 S81 rows now (COORD decides today: probe on the
v1 pin tree, since the autopilot already runs it).

## 2. Trees with inputs outside the tree

Root cause: the publish smoke runs on the builder host, where lane folders exist. The tree is then copied to hosts
that do not have them. The marker lists hosts but the smoke did not run on them.
Fix (TOOLS-CONVERGE-1115): (a) the publish step runs ext_source_check and the kit_rtl smoke on a gen host other than
the builder, inside a mount namespace that hides /srv/*/claude/* except kw45 and rt (bwrap or `unshare -m` with a
tmpfs over the lane root). A private path then fails at publish for every die, not at the first launch. (b) the
marker carries `smoke_host` and `ext_source: 0 findings`; the autopilot refuses a marker without both. (c) r290 moves
from REPORT to enforce per die as soon as that die's marker passes (b); plan, asbuilt and native_domains files are
copied into the tree as a data overlay at ADOPT. (d) the autopilot switch at 05:57 used a marker written 03:31 for a
tree that r285 had called failed: a marker has `supersedes` and an expiry, and a ruling that fails a tree deletes
its marker in the same commit.
Now: HEAD needs head-97/pd/native_domains/*.json in the tree (or on epyc10) and the 7 fail keys released.

## 3. UNDER-USE counter

Root cause: under_use.py line 13 treats every status ENQUEUED as "waiting for a launch", in any event, with any
queue result. The same error inflates hold_items:* (S81 "156 held" includes rows that already failed in the queue).
Fix (KIT-OPS-7): count only rows of the die's current event; split by q_status (queued = waiting, RUNNING, FAIL,
SIGNED). "Not launching" = current-plan types with no live attempt and no signed record, grouped by the first gate
that refuses them (hold name, fail key class, no row). Expected true figures now: S81 ~330 held or failed, QC 22
failed + 12 held, HEAD 7 failed, KV 4, HBM 77 parked.

## 4. Retry on an unfixed cause

Unchanged from 0513 section 3; no work has started. Add one case: KIT-LOST. The hub copy of run_kit.sh was removed
while the queue still held the job (kv3_pc_v1 x2 at attempt 6, kv3_pc__cl254f2e73 at attempt 28). Fix in the same
ledger (FLOW-HEALTH-1): an OOM resubmit uses measured peak x 1.25; a second identical fingerprint blocks; a runner
dir named by a queued or running job is never pruned (the wave checks the queue before it removes an attempt dir).
If FLOW-HEALTH-1 is not alive, COORD starts a Sonnet lane for REPEAT-STOP today.

## 5. intel1 disk

No lane acted. Fix stands (0513 section 4). CLEAN-ALL-1115 has no post file, so the owner may not exist: COORD names
a live owner. Structural: the tree builder deletes the superseded tree on each host at switch time; the autopilot
GEN-DISK-LOW line posts NEEDS-ACTION once after 6 ticks instead of logging forever.

## 6. Fix latency from approval to effect

r290 was approved 06:03. It takes effect only after merge, rt/<sha> roll-out, a v3 tree delta on every host, new
markers and a fail-key release. Each step is by hand. This is 0513 class 1 again and the reason for data-only trees:
tools from rt/<sha>, so an approved tool fix reaches every kit one tick after merge. Until then: the merge of a
commit that names a FAIL-CLASS id releases that class's fail keys automatically (MERGE-QUEUE-1 + KIT-OPS-5).

## 7. Config history keys

Same as 0513 section 6. The autopilot's own switch now writes `prev_treeswitch1115` and then reports it as an unread
key. Fix: the autopilot writes history under `_history`, which the reader check skips.

## Not checked

- Why the autopilot switched at 05:57 on a 03:31 marker (which commit or config edit armed it).
- Whether DIE-S81-92, FLOW-HEALTH-1, CLEAN-ALL-1115 and KIT-OPS-7 agents are alive (only their posts were read).
- The S81 v1 pin tree on a real kit; no S81 launch has used it.
- Thread-hours of the repeated runs (estimated from 16 threads per job).
