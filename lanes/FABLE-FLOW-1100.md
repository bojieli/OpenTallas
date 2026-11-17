# FABLE-FLOW-1100: procedural and flow failures, 07:43-09:50 PST

Reviewer: FABLE-FLOW-1100 (Fable). Read-only: no deletes, no kills, no git in owner checkouts. One ALERT posted
(epyc7 disk). Measured 2026-11-17 09:43-09:52 PST on hub intel2 and the 6 build hosts.
Sources: autopilot/log.txt 07:43-09:43 (27 ticks), kit_wave.json + kit_wave_state.json (hub copy), `kit_wave.py plan`
and `unchanged` (read-only), tools/failure_breakdown.py (09:43), `ot-run --status` (09:43), rt/history.log,
per-host df and tree listing. Previous: FABLE-FLOW-0900. Scope: process and tooling only.

## Headline

1. The wave did not recover: 3 LAUNCH in 2 h (QC 2, S81 1, KV 0, HEAD 0). 0900 had 13, 0700 had 42.
   `kit_wave.py plan` says "would launch now (0)" with eligible 0 on all four dies.
2. The cause is one mechanism, not the 233 unreachable terms. Each die is held whole (`items: ["*"]`) by the
   tree-switch pilot record (hold_records.py add_pilot_hold, r393), and in every die the pilot item cannot run.
   344 types wait behind 4 pilots: S81 203, QC 79, KV 46, HEAD 16.
3. Fleet use: median 41% over 27 ticks (range 37-51), 47% at 09:39 (0900: 38%). By load on 6 hosts: 311 of 624
   threads = 50%. The gain is running QC/S81 jobs finishing late stages, not new launches. 0 admission waiters.
4. r565, r569 and r570 are merged and in rt/current 5a5a7f84f431 on hub and 5 hosts. epyc8 is one snapshot
   behind (a07c0d0a834c, sync refused at 45 GB free), which still holds all three. r570 is not deployed: the
   cron runs a private v1 copy, and its last run crashed on the bug r570 fixes.

## Are the fixes live

| Fix | In rt/current | Working? |
|---|---|---|
| r565 SUPERSEDED markers do not protect | yes (build_protected_live.py:42) | yes in code; RETIRE-SUPERSEDED still "retired 0" at 09:11 |
| r569 job dirs on the freest scratch root | yes (09:26 sync) | live on 5 hosts. No help on epyc7 (root 39 GB, so scratch3 usable is negative) or epyc8 (scratch 39 GB) |
| r570 lane quota v2 | yes | NOT deployed. Cron (:20 hourly) runs /srv/opentallas-scratch2/claude/fleet-ops-r/lane_quota.py, the 08:00 v1 copy without BURST or scratch3. Last run: TimeoutExpired on the epyc7 scan (1500 s), whole poll aborted. No autopilot/lane_quota_state.json. No alert can fire |

## Classes, ranked by fleet time wasted

### A. Tree-switch pilot deadlock (about 40% of the fleet: most of the idle half)

Count: 344 types held on 4 dies, 0 at 0900 by name (it was reported as "wave silence"). Trend: worse; launches
6.5/h -> 1.5/h.

| Die | Pilot record | Pilot item | Why the pilot cannot pass |
|---|---|---|---|
| S81 (203 held) | origin config: tree 20ee09596c16, gunit__t1. Hub copy: pilot-s81-c538c5145455, ot_s81sl_leaf__t62 | two pilots in 40 min | gunit__t1 launched 09:12, passed kit_rtl, FAIL at place KIT_PREFLIGHT (5 issues) 09:29, relaunch refused (same fail key). The new pilot leaf__t62 is also held by record s81-mig-003-k3-k4 (event_adopt + lint_clean:s81); its last row is FAIL kit_rtl "7 filelist path(s) outside the kit source tree" (11-16 20:15) |
| KV (46 held) | pilot-qwen_kvsys-d9187b9c24f1 (D16, applied 07:17) | kv3_hg_v1 | the pilot is on the hg/hgi stop list (record qwen_kvsys-mig-003-k3, "no hg launch without the ring split"). No attempt since 11-16 21:46 |
| HEAD (16 held) | pilot-s81_head-bdd769da0966 | hd_serdes | the pilot is held by s81_head-hold-hdserdes-01 (proof:head-serdes-fanout). No row on the current event |
| QC (79 held) | pilot-qwen_compute-c8e63f164faa | sle_fe_v1__cl1cbb7497 | the record names the Kf tree; the die is on manifest e5d43a25c4cf (D4). The term gen_pilot:...:c8e63f164faa can never be met again. The pilot is also under qc-l2-stop-m5-changed-1117 |

Root cause in the tooling:
- pilot_item_for() takes die.pilot_item or the first item name. It never checks that the item is launchable.
  The doc string says "fails open, the die can never deadlock"; it fails open only when no name resolves.
- The release needs GEN + preflight PASS. A pilot that fails for a type-local reason (gunit preflight) keeps
  202 unrelated types held, and LAUNCH-REFUSED then stops the pilot itself.
- A stale auto-pilot record is retired only when a new one is added (QC has pilot_item None, so none was).
- HOLD-AUDIT has no class for it (TERM-UNREACHABLE 233, TERM-VARIANT 21, HOLD-SUPERSEDED 75: flat since 09:04;
  these are mostly parked HBM). UNDER-USE counts 83 rows not launching, 36 of them HBM; the 344 are not in it.
- S81 switched trees 3 times in 2 h (d5 08:41, d5e, c4b 09:26). Each switch re-arms the hold.
Structural fix (WAVE-PILOT-FIX, one change):
1. A pilot is valid only if `plan` would launch it: not in any other hold record, no refused fail key, a gen
   host admits. Pick the smallest launchable item per family; none launchable -> no hold + one ALERT.
2. Release on kit_rtl + GEN PASS of the pilot (tree proof). A preflight or place fail is a type fail, not a tree fail.
3. Pilot FAIL, or no live pilot attempt for 2 ticks, releases the hold and posts NEEDS-LANE once (fail open).
4. An auto-pilot record whose sha is not the die's src_manifest_hash is dropped each tick.
5. HOLD-AUDIT gains PILOT-DEADLOCK; UNDER-USE counts "*" holds per die.
Do now, by hand: drop the 4 auto-pilot records (or set pilot_after_switch false) so the 344 rows launch.

### B. Disk and gen hosts (about 8%: epyc8 out, QC has no gen host)

Count: free scratch2 829 GB on 6 hosts (0900: 587): intel1 59, epyc2 129, epyc7 45, epyc8 39, epyc9 170,
epyc10 387. Hub root 151 GB (64). GEN-DISK-LOW 30 lines (21). Refusals now: epyc8 REFUSED (38 < 50), localhost
REFUSED (105 < 150), epyc7 only `--dir` jobs (root 39 < 150), epyc8 rt sync FAILED 09:26.
gen_hosts against trees (tree present and bind.py in it):

| Die | gen_hosts | Finding |
|---|---|---|
| QC | epyc8 | tree D4 present, but epyc8 is refused and under the gen floor (39 < 60): QC has zero usable gen hosts |
| S81 | epyc10, epyc8, intel1 | c4b tree on all 3 (delta, .link-base: first r562 use). epyc8 and intel1 (59 < 60) are under the floor: epyc10 only |
| HEAD | epyc10, epyc8, intel1 | tree on all 3; same floor state: epyc10 only |
| KV | epyc10, epyc7 | D16 on both. 08:02-09:14 the list named epyc8 and intel1 without D16 (SRC-INCOMPLETE, 84-file hand copy, then cut) |
| HBM | epyc10, epyc2 | epyc10 has NO src_hbm_main_d6b0b70323 ("src_overlay: hbm unreadable on epyc10" every tick; gen_host is epyc10). Parked die, so no fail yet |

ALERT: `src_manifest.py replicate --hosts epyc7` (QC D4, full rsync, 56 GB, started 09:15 from epyc8) has
written 29 GB; epyc7 has 44 GB free and 27 GB to go, so it ends near 17 GB. epyc7 is one of KV's two gen hosts.
Root cause: gen_hosts is a hand-edited list; replicate has no free-space check and no delta for a host with no base.
Structural fix (FLEET-OPS-R): gen_hosts becomes derived. Each tick: gen_hosts(die) = hosts where the die's
src_manifest_hash verifies AND free >= gen floor. A hand entry without a verified tree is dropped with one
CONFIG line. replicate refuses when target free - tree size < floor. TREE-SWITCH needs >= 2 derived hosts.

### C. kit_rtl filelist escape (about 2%; no longer QC only)

Count: 2 QC fails in the window (26 at 0900), both on D3 before 07:50. D4 is proven (sle_ctl past kit_rtl;
class 1ed3a091ec ACKed 09:08 by QC-PLAN-R3, guard released 08:20). But failure_breakdown still lists kit_rtl
28 QC and 24 S81 rows, the state holds 111 S81 current-event rows FAIL@kit_rtl, and the last KV and S81 pilot
rows failed with the same "filelist path(s) outside the kit source tree" text. Those rows are refused once and
never relaunch although the tree changed. Fix: the publish canary of 0900 A1 (not built yet), and a
tree switch clears refused fail keys of class kit_rtl. Owner: WAVE-PILOT-FIX; QC-PLAN-R3, S81-TYPES-R3 rows.

### D. Cell caps (1 type, about 16 h of one KV hub attempt)

Count: 1 FAIL (kv3_hub_C 773,818 cells @cells, 08:32) after the attempt sat about 990 min. Four constants, three
values: 150k (prebuild_gate.py:22; kit_wave.py:7589 prelint default), 400k (kit_wave.py:121; type_bound.py:43),
517k (kit_wave.py:122 CELL_CAP_MAX; autopilot.py:97). Not consistent with the owner rule "split > 400k":
400k acts as a late run stop after synth, not as a split trigger at plan time; 517k lets a kit pass 400k without
a split; a KV hold text says "cell cap removed". Fix: one constant (type_bound 400k) checked on the bind
estimate before launch -> NEEDS-LANE split, never a launch; the run-time check and the 150k and 517k copies
become advisory text. Owner: WAVE-FLOW-R2; KV-HUBC-SPLIT has hub_C (NOT READY 09:32).

### E. Hub checkout edits and runtime skew (under 1%)

Count: HUB-SYNC-FAILED 22 lines (0900: 5), since 08:23: kit_wave.json and lanes/handoff/tree_switch_s81.json
edited in the hub checkout and not committed. CONFIG-DRIFT 3. `plan` (origin) and the hub file name different
S81 trees and pilots. epyc8 runs rt a07c0d0a834c, the hub 5a5a7f84f431. TOOL-SKEW 135 lines (hbm 242 of 242).
Fix: tree-switch apply commits through coord-commit in the same step (refuse a bare edit); rt sync needs
no free-space floor for a 1 GB snapshot, or gets its own 5 GB floor. Owner: WAVE-FLOW-R2, FLEET-OPS-R.

### F. Stale rows, noise, other known items

- Stale: 286 current-event (0900: 320), +220 on superseded blocks. S81 337 (FIX-S81-COL-STALE 203, unowned 5).
- Runaway git: 0 `git log -S` on 6 hosts now; the owner lane ACKed and killed its own (08:53). No guard exists.
  Fix: lane hook blocks `git log|grep ... -S/-G/--all` in partial clones unless GIT_NO_LAZY_FETCH=1.
- count_hourly stdin: tools/count_hourly.py has no stdin read now; not re-tested.
- Gate flakes on the epyc7 root floor: not seen in the window; the cause stands (root 39 GB).
- Tick 119 s (137). REAP-DEAD SILENT 11 (22). RELAUNCH-ON-FIX 1.

## Do now

1. WAVE-PILOT-FIX: release the 4 pilot deadlocks (344 types), then the 5-point pilot fix.
2. FLEET-OPS-R: stop or re-point the QC D4 copy to epyc7 (ends near 17 GB free); free epyc8 scratch (QC's only
   gen host, refused); point the lane_quota cron at rt/current.
3. FLEET-OPS-R + WAVE-FLOW-R2: derived gen_hosts (verified manifest + floor); remove hbm@epyc10.
4. WAVE-FLOW-R2: one 400k split check at plan time.
5. S81-DIE-R3: commit the hub edits of kit_wave.json and tree_switch_s81.json through coord-commit.
