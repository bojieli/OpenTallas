# FABLE-FLOW-1800: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 17:44-18:10 PST on hub intel2.
Window: autopilot/log.txt 15:45-17:45 PST (plus 17:45-18:07 where stated), lanes/FLOW-HEALTH.tsv (17:22),
lanes/NOPROG.tsv (17:37), kit_wave.json (17:51) + kit_wave_state.json (17:44), failure_breakdown.py (17:49),
`ot-run --status` (17:50), df on 7 hosts, queue lines r178-r195. Scope: process and tooling only.
Previous review: FABLE-FLOW-1600.

## Headline

1. 99 launches in 2 h, 88 fails, 86 of them before P&R. About 10 of the 99 reached geom/place/route, all QC.
   S81: 56 launches, 56 fails at gen. KV: 24 launches, 24 fails at kit_rtl. No S81 or KV launch of this window
   reached placement.
2. Both big classes were launched twice or three times on a cause nobody had fixed. The wave files a
   deterministic tool error (sdc_lint refusal, TypeError, AttributeError) as INFRA and retries it: 22 of the 32
   failed S81 items were launched 2 times, 9 of the 10 KV items 2-3 times. 46 of the 88 fails are repeat launches.
3. The class breaker merged at 15:54 (flow-health-1115b) and opened 0 times through 56 S81 and 24 KV fails of
   one class each. Both classes were stopped by hand: S81 by list at 16:30 (38 min after the first fail), KV by a
   die hold at 17:35 (51 min after the first fail).
4. Launch rate fell to 4 in hour 17. S81 waits on G1d (gate failed 15:36 on a bind overlay without the new
   schema keys, seen 1.5 h later), KV waits on a tree that is not consistent in itself, QC binds fail on another
   lane's rows. Three plan gates are blocked by process, not by design.
5. Fleet at 17:50: epyc2 28/128, epyc7 58/96, epyc8 57/96 threads loaded; intel1 192/112, epyc9 122/96,
   epyc10 145/96. About 175 of 624 build threads idle (28%) while three hosts are over their thread count.

Closed since 16:00: `--src-tree` (0 fails), param_wrap port table (6 fails, fix merged 16:56), merge queue
throughput (19 MERGED, 1 MERGE-FAIL, 1 BOUNCE in 2 h; was 4 per hour), signed-terminal (merged 16:09;
SIGNED-UNVERSIONED 13 -> 3 lines, 0 relaunch refusals), test watcher leak (merged 16:08), ot-run drift (merged
16:52), hub scratch (131 -> 161 GB), no-progress classifier (installed 16:40, no exclusions).

## Kit wave, 15:45-17:45

| 10-min bucket | 15:4x | 15:5x | 16:0x | 16:1x | 16:2x | 16:3x | 16:4x | 16:5x | 17:0x | 17:1x | 17:2x | 17:3x |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LAUNCH | 31 | 4 | 29 | 3 | 1 | 12 | 5 | 10 | 0 | 1 | 0 | 3 |
| FAIL | 0 | 4 | 30 | 4 | 21 | 2 | 6 | 10 | 5 | 4 | 0 | 2 |

2 h totals: LAUNCH 99 (S81 56, KV 24, QC 19, HEAD 0), FAIL 88. FABLE-FLOW-1600: 162 / 259. 13:50: 120 / 212.
Launches per hour: 50 (81 at 16:00, 60 at 13:50). FLOW-HEALTH.tsv: hour 16 launches 60, fail before P&R 73,
passes 0; hour 17 launches 0, fail before P&R 5, preflight refused 3. Passes in both hours: 0.

| Count | Die | Stage | Class | State at 18:05 |
|---|---|---|---|---|
| 56 | S81 | gen | sdc_lint: SDC clock window outside plan clock.tap_window (32 items; 22 twice, 1 three times) | held by list 16:30 (336 types), release on G1d adopt / Event F |
| 24 | KV | kit_rtl | TypeError core_tap_early_ps (16), AttributeError reset_tree.pin_root_copies (8); 10 items, 9 of them 2-3 times | die hold 17:35; tree defect, owner KV-102 (r195) |
| 6 | QC | kit_rtl | param_wrap: base without a port table (2 items x 3) | fixed, merged 16:56 |
| 1 | QC | gen | KIT_NOT_SELF_CONTAINED (slw_st_a_v2__cl9f076a5c; again at 17:53, relaunched 17:55) | open, see class 2 |
| 1 | QC | place | pre-route LEC not equivalent (glue) | design/RTL, not in scope |

Stage reached by the attempts started after 15:45 (kit_wave_state, latest attempt per item, 56 rows):
S81 gen 25 + kit_rtl 7 (all FAIL or RETRY-INFRA), KV kit_rtl 10 (all FAIL or RETRY-INFRA), QC geom-enqueued 5,
place 2, gen/kit_rtl 4 (1 FAIL), HEAD place 3 (launched 17:55 on NF12). Share of the 99 window launches that
reached P&R or its queue: 7 to 12 (QC only), about 10%.

## Summary, ranked by waste

| # | Class | Count | Trend vs 16:00 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Plan gates blocked by process (S81 G1d overlay + cleaned input + silent waiter; QC foreign rows; KV tree) | 3 dies, 5 failed gate runs | new | the cause of hour 17 at 4 launches; about 28% of threads idle | new Sonnet lane PLAN-GATE-PRE-1115; die owners |
| 2 | Deterministic tool error filed as INFRA and retried | 46 of 88 fails are repeats | new reading (was hidden in class 4 of 16:00) | about 45 gen/kit_rtl runs, under 1% CPU; it doubles every burst | FLOW-HEALTH-1 |
| 3 | Class breaker merged but never opens | 0 opens, 2 classes of 56 and 24 | open, fourth review | 38 + 51 min of hand reaction | FLOW-HEALTH-1 |
| 4 | Source tree built from mixed vintages (KV 7u), staged path by path | 8 SRC-INCOMPLETE lines (15 at 16:00), 24 fails, 1 PREFLIGHT-SKEW refusal | SRC-INCOMPLETE closed 16:13; next layer opened 16:39 | KV wave at 0 passes since 15:24 (2 h 40 min) | KV-102 (tree), KIT-OPS-5 (guard) |
| 5 | Holds added one fail at a time; hold table grows | S81 481 hold keys (352 at 16:00), KV `*`, QC 50, HBM `*` | worse | S81: 40 of 394 types signed, 3 running | WAVE-HOLDS-1115 |
| 6 | Host imbalance: epyc2 out of the gen set | epyc2 22% loaded, scratch 59-88 GB against the 70 GB floor, 4 GEN-DISK-LOW lines; kit_topology symlink path | new | 100 threads, 16% of the fleet | KIT-OPS-5 (install WAVE-PREPNR patch), CLEAN-ALL-1115 |
| 7 | Sync and cleanup remove live plan inputs | 1 rsync --delete (4 plan files), 1 cleaned elab input (hard_params.json), CLEAN freed 0 GB on epyc2 | new this window, third time this week | 1 failed elab + 1.5 h of G1d | CLEAN-ALL-1115 |
| 8 | SDC-only plan deltas switch the whole wave event | HEAD NF6 -> NF10 -> NF11 -> NF12 in 49 min | new | 3 re-keys of 26 types; small | KIT-OPS-5 |
| 9 | No-progress table is advisory and unread | 6 SLOW, 0 NO-PROGRESS; 2 containers 18.7 h without a stage log | better (was 38 unjudged) | about 2% | FLOW-HEALTH-1 |
| 10 | Gate runner leaves processes and clones | 3 yosys + lec_async 2 h old in deleted gc-* trees on epyc2; slot0 clone 29 GB | falling (was 36 watchers) | 0 CPU; 29 GB of the epyc2 shortfall | MERGE-QUEUE-1 |
| 11 | Bookkeeping | STALE 174 current (+137 superseded); S81 unowned 186; kit_wave_blocked.tsv empty since 08:14 | worse (141; 144) | none | FLOW-HEALTH-1 |

## 1. Plan gates blocked by process

Measured, three dies in this window:

- S81 G1d: compose passed (0 placement failures, 0 landing errors). The gate failed at 15:36 in the bind tree:
  G0 17 errors "unknown key band_fixed_um / band_tap_windows_um" because overlay ovl_b6E carried the B6gE schema
  and the compose tree carried the BANDTAP schema; and ELAB_RC=1 FileNotFoundError on
  col_h9_l4_lp_kit_vg_romq_split.hard_params.json, a file a cleanup had removed. The waiter wrote the triage at
  15:36; the owner read it at about 17:0x. 336 S81 types and the whole sdc_lint class release on this adopt.
- QC S4q6b and S4q7c: both rebinds failed with ERRORS 2 after a full bind each. One error is the same in both and
  in the row lane's own rebind: "EMIT control reset localization ... emitted/published reset edge mismatch". At
  18:00 QC-SC-ROWS withdrew the rows for all 9 types: no row can pass under the present bind precedence. The rows
  were posted READY and merged into two plan events before their own bind result existed.
- QC bind hosts: the bind on epyc2 stopped at once with rc 9 "not a git tree". The plan trees are whole only on
  epyc9 (64 GB git dir). One host can bind QC; a 2-bind cap already queued S4q7d.
- KV 7u: see class 4. The adopt at 15:24 had a passing bind and a tree whose own bind.py cannot run kit_rtl.

Root cause in the process: a plan gate is run on a hand-assembled tree (compose tree, bind overlay, rows of other
lanes, staged tools). Nothing compares the parts before the 1-2 h bind starts, and the result goes to a file that
only the launching lane reads.

Structural fix (new Sonnet lane PLAN-GATE-PRE-1115, one tool `plan_gate_pre.py`, run by ot-run `--priority plan`
before every bind/G0/elab; it is a precondition check of minutes, not a limit on a design run):
- Schema closure: every key of the composed plan and sidecar must validate against the schema.py of the BIND tree.
  An unknown key stops the launch in seconds and names the overlay. The G1d miss cannot repeat.
- Input closure: every path the elab/bind manifest names exists on the bind host. Missing files are listed before
  launch. CLEAN-ALL reads the same manifest list as a keep set (class 7).
- Rows from another lane carry a `ROWS-PROOF` line: the row lane's dry-run of the consumer check on EMITTED bind
  RTL (the check QC-SC-ROWS ran only at 18:00, 9/9 rejects in minutes). rows_apply refuses rows without it.
- The bind reads its source identity from a manifest sha file, not from `git rev-parse`. Then a bind tree is a
  plain directory and can be on every gen host (owner rule: never pin). KIT-OPS-5 owns the copy.
- Waiter results: every waiter ends with `post.sh <LANE> "RESULT ..."` or `"FAILED ..."`. The autopilot loop-gap
  scan lists plan-priority units that ended without a queue line within 10 min as `PLAN-GATE-SILENT <die> <unit>`.
  A failed gate is then on the queue in the same tick, not after 1.5 h.

## 2. Deterministic tool errors are retried as INFRA

Measured: the classifier names SdcLintError, TypeError, AttributeError "INFRA: python exception / plan-schema
refusal in the kit tool: tool or source skew" and gives the row RETRY-INFRA. S81: 28 launches 15:46-15:48, 30
fails at 16:0x, 27 launches at 16:0x (same items), 20 fails at 16:2x. KV: 10 items launched 10 + 5 + 9 times in
three ticks. At 17:44 22 S81 gen rows and 4 KV rows still stand at RETRY-INFRA and launch again when their hold
lifts, whatever the cause. KIT_NOT_SELF_CONTAINED on slw_st_a_v2__cl9f076a5c is at attempt 10 (failed 17:33,
17:53, relaunched 17:55).

This is why the S81 class "kept appearing one by one": half of the new fail lines were second attempts.

Structural fix (FLOW-HEALTH-1): INFRA retry needs evidence that the cause is outside the kit inputs (host, disk,
OOM, docker, ssh). A Python exception from a kit tool, a lint refusal, a schema refusal and
KIT_NOT_SELF_CONTAINED are functions of (tool sha, src tree sha, plan sha, item). Class them TOOL-DET and key the
retry on that digest: the row relaunches when one of the three shas changes and never before. The digest is
already computed for the "relaunch refused: inputs equal" rule on resumes; apply it at first launch too. This is
self-stopping and needs no hold and no limit on a design run.

## 3. The class breaker does not open

Measured: flow_guard is in rt/current (kit_wave.py lines 6843-6970, 8373). Log 15:45-18:07: 0 CLASS-BREAKER
lines. FLOW-HEALTH.tsv breakers_open is empty for hours 16 and 17. kit_wave_state flow_guard: open 0, fails 2,
fails2 3, the oldest entry at 17:33. kit_wave_blocked.tsv has only its header (file of 08:14) although the 16:23
log line says "listed in kit_wave_blocked.tsv".

Not proven here which of these holds: the fail records were reset at 17:3x by a restart, the class key keeps the
type name (each sdc_lint message starts "type <name>"), or the window is shorter than the tick spacing. I did not
read flow_guard.py.

Fix (FLOW-HEALTH-1, this hour): replay the 15:45-17:45 log through flow_guard in a test; the test must open the
breaker on S81|gen|sdc_lint after 10 fails and on KV|kit_rtl|TypeError after 10. Normalise type and item names in
the key. Persist the fail list across restarts. Write kit_wave_blocked.tsv from the same state. Until this
passes, class 5 stays hand work.

## 4. KV 7u: a source tree of mixed vintages

Sequence: 15:24 adopt, 0 whole gen hosts (FABLE-FLOW-1600 class 2). Paths staged per tick until 16:13 (8 more
SRC-INCOMPLETE lines, last 16:04). 16:39 first launches: 24 fails in 40 min. 16:55 PREFLIGHT-SKEW "gen_phys.py: No
module named rck_island" (1 row). 17:32 KITRTL-FAIL: the tree's own bind.py fails the same way with no staging:
its gen_phys.py is a main copy of 15:15 on the tree's older schema.py; with main schema.py the next error is
missing PCC/PCF leaf sources; reset_tree.py is older than bind.py. r195 gives the rebuild to KV-102.

Per-instance pattern: yes. Four layers were found by launching the wave (paths, gate_events_extra, staged tool
mix, tree defect), each fixed alone, each costing a tick or a burst. kitrtl-fail-1115c (READY 18:05) adds a
retry with the tree's own bind.py on an API-skew error; by the lane's own post it does not fix this tree, and it
is one more per-instance layer.

Structural fix:
- KV-102 / every die owner: a src tree is created by one command from ONE tools sha plus a row list
  (`make_src_tree --tools-sha X --rows ...`), and records that sha in the tree. No file copied in by hand.
- KIT-OPS-5, in adopt_guard (r154 tool_smoke exists): the smoke runs the full kit_rtl + gen phys for ONE type per
  family on the adopted tree, on two gen hosts, before the wave config commit. FLOW-HEALTH's SKEW section already
  computes the 227-module closure against main per tree; add "closure consistent with ONE sha" as a refusal for a
  new adopt (old trees keep running). An adopt that cannot build one kit is then not committable.
- Drop kit_tools mixing as a repair: main tools on an old tree is the source of both KV errors. A tree is run
  with its own tools or rebuilt.

## 5. Holds by fail, hold table growth

S81 hold keys 352 -> 481 in 2 h. The sdc_lint class took three steps: class hold 16:12, 23 more fails, hold by
list 16:30 (r187), plus a loop-gap addition. The list (rows/s81_tapoffset_drop_*.json, 336 types) existed at
13:32 when the tap-offset tables were dropped. KV: 10 per-item holds at 17:10, die hold at 17:35. DRT-0255 at
17:27 was done right: held by family from the evidence line in one commit.

Structural fix (WAVE-HOLDS-1115): a plan event or tool change that invalidates items posts its item list as a
file with the event; the hold is set from that list in the adopting commit, with the release term. With class 2
(digest-keyed retry) and class 3 (breaker) working, the per-fail hold is not needed at all. Also print per die
"held N of M, by release term" in the loop-gap line: S81 is now a die that launches 3 types of 394.

## 6. Host imbalance

ot-run 17:50: epyc2 admits 610 GB, 28/128; epyc7 564 GB, 58/96; epyc8 678 GB, 57/96; intel1 192/112; epyc9
122/96; epyc10 145/96. No admission refusal on a gen host in the window; one `ot-run: NOT RUN` (intel1 scratch
26 GB under the 50 GB floor, one job). epyc2 is out of the gen set twice over: GEN-DISK-LOW (59 GB under 70) and
the kit_topology symlink path defect (WAVE-PREPNR fix READY 18:04, needs KIT-OPS-5 install). RESTAGE-PICK lines
show room=0 on epyc10 and intel1 and cap>0 only on epyc7/epyc8, so placement is already steering; the idle share
is mostly epyc2 plus the missing launches of class 1.

Fix: MERGE-QUEUE-1 lands wave-prepnr-1115; KIT-OPS-5 installs the die-src patch and passes one epyc2 kit through
kit_topology; CLEAN-ALL-1115 frees epyc2 by moving the gate clone slot (29 GB) and the 45 GB HEAD-MYTILE full
clone (class 10). Then 100 threads return.

## 7. Sync and cleanup remove live inputs

Three events in 2 h: rsync --delete into S81 ev/ removed 4 plan files (restored, rule acked 17:5x); a cleaned
hard_params.json failed the G1d elab; CLEAN-ALL freed 0 GB on epyc2 because every top writer is under 24 h or
named by a manifest, while 23 GB treeA is kept by 7 QC bind reports of which 6 are superseded.

Structural fix (CLEAN-ALL-1115): keep set = files named by the plan-gate manifest of every CURRENT event (class 1
input closure) plus live/queued jobs; bind reports of superseded events stop protecting trees once the current
event's bind passed. Plan dirs (ev/, rows/, run/) are written by a `plan_sync` wrapper that has no --delete
option; a lane-level rule alone will be forgotten.

## 8. SDC-only deltas as wave events

HEAD: NF10 16:53, NF11 17:05, NF12 17:42, each "SDC only, one type". The wave moved to NF12 at 17:55 and
launched 3 types. HEAD-100 notes that the plan was edited after prep, so head_wave_kit_rtl.py raises "prepared
plan changed" on the stale wave_prepare.json sha until the record is refreshed by hand.

Fix (KIT-OPS-5): prep writes wave_prepare.json as its last step from the final plan sha (no edit after prep);
a delta that changes kit inputs of N types re-keys those N types only (the kit input digest decides, as in
class 2). Then an SDC-only event costs one launch, not a die switch.

## 9. No-progress table

NOPROG 17:37: 168 jobs, PROGRESSING 162, SLOW 6, NO-PROGRESS 0. The SLOW rows: col_h10_r1__t1 GRT 18.7 h on
epyc7 and 18.5 h on epyc10 (the same type on two hosts, 14.5 cores each); ot_s81sl_leaf__t21 GRT stagnant 2.5 h;
hd_lep0N pregrt_ff_hold with no log write for 7.0 h (event NF6, now superseded by NF12); two docker containers
on intel1 (flamboyant_maxwell, optimistic_franklin) 18.7 h with no stage log, event s29q103S2 (superseded).
The table is advisory and names no owner, so no lane acts on it.

Fix (FLOW-HEALTH-1): each SLOW/NO-PROGRESS row gets the owning lane from OWNERS.tsv and is posted once to that
lane; a row on a superseded event is posted to WAVE-HOLDS as SUPERSEDED-RUNNING. No automatic cancel.
Note for COORD on wave-prepnr-1115 (READY 18:04): it adds a DESIGN-FAIL class GRT-CONGESTION at "iteration-10
overflow >1000 or rising". Check before approval that this is a label and a NEEDS-LANE post only and stops no
running GRT; the owner removed GRT early stops on 11-14.

## 10. Gate runner leftovers

epyc2: 3 yosys + lec_async processes 2 h old in deleted gc-* worktrees of gate slots 0/3/4; slot0 clone 29 GB.
The test-reap fixture (merged 16:08) reaps tagged pytest watchers; the gate's process scope is not done.
Fix (MERGE-QUEUE-1): run each gate under `systemd-run --scope` and stop the scope at exit; gate clones live on
epyc8/epyc10 (755 GB / 4.7 TB free), not on epyc2.
Also: MERGE-QUEUE posted DRIFT for hub kw38/rt (48 files differ, running processes) at 17:37 and "drift cleared"
in the same minute with the same 48 files. The clear line is false or the check clears on a second sighting;
MERGE-QUEUE-1 to correct.

## 11. Bookkeeping

STALE 174 current-event (+137 superseded), was 141. S81 210, unowned 186 (was 144): DEDUP/SUPERSEDED/CANCELLED
rows of 11-13/11-14 on col types that are held for Event F. The filter of FABLE-FLOW-1600 class 11 (do not count
a row whose item has a plan-event hold as STALE unowned) is not in. Real gaps today: QC kit_rtl 15, QC "other
flow error" 3, "kit input missing" 2, S81 kit_rtl 3, QC cores without a wave row 3, S81 core 1.
REAP-DEAD SILENT still prints QC native59 every tick (24 lines); PLAN-CORE-NOT-IN-ONLY hbm 12 lines.

## Disk

Hub scratch2 161 GB free, 96% (131 at 15:45). epyc2 86 GB, 90% (58 at 17:1x, 135 an hour earlier). epyc7
172 GB, 98%. intel1 277 GB, 93%. epyc8 1.2 TB, epyc9 1.8 TB, epyc10 4.8 TB. No ENOSPC in the window.

## Does a class recur because fixes are per-instance? Yes, four of them

| Class | Per-instance steps today | One structural step |
|---|---|---|
| KV 7u tree | paths per tick, gate_events_extra, tool mix, tree defect, now a retry-with-own-bind | tree from one tools sha + adopt smoke of one kit per family |
| S81 sdc_lint | class hold, 23 more, hold by list, loop-gap addition | invalidated-item list posted with the event; digest-keyed retry |
| QC binds | each event rebinds 1-2 h to find the same foreign row error | ROWS-PROOF before rows_apply |
| Plan gate parts | schema hunk added to overlay by hand (ovl_b6E -> ovl_b6G), file restored by hand | plan_gate_pre schema + input closure |

## For COORD, in order

1. FLOW-HEALTH-1 now: replay test for the breaker (class 3) and TOOL-DET digest-keyed retry (class 2). Without
   them the 22 S81 and 4 KV RETRY-INFRA rows relaunch on the unfixed cause when their holds lift.
2. New Sonnet lane PLAN-GATE-PRE-1115: plan_gate_pre.py (schema closure, input closure, ROWS-PROOF) and the
   PLAN-GATE-SILENT loop-gap line (class 1). First use: S81 G2/G3 and QC S4q7d.
3. KV-102: rebuild src_kv_kvgeom7u from one tools sha (r195); KIT-OPS-5: adopt smoke of one kit per family on two
   hosts as a commit precondition (class 4). Do not rely on kitrtl-fail-1115c for KV.
4. KIT-OPS-5 + MERGE-QUEUE-1: land and install wave-prepnr-1115, return epyc2 to the gen set; CLEAN-ALL-1115: move
   the gate clone slot and the HEAD-MYTILE clone off epyc2 (classes 6, 10).
5. KIT-OPS-5: QC bind tree without git on two more hosts (class 1); HEAD re-key by kit digest (class 8).
6. FLOW-HEALTH-1 after 1: NOPROG rows to owners (class 9), STALE filter (class 11).

Not checked: flow_guard.py itself (class 3 cause is open); whether the 5 QC geom-enqueued rows have started
placement; the G1db bind result (still binding at 17:28); the content of wave-prepnr-1115; SIGNED relaunches
after 16:09 beyond the 3 log lines.
