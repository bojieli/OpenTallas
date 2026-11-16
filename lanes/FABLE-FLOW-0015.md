# FABLE-FLOW-0015: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 23:44-23:58 PST on hub intel2.
Window: autopilot/log.txt 21:45-23:45 PST (5,506 lines), lanes/FLOW-HEALTH.tsv (written 22:29), kit_wave.json
and kit_wave_state.json (23:47), tools/failure_breakdown.py (23:45), `ot-run --status` (23:45), df and load on
6 build hosts (23:49), lane posts 22:00-23:50 incl. rulings r239-r250.
Previous review: FABLE-FLOW-2200 (window 19:45-21:45). Scope: process and tooling only.

## Headline

1. Launch volume is back: 190 launches (was 39), 32 fails (was 19). S81 149 launches, 11 fails. Idle build
   threads fell from about 45% to about 18%.
2. KV is still at zero useful launches, now for about 8 h. It was adopted twice in this window and both
   adopts were broken by the bind output: 13 launches, 12 kit_rtl fails (22:33-23:13), then 0 launches since
   23:26 because the wave reports the source incomplete on every gen host. The second break is live now and
   no post names it.
3. r249 (23:46) says the S81, QC and HEAD wave trees lack the code that reads OT_PG_DIE_PHASE and
   OT_TT_SETUP_REPAIR, so those config keys did nothing. 177 launches in this window ran on those trees.
4. The lane stop left four things half-done: the KV 7uh switch (not checked by a launch), FLOW-HEALTH.tsv
   (last written 22:29), the tool_skew and holdgen branches (READY, not in the runtime), and a new
   `tree_switch` hold on S81 and QC whose release waits on one lane.

## Kit wave, 21:45-23:45

| | 21:45-22:45 | 22:45-23:45 | 2 h | FABLE-FLOW-2200 |
|---|---|---|---|---|
| LAUNCH | 78 | 112 | 190 (S81 149, QC 24, KV 13, HEAD 4) | 39 |
| FAIL | 9 | 23 | 32 (KV 12, S81 11, QC 9) | 19 |
| ENQUEUE (place done) | | | 15 | 25 |

Repeats: 28 distinct items for 32 fails, so 4 fails (12%) are repeats; was 10 of 19 (53%).
S81 launches by 10 minutes from 22:30: 41, 43, 34, 17, 8, 3, 3.

| Count | Die | Stage | Cause | State at 23:47 |
|---|---|---|---|---|
| 11 | KV | kit_rtl | filelist paths outside the kit source tree: `bind_out` was bound in the old kv102t18 tree while `src` was c1 | config moved to 7uh at about 23:2x; see class 1 |
| 1 | KV | kit_rtl | kv3_hub_C: leaf module qkd_ahub has no source in the bind | KV-102, r249 item 7 |
| 3 | QC | kit_rtl | KIT_NOT_SELF_CONTAINED on a kit-store snapshot path (22:13) | snaphost fix merged; strict is on again |
| 3 | S81 | pipeline | ssh timeout epyc7 -> epyc10 while copying a kit snapshot (23:43) | typed FLOW design:pipeline; it is infra |
| 2 | S81 | kit_snap | slice_station__t51: 8 kit files named by child views exist on no host | failed, relaunched on "changed tools", failed again |
| 2 | S81 | prov_views | view input missing (one path on epyc4, a host held for drain) | open |
| 4 | S81 | place | preflight 2, FT site off grid 1, landing band 1 | design or kit recipe, owners named by fail_route |
| 5 | QC | gen, gen_lint, kit_topology | plan contract 1, RTL lint 2, kit_istations 2 | design or plan |
| 1 | QC | place | native59 killed by earlyoom on epyc9 (22:03, host memory 3% free) after 23.5 h | retried on another host |

## FABLE-FLOW-2200 fixes: did they land

| Class in 2200 | State | Evidence |
|---|---|---|
| 1 adopt by hand edit | partly | S81 adopted on B6gG3b (149 launches). KV adopted twice, both broken. No one-step adopt command |
| 2 host disk | better | epyc7 scratch2 736 GB free (was 0.5); runtime equal on 7 hosts per KIT-OPS-5. epyc7 root fs 119 GB is under the 150 GB floor, so jobs without `--dir` are refused there. I found no 5-minute df table |
| 3 kit_snap against self-contained | landed | snaphost @6b4ee351b58 on main; no KIT_NOT_SELF_CONTAINED after 22:13. Two new kit_snap fail forms (rows 4 and 5 above) |
| 4 relaunch of known-failing rows | working | 27 fail keys, 3 LAUNCH-REFUSED, 5 RELAUNCH-ON-FIX. One over-release, class 5 |
| 5 typed classes | landed | FAIL lines carry `FLOW[design:kit_rtl]`, `INFRA[missing_input]` from 22:33. 14 of 32 still read "unclassified failure" |
| 6 tool_skew wording and coverage | not landed | 25 "TOOL-SKEW refuse" lines, 0 "WARN" lines; skew2 @87ba593cd35 READY since 22:31 |
| 7 config does not reach the kit | worse | r249, class 2 below |
| 8 periodic jobs failing each tick | mixed | ADOPT-GUARD 0 (was 24); SRC-INCOMPLETE 15, now KV on 5 hosts (was epyc2); ARCHIVE FAILED 7 on one record; HUB-SYNC-FAILED 2 |
| 9 stale and unowned | better | STALE 205 current (+155 superseded), was 271 (+158). Unowned unchanged: S81 198, QC 11, KV 8, HBM 11 |
| HOLDGEN | partly | per-tick HOLD-AUDIT line exists (7 ticks, all four counters 0). convert @1bc11db1ab4 READY, not merged |

## Summary, ranked by waste

| # | Class | Count | Trend | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Bind output carries absolute paths of the tree it was made in | KV: 11 fails, then 0 launches from 23:26 | same die, second form | KV die 100% for 8 h; under 1% of CPU | KIT-OPS-5, KV-102 |
| 2 | Config key with no reader in the die tree | 177 launches on 3 dies | worse (was 4 HEAD rows) | S81 holds 105 of 118 RUNNING wave rows; about 40% of the 264 running jobs are at risk of a rebuild | TOOLS-CONVERGE-1115, KIT-OPS-5 |
| 3 | Hold released only by a lane post | `tree_switch` on S81 and QC from 23:47 | recurs (2200 class 1) | none yet; S81 and QC stop launching until the trees arrive | WAVE-HOLDS-1115, HOLDGEN-1115 |
| 4 | Ready branches wait for the runtime | skew2 76 min, holdgen 72 min | same | none directly | MERGE-QUEUE-1 |
| 5 | Fail key released by any tool change | 1 item, 2 identical fails | new | under 1% | FLOW-HEALTH-1 |
| 6 | Infra failure typed as design | 3 ssh timeouts, 1 OOM after 23.5 h | new | one 23.5 h LEC job lost | KIT-OPS-5 |
| 7 | Serial launch makes long ticks | 2 ticks of 1,416 s and 968 s | new | none; fail detection late by up to 24 min | KIT-OPS-5 |
| 8 | Health tables measure old trees | SKEW section lists S81 B6gE and KV 7u | new | none | FLOW-HEALTH-1 |
| 9 | Rows that never reach a terminal state | 23 S81 DEDUP rows released each tick; 1 archive record retried 7 times | same | none; 670 of 5,506 log lines | FLOW-HEALTH-1, CLEAN-ALL-1115 |
| 10 | Hand-typed post times | KIT-OPS-5 posts stamped 24:0x, 24:2x, 24:4x | new | none | KIT-OPS-5 |

## 1. Bind output names the tree it was made in

First form, 22:23-23:13. r239 moved the KV `src` to kw45/src_kv_kvgeom7u_c1. `kit_rtl.bind_out`, `plan` and
`asbuilt` stayed on the old tree. The bind filelists name kw45/kv102t18_kvgeom7u/rtl/..., kit_rtl rejects
them, 11 of 13 launches fail. KV-102 found it at 23:11.

Second form, live. KIT-OPS-5 moved all four paths to the 7uh tree (commit c33142707cf4) and posted that
everything is present on six hosts. Since 23:26 every tick logs
`WORK-ROOT qwen_kvsys: src/plan inputs incomplete on every gen host`, naming
`/srv/opentallas-scratch3/claude/kw45/src_kv_kvgeom7uh_c1/...`. I checked on epyc10:
`kvbind_kvgeom7uh_c1/out_h1/bind.f` and `bind_report.json` contain scratch3 paths. The tree exists at scratch2
on all hosts and at scratch3 only on epyc2, where the bind ran; epyc2 is not a KV gen host. KV launches: 0.

Root cause: bind writes absolute source paths, so a bind is valid only at the path and host where it ran.
The "present on all hosts" check tested the four config paths, not the paths inside the bind.
Fix now (KIT-OPS-5 or KV-102): re-bind from the scratch2 path, or rewrite the prefix in out_h1.
Structural fix: bind writes paths relative to the source root and records the tree's content sha; kit_rtl
resolves them against the wave `src`. The adopt check then is one rule: the sha recorded in the bind equals
the sha of `src`. An adopt counts as done when one row passes kit_rtl, not when the config is pushed.

## 2. Config key with no reader in the die tree

r249: die_gen_env sets OT_PG_DIE_PHASE and OT_TT_SETUP_REPAIR, and the S81 B6gG3b/src, QC qc-s29-tree2 and
HEAD c327 trees have no code that reads them. The tool_skew gate reports S81 191, QC 139, HEAD 153 and KV 45
modules different from main, in `warn` mode, and the launches went on: S81 149, QC 24, HEAD 4. Whether the
105 running S81 rows are kept is a design ruling (r249 lets them finish); the process fault is that the
config accepted keys that could not act, for the second review in a row.

Root cause: a die tree is cut from main at one sha and config keys are added later from a newer main. Nothing
ties a key to the code that consumes it.
Fix (TOOLS-CONVERGE-1115): at config load, each key in die_gen_env and item_env must occur as a string in
the die tree's tools/die_plan; a key with no reader refuses launches for that die and posts once. This is
exact, cheap, and needs no module diff. Keep the module-count gate in `warn`.
Fix (KIT-OPS-5): the same "one fresh kit" check r249 asks for after a switch (pdn.tcl offset, repair script
present) runs after every config commit that adds an env key.

## 3. Hold released only by a lane post

Commit eb277e6e0d4 (23:47) holds new S81 and QC launches under `tree_switch:<die>` until TOOLS-CONVERGE
posts each tree. The stop at 23:2x-23:44 shows the risk: if that lane does not come back, two dies launch
nothing and the hold audit reads 0 on every counter, because the term is reachable in principle.
Fix (HOLDGEN-1115): a hold whose term is a lane action carries the lane name and a deadline; the per-tick
audit adds a counter OWNER-SILENT for holds whose owner has not posted for 60 min, and fail_route sends one
NEEDS-LANE. COORD confirms at this resume that TOOLS-CONVERGE-1115 is running the three builds.

## 4. Ready branches wait for the runtime

claude/tools-converge-1115-skew2 READY 22:31 and claude/holdgen-1115-1115b READY 22:35 (posted again 23:47)
are not in the runtime at 23:47; typedclass, snaphost and kitpack merged within 30 to 60 min. I did not read
the queue state file, so I cannot say whether these two wait on approval or on a gate.
Fix (MERGE-QUEUE-1): one table per tick, branch, READY time, state, reason; a READY older than 45 min
without a ruling goes to COORD once.

## 5. Fail key released by any tool change

slice_station__t51 failed at 23:25 with KIT_INPUT_MISSING, was refused at 23:27 (key unchanged), was
released at 23:34 as "changed tools" after a runtime sync, and failed the same way at 23:43. Four other
RELAUNCH-ON-FIX rows had a real overlay change.
Fix (FLOW-HEALTH-1): for class `missing_input` the key is the list of missing paths; it releases when one
of them exists. Tool hashes release only `design:<stage>` keys of the stage whose import closure changed.

## 6. Infra failure typed as design

Three S81 rows failed at 23:43 on `TimeoutExpired` of a nested ssh (epyc7 to epyc10, snapshot copy). The
class is `FLOW[design:pipeline]`, so the fail key will refuse a relaunch that would pass. native59 lost
23.5 h to earlyoom on epyc9; `ot-run --status` shows reserve 0 and peak 0 on every host, and load 186 on 96
threads on epyc9.
Fix (KIT-OPS-5): a timeout or rc 255 of a transport command is `INFRA[transport]`, retried on another host,
never keyed. Snapshot copies go hub to host, not host to host. Admission: a job older than 6 h is exempt
from earlyoom (oom_score_adj) and the newest job on the host is the victim.

## 7. Serial launch

Ticks at 22:55 and 23:12 took 1,416 s and 968 s, of which kit_wave_step 1,322 s and 868 s: about 10 s per
launch, one at a time. The timer period is 10 min, so polls and fail lines came up to 24 min late.
Fix (KIT-OPS-5): launch through a pool of 8, or cap the launch phase at 5 min and continue next tick.

## 8. Health tables measure old trees

lanes/FLOW-HEALTH.tsv was last written 22:29. Its SKEW section (22:07) lists S81 .../B6gE/src and KV
kw45/src_kv_kvgeom7u; the wave runs B6gG3b/src and src_kv_kvgeom7uh_c1. Its cross-host compare reports "ok".
Fix (FLOW-HEALTH-1): read the tree list from kit_wave.json at run time; run from a timer, not from a lane.

## 9. Rows with no terminal state

- 23 S81 col rows get "DEDUP RELEASE ... relaunches on the normal path" on every tick (29 ticks, 670 lines)
  and have not relaunched for 31 to 42 h. STALE lists them unowned.
- ARCHIVE FAILED 3054c87a89d6 (hd_spn_eshim_rx attempt_3, event head_rp21z4_1113) retries each tick on a
  path that no longer exists.
Fix: a released DEDUP row either launches in that tick or takes a typed hold naming why; an archive whose
source is missing on all hosts goes to LOST after 2 tries and posts once.

## 10. Post times

KIT-OPS-5 posts carry 24:0x, 24:2x and 24:4x. Sorted by time they follow every other post, and the pair
"epyc7 removed from gen_hosts" and "epyc7 back" reads in the wrong order next to the 23:5x post.
Fix: post.sh stamps the time; a typed time in the text is dropped.

## Other state at the resume

- HUB-SYNC-FAILED 23:12-23:42: lanes/NOPROG.tsv edited in the hub checkout by the noprog timer and not
  committed. It cleared at 23:42. The timer should commit through coord-commit.sh.
- QC moved to event S4Q6D at about 23:3x; 18 old-event units run to the end and 4 SKIP-OLDPLAN lines show
  their results are dropped. First S4Q6D launches at 23:45 (3 rows).
- Disk free: epyc2 139 GB, intel1 254 GB, hub 208 GB, epyc7 736 GB, epyc8 908 GB, epyc9 1,194 GB,
  epyc10 4,129 GB. No wave launch was refused for disk in the window.
- 9 temporary state files from 11-03 to 11-15 sit in the hub checkout (autopilot/.state.json.*,
  STALLS.txt.tmp.*). Not from this stop.

## Not checked

- The merge queue state file and why skew2 and holdgen are not merged.
- Whether epyc7's ssh limit or load caused the three timeouts.
- The kit_rtl logs of the 14 S81 kit_rtl FAIL rows from 14:01 (KIT-OPS-5 says bind.py predates --src-tree).
- intel2 and epyc4 are not seen by the STALE live check.
