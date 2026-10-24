# TOPDOWN-PLAN (reconstructed 2026-10-24 06:30 PDT)

The previous coordinator host (rtx-pro, "localhost" in docs/FLEET.md) died around 2026-10-23 23:45 PDT.
Its local lane files (lanes/TOPDOWN-PLAN.md, lanes/GEOM-REVIEW.md, lanes/COORD-REVIEW-QUEUE.md, HANDOFF.md) were
never committed and are lost. This file is rebuilt from:

1. the coordinator's "OpenTallas Top-Down Day" artifact (snapshot 2026-10-23 18:45 PDT, main 0fea3794a);
2. COORD rulings quoted in main's merge messages up to 3e05af806b (23:14 PDT);
3. the claude/*-1023 branches that were still pushing when it died (tips 18:00-23:45 PDT), not in main.

Old fleet (rtx-pro, ot-epyc1..9, ot-gold*, agidock, pve1) is gone. New fleet, all Ubuntu 26.04, no GPU:

| alias | threads | RAM | disk free | role |
|---|---|---|---|---|
| localhost (84.32.71.203) | 256 | 755 GB | 3.3 TB | coordinator, central merge point ~/OpenTallas, only host that pushes to GitHub |
| epyc2 | 128 | 1 TB | 3.3 TB | die-level jobs |
| epyc3 | 96 | 1 TB | 6.9 TB | die-level jobs, big scratch |
| intel1 | 112 | 1 TB | 435 GB | tile / partition work (small disk) |
| intel2 | 112 | 1 TB | 435 GB | tile / partition work (small disk) |

Toolchain on every host: ~/.local/opentallas-tools/bin (verilator 5.050, yosys 0.68, opensta be771a0), docker +
openroad/orfs:latest = :asap7lock at the docs/FLEET.md digest. Each server has ~/OpenTallas cloned from `hub`
(= localhost); servers fetch from hub, never from GitHub.

## Gate flow (owner, 10-23 05:08)
G0 plan check -> G1 plan review (GEOM-REVIEW) -> G2 routing probe -> G3 partitions (kit, render, geometry PASS, P&R)
-> G4 abutted die (seam timing + routing) -> G5 token pass. Rules R2-R8 (see tools/die_plan/README.md). Clock: grid
taps at 400 um (CP1 r8 RULING 21:26), common latency 250 ps, face-flop spread and seam skew <= 80 ps.

## Die board at loss (best reconstruction)

| die | G0 | G1 | G2 | G3 | G4 | G5 |
|---|---|---|---|---|---|---|
| S81 | v4.7b PASS (main); v4.8 on s81-p9-r8eq unmerged | COND | v4.8 G2 PASS 31 probes (unmerged) | 6/7 frame kits FAIL review earlier; core-s81* hard cores in progress | not run | FAIL 6/6 entry replay; fc30 entry gaps lowered (tokj-s81-lower merged), fc30 status fault fix on s81-p9-fc (unmerged) |
| Qwen compute | PASS, G0C 52/56 (qc-p6-g0c merged) | COND | PASS | mixed; A0 v6 core clock drops on qc-p6-a0v6 (unmerged) | CP1 pair physically clean, seam timing unproven after grid-tap ruling | 3/4; xt1 0/64 pending re-run on bound_r8 (bind_smoke exists) |
| Qwen KV | v3.8h merged; v3.8s FIRM astk stations on kv-p8-hub (unmerged) + GEOM-REVIEW8 PASS (unmerged) | PASS (v3.8s) | open | IO only; hub_Ei P&R waits for clock variant spread <= 80 | not run | not run; kv41 bound top lint 0; hierarchical Verilator bench on tokj-kvslice (WIP); PV boot constants need W request-lane pads (kv-p7) |
| HBM d4g | fallback plan P7 merged | COND | partial | none | not run | held; HBM-ARCH B2 redesign WIP (hbm-arch, H-tree clock, 5 SerDes); binder4 physical/die_plan/hbm/r8 held back (COORD 23:10) |

## Lanes (dispatched 2026-10-24)

| lane | scope | host(s) | branch prefix |
|---|---|---|---|
| ROOT-MERGE | review + merge the finished unmerged 10-23 branches listed below; keep main green | localhost | (main) |
| FLEET-NEW3 | retarget tools/fleet/ot-run + tools/closure_loop/hosts.json + docs/FLEET.md to the new fleet; tool parity check | all | claude/fleet-new3-1024 |
| CP1-R10 | CP1 abutted pair on grid taps (r9 tools): seam setup @SS / hold @FF to 833 ps; decides the seam method | epyc3 | claude/cp1-r10-1024 |
| QC-TOK | Qwen xt1 re-run on bound_r8 (bind_smoke), then all 4 link tests; then R8 padding 875k -> <150k regs | intel1 | claude/qc-tok-1024 |
| QC-A0 | Qwen A0 cores re-kitted on grid taps (from qc-p6-a0v6), G3 gate | intel2 | claude/qc-a0-1024 |
| KV-TOK | finish tokj-kvslice hierarchical KV bench; KV PV W request-lane pads (kv-p7) -> final boot image; KV token tests | epyc2 | claude/kv-tok-1024 |
| KV-G3 | KV hub/row partitions from bound RTL on v3.8s (after merge), hub_Ei clock variant spread <= 80 | intel2 | claude/kv-g3-1024 |
| S81 | S81 v4.8 -> G3 frame kits with internal stations + core-s81 hard cores; triage 6/6 entry-replay failure | localhost + epyc3 | claude/s81-p10-1024 |
| HBM-ARCH | continue hbm-arch B2 redesign -> plan G0/G0C/G2, then lift the binder4 hbm/r8 hold | localhost + epyc2 | claude/hbm-arch-1024 |

## Merge queue (ROOT-MERGE), unmerged branch tips at loss

- kv-p8-hub-1023 (v3.8s FIRM astk stations) + geom-review8-1023 (+8, v3.8s PASS) -> clears the KV-P7 condition
- s81-p9-1023 (+8 incl. s81-p9-fc-lpr), s81-p9-face-1023, s81-p9-r8eq-1023 (v4.8 G2 PASS), s81-p9-fc, s81-p9-tool, s81-p9-tool2, s81-p9-cf
- core-s81-1023, core-s81-eng-1023, core-s81-svc-1023 (TT WNS -25 ps: record, not closed)
- cp2-tool-1023, tokj-s81-split-1023, kv-p7-hubtool-1023
- qc-p6-a0v6-1023, qc-p6-ftc-1023
- kv-p7-1023 (boot image on kv41, PV not final: record)
- NOT to merge yet: hbm-arch-1023 (WIP), tokj-kvslice-1023 (WIP), kv-p7-v38-1023 (G0 FAIL WIP), core-hbm-1023 (stopped by COORD)
- superseded, leave: kv-p6-*, qc-a0v2..v5, plan-*-1023 older, codex/*-1023 04:xx batch (pre-05:08 bottom-up)

## Queued lanes (waiting for a subagent slot; 20-concurrent cap reached 2026-10-24 07:05)
- DIE-STA: abstract-model (ETM/ILM) die STA validated vs flat stitched STA on CP1; flat die STA capacity on 1 TB host. (SDC lint + boundary-register guard given to CP1-R10.)
- PART-CAP: measure OpenROAD scaling at 400k / 800k / 1.6M / 3M cells on ASAP7 833 ps; find origin of the 400k cap; recommend partition size (fewer seams, fewer types).
- TYPE-DEDUP: collapse near-duplicate partition types (S81 74 ot_s81sl_leaf__t*, QC 20 / KV 5 / HBM 18 in near-duplicate groups) into one netlist with strap pins.
