# Restart after the 11-08 11:12 Claude limit and the 12:15 Codex limit (COORD, 2026-11-08 17:1x PST)

Claude lanes all died at about 11:12. Codex covered 11:13 to about 12:15, then hit its own limit (until 11-12 23:16) and wrote NO "Handoff to Claude" section. Its reports stop mid-step. The owner re-logged in at 17:0x. Nothing but the autopilot acted on results for about 5 h. Count was 238 at 10:55 (S81 60/62+27/205, HEAD 4/4+17/25, QC 25/26+1/119, KV 32/32+1/56, HBM 71/105+0/81).

**Binding constraint now is DISK, not CPU or RAM.** 17:07: hosts admit 2.5 TB RAM at load 9-50/128, but intel1 scratch2 25 GB and epyc4 root 98% REFUSE; hub scratch2 65 GB, epyc5 35, epyc6 55. New work: put it on the host with the most free scratch, keep --disk requests measured, delete your own finished scratch as you go.

## Every successor
1. Read lanes/_BRIEF_COMMON_1107.md and lanes/_CORE_LANE_RULES.md in full, then this file.
2. Read the lanes/CODEX-*-1113.md reports for your scope (end first; hub-only lines were merged in at 17:1x), then your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md since 11-08 09:00. Codex branches are on the intel2 hub (codex/*-1113).
3. COLLECT first. Codex and predecessor jobs in your scope are now yours, and many finished in the last 5 h with nobody reading them. Never duplicate or stop a CPU-active job. Codex's HOLD_ROUTE/HOLD_CTS stay until you view the geometry they wait for; then decide yourself. Codex was in watcher mode, so a "no adoption / no POR / no merge" note means it was not allowed, not that the idea was rejected: if the evidence is good, post READY.
4. A Codex READY becomes yours: re-post READY with branch@sha + evidence.
5. First STATE within 30 min. Keep lanes short: finish your scope or post PARKED with the exact next step. Do not park early on a limit warning.
6. Answer the GEOM REQ rows of your die in LOOP-GAPS in one batch: view a representative per class, post SMELLS, or mark superseded.

## COORD rulings 17:1x (the owner may veto)
R1 Enable `--c-old-keep-h48` (landed 685b58b80c3) in every host's standing OT_AUTOCLEAN_ARGS. Under the owner's 11-07 and 11-08 cleanup orders and my 08:0x .keep ruling: only 2_1..2_4/3_1..3_5/4_1_cts intermediates, only when finished or superseded and not resume-pending or referenced. Owner: DISK-URGENT lanes. Positive control on one host first.
R2 Hub cold protected trees (die-head-48, flow-21, ss24, ss32, kw21/src_c926f, kw23/src_e9eda): HEAD reports die-head-48 has no caller left. A tree may be archived to AGIdock and removed only after the full deletion safety list passes (references grep, live, PROTECTED union, git HEAD). Trees holding counted views stay. No same-path relocation.
R3 t50 kw10 auto-resign waiter with its captured 100 GB floor: admission floors are not sign-off rules. If still waiting, cancel that exact client and re-sign through the canonical frontend (50 GB floor). Owner: S81-TYPES.
R4 Output-endpoint hold misses in the ECO near-miss census: align the ECO helper with sign-off's port-only classification (sign-off assigns these to the parent, NEEDS_PARENT counts). A tool alignment, not an extra ECO allowance: one iteration, <=30 ps, <=100 of the remaining endpoints. Owner: KW-FIX.
R5 SVC R5 +77.76 um: stays no-growth under Option C. Raise it again only with the actual repartition result.
R6 E6 anonymous 16 GiB OOM at 11:26: no owner found, no rerun. Closed.
R7 Codex and predecessor class READYs (list in ROOT-MERGE scope): approved in principle. ROOT-MERGE lands each after tip-vs-base shows 0 tip-only failures and the owning die lane confirms in the queue.
R8 Owner rulings of 11-08 stand: ECO exceptions KV e2/e6 + S81 gunit ba0; resume not rebuild; all class fixes + relaunch; types safe by construction (relays, matched taps, nearest reset taps); Fix A hold-safe hops; Fix B macro congestion budget; S81 Option C.

## Successor table
| lane | scope | Codex reports |
|---|---|---|
| ROOT-MERGE-53 | Land every unmerged READY since 11-08 09:00 (scan the whole queue by sha). Known: kw-fix-35k-supersede-keep 7fe4a970bb; kw-fix-35cv-autoviews 18e54f8be90; die-head-87-coretap-esc cb13e19342a; hbm-hard-6-ep c0501e8f63; codex/qc-lec-escidx a5644801c46; codex/qc-hc-kwrs-comments ab748ad669; codex/clock-density-f4 55bd0e1c2b3; codex/hbm-gen-budget a056e5a54e; codex/hbm-unbound-input 224a127d48. Then tags. | CODEX-GAPS |
| KW-FIX-36 | kit-wave operator + FLOW class fixes. In order: (a) KV SRC-INCOMPLETE on epyc4/5 (composed_rtl missing, repeating every tick in the autopilot log); (b) UNINDEXED-SRC-STALE relaunches (~166 kits, one batch per die, restage step); (c) ECO tool bug on GRT-routed clocks (blocks S81 t51 and HBM vecd4ae); (d) RC model correction (estimate 1.3x under routed); (e) composed queue_src grammar (kv3_io_cor, q_su11 enqueue rc 1); (f) new kit output off the hub; (g) R4. Then read autopilot/structural.tsv 11:00-17:00 and batch by class. | CODEX-WAVE, -WAVE-ECO, -WAVE-SOURCE, -LEF-CLOCK |
| DISK-URGENT-2 | intel1 + intel2 (hub) scratch2: intel1 25 GB, hub 65 GB. Target 300 GB each. R1, R2. Delete superseded and terminal-FAIL attempts first. | CODEX-FLEET |
| DISK-URGENT-3 | epyc4 (root 98%), epyc5, epyc6, epyc2 scratch. Target: every host admits and >=150 GB scratch. R1. | CODEX-FLEET |
| DIE-S81-81 | S81 cores: bksel + split, gunit bf forms, t51 ECO, t50 | CODEX-S81, -S81-LEC, -S81-STATION |
| S81-TYPES-10 | S81 types: 38 congestion rows, leaf vRF/vCH, COLH south channel draft, RCK TX/RXB/RXS, stations, R3 | CODEX-S81-TYPES, -S81-RCK, -S81-RCK-TX, -S81-RCK-RXB-PHYS |
| S81-SVC-6 | svc_rs H8/R5, SM, compiler, DS + QW token | CODEX-SVC-RTL, -SVC-SM, -SVC-TOKEN, -TOKEN, -DS-EPOCH |
| TYPE-SAFE-3 | relay and hold-safe construction events for the current plans on all dies | CODEX-HBM (TS2 notes) |
| DIE-HEAD-88 | HEAD LEP/HOST/CTL/TX/HSPLIT | CODEX-HEAD, -HEAD-CTL, -HEAD-TX-HS |
| HEAD-FORMS-4 | HEAD MESH/TILE/SC/SPN | CODEX-HEAD-MESH, -HEAD-SPN-TILE |
| DIE-QC-94 | QC NK, SU1, FIFO2, CTLM, landing rings | CODEX-QC, -QC-SU1 |
| QC-TYPES-11 | QC types: 38 waiting on child core, HC forms, SETUP-AT-GRT class | CODEX-QC-TYPES, -QC-TYPES-REACH |
| DIE-KV-94 | KV plan, FDI, PC, hubs, PHY; red test_kit_reset_contract[qwen_kvsys] | CODEX-KV |
| KV-TYPES-6 | KV types: PDN-0006 class (exact-native PG packet, f90cb5cb9e), PV, waits on child | CODEX-KV-TYPES |
| DIE-HBM-93 | HBM die owner: plan events, LAT, KCLS, SU batches, 60 types waiting on child cores, vsN4/5, q_spt | CODEX-HBM, -HBM-KCLS, -HBM-OPEN, -HBM-SVGR, -HBM-STALE |
| HBM-HARD-7 | HBM hard cores: Q2NF (F4 pilot), RESTJ C, OPSA P2h, GQI prune, EP, kshare, TKM | CODEX-HBM-HARD, -HBM-OPSA, -HBM-Q2NF |
