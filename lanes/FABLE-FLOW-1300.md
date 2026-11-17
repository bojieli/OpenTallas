# FABLE-FLOW-1300: procedural and flow failures, 09:43-11:52 PST

Reviewer: FABLE-FLOW-1300 (Fable). Read-only: no deletes, no kills, no git writes in owner checkouts.
Measured 2026-11-17 11:43-11:52 PST on hub intel2, the 6 build hosts and rtx-pro.
Sources: autopilot/log.txt 09:43-11:43 (24 ticks, 1001 lines), kit_wave.json, kit_wave_state.json, `kit_wave.py plan`
(read-only), tools/failure_breakdown.py (11:43), `ot-run --status` (11:43), rt/history.log, lanes/MERGE-QUEUE-1.md,
lane posts, per-host df, blob hashes of the die trees against origin/main. Previous: FABLE-FLOW-1100.
Scope: process and tooling only.

## Headline

1. r585 (second commit), r586, r587 and r588 are merged but NOT live. The hub runtime sync has failed on every
   merge since 10:55: `ot-tools-sync` refuses at "rt: 93-98 GB free < 100 GB (OT_RT_MIN_FREE_GB)". rt/current is
   24c7347cc887 (10:50 merge) on the hub, epyc2/7/8/9/10; intel1 is at b34c0560d6fb (10:21). Five merges are
   stranded: b68fab5 (r584), 4e0f325 (r585), 5e755fe (r586), 6b50ce8 (r587), b120422 (r588). MERGE-QUEUE posts
   a STATE line each time; no ALERT, and the rulings are being counted as fixed.
2. No approved die-tool fix of today is in any die's current tree. 21 of today's 42 merges touch
   tools/die_plan, tools/ref_tile, tools/grt_nonport_hold.tcl or physical/die_plan; KV, S81, HEAD and QC trees
   carry 0 of the 21 as merged (table below). The pins are 223-335 main commits old.
3. The wave recovered and then went quiet again: 115 LAUNCH in the window (1100: 3), but 111 of them in the
   10:00-10:30 half hour after the pilot holds were dropped; 4 since 10:30. Fleet use median 55% (range 44-65;
   1100: 41%). 73 FAIL, 69 of them one class in one burst.
4. PILOT-DEADLOCK=0 on all 19 audits since r575 went live (10:06): that fix holds.

## Are the fixes live

| Fix | Merged | In rt/current | Effect seen |
|---|---|---|---|
| r575 WAVE-PILOT-FIX (PILOT-DEADLOCK, launchable pilots, breaker reset) | 10:05 c9716823 | yes | yes. PILOT-DEADLOCK=0 x19; TERM-UNREACHABLE 233 -> 3 at 10:46. Breaker opened on the S81 kit_snap class at 10:06:39 after 10 fails and released at 10:07:12 ("inputs changed", PROBE). It could not stop the other 59: all 69 col members were launched in ONE tick at 10:02 when the holds were dropped by hand |
| r585 provenance paths live-protected | 10:18 bc75214 (list) + 11:10 4e0f325 (scan fix) | first commit yes, scan fix NO | partly. The cron reads rt/current build_protected_live.py and ~/.local/state/prov_paths.json; the cache was written once by hand at 10:43 (706 paths) and protected_live.txt went 1394 -> 1454 roots. The scan that refreshes the cache is the un-synced commit: the rt copy "found 0 paths". The cache protects for 72 h, then silently stops |
| r585 audit result | - | - | 442 of 706 provenance paths exist on no host (prov_missing_1117.txt). FLEET-OPS-R restored 7 files + 2 signoff.json for S81 by hand at 11:16; 8 files are reported not restorable |
| r587 RESTORE-NEEDED queue + rtx-pro worker | 11:30 6b50ce8 | NO | no. Worker cron on rtx-pro runs every 10 min ("queue 0 pending 0"). The hub queue files are 0 bytes: the wave code that writes rows is not in rt. export_restore stage is off by design (no die has signed_export) |
| r588 one kit-common list | 11:40 b120422 | NO (and not in any die tree) | no new kit has been generated from it. The 6 KV ring masters and bksel r3 passed by hand copy of hold_sdc_guard.tcl (ring masters SIGNED 11:49). Core kits built from a lane worktree get r588 only after that lane rebases |
| r586 GRT frames | 11:30 5e755fe | NO | none. tools/die_plan/legacy_gate.py is also pin-old in all 4 trees, so it needs the rt sync AND a tree republish |
| r574 apply commits through coord-commit | 10:05 | yes | yes. HUB-SYNC-FAILED ended 09:50, CONFIG-DRIFT resolved 10:00 |
| r570 lane quota v2 (1100 finding) | 09:20 | yes | still NOT deployed. Cron still runs the private 08:00 copy in fleet-ops-r/; last run TimeoutExpired on epyc7 again; no state file |

## Classes, ranked by fleet time wasted

Shares are estimates from idle threads and held replica counts, not measured per job.

### A. Approved fixes do not reach running code (about 25%: most of the S81 col and QC idle share)

Two separate delivery paths, both broken, neither alarmed.

A1. rt sync blocked by a disk floor (new; 5 merges stranded, 0 at 1100).
- Root cause: ot-tools-sync needs 100 GB free on the hub scratch for a snapshot of about 0.4 GB (rt holds 22
  snapshots, 9.2 GB). Hub scratch2 has 93-98 GB. intel1 missed 3 syncs at 36-38 GB < 50 GB; it now has 129 GB
  but nothing re-syncs a host until the next hub success. 1100 already asked for a 5 GB rt floor; not done.
- Fix (FLEET-OPS-R): OT_RT_MIN_FREE_GB = 5 on hub and hosts (absolute size of one snapshot x 3). A failed sync
  is an ALERT, and MERGE-QUEUE reports each ruling as "merged, NOT LIVE" until `rt/current == main` on the hub
  and every gen host. A lagging host re-syncs on every tick, not only on the next merge.

A2. Die trees are frozen pins (known; measured here for all dies).

| Die | Current tree | Pin (main) | Main commits behind | Die-tool merges since pin | Today's 21 die-tool merges in tree | Today's files: ==pin / overlay / new-file absent |
|---|---|---|---|---|---|---|
| S81 | f2s4_cohort_d5e | 3c913dbdfb23, 11-16 09:31 | 305 | 139 | 0 | 23 / 7 / 9 |
| KV | hg5_340b90be_d16 | eb1e73448bd0, 11-16 03:11 | 335 | 152 | 0 | 29 / 1 / 9 |
| QC | s4q9l2_d4 | eb1e73448bd0, 11-16 03:11 | 335 | 152 | 0 | 28 / 2 / 9 |
| HEAD | nf15d2_pgr1_d1 | d0ee4a2afb10, 11-16 16:45 | 223 | 102 | 0 | 29 / 1 / 9 |
| HBM | src_hbm_main_d6b0b70323 | d6b0b70323, 11-13 | 812 | 352 | 0 | tree has none of the paths (parked) |

Marker checks in the trees (file present / string present): kit_common_files.py (r588) absent in all;
prd_obs_check.tcl (r579) absent in all; OT_GRT_PORT_HOLD_MARGIN_PS (r584) only in the unpublished S81
d6_1117_work and d7b_1117_work trees; cell_cap.py (r576), rck_balance.tcl, ft_channel_route.py absent in all.
hold_sdc_guard.tcl (HOLD-SDC-1116, merged 11-16 14:08) exists only in the HEAD tree: KV, QC and S81 wave type
kits run every hold repair without the sign-off SDC guard. The pending KV trees d17 and d19 are also pin-old.
- Root cause: a tree is `git archive <pin>` + a hand-listed overlay. A flow fix reaches kits only when a lane
  copies files into the next tree (QC N: "r572 by copy+mv"). TOOL-SKEW only warns (S81 88 modules, QC 10, KV 5,
  HBM 242 of 242; 120 lines) and compares against the pin, so it cannot see a missing approved fix.
- Fix (WAVE-FLOW-R2 + FLEET-OPS-R): split tools from design in the tree. Kit generation reads tools/ and the
  flow files from rt/current (already replicated, hash-named); the die tree pins only rtl/ and
  physical/die_plan/<die>. A die that must freeze a tool names it in an explicit `tool_pin` list with an owner
  and a 24 h expiry. Until then: publish_gate fails a tree whose tool files differ from main unless listed, and
  the tick prints FIX-NOT-IN-TREE <die> <ruling> per approved ruling (source: the ruling's file list).

### B. Missing kit inputs named by provenance (69 FAIL in 10 min; about 3% direct, S81 col family held behind it)

Count: 69 S81 col FAIL @kit_snap KIT_INPUT_MISSING, 10:06-10:16 (0 at 1100: the class was hidden behind the
pilot hold). failure_breakdown: S81 "kit input missing" 75 types. 442 of 706 provenance paths are on no host.
- Root cause: views in a published tree name original-kit paths outside the tree (count-archive-2, lane dirs);
  cleanup deleted them; the publish gate never checked they exist. The file named in all 69 fails
  (s81views_v20261110/x/ot_s81_cfg7_seq_bfp/xbase/6_final.odb) is back on epyc10, epyc8 and intel1 since 11:16,
  but no col row has relaunched: the col types are now outside S81 `only_items` (D6b rebase), and the fail key
  does not hash "input now exists".
- Second cause: 69 identical items launched in one tick. Dropping a pilot hold by hand skips the pilot.
- Fix: (1) FLEET-OPS-R: publish_gate fails a tree when a provenance path of any view is on no gen host and not
  in the signed export; the 442 list becomes a burn-down with an owner per root. (2) WAVE-PILOT-FIX: after any
  hold release or tree switch, at most one item per family per tick until one passes kit_snap + kit_rtl.
  (3) WAVE-FLOW-R2: the fail key of a missing_input fail hashes the existence of the named paths (same change
  as the views part of a8c31abb21c, which covers kv3_hub_Wi only for new fails).

### C. Gate and job control by lanes (3 events; about 2%, but about 2 h of QC plan time)

- publish_gate 1800 s step cap: M5 apply and N1B apply both blocked. The fix branch pubgate-g0-timeout
  @51d95eed is NOT gating: its ot-gate-remote was pinned to epyc7, and ot-run answered "NOT RUN: no host
  qualifies (epyc7 ROOT FS 74 GB < 150)" at 11:22. No gate record exists; no merge by 11:52. The lane reported
  "gate running". Fix (MERGE-QUEUE): ot-gate-remote never takes one host (owner rule: never pin); NOT RUN is a
  non-zero exit that posts NEEDS. Fix (FLEET-OPS-R): a step timeout is derived from the last measured wall time
  of the same step x 3, never a constant.
- SIGTERM on QC N1 CB16 (epyc2 unit oth-ubuntu-2806746, rc 143): sender found. FABLE-FIX-QC-N killed PIDs
  3787306 and 4061197 at 11:27 (its own 11:29 post: "superseded bind") two minutes after QC-PLAN-R3 handed N1
  over, without telling the owner first. Not earlyoom, not a watchdog. Fix (FLEET-OPS-R): every ot-run job
  carries OT_LANE; ot-heavy-stop and raw kill of a unit of another lane need `--handoff <post id>` and write
  one line to the victim lane's posts. A kill then always has a named sender in the log.
- Waiters report RUNNING for dead jobs: KV-HUBC-SPLIT's private wait6.sh showed 6 ring masters RUNNING for
  about 85 min (09:54-11:20) after all six had exited 2 at 5_1_grt, because it only looks for signoff.json.
  Yes, the waiter must read the exit code. There is no shared waiter in tools/fleet; each lane writes its own.
  Fix (FLEET-OPS-R): one `ot-run --wait UNIT...` that reads the unit state and the ot-job exit record:
  RUNNING only while the unit is active; exited without signoff.json = FAIL <rc> <last stage>. Lane scripts
  that test for an output file only are refused by the lane hook.

### D. Kit helper files (7 kits; about 1%, 85 min of 6 KV masters + 1 bksel round)

Count: 7 kits dead at 5_1_grt on a missing hold_sdc_guard.tcl (0 before; class born with HOLD-SDC-1116).
- Root cause: per-generator copy lists. r588 replaces them with one hand-kept list. Two holes stay:
  hold_pad_hb4.tcl skips the guard silently when the file is absent (bksel r2 ran its first hold pass
  unguarded), and the list is still a list.
- Fix (S81-CORES-R3): gen-time closure check: every `source`, `/work/<file>` and `[file join ... <file>]` in
  the kit's tcl/sh/py must resolve inside the kit, else gen FAIL. An absent guard is an error, not a skip.

### E. Disk and admission (about 4%: epyc7 root, localhost, gen floors)

Free scratch2: intel1 129, epyc2 124, epyc7 85, epyc8 56, epyc9 66, epyc10 165 = 625 GB (1100: 829). Hub 98.
Refusals now: localhost REFUSED (97 < 150); epyc7 takes only `--dir` jobs (root 74 < 150): this is what
dropped the pubgate gate; epyc8 under the gen floor (57 < 60) for QC, S81 and HEAD, so QC again has no gen host
above the floor; intel1 was under it (39) until 11:2x. GEN-DISK-LOW 27 lines (1100: 30). Waiters: 1 (epyc10,
90 GB). kw45 on intel1 wrote 169 GB in 6 h (quota alert only). epyc10 fell at 152 GB/h at 11:11 before
auto-retire freed 103 GB. Fix (FLEET-OPS-R): the unfinished 1100 item, derived gen_hosts, plus the rt floor
of A1; epyc7 root needs 76 GB freed or its jobs default to --dir on scratch2.

### F. Stale rows and noise

- Stale current-event rows 118 (1100: 286): S81 6, QC 16, KV 2, HBM 107. Unowned 13 (QC 2, HBM 11).
- `kit_wave.py plan` says "would launch now (161)" while the tick launched 4 in 80 min: plan counts running
  rows (kv3_hub_Ei) and refused fail keys as launchable. Fix (WAVE-FLOW-R2): plan applies the same select() as the tick.
- QC: 26 rows FAIL @kit_rtl "filelist path(s) outside the kit source tree", refused once and silent since 10:22.
- ARCHIVE FAILED 3054c87a89d6 x15 (probe traceback), unowned. ADOPT-GUARD PLAN_MISSING hbm x3 (parked).
- Tick 142-192 s (1100: 119 s): kit_wave_step 73-125 s, loop_gaps 49 s.

## Do now

1. FLEET-OPS-R: lower OT_RT_MIN_FREE_GB (or free 5 GB on hub scratch2) and re-run ot-tools-sync for
   b1204227591; confirm rt/current on hub + 6 hosts. Until then r585b/r586/r587/r588 are not live.
2. MERGE-QUEUE: rerun the pubgate-g0-timeout gate on epyc9 or epyc2 (not pinned to epyc7); it blocks QC M5 and N1B.
3. S81-DIE-R3, KV-R3, QC (FABLE-FIX-QC-N), HEAD: next tree of each die carries today's 21 die-tool merges
   (S81 D6b has r584 only; KV d17/d19 have none). Add hold_sdc_guard to KV/QC/S81 type kits.
4. WAVE-FLOW-R2: tools from rt/current, not from the die tree (A2); FIX-NOT-IN-TREE line meanwhile.
5. FLEET-OPS-R: shared `ot-run --wait`; OT_LANE on jobs with cross-lane kill refusal; lane_quota cron to rt/current.
6. WAVE-PILOT-FIX: one item per family per tick after a hold release.
