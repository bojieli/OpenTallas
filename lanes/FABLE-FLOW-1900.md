# FABLE-FLOW-1900: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE-FLOW-1900 (Fable). Read-only. Measured 2026-11-16 17:43-18:00 PST on hub intel2.
Window: autopilot/log.txt 15:44-17:43 PST (21 ticks). Sources: lanes/FLOW-HEALTH.tsv (last row hour 16),
tools/failure_breakdown.py (17:45), `ot-run --status` (17:43), df/free/kw45 on 6 build hosts (17:48),
kit_wave.json, lanes/posts/*, CODEX-LOG handoff 17:04. Previous: FABLE-FLOW-1113. Scope: process and tooling only.

## Headline

1. ACT NOW, hub memory. intel2 has 36 GB free of 1007. One process holds 869 GiB RSS: pid 70691,
   `skyhum-work/.../afg_cli.py search`, started 17:00:29, session scope 3061721. It is not an OpenTallas job.
   S81-CORES-R reports serdes J3/G3 PLACE earlyoom-killed on the hub at 16:58/16:59. The autopilot, count-hub,
   the merge service and all waiter clients live on this host. I did not touch the process (read-only, not ours).
2. ACT NOW, epyc10 disk. 1,047 GB free at 13:22, 360 GB at 17:48: 156 GB per hour. Full at about 20:00 PST.
   It is the only gen host of KV and the only host with the HEAD tree. 57 kw45 trees (50 at 13:22).
3. Four of seven build hosts are out for new work on disk: epyc2 48 GB, intel1 33, epyc7 51 (root 106 < 150),
   epyc9 31-81. Only epyc8 (627 GB) and epyc10 admit freely.
4. Fleet use 32-46% on 20 of 21 samples, epyc10 at load 142-220 on 96 cores. Fifth review of this class.
5. KV D3 adoption: 22 launches at 16 h, 24 gen-stage fails at 17 h, 0 kits reached place.

## Kit wave, 15:44-17:43

| Hour | 15 (from :44) | 16 | 17 (to :43) |
|---|---|---|---|
| LAUNCH | 2 | 31 (KV 22, S81 5, QC 4) | 2 |
| FAIL | 5 | 6 | 24 (all KV) |
| LAUNCH-REFUSED same key | 6 | 9 | 5 |

Fails by class: KV ContractError "multiple clock pins need measured per-pin means" 12; KV KIT_NOT_SELF_CONTAINED
(provenance.json) 7; KV INFRA-VIEW-MISSING 5; S81 KIT_INPUT_MISSING 5; INFRA OOM kill on epyc10 3; design 3.
Tick time: median 207 s, max 306 s (1113: median 91 s). kit_wave step 98 s, loop_gaps 58 s.
STALE: 202 current-event (1113: 106) + 149 superseded. Unowned: S81 149, HBM 11, QC 8.

## Fixes of 1113

| Fix | Landed | Effect now |
|---|---|---|
| Gen on every host with a verified tree | partly: TREE-SWITCH sets gen_hosts when a tree is whole; S81 on epyc10+epyc8 at 17:34 | KV epyc10 only; HEAD names epyc2, which has no tree |
| Shared base + data pack | no | 4 HEAD trees (nf15, nf15a, nf15b, nf15c) published in 6.5 h, about 48 GB each |
| Autoprune rules | guard 2dda on all 7 hosts, timer back on 17:3x | "freed little (hardlinked)"; autoclean and reaper stay off |
| Delete at result | READY d02d0f4d5bc, gate 136/136, not merged | none yet |
| Pending actions as data | no | Codex cover 14:23-17:07 again parked nine lanes by hand |
| One marker per die; breaker at 3 fails | breaker works: 3 classes opened at 17:29-17:35 | KV stopped after 12+7, not after 3 |
| HOLD-AUTO-RELEASE once per transition | partly | 728 lines in 2 h (was 2,700 per hour) |
| NOPROG.tsv out of the hub checkout | no | HUB-SYNC-FAILED 14 in 2 h |
| hbm one line per day | no | 40 ALERT lines in 2 h (sixth review) |
| RETIRE-SUPERSEDED for DEDUP rows | no | S81 unowned 149 |

## Classes, ranked by waste

| # | Class | Count, trend | Share of fleet time | Owner |
|---|---|---|---|---|
| 1 | Hub shared with unbounded foreign jobs | 1 process 869 GiB; 2 serdes jobs killed; new | 2 place runs lost; whole control plane at risk | FLEET-OPS-R |
| 2 | Disk: publish rate above delete rate | 4 of 7 hosts refused; epyc10 -156 GB/h; worse | about 45% of threads closed to new gen | FLEET-OPS-R |
| 3 | Load on one host | epyc10 1.5-2.3 x cores, others 7-46; flat | 54-68% of threads idle for 2 h; 3 OOM kills on epyc10 | FLEET-OPS-R |
| 4 | Die source published without its closure | KV 24 fails, QC 12 bind/*.py, S81 5; worse | under 1% compute; KV got 0 kits in 2 h; QC Lr2 run lost | KV-R, QC-PLAN-R, FLEET-OPS-R |
| 5 | Release without a passed pilot | KV 22 launched, 3 pilots allowed; new | under 1%; 19 rows burned an attempt | KV-R, HOLD-FLOW-R |
| 6 | Self-heal and alert loops that never converge | HEAD SRC-SYNC 20 of 21 ticks; PLAN_MISSING 20; flat | none direct; tick 207 s | HEAD-DIE-R, FLEET-OPS-R |
| 7 | Stale rows owned by dead lanes | 202, doubled | none direct; hides real work | FLEET-OPS-R |
| 8 | Unguarded manual deletes and stale clones | 1 QC .git delete without guard; 1 git grep held 966 GB; wt-thin15 49 GB | E8 near zero once; E9 ENOSPC once | FLEET-OPS-R |
| 9 | Merge gate staging | E7 overfill, once; fix 0a5 GREEN, approved r386 | E7 gates lost, about 2 h of one host | FLEET-OPS-R |

## 1. Hub memory

Evidence: `free -g` 965 used, 36 free, swap 0. Top RSS 910,127,328 kB = pid 70691, a skyhum-work job. 24 skyhum
processes on the hub. held_hosts keeps ot-run jobs off the hub, but serdes J3/G3 PLACE ran there outside ot-run.
Root cause: the hub has no memory boundary. Any shell job of the same user can take all RAM, and earlyoom then
picks OpenTallas processes (it avoids python3, so it kills openroad and waiter clients first).
Fix (FLEET-OPS-R):
- Every non-coord job on intel2 runs in a systemd slice with MemoryMax (for example 256 GB). The autopilot,
  count-hub and merge units get MemoryMin and OOMScoreAdjust -900.
- earlyoom `--prefer` matches processes outside the coord slice.
- No P&R on the hub by any path: the lane launch wrapper refuses the hub host name, not only ot-run.
- The autopilot prints ALERT HUB-MEM when available memory is under 10% and names the top process.
Owner call needed now: stop or cap pid 70691.

## 2. Disk

| Host | scratch2 free 17:48 | 13:22 | kw45 trees | Lane folders |
|---|---|---|---|---|
| epyc10 | 360 GB | 1,047 | 57 | 212 |
| epyc8 | 627 GB (966 GB came back from a dead git grep) | 263 | 30 | 248 |
| epyc9 | 31-81 GB | 119 | 44 | 386 |
| epyc7 | 51 GB; root 106 | 319 | 26 | 370 |
| intel1 | 33 GB | 95 | 31 | 267 |
| epyc2 | 48 GB | 26-90 | 19 | 256 |

Root cause, unchanged: each plan variant is a full 48 GB tree, and nothing deletes the variant it replaces. The
guard protects every tree that any handoff names, so all 44 trees on epyc9 are protected. Hard-linked trees free
nothing until the last link goes. Cleanup is by hand, one folder per request (wt-thin15 took a ruling, r388).
Fix:
- (FLEET-OPS-R) base + pack (1113 class 2). Until then: publish refuses when the die already has 2 trees on the
  host; the publisher names the tree it replaces and the switch deletes it in the same step.
- (FLEET-OPS-R) the guard reads structured roots only: markers, kit_wave.json, queue, live process, unit files.
  Handoff prose never protects a tree. This also ends the /mq-gate and /s81-b3-clk anchor refusals on epyc7.
- (FLEET-OPS-R) merge d02d0f4d5bc (delete at result) today.
- (FLEET-OPS-R) ALERT DISK-RATE: free space and GB per hour per host each tick; "full in under 4 h" posts once.
Now: epyc10 needs about 300 GB before 20:00. First candidates: nf15, nf15a, nf15b (superseded by nf15c),
hg1A_d1 and hg1A_pgr1_d2 (superseded by d3), f2s3_mainref_pg_d2 once no S81 job reads it.

## 3. Load on one host

Evidence: UNDER-USE idle 157-347 threads on every sample; epyc10 load 142-220; epyc7 load 7-16; epyc2 23-63.
Rows not launching 107: running 30, WAIT-FORM 25, ROUTE-HOLD 18, failed 12, KW-FIX-45 8. So part of the idle is
demand: 43 rows wait on a form or route verdict. The rest is placement: gen and its children stay on the tree
host. INFRA OOM kills on epyc10: 3 (15:49-15:56), with 167 GB available there and 475-804 GB on four other hosts.
Fix (FLEET-OPS-R): place, CTS and route take a kit, not a tree; the wave sends them to the host with the most
admitted memory. Only gen needs the tree. KV-R and HEAD-DIE-R: replicate the current tree to epyc8 (in progress,
HEAD 11 of 48 GB at 17:39). WAIT-FORM 25 and ROUTE-HOLD 18: each needs a live owner (HOLD-FLOW-R to list them).

## 4. Source published without its closure

- KV `src_kv_pin_eb1e73448bd0_hg1A_pgr1_d3`: views under kvhg1_views_1116 lack provenance.json (7 fails);
  signoff.json has no per-pin clock means (12); 5 cland views are named on epyc2/intel1 paths that are gone (5).
  The same tree lacks GRT-PATCH-1 (GRT-ARM LAUNCH-SKIP 6): the pin eb1e is older than the patch.
- QC stage: 12 physical/qwen_compute/bind/*.py are loaded by name at run time, so the import closure missed them.
- S81: KIT_INPUT_MISSING 5 (child-view kit files on no host). TOOL-SKEW UNMEASURED s81 14 times: the hub cannot
  read the d3 tree, so the skew check is blind exactly after a switch.
Root cause: the manifest lists what the publisher copied, not what gen reads. Nothing runs gen before adoption.
Fix:
- (FLEET-OPS-R) adoption gate = one dry gen per kit class from the published tree in a sandbox that mounts only
  the tree (the bwrap smoke). Any read outside it, or a missing view file, fails the publish. ext_source_check
  becomes blocking (third review).
- (KV-R, QC-PLAN-R) view packs carry provenance.json and signoff.json with per-pin means; dynamic siblings are
  declared in the manifest by directory, not by import trace.
- (FLEET-OPS-R) the skew check runs on a gen host when the hub has no copy.

## 5. Release without a passed pilot

Evidence: handoff 17:04 allows three KV pilots and keeps 31 holds. The wave launched 22 KV rows at 16 h.
kit_wave.json shows 0 hold_items for KV at 17:50 (I did not find where the 31 holds are stored). The release
key was `event_adopt:kvgeom7yhr`, the previous event.
Root cause: holds release on an adoption event, and a pilot result is not part of the condition. A hold keyed
to event N is met when event N+1 reuses the die.
Fix (HOLD-FLOW-R): a die switch sets wave mode PILOT in the same atomic apply. In PILOT the wave launches only
rows in `pilots[]`; the mode ends when one pilot per kit class has passed gen and place. release_on keys name
the plan sha, not the event name. KV-R: re-hold the 19 non-pilot rows until D3 views are whole.

## 6. Loops that never converge

- s81_head: SRC-INCOMPLETE on epyc2 and "4 files copied" on 20 of 21 ticks. The tree is absent on epyc2; a
  4-file heal cannot make it whole. ADOPT-GUARD FIX "set plan_sha256" printed 20 times, never applied.
- s81: 655 files copied to epyc2, 6 times.
- hbm (parked): 40 alerts. HUB-SYNC-FAILED 14 (NOPROG.tsv).
Fix (FLEET-OPS-R): a self-heal runs at most twice per (host, tree); then the host leaves gen_hosts and one
NEEDS-ACTION is posted. HEAD-DIE-R: remove epyc2 from HEAD gen_hosts now and set the plan sha with the NF15b
atomic apply. Parked dies are skipped by ADOPT-GUARD.

## 7. Stale rows

202 current-event, doubled since 09:48. The owner column names KIT-WAVE-1 (107 rows), DIE-S81-90, FAIL-S81-1,
DIE-QC-97, HBM-CORES: none is in today's lane list, so all 202 have no live owner. The live check did not see
intel2, epyc4 and epyc8, so jobs on epyc8 (31 running) may be counted stale.
Fix (FLEET-OPS-R): OWNERS.tsv maps die and family to the -R lanes; a retired lane name is a load error.
RETIRE-SUPERSEDED also retires DEDUP members. The live check fails loudly when a live host is not seen.

## 8. Manual deletes and stale clones

Today: CLEAN-ALL hollowed trees (epyc7 220k files); a QC .git-only repo (6.1 GB) was deleted without the guard;
an inherited read-only git grep held 966 GB of deleted packs open on epyc8; a clean 49 GB worktree on epyc9 sat
until ENOSPC truncated private helpers.
Root cause: lane clones and worktrees have no lifetime. Each is a full copy, and its owner lane is gone.
Fix (FLEET-OPS-R): every clone is registered at creation (lane, host, path, branch). A registered clone that is
clean, pushed and without a process for 24 h is removed by `git worktree remove`, no ruling needed. Deletion
exists only as one guarded command; a raw rm under scratch is blocked by the hook. A process with deleted files
above 50 GB open is listed in the HOST-REPORT.

## 9. Merge gate and merge lane

E7 overfill: test_deps staged output-directory literals as inputs. Fix 0a5e17c9eb9 is GREEN and approved (r386).
MERGE-QUEUE-1 last post 13:09; ot-merge-queue.service was in "activating" at 17:50 and the timer is active, so
the service is the successor. Not verified: that it merged since 16:49. Approved and not seen merged at 17:04:
SVC 582420b (merged 56c2463 by 17:36), SerDes 8a971a5. Fix (FLEET-OPS-R): the service posts one line per train
(merged, refused, queue length), so a silent merge lane is visible within one train.

## Not checked

- Whether pid 70691 or an earlier run caused the 16:58 kills (earlyoom journal showed no kill lines to me).
- Where the 31 KV holds live; per-lane folder sizes; the epyc10 growth split between trees, binds and routes.
- FLOW-HEALTH.tsv has no hour-17 row yet. The QC "other flow error 26" class was not opened.
