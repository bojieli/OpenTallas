# FABLE-FLOW-1700: procedural and flow failures, 13:43-15:50 PST

Reviewer: FABLE-FLOW-1700 (Fable). Read-only: no deletes, no kills, no git in owner checkouts.
Measured 2026-11-17 15:43-15:55 PST on the hub clock (the brief's "15:00-17:00" is this window) on intel2 and the
6 build hosts. Sources: autopilot/log.txt 13:43-15:45 (758 lines), lanes/FLOW-HEALTH.tsv, failure_breakdown.py
(15:43), `ot-run --status`, rt/history.log, mq1 origin/main log, kit_wave.json, kit_wave_state.json, lane posts,
RULING r603-r624. Previous: FABLE-FLOW-1500. Shares are estimates from idle threads and item counts.
Not checked: AGIdock itself (count source), per-job thread-hours, the content of the 76 private wait loops.

## Headline

1. The wave has almost stopped launching. Launches per hour: 77 (12) -> 18 (13) -> 2 (14) -> 0 (15). 6 LAUNCH
   lines in the window (S81 5, KV 1, QC 0, HEAD 0), 3 SIGNED. UNDER-USE 15:41: 365 of 624 threads idle (42% used).
   Each die is stopped by a different process cause: QC adoption gap (D), S81 breaker + old tree (B, C), KV refresh
   not applied + D21b gate re-run (B, G), HEAD apply rebuilt 3 times (E, G).
2. The runtime is live everywhere, the die trees are not. rt/current = main 385e0de1caa3 (r624) on the hub and all
   6 hosts (15:44-15:45; 20 syncs since 14:12, none refused). No die tree has any fix after r582, and TOOLS-LAG
   cannot see r604, r616, r620, r622, r623 at all (B1).
3. tools_refresh is applied nowhere: 7 rulings (r605, r610, r612, r613, r615, r617, r624) and 3 starts in 95 min,
   0 trees switched.

## 1. Merged fixes: live and working?

| Ruling | Live in rt (7/7) | Working |
|---|---|---|
| r603 class release | yes, 14:12 | yes so far: kv3_hub_Wo last RELAUNCH-ON-FIX 13:52 (before merge), none after; 1 RELAUNCH-ON-FIX in window vs 12 items in 1500 |
| r604 cell cap, 3 points | yes | no evidence: 0 SPLIT-NEEDED lines; lanes/CELL-WAIVER.tsv has 0 rows. The preflight and native_cell_cap.tcl points live in the die tree, so only the enqueue point is live |
| r605..r624 tools_refresh | yes | NOT applied. KV = dry (compose + overlay 7/7 main-wins + guard OK, bind failed on a guessed recipe; second dry tree _t8569788 in progress, not on epyc9). QC = false. S81, HEAD, HBM = no key. Bind commands posted 15:39 by FABLE-FIX-KV-HG, HEAD-PLAN-R4, QC-PLAN-R3; no dies.<die>.tools_refresh_bind_cmd is in kit_wave.json |
| r611 rt prune refs | yes | hosts hold 43 snapshots each, hub holds 173. No prune loss seen. Hub count grows by 10/h |
| r618 ot_wait scope | yes, 15:31 | unused: 0 ot_wait.py processes on 7 machines; about 76 shell wait loops alive (loose pattern) |
| r621 gate selection | yes, 15:44 | not exercised yet |
| r622 tap print | rt only | no: tap_insertion.tcl is copied into kits by the die tree gen_phys; no die tree has it |
| r623 job.json env | rt only | no: ref_tile gen_job runs from lane clones / die trees |
| r616 S81 dup bb | rt only | no: S81 tree d5e lacks it; the 11 slice_C items fail again if relaunched |
| r620 PHY rows + rail check | rt only | only in hand kits that overlay it (HEAD sd9g3) |

Die trees: s81 d5e 289 commits behind, s81_head _pgr1_d1 261, qwen_kvsys d16 394, qwen_compute n1b_d2 394,
hbm 1048. TOOLS-LAG lists stop at r582 on every die.

## Classes, ranked by fleet time wasted

### A/B. Fixes do not reach kits (about 30%; trend flat since 1100, third review in a row)

- B1 (new root cause). tools_lag.py finds a ruling only when a commit MESSAGE names rNNN. Lanes commit before the
  ruling exists, and the merge commit says "COORD APPROVED" without the number. Checked: 24c494a (r604),
  25ac67b (r616), 0b5eafc (r620), 2236975 (r622), 040e6e3 (r623) carry no ruling id. So the refresh trigger and
  any FIX-NOT-IN-TREE hold are blind to every fix approved today.
  Fix (MERGE-QUEUE + WAVE-FLOW-R2): the merge commit records `Ruling: rNNN` taken from the RULING line that names
  the branch sha; tools_lag reads merge commits (git log -m --first-parent). Fallback: any commit on a die-tool
  path since the pin counts, named or not.
- B2. The refresher composes a full tree per main sha (26 min, 5-host replicate) while main moves every 5-10 min.
  Two KV dry trees already exist. Fix (WAVE-FLOW-R2): one refresh per die per hour at most, target = rt/current at
  start; set the three posted bind commands in kit_wave.json now, run KV true, then S81 (r616) and HEAD, QC last.
- B3. New plan trees are born stale: KV D21b is gated on tools 24c7347c (10:52), 5 h and r603-r624 behind.
  Fix (plan lanes + publish_gate): publish_gate reports TOOLS-LAG of the candidate and refuses a tree that lacks a
  ruling whose `fixes:` names its die; tools_refresh runs as the last step of apply.
- Structural end state (unchanged, 1300 and 1500): kits take tools from rt/current; the tree pins rtl + plan only.

### C. Same-class burst past the breaker (14 place fails; about 3%: 14 kits x about 2 h to a static verdict)

Count: KIT_PREFLIGHT @place 13 x "issues 4" (S81 dsdv_slice_*_C, duplicate_modules) + eng__t1, 13:43-15:03.
Other bursts: 9 AUTO-GEOM FAIL on KV-HG5 (design class, 14:03); breaker open on `qwen_kvsys|gen|PLAN ContractError`.
- Root cause 1: KIT_PREFLIGHT is a static check but its verdict comes from the place stage, about 2 h after
  launch. All 14 were in flight when the breaker opened (14:27:32, n=12).
- Root cause 2: the breaker released itself twice without a pass: 14:28:14 "the die's inputs changed" (42 s after
  opening; the change was a retry/overlay edit, not a fix) and 15:33:09 "probe gunit__t1 ran 60 min without a
  result: counts as a pass" (same form 13:44 for s81|kit_snap). The probe was not a member of the failing family.
- Root cause 3: r616 merged 15:10 but is not in d5e (class B), so a release relaunches the same failure.
- WAVE-PILOT-FIX retry-probe (claude/wave-pilot-fix3-1117): NOT merged, not on origin, no READY post.
  Its post also says rt/current stayed 24c7347c until 15:02; rt/history.log shows 13 hub switches 12:02-15:01.
- Fix (WAVE-PILOT-FIX): (1) run KIT_PREFLIGHT in gen, before enqueue, so the verdict takes minutes; (2) a class
  releases only on a probe PASS of an item from the failing family, never on a timeout; (3) "inputs changed"
  releases only when a part the class depends on changed (reuse r603 release_parts) and the tree contains the
  fixing ruling; (4) land retry-probe (3 in flight per cohort).

### D. Adoption gap, QC N1B (about 10%: QC 0 launches for 65 min and counting; 90 superseded-event rows)

- 14:40 apply set gen_hosts = [epyc9] (apply narrows gen_hosts to where the tree is). 14:47-15:27, 8 ticks:
  WORK-ROOT "src/plan inputs incomplete on every gen host": the wave looked for files under
  kw45/src_qc_pin_eb1e73448bd0_s4q9n1b (the name before the _d2 rename; class G). Since 15:3x gen_hosts =
  [epyc9, epyc8]; N1B is on epyc8 + epyc9 only. 27 running rows were REKEYed; RETIRE-SUPERSEDED relaunch-on-current
  = 1; the rest of the 123 types have no N1B row.
- Fix (QC-PLAN-R3 for the tree today; WAVE-FLOW-R2 for the tool): apply_reviewed_tree_marker self-replicates to
  every gen host of the die before the locked write (src_manifest replicate + verify --ro) and refuses with the
  host list when one fails; it never narrows gen_hosts without --keep-gen-hosts. On adopt the wave creates the
  current-event rows for every type of the plan in the same tick (ADOPT-ROWS n/n line) and alerts when
  rows < plan types after 2 ticks.

### E. Hand-launch drift (about 3%: 6 svc runs, HEAD rs8 30-75 min, HEAD tree build 3 attempts, KV dry pass 1)

- svc split: launcher lacked OT_ROUTE_HOLD_CORNERS=mm, 6 runs died at CTS. r623 fixes job.json, but only for kits
  generated by a tree that has r623 (class B).
- HEAD rs8: ot-run ISOLATION refusal (plan outside --dir) unseen; then "attempt 1 failed in 3 s (plan copy outside
  its dir)" again at 15:23, and the tree build failed twice (partial clone, wrong assertion; attempt 1 ran on past
  the failed step).
- Root cause: a refusal is a log line, and each lane has its own wait loop that watches for a file, not a state.
- Fix (FLEET-OPS-R): ot-run exits non-zero and prints one line `OT-RUN NOT-RUN <reason>` on stdout for every
  refusal, and posts it to the lane named by --lane; `ot-run --wait` (ot_wait inside) is the only supported wait
  and returns NOT-RUN at once. Lane hook refuses new `while ... is-active|pgrep|sleep` scripts. `ot-run --kit DIR`
  launches a stage from job.json only (no hand env).

### F. Signed record with a PHY rail defect (1 record now; every signed PHY-region type is exposed)

- hd_serdes sd9f: rows 5671, bad 3047. Posted SUSPECT 15:20; lanes/COUNT-REVOKED.tsv has no sd9f row, so it still
  counts. KV kv3_sys_c has no signed record. S81 serdes: 11 held.
- Fix (HEAD-TYPES-R4 today; WAVE-FLOW-R2 tool): the count stays "AGIdock records minus COUNT-REVOKED rows keyed by
  sha256". Add one row for sd9f (reason r620, pg_rail_check.json path). Archive files are never edited. A revoked
  record returns only through a NEW signed record of the type. Make it self-acting: a sweep runs pg_rail_check on
  the routed DB of every signed type with a PHY supply region and writes the rows; any new blocking checker
  ruling must name its sweep over signed records.

### G. Stale tree names inside artifacts (4 cases in 2 h; about 4%, mostly gate re-runs)

sd9f plan -> pruned NF15d2 tree (_pgr1, not _pgr1_d1); QC wave -> _s4q9n1b, not _d2 (40 min of QC); KV D21 bind.f
embeds the pre-rename path in 22 lines (70 min gate re-run); HEAD NF15f prep, 4 files name the NF15d2 tree
(plan sha changed 65606a72 -> 366b0c00). Also HOLD-TERMS: 2 holds wait on event NF15c that no one plans.
- Root cause: absolute kw45/src_* paths are written into bind out, plan prep and kit lists, then trees are
  renamed (_dN) or pruned.
- Fix (WAVE-FLOW-R2 + plan lanes): tree-relative paths in bind.f / prep (resolved from the tree root);
  publish_gate fails a tree or bind out that contains a kw45/src_* string other than its own root; trees are
  never renamed after the first gate step (a fix is a new tree); the delete guard keeps a tree that a signed
  record's rebuild plan names until the record is re-pointed.

### H. Release on merge while the tree pins old tools (0 lost; caught by hand once)

- The two S81 serdes holds (11 + 6 items) still release on result:FABLE-FIX-S81-SERDES2:rail-gen alone. The
  second term asked at 15:36 is not in kit_wave.json at 15:50. Only the lane withholding its post protects it.
- Answer: "release when a fix merges" is NOT safe. A merge changes rt, a kit is generated by the die tree.
- Fix (WAVE-FLOW-R2): a release term `ruling:rNNN` is true only when the die's current tree contains that
  ruling's commits (tools_lag); `result:` terms for generator fixes are refused by hold validation unless paired
  with one. S81-TYPES-R3: add the h-form term now.

### I. Disk and admission (about 4%)

localhost REFUSED (131 < 150 GB); epyc7 --dir only (root 72 < 150). epyc2 scratch2 73 GB, falling 34 GB/h (floor in
under 1 h), AUTO-RETIRE deleted 0. Lane quota alerts repeat with nothing stopped: kw45 epyc9 306 GB/6 h, epyc8
188, wave-src epyc7 170. Hub rt 173 snapshots. Fix (FLEET-OPS-R): quota breach stops that lane's new launches on
that host; dry refresh trees are deleted when the next one publishes; hub rt prune to the host rule.

### J. Stale rows

Stale current-event 122 (1500: 121): S81 5, QC 23, HBM 107. Unowned 16 (QC 5, HBM 11). NOPROG-DRIFT: noprog_stage.py
differs from main on all 7 hosts.

## Do now

1. WAVE-FLOW-R2: put the 3 posted bind commands in kit_wave.json, KV true, then S81 and HEAD refresh; B1 fix with
   MERGE-QUEUE (ruling id in the merge commit).
2. QC-PLAN-R3: N1B on every QC gen host; confirm N1B rows exist for all plan types. WAVE-FLOW-R2: apply
   self-replicates, adopt creates rows.
3. WAVE-PILOT-FIX: READY for retry-probe; no release on probe timeout; preflight at gen.
4. HEAD-TYPES-R4: COUNT-REVOKED row for sd9f. WAVE-FLOW-R2: rail-check sweep over signed PHY types.
5. S81-TYPES-R3: second release term on both serdes holds. WAVE-FLOW-R2: `ruling:` release term.
6. FLEET-OPS-R: ot-run NOT-RUN exit + post, `ot-run --wait`; quota stop; epyc2 scratch2.
7. Plan lanes: no tree rename after gate start; publish_gate foreign-tree-path check.
