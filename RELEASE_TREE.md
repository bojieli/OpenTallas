# OpenTallas release tree (RECONSTRUCTED 2026-10-24 06:50 PDT)

The original hand-edited tree (~/claude-takeover-20261007/RELEASE_TREE.md on rtx-pro) was lost with that host and
was never committed. This copy is rebuilt from the coordinator's "Top-Down Day" artifact (10-23 18:45 PDT), COORD
rulings in main's merge messages up to 3e05af806b, and the unmerged claude/*-1023 branches. Format follows
tools/auto_owner/release_tree_render.py. Gates are the plan-first flow (owner 10-23 05:08): G0 plan check, G1 plan
review, G2 routing probe, G3 partitions, G4 abutted die, G5 token pass. Owners are the 2026-10-24 lanes.
This file is now version-controlled on branch coord/state (GitHub) so it cannot be lost again.

## EDIT · rules
- Tick a line only with committed evidence (sha). Failed verdicts stay, struck through only when superseded.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS DONE BLOCKED.

## DIE seam · Seam method (all dies) · CP1 = Qwen compute abutted pair
- [x] SEAM.PHYS CP1 physical abut clean · CP1 · PASS · 10-23 10:44
- [ ] SEAM.TIME CP1 seam setup + hold at 833 ps on grid taps (r8 RULING, r9 tools) · CP1-R10 · RUNNING · r4 -19.5/-3.6, r6 -90.6/-24.9 ps; r8/r9 result not recorded
- [ ] SEAM.METHOD Seam method confirmed for every die G4 · COORD · WAITS · waits → SEAM.TIME

## DIE s81 · S81 (DeepSeek-V4.1 ROM layer die)
- [x] S81.G0 Plan check v4.7b · S81-P9 · PASS · ab90f2ade G0 PASS, G0C 76/168
- [ ] S81.G0.V48 Plan v4.8 (r8eq) on main · ROOT-MERGE · RUNNING · s81-p9-r8eq-1023 unmerged
- [ ] S81.G1 Plan review · S81 · WAITS · COND: needs G2 on exact plan → S81.G2
- [ ] S81.G2 Routing probe v4.8 · S81 · PASS · 31 probes overflow 0 (unmerged branch evidence)
- [ ] S81.G0C Completeness 76/168 types clean (92: 75 ot_s81sl_leaf, 14 svc_*_rs, 2 svc_hi_pvso_entry, 1 eng; >400k cells, no hard_cores) · S81 · FAIL · check.py --completeness on main 3e05af806b, 10-24 06:40
- [ ] S81.G3 Frame partitions with R3 internal stations · S81 · RUNNING · 6/7 frame kits FAILED review (paths to 2.2 mm)
  - [ ] S81.G3.CORES Hard cores ve / eng / svc · S81 · RUNNING · svc hcore TT WNS -25.29 ps (ld_grp we decode)
- [ ] S81.G4 Abutted die · S81 · WAITS · waits → S81.G3, SEAM.METHOD
- [ ] S81.G5 Entry replay token pass · S81 · FAIL · 6/6 FAIL; fc30 gaps lowered (8e8db3c53); fc30 status-fault fix on s81-p9-fc

## DIE qwen_compute · Qwen compute
- [x] QC.G0 Plan check · QC-P6 · PASS · d33d3c4e4 G0 PASS, G0C 52/56
- [ ] QC.G0C Completeness 52/56 (sle_st_a/b, slw_st_a/b ft_budget M9 over) · QC-A0 · FAIL · 10-24 06:40
- [ ] QC.G1 Plan review · COORD · WAITS · COND
- [x] QC.G2 Routing probe · Codex · PASS · probe run by Codex 10-23
- [ ] QC.G3 Partitions · QC-A0 · RUNNING · collective part routes clean; A0 cores FAIL clock (v2..v6 tap methods)
  - [ ] QC.G3.A0 A0 cores on grid taps · QC-A0 · RUNNING · qc-p6-a0v6 G0 PASS unmerged
  - [ ] QC.G3.FTC coll_ftc g3h · QC-A0 · TODO · qc-p6-ftc unmerged
- [ ] QC.G4 Abutted die · QC-A0 · WAITS · waits → QC.G3, SEAM.METHOD
- [ ] QC.G5 Token pass on generated die · QC-TOK · RUNNING · 3/4
  - [x] QC.G5.TP8 tp8 · TOKEN · PASS · 10-23 14:41
  - [x] QC.G5.XDIE xdie · TOKEN · PASS · 10-23 14:41
  - [x] QC.G5.OVL4U ovl4u · TOKEN · PASS
  - [ ] QC.G5.XT1 xt1 on bound_r8 (R8 re-bind) · QC-TOK · RUNNING · was 0/64 before R8
- [ ] QC.PAD R8 delay padding 875k → <150k regs · QC-TOK · TODO · plan change (trees not chains)

## DIE qwen_kvsys · Qwen KV
- [x] KV.G0 Plan check v3.8h · KV-P7 · PASS · 0a0966d6f
- [ ] KV.G0C Completeness 48/49 (kv3_hub_Wi: 22 hard cores without pins) · KV-G3 · FAIL · 10-24 06:40
- [ ] KV.G0.V38S Plan v3.8s FIRM astk stations on main · ROOT-MERGE · RUNNING · kv-p8-hub-1023 unmerged
- [ ] KV.G1 Plan review · ROOT-MERGE · PASS · GEOM-REVIEW8 v3.8s PASS (geom-review8-1023 unmerged)
- [ ] KV.G2 Routing probe · KV-G3 · TODO
- [ ] KV.G3 Hub + row partitions from bound RTL · KV-G3 · RUNNING · IO parts 2 PASS 1 COND; hub_Ei waits clock variant spread <= 80
- [ ] KV.G4 Abutted die · KV-G3 · WAITS · waits → KV.G3, SEAM.METHOD
- [ ] KV.G5 Token tests · KV-TOK · RUNNING · kv41 lint 0, bind 85/160; hier Verilator bench WIP (tokj-kvslice)
  - [ ] KV.G5.BOOT Final boot image (PV W request-lane pads) · KV-TOK · RUNNING · kv-p7-1023 non-PV valid

## DIE hbm · HBM d4g
- [x] HBM.G0.FB Fallback plan P7 record · HBM-P7 · DONE · 22911ecdb
- [ ] HBM.G0C Fallback plan completeness 34/60 (110 core_faces, 10 die_io_plan, 1 ft_budget) · HBM-ARCH · FAIL · superseded by B2 when it lands
- [ ] HBM.G0 HBM-ARCH B2 plan G0 + G0C · HBM-ARCH · RUNNING · hbm-arch-1023 WIP (H-tree clock, 5 SerDes)
- [ ] HBM.G1 Plan review · HBM-ARCH · WAITS · waits → HBM.G0
- [ ] HBM.G2 Routing probe · HBM-ARCH · WAITS · old plan: hc2/hc7 congested, VM|SU2 face overloaded
- [ ] HBM.R8 r8 bind (held from binder4, COORD 23:10) · HBM-ARCH · BLOCKED · waits → HBM.G0
- [ ] HBM.G3 Partitions · HBM-ARCH · WAITS · 694 cores pinned on fallback
- [ ] HBM.G4 Abutted die · HBM-ARCH · WAITS
- [ ] HBM.G5 Token tests · HBM-ARCH · BLOCKED · held for final plan; price −3.4% accepted

## INFRA · fleet and coordination
- [x] INFRA.FLEET New fleet provisioned (toolchain + ORFS image on 5 hosts) · COORD · DONE · 2026-10-24
- [ ] INFRA.OTRUN ot-run / hosts.json / FLEET.md retargeted · FLEET-NEW3 · RUNNING
- [ ] INFRA.MERGE 10-23 review queue merged · ROOT-MERGE · RUNNING · lanes/COORD-REVIEW-QUEUE.md
- [ ] INFRA.WATCH auto_owner watchers redeployed against this tree · COORD · TODO

## WAITS · who
### Waiting on the owner
- nothing yet
