# FABLE-FLOW: flow and procedural review, 19:48 to 21:47 PST 11-19 (read-only)

Sources: autopilot/log.txt (1,738 lines, 9 ticks), kit_wave_state.json (21:36), lanes/FLOW-HEALTH.tsv (21:21),
lanes/PROGRESS-WATCH.tsv (21:43), tools/failure_breakdown.py (ran 21:45), ot-run --status (21:46), rt/history.log,
rt/current git log (d4d596794706), one ls on epyc9, FABLE-FLOW-1949.md.
Fleet in ot-run: 736 threads (7 hosts incl. localhost) x 2.0 h = about 1,470 thread-hours.

Not checked: the stage-ODB cleaner, leaked scopes and noisy loops of FLOW-FIX-2045 (no run logs read; see "Open
items"); the cause of the KV bindcopy loss (class 3); whether "bootstrap GEN failed" on HEAD is a design or a
flow error; the 8 test_kit_wave.py failures.

## Numbers
- LAUNCH 185 (19:48-20:00 11, 20h 121, 21h 53). By die: QC 67, KV 57, S81 28, HEAD 33. No die at 0 for an hour.
- KIT-WAVE FAIL 132 (9 in the prior window). Every one ended before place and route except 2 MPL/DPL place errors
  and 1 clock-landing error. By class:
  - 56 QC SRC_MANIFEST (class 1)
  - 30 HEAD kit_rtl: 16 "type held or not explicitly staged" on 8 ot_sram macro rows (class 2), 14 "bootstrap GEN
    failed: 1" on hd_host_e, hd_host_n, hd_serdes (owner HEAD-100, not classified here)
  - 18 "no partition type <name> in the plan" (class 2): KV 13, QC 2, S81 2 + 1 at 21:45
  - 15 KV "bind of record names HDL sources that are gone" (class 3)
  - 6 S81 leaf t56 bind rst_n error, 4 KV qkd_pv_fin_s8_pin gen, 1 QC sle_su_l0 contract (design owners)
  - 2 infra: ssh timeout to epyc8 (kit_store 21:05, roam pullback 21:32)
- SELF-STOP ("superseded by attempt N of the same item"): 0 (13 in the prior window). REAP-REVIVE 0.
- REAP 79 rows "CANCELLED; units []" at 21:07 and 21:33 (QC 50, HEAD 13, S81 10, KV 6): clean-up of macro rows and
  old-event rows, no live unit stopped.
- ORPHAN stopped 7 at 20:21 (1.3-4.1 h old, attempts older than their successor), ORPHAN-DEAD 1, KIT-LOST 1.
- DIE-OFF hbm 5, 0 after 20:25 (hourly now). ITEM-SYNC phy_serdes_b 5, 0 after 20:43. HUB-SYNC-FAILED 1 (was 7).
- ADOPT-GUARD PLAN_MISSING hbm: 9 alert pairs, still every tick.
- EARLYOOM-RESUBMIT 2 (S81 slice_station__t52 56 GB, QC slw_stm_v2 72 GB): "no die host admits" both times.
- failure_breakdown: signed any plan 473, current plan 408 (unchanged from 19:44). STALE 104, all HBM (parked);
  the 85 S81 STALE rows of 1949 are gone. Non-design classes: QC "other flow error" 16 (the class 1 rows), QC
  cancelled (superseded) 10, HEAD cancelled (superseded) 8, HBM 90 + 12 cores.
- Disk and admission: 0 disk refusals, 0 admission refusal lines. Hub root 120 GB free (74%).
- ot-run 21:46: threads asked 5,085 on 736 (6.9x), load 1,767 (2.4x). epyc8 load 383/96, 105 running, 1,227 threads
  asked, admits 0 GB, 56 waiters asking 5,288 GB. epyc2 1,018 threads asked on 128, admits 0. The others admit
  13-22 GB. "next 16-thread 32 GB job -> intel1 (would queue)".
- Tick 528-881 s (mean 686 s; kit_wave_step 385-700 s, loop_gaps 74-150 s). 1949 was 398-598 s.
- Src and tool skew: TOOL-SKEW WARN s81 368, qc 415 modules. UNMEASURED s81_head (pin manifest 385f61b5582a
  missing, ninth window) and now qwen_kvsys (rt/dcd56363d450.manifest.json missing since the D25e apply).
  TOOLS-LAG qc 1,522 commits (the die moved to event N46Q but its tool pin is still eb1e73448bd0), hbm 2,619,
  head 514, s81 203, kv 90.

## Did the 1949 fixes land
- 1 DIE-OFF fail-open f0fe518fb5 and write-time event check d87888c9fe2: in rt. 0 DIE-OFF on a live die.
- 2 SELF-STOP strict higher attempt 488bcba257: in rt 19:56. 0 cases in 2 h. Landed and verified.
- 3 Host pick by load, waiter re-pick: NOT landed (no ot-run commit on main since 19:45). Worse, see class 4.
- 4 Relabel re-arms the counters: NOT landed. 5 FAIL-STALE passes dropped 39 fail keys (class 5).
- 5 Leaked scopes: 11320c66869 in rt 20:00 (scans skip only unreadable hosts). The stop-then-verify list is not
  landed. 7 orphans stopped at 20:21, none after.
- 6 Noise: DIE-OFF hourly and ITEM-SYNC fixed (ef3d8fe8d52, rt 20:43). hbm ADOPT-GUARD alert not fixed.
  HUB-SYNC row files fixed (b2dfb1501c8).
- 7 rt follows main: landed. 37 rt switches in the window, 2-7 min behind main.
- PROGRESS-WATCH: landed 19:56, 13 alert rows, runs every 10 min. It caught NO-ADVANCE on every die. It has no
  rule for class 1 (many rows of one die failing the same pre-flight check).

## Classes, ranked by loss

### 1. QC kits refused by SRC_MANIFEST: 56 fails, 20:17 to 21:31, still open at 21:47. New.
- Two separate causes, one class.
  - 20:17-21:05, snapshot n46_s0, 39 fails: a lane renamed clock_contract.json to
    clock_contract.json.SONNET-DISABLED-1120 inside the pinned snapshot (8 findings). 2e93781976 (rt 21:00) made
    extra files a note, but a rename is also a missing file, so 15 more rows failed at 21:05.
  - 21:31, snapshot n46_s1 (adopted 21:19), 17 fails: the manifest names tools/_s81ph_gen.py.orig, a patch
    backup. On epyc9 the file exists (written 19:49, 4 links against 19 for the real file); on the host that ran
    the check it is missing. The manifest was built from a tree that held the backup, and the copy to the other
    gen hosts did not carry it.
- Now: 17 current-plan QC rows are FAIL with BLOCKED-REPEAT (3 identical fingerprints) and 17 NEEDS-LANE posts
  went to DIE-QC-103. Copying the file will not release them: the block is released only by a changed own input.
- Root cause: a pinned snapshot is writable by any lane, its manifest is built from whatever is in the tree, and
  the adopt step does not run the manifest check on every gen host before the die switches.
- Structural fix (three parts, each small):
  - the snapshot builder writes the manifest from the tracked file list, never from a directory walk, and the
    copy uses the same list (rsync --files-from), so manifest and copy cannot differ;
  - snapshots are read-only after build (chmod -R a-w plus the directories), so a rename fails at the lane;
  - atomic apply runs the src_manifest check on every gen host and refuses the switch on any finding.
  - Also: a src_manifest failure is a die-level fact. One failure opens a die breaker with one post; it does not
    count against 17 rows, and the rows relaunch when the check passes.
- Owner: WAVE-PILOT-FIX (breaker, apply check), new Sonnet lane SNAP-RO-1119 (builder and read-only).
- Immediate: DIE-QC-103 or WAVE-PILOT-FIX drops the .orig entry (new snapshot s2) and unblocks the 17 rows.
- Share: machine under 1% (17 rows x 8 min = 2.4 attempt-hours measured, hub side). Schedule: 17 to 22 QC types
  made no progress for 1.5 h and still do not.

### 2. Plan-synthesized rows for names that are not partition types: 34 fails. New at 20:23, mostly fixed.
- 7ef2756099 (rt 20:23) made every plan type a wave row. It also made rows for memory macros (HEAD 8 ot_sram
  rows x 2 = 16 fails, QC ot_sram/ot_rom) and for bound and core names (kv_cland_*, qkd_kvs_*, 18 fails).
  2f1ed17335 (rt 21:00) and 873479d667 (rt 21:08) stopped the synthesis; the rows that already existed failed
  once more after the HEAD r9 -> r10 switch (21:21-21:26) and were cancelled at 21:33.
- Still leaking: qwen_kvsys/qkd_kvs_pcc_h_head_p failed "no partition type" at 21:45, after both fixes.
- PLAN-ROWS lines (21:22, 21:35) report 0 synthesized, 0 picked, 0 launched for all four dies.
- Root cause: the row source was a name list, and the check "is this a partition type of the plan" ran in the
  die tool after launch.
- Structural fix: the wave builds rows only from the plan's own partition-type table (the list bind accepts),
  and a row whose name bind does not know is refused at synthesis with one line, never launched.
- Owner: WAVE-PILOT-FIX. Share: under 1% (each fail 0.2-0.4 h of a light hub process).

### 3. KV D25e adopted before its bind inputs were on every gen host: 15 fails + 19 SRC-INCOMPLETE lines.
- Apply at 20:51. SRC-INCOMPLETE on epyc10, epyc2, epyc7 from 20:52 (bindcopy_kv_d25e files missing). SRC-SYNC
  copied 113 files at 21:08. 15 rows failed at 21:19 ("HDL sources that are gone"), RELAUNCH-ON-FIX released
  all 15 at 21:22. Self-healed in 31 min. At 21:47 SRC-INCOMPLETE lines again for QC n46_s1_postbind and KV
  d25e_bind on epyc7 and epyc8.
- Root cause: same as class 1, third part. Apply does not prove the tree whole on each gen host. Whether a
  cleaner removed the files or the copy never finished is not checked.
- Structural fix: the apply check of class 1. Owner: WAVE-PILOT-FIX. Share: under 1%, 31 min of KV launches.

### 4. Fleet over-asked 6.9x in threads; epyc8 holds 56 waiters. Unchanged, worse.
- UNDER-USE idle 0 in 8 of 9 ticks, so the 10-13% idle of 1949 is gone. The cost moved: load 2.4x the threads on
  the whole fleet, 4.0x on epyc7 and epyc8, 1.5x on epyc9. epyc8 waiters ask 5,288 GB on a host that admits 0.
- Two ssh timeouts to epyc8 became kit failures (21:05, 21:32); BAD-HOSTS epyc7 epyc8 once.
- Root cause: jobs declare 8-16 threads, admission counts memory only, and a waiter never leaves its host.
- Structural fix (no cap, host choice only): order hosts by load per core before memory; a WAITING job moves to
  any admitting host after 2 polls; resume jobs name no host. An ssh timeout to a host over 2x its cores is
  retried on the hub, not recorded as a row failure.
- Owner: FLOW-FIX-2045. Share: not measured as time lost. Measured: 56 queued jobs, 2 infra fails, 2 earlyoom
  kills.

### 5. A tree switch re-arms repeat counters: 39 fail keys dropped in 5 passes. Not landed.
- HEAD switched tree twice in 61 min (r8b -> r9 20:05, r9 -> r10 21:05), KV once, QC once. HEAD hd_host_e
  failed "bootstrap GEN failed" 6 times and hd_serdes 5 across the three trees; each switch released the block.
- Structural fix (as 1949 class 4): fail key = plan block sha + the item's own inputs + stage tools. The event
  label and the tree path are not part of it.
- Owner: FLOW-FIX-2045. Share: under 1% here (all pre-place), 11 wasted relaunches.

### 6. Noise and tick time.
- hbm ADOPT-GUARD PLAN_MISSING: 18 alert lines for a parked die. Use the parked flag DIE-OFF already uses.
- STUCK-STATE s81 17 and s81_head 17 rows alert every hour since 20:01 with no owner action recorded.
- Tick mean 686 s, up 25%. kit_wave_step is 70%; loop_gaps doubled to 119-150 s.
- TOOL-SKEW UNMEASURED on two dies: apply should write rt/<pin>.manifest.json or refuse.
- Owner: FLOW-HEALTH-2 (alerts, pin manifest), WAVE-PILOT-FIX (tick). Share: 0% machine.

## Open items of FLOW-FIX-2045
No commit on main since 19:45 names the lane, the stage-ODB cleaner, spill or waiters, and the lane has no post
in the queue. Cleaner, host imbalance, relabel re-arm and scope verify are all still open. SUBSTEP-1 removed
sub-step ODBs 8 times in the window (20 GB, "terminal attempts" only by its own line); whether it still removes
files of live runs was not checked here.

## Share of fleet time, summary
- Procedural failures: under 2% of 1,470 thread-hours (132 fails, all short and before place; 2.4 attempt-hours
  measured for the 17 open QC rows, the rest estimated at 0.2-0.4 h each).
- Schedule loss is the real cost: QC 17 rows blocked now; KV 31 min; HEAD 3 types 0 progress in 2 h.
- Over-ask (class 4) is the largest unmeasured term.
