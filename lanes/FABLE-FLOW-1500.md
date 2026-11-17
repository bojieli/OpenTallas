# FABLE-FLOW-1500: procedural and flow failures, 11:43-13:50 PST

Reviewer: FABLE-FLOW-1500 (Fable). Read-only: no deletes, no kills, no git writes in owner checkouts.
Measured 2026-11-17 13:43-13:56 PST (hub clock; the brief's "13:00-15:00" is this window) on hub intel2, the 6
build hosts and rtx-pro. Sources: autopilot/log.txt 11:43-13:43 (1006 lines), lanes/FLOW-HEALTH.tsv,
tools/failure_breakdown.py (13:43, incl. TOOLS-LAG), `ot-run --status`, rt/history.log, origin/main log,
kit_wave.json, derive-gen-hosts.log, lane posts, one kit_snap attempt dir. Previous: FABLE-FLOW-1300.
Scope: process and tooling only. Shares are estimates from idle threads and item counts, not per-job measures.

## Headline

1. Runtime sync is unstuck on the hub and 5 hosts, not on intel1. main = 9a8cc15c8d31 (r602, 13:30).
   rt/current = 9a8cc15c8d31 on hub, epyc2, epyc7, epyc8, epyc9, epyc10. intel1 = 58eeec834764 (r595, 12:20):
   5 syncs refused in a row (12:32-13:31) at "34-49 GB free < 50 GB (OT_RT_HOST_MIN_FREE_GB)". All of r585-r602
   are merged. Not live on intel1: r596, r597, r598, r599, r600, r602. intel1 still runs 193 units.
2. The r587 restore queue cannot see the class it was built for. 0 rows queued, 0 restored, while 3 new
   KIT_INPUT_MISSING fails landed at 12:13 with the writer live. Cause is in the code, not in the sync (class B).
3. Fleet use fell: 55% (11:45) -> 57 -> 39 -> 31 -> 36% (13:33). 98 LAUNCH, 9 FAIL, 3 passes in hour 12, 0 in
   hour 13. All 98 launches came from pin-old trees (S81 85 from d5e, KV 11 from d16, QC 2 from d4, HEAD 0).
4. kv3_hub_Wo was launched 4 times in 46 min behind a cell-cap fail (406,241 cells): "changed views" releases an
   item whose fail has nothing to do with views (class C).

## Answers to the brief

| Item | State |
|---|---|
| Runtime sync | hub + 5 hosts = main. intel1 5 merges behind. MERGE-QUEUE posts STATE "failed rc=4" + DRIFT each time; the DRIFT line is then "cleared" against the previous sha, which reads as resolved. No ALERT. The 1300 fix (rt floor 5 GB, re-sync a lagging host every tick) is not done for hosts; the sync-alert branch is not on main (no commit, no READY post found) |
| Rulings merged, not live | none on hub/epyc*. intel1: r596 r597 r598 r599 r600 r602 |
| r600 guard | merged 13:05 (26f27e903e0), in rt/current on hub + 5 hosts (ot_delete_guard.py has adopted_at); current_trees.json present on hub and all 6 hosts (13:30). intel1 has the json but the old module. FLEET-OPS-R's retire2/retire3 repoint to rt/current is promised (13:03 ACK), not confirmed by a post |
| Old-tree launches | S81 col: 5 col members launched 12:45 from d5e, 2 STOPPED-HELD 13:04, hold s81-fix-s81-col-d6b active (unreleased). Other dies: yes, every launch is from a tree that lacks approved fixes (TOOLS-LAG: s81 280 commits / 11 rulings, kv + qc 385 / 13, head 252 / 9, hbm 1039 / 25). TOOLS-LAG is die-level and advisory; nothing maps a missing ruling to the items it fixes, so the col hold was hand-made and no other family has one |
| Uncapped lo7 | stopped 13:15 by S81-TYPES-R3 (5,688,959 instances at floorplan, about 7.7 h on epyc8, launched by ot-run directly, never through the wave plan probe). r576 put the only limit in the wave plan probe and removed run-time stops, so any direct launch is unlimited. Answer: yes, see class D |
| ot_wait.py (r591) | not adopted. 0 ot_wait.py processes on hub, 6 hosts, rtx-pro. 6 private waiter scripts alive on the hub, 5 on rtx-pro. One lane (QC-PLAN-R3) states it uses `--once` before deletes |
| Disk | epyc10 + epyc9 scratch3 on root done; old copies due 21:33/21:41 host time. epyc8 bind still pending although lo7 stopped at 13:15 (scratch3 still nvme0n1p1). intel1 scratch2 21 GB, scratch 16 GB: REFUSED by ot-run, out of gen_hosts since 13:07, still first in kit_wave place_prefer. epyc10 REFUSED (scratch 44 < 50). epyc7 --dir only (root 73 < 150). localhost REFUSED (139 < 150): 2 QC CRASH infra-notrun |
| link-base (r602) | merged 13:30, live on hub + 5 hosts, not intel1. Known limit stays: verify of a base tree with linked children fails |
| r587 restore queue | hub restore_needed.jsonl and restore_done.jsonl 0 bytes; rtx-pro worker runs every 10 min, "queue 0 pending 0". Not working for the live class |

## Classes, ranked by fleet time wasted

### A. Fixes do not reach running kits (about 30%: most of the 45-69% idle fleet)

Count: 98 of 98 launches from pin-old trees (1300: 115 of 115). Trend: flat; now measured every tick by r592.
- A1 host sync. Root cause: a 50 GB host floor guards a 0.4 GB snapshot, and a refused host is retried only at
  the next merge. intel1 fell to 21 GB while 193 units kept writing (kw45 175 GB / 6 h, alert only).
  Fix (FLEET-OPS-R): rt floor = 3 x snapshot size on hub and hosts. A host with rt/current != hub is removed from
  hosts/place_prefer/gen_hosts by derive_gen_hosts in the same run and re-synced every tick. MERGE-QUEUE reports
  "merged, NOT LIVE on <hosts>" until equal; DRIFT clears only when the host equals the current hub sha.
- A2 die trees. Root cause unchanged from 1300: tree = `git archive <pin>` + hand overlay. r592 reports it, nothing
  acts. Fix (WAVE-FLOW-R2): each ruling carries `fixes: <die>/<family glob>`; the tick turns a missing ruling into
  an automatic family hold FIX-NOT-IN-TREE that releases on the tree switch. Then the S81 col case is impossible
  for every family and needs no hand hold. Structural end state stays: tools from rt/current, tree pins rtl + plan.

### B. Missing provenance inputs (S81 76 types held; 3 FAIL in window, 69 at 1300; about 5%)

- Root cause 1: export_restore.restore_rows queues a path only if it is a value in provenance `export` with
  signoff_sha256. The paths that fail are original-kit files (.../kl_dsfd_coll_lane_e_safe8_..._vB/base/6_final.odb,
  die-s81-51/.../lec.json, PROVENANCE.json): not export keys, so 0 rows and no log line. Verified in attempt a17
  of dsdv_slice_lepe_nh_mus_LP__t1: KIT_INPUT_MISSING with no KW_KIT_SNAP_RESTORE_* line.
- Root cause 2: the FLOW-GUARD class s81|kit_snap stays open and holds the col family (17 LAUNCH-HELD at 12:40).
- Fix (FLEET-OPS-R): every missing path gets a row. The worker resolves it by module + record id in the signed
  export on rtx-pro/AGIdock, else marks UNRESTORABLE, and the wave turns UNRESTORABLE into one NEEDS-LANE per view
  (rebuild or repoint), not a repeat fail. A skipped path prints KW_KIT_SNAP_RESTORE_SKIPPED <n> <reason>.
  publish_gate fails a tree whose views name a path on no host and not in the export (1300 item, still open).

### C. Relaunch on an unrelated input change (new; 12 items launched 3-4 times in 100 min; about 3%)

Count: kv3_hub_Wo 4 launches (12:53, 13:05, 13:30, 13:38) after "cell count above the kit run cap 406241", then
KIT_NOT_SELF_CONTAINED; 8 S81 items launched 4 times and 4 items 3 times from d5e (cause per item not traced).
- Root cause: r589 releases a failed item when any view hash changes. Staging of ring-master views changes the
  hash each time; the fail class (PLAN cells, kit_rtl self-contained) does not depend on views. Also the wave
  still fails @cells at run time although r576 says no run-time stop exists.
- Fix (WAVE-FLOW-R2): the fail key names the input parts its class depends on (cells -> rtl + plan only; kit_rtl
  -> file list; place/route -> views). A change in another part does not release. PLAN cells > SPLIT_CELLS at
  run time becomes SPLIT-NEEDED terminal with a NEEDS-LANE, never a relaunch.

### D. Jobs outside the plan-time cell limit (1 run, 7.7 h x about 32 threads + 320 GB scratch3; about 2%; blocked the epyc8 bind)

- Root cause: the limit lives in one caller (kit_wave plan probe). Direct ot-run launches skip it.
- Fix (FLEET-OPS-R + WAVE-FLOW-R2): the limit belongs to the kit, not the launcher. Kit generation writes
  cells_est into the kit manifest and refuses to emit a P&R kit over cell_cap.SPLIT_CELLS unless the kit carries
  `split_waiver: <ruling id>`. ot-run reads the manifest for any job whose --dir is a kit and refuses the same way
  (NOT RUN, non-zero exit). native_cell_cap.tcl stops at floorplan when the real count exceeds the cap without a
  waiver. Self-stopping in 3 places, whatever launched it.

### E. Disk and admission (about 5%: intel1, epyc10, localhost refused; epyc7 --dir only)

Free scratch2 GB: intel1 21, epyc2 113, epyc7 51, epyc8 194, epyc9 67, epyc10 45 = 491 (1300: 625; 1100: 829).
Trend: worse. GEN-DISK-LOW 23 lines. derive_gen_hosts works (12:15 dropped epyc10, 13:07 dropped intel1) but runs
hourly and covers gen_hosts only: kit_wave hosts and place_prefer still list intel1 first and epyc10.
- Root cause: AUTO-RETIRE deleted 0 on every run (all candidates protected by d5e / pending trees), QC published
  four full 56 GB trees on epyc8, and the lane quota is alert only.
- Fix (FLEET-OPS-R): derive covers hosts + place_prefer and runs every tick. Plan lanes publish with delta-apply
  --link (r602 makes this work); publish refuses a full copy when a base tree is on the host. Quota breach stops
  new launches of that lane on that host. Finish the epyc8 scratch3 bind now (lo7 is gone).

### F. Lane job control (waiters, wrong retire, near-miss delete; about 1%, high risk)

- ot_wait.py unused: 11 private waiters alive. Fix (FLEET-OPS-R): `ot-run` prints the ot_wait command with every
  unit id; the lane hook refuses a new script that loops on is-active or on an output file.
- Wrong retire of M5T: closed by r600 on 6 of 7 machines. QC-PLAN-R3 near-miss delete of the M5T .building dir was
  stopped by ot-delete. Residual: the guard was deployed unmerged first; r600 correction ACKed.

### G. Stale rows and noise

Stale current-event 121 (1300: 118): S81 5, QC 20, HBM 107 (parked). Unowned 16 (QC 5, HBM 11). QC 25 kit_rtl
rows silent since 10:22, 3 of them now stale and unowned. RETRY-IGNORED 147 lines, TOOL-SKEW 85, TOOLS-LAG 60.

## Do now

1. FLEET-OPS-R: free intel1 scratch2 (21 GB) or lower the rt host floor, re-sync to 9a8cc15c8d31; drop intel1 and
   epyc10 from kit_wave hosts/place_prefer until they admit; finish the epyc8 scratch3 bind.
2. FLEET-OPS-R: restore_rows queues every missing path (class B); log skipped paths.
3. WAVE-FLOW-R2: class-scoped fail-key release (C); FIX-NOT-IN-TREE automatic family hold from rulings (A2).
4. WAVE-FLOW-R2 + FLEET-OPS-R: cell limit in kit generation, ot-run and native_cell_cap.tcl with waiver (D).
5. MERGE-QUEUE: "merged, NOT LIVE on <host>" per ruling; DRIFT never cleared against an older sha; land the
   sync-alert branch.
6. All lanes: ot_wait.py for every wait; QC-PLAN-R3 publishes by delta-apply --link.
