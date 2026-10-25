# OpenTallas release tree (refreshed 2026-10-24 ~20:30 PDT by the rtx-pro coordinator from the 19:10 handoff + lane PARKED sections)

The original hand-edited tree (~/claude-takeover-20261007/RELEASE_TREE.md on rtx-pro) was lost with that host and
was never committed. This copy is rebuilt from the coordinator's "Top-Down Day" artifact (10-23 18:45 PDT), COORD
rulings in main's merge messages up to 3e05af806b, and the unmerged claude/*-1023 branches. Format follows
tools/auto_owner/release_tree_render.py. Gates are the plan-first flow (owner 10-23 05:08): G0 plan check, G1 plan
review, G2 routing probe, G3 partitions, G4 abutted die, G5 token pass. Owners are the 2026-10-24 lanes.
This file is now version-controlled on branch coord/state (GitHub) so it cannot be lost again.

## EDIT · rules
- Tick a line only with committed evidence (sha). Failed verdicts stay, struck through only when superseded.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS DONE BLOCKED.

## DIE seam · Clock, reset and seam method (all dies)
- [ ] SEAM.CLOCK Industry MSCTS spine + pair-skew/CPPR die STA (owner dec. 5) · CLOCK · RUNNING · FF hold FAILS on all 5 trial dies (-46..-417 ps, inter-tap skew)
  - [ ] SEAM.CLOCK.STA2 die_sta v2 reruns (half-period wrap fix 97fd4371ec) · CLOCK · RUNNING · intel2 die_sta pids, collect
  - [ ] SEAM.CLOCK.HEAD S81 head seam 81.9 ps TT: re-measure with pair metric · CLOCK · WAITS · → SEAM.CLOCK
- [ ] SEAM.RESET Adopt the unified reset tool (on main 850892f60) in CP1/KV hub/S81 frames · RESET · RUNNING · CP1 col_h10 kits in DRT
- [ ] SEAM.CP1 CP1 kits signed (seam PASS TT +434.5 / FF +104.9) · RESET · WAITS · r0 recovery -310 (per-tap rsync), r1 FF hold -6.9; reach leaf 6435e46354 unmerged

## DIE s81 · S81 (DeepSeek-V4.1 ROM layer die) + 4 head dies
- [ ] S81.G3 Frames g3k5/g3k6 · S81 · WAITS · 7 kits await GEOM; xa relay->bs2 -368 → SEAM.CLOCK, SEAM.RESET
  - [ ] S81.G3.CORES Hard cores + kits (SIGNED: vq, hrow r15, LLd, l5f, cfg7_seq) · S81 · RUNNING · C3 leaf re-kits epyc2, RTL boundary fixes, hcore WPRE
  - [ ] S81.G3.ST405 Station405 (t12 SIGNED) · S81 · RUNNING · 21 B routes; t33 repeater, t4/t32 relaunch
  - [ ] S81.CONST Drop constant output pins (owner dec. 8) · S81 · READY · s81-const@1402d0b088 approved
- [ ] S81.HEAD Head die · S81 · RUNNING · elemA c7 / elemB c2 routed NOT SIGNED; hd_tile/tap160 re-route after review
- [ ] S81.XDIE Reserve pair + pair-B endpoint, rebase on 26-slot ledger · S81 · TODO · real G0C 108 (not 91)
- [ ] S81.IR PHY supply + bump rows over SerDes windows (owner dec. 7) · S81 · TODO · IR 235-270 mV there
- [ ] S81.G4 Abutted die · S81 · WAITS · → S81.G3, SEAM.CLOCK
- [ ] S81.G5 Token pass · TOK-DS · RUNNING · entry 6/6 + L0/L2/L14/L20 control PASS; exactness → TOK.DS.COMP

## DIE qwen_compute · Qwen compute
- [ ] QC.CAP Adopt accepted capacity plan (G0C 56/56) on main · QC · RUNNING · qc-cap@806bcb4058 APPROVED-IF gates; xt1 re-run on this bind owed
- [ ] QC.G3.A0 A0 v7 NK/NL routes · QC · RUNNING · heavily congested -> structural fix; A0 +7 cyc vs 6 to price
- [ ] QC.G3.FTC coll_ftc g3i · QC · RUNNING · intel2
- [ ] QC.G3.TYPES Rebind G3 types on the capacity plan · QC · WAITS · → QC.CAP
- [ ] QC.G4 Abutted die · QC · WAITS · → QC.G3.A0, SEAM.CLOCK
- [ ] QC.G5 xt1 on main capacity plan (64/64 both clusters on rebind) · TOK-QK · WAITS · → QC.CAP

## DIE qwen_kvsys · Qwen KV
- [ ] KV.BIND Re-bind kv44 (owner dec. 9) · KV · RUNNING · bind 0 err; final verify live epyc2; B/C/D fixes to integrate
- [ ] KV.G3.HUB hub_Ei vL (unified reset tool on vK plan) · KV · RUNNING · vK GRT 0 overflow, pair skew 68.0/62.2, recovery +486 ps
- [ ] KV.G3.CORES KV hard cores (none SIGNED) · KV · RUNNING · pv_pair FF hold -10.75; head_eighth 216 x8 to collect
- [ ] KV.G4 Abutted die · KV · WAITS · → KV.G3.HUB, SEAM.CLOCK
- [ ] KV.G5 Boot + token · TOK-QK · RUNNING · boot stalls 528/7161: bugs A/B/C1/C2 -> kv43

## DIE hbm · HBM B2l (DS + Qwen)
- [ ] HBM.B2M B2m = B2l + true H-tree, seam OCV, SerDes IR, %g origin bug · HBM · RUNNING · trunk OCV seam skew 407-594 ps
- [ ] HBM.NATIVE Native B2l RTL integration · HBM · RUNNING · VM ring + SU/HC + IDX gates PASS; R-IDX wiring + transport delays left
- [ ] HBM.G3.CORES 89 core kits + 26 placement FAILs (core insertion) · HBM · RUNNING · early core taps
- [ ] HBM.G4 Abutted die · HBM · WAITS · → HBM.B2M, SEAM.CLOCK
- [ ] HBM.G5 Token · TOK-HBM · RUNNING · layer gate FAIL on SU/HC transport; DS 1,561-1,886 / QW 893-943 tok/s

## TOKEN · token-pass gate per design
- [ ] TOK.DS DeepSeek token · TOK-DS · RUNNING
  - [ ] TOK.DS.COMP Compiler gaps G-COMPILER-ROWS / G-NORMALIZE-SO · TOK-DS · TODO · main DS blocker
  - [ ] TOK.DS.R8 Price v4.8 landed pads (≤13 cyc) in latency tables · TOK-DS · TODO
- [ ] TOK.QW Qwen token (stg 527/527, head, attnret, xhead PASS; 1u 4,428 / 4u 11,844 tok/s) · TOK-QK · RUNNING · s8 bound-row on intel2
- [ ] TOK.FREEZE Final evidence run at RTL freeze · COORD · WAITS · → S81.G5, QC.G5, KV.G5, HBM.G5
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## INFRA · fleet and coordination
- [ ] INFRA.SIGNOFF 138 old modules need re-signoff (DBs lost) · S81 / QC / KV / HBM · RUNNING
- [ ] INFRA.DISK epyc2 scratch 87%, rtx-pro 83% (full 43 GB worktrees) · COORD · RUNNING · prune pass 2

## WAITS · who
### Waiting on the owner
- nothing open (decisions 1-11 recorded in BRIEFING)
