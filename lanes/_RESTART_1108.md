# Restart after the 11-08 02:2x weekly limit (COORD, 2026-11-08 04:28 PST)

All Claude lanes died at about 02:2x. Codex covered 02:22-04:26 and handed back at 04:26 (CODEX-LOG.md "## Handoff to Claude 2026-11-08 04:26 PST" + addendum 04:27). Its packets are handoff/codex_to_claude_20261108_0426.md, handoff/codex_gaps_to_claude_20261108_0427.md, handoff/codex_kv_0222_handback.md and handoff/codex_lane_snapshot_20261108_0426.md (large: grep it), plus the lanes/CODEX-*-0222.md reports. The reset handbacks appended at the end of each report supersede its earlier notes.

## Every successor
1. Read lanes/_BRIEF_COMMON_1107.md and lanes/_CORE_LANE_RULES.md in full.
2. Read the Codex reports for your scope (end sections first), then your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md since 11-07 20:00.
3. COLLECT first. Codex jobs in your scope are now yours. Never duplicate or stop a CPU-active job, except where a COORD ruling below says so. Keep every Codex HOLD_ROUTE / HOLD_CTS until you have viewed the geometry it waits for; then decide yourself.
4. Codex branches are on the intel2 hub (codex/*-0222). Verify each ref there and never use donor-only remotes. A Codex READY becomes yours: re-post it as READY with branch@sha + evidence, and I rule within 20 min.
5. Post your first STATE within 30 min. Post PARKED with the exact next step before you stop.

## COORD rulings 04:3x (decided by COORD; the owner may veto)
R1 QC NK vR7, intel1 unit oth-ubuntu-2392441-1794111263: no WNS/TNS change in more than 5 h = hung by intent (2-h watchdog). Stop that exact unit and continue from its retained 4_CTS checkpoint in a NEW output with the landed non-port hold scope. Owner: DIE-QC-92.
R2 HBM q_spb1 lockup form codex/qspb1-lockup-0222@94b8b7bc6f (LEC EQ 7848, PLACE PASS): released to CTS -> route -> sign-off as a parallel safe form; first to sign off wins. flat160 is a target, not a gate. Owner: DIE-HBM-92.
R3 HBM PMA eye (missing native PLL/PMA clock-eye view): optimistic academic model (OWNER 12.24). RX data valid centred on the rck edge +-T/4; TX pads timed against the forwarded clock with setup = hold = 0 at the pad. Record it as an assumption in the pad_clock data_inputs/data_outputs, not a measurement. Owner: DIE-HBM-92.
R4 HEAD HSPLIT e HOLD_ROUTE: DIE-HEAD-87 views the geometry and releases or redesigns. Same for the other HEAD holds.
R5 Private plan/latency adoptions: each needs a READY plan event (EQ/bind/count dry run) from its die lane; there is no blanket adoption.
R6 Extra-ECO exceptions (KV M5 e2/e6, S81 gunit ba0) stay OWNER-only: no --owner-override, keep the holds, and build the structural forms in parallel.
R7 Codex HBM /tmp deletion deviation: noted. It held no unique edits; no action.
R8 Codex tool-class READYs (native-kit-skip-dietop 6d82dfe0f6, q2nf-rep 2975d43186, prov-dir bd4edf5333, ista-respread 1ee657291e, plus others in the reports): approved in principle. ROOT-MERGE-52 lands each after tip-vs-base tests show 0 tip-only failures and the owning die lane confirms it in the queue.

## Successor table
| lane | scope | Codex reports |
|---|---|---|
| ROOT-MERGE-52 | lands approved branches: kitparam v2 claude/die-hbm-91-kitparam-1108@a2eb941596, qc53v4s claude/qc-types-7s-start-1108@66a32140a0b, then R8 items; tags; gunit forms after DIE-S81 PASS | CODEX-GAPS, CODEX-WAVE |
| KW-FIX-35 | kit-wave operator + FLOW class fixes: contract-kit TT IO rebind fix in signoff.py (COORD 02:0x); QC v4s switch + 3 types; QC-TYPES-8 02:15 class rows; ftwin/kcls/kitparam relaunches; c1x_C t5 | CODEX-WAVE |
| DIE-HBM-92 | HBM die owner + KCLS/PROV/receipt/reach, q_spb1 (R2), PMA (R3), QOUT count, HNX | CODEX-HBM, -KCLS, -OPEN, -REACH, -STALE |
| HBM-HARD-6 | HBM hard cores: q3_vm plan event, gqi, wbq_sw, OPSB PS2, OPSA P2g, Q2NF, RESTJ, TKM, kshare | CODEX-HBM-HARD, -Q2NF, -RESTJ |
| DIE-QC-92 | QC cores: NK (R1), SU1, NL, FIFO2, landing rings | CODEX-QC, -SU1, -SU1-PLACE-B, -CAL-FIFO2, -PARAM |
| QC-TYPES-9 | QC types: 24-row relaunch, sle_fw_v3, FW START, vFR | CODEX-QC-TYPES |
| DIE-S81-79 | S81 cores: bksel vJ/vK, gunit, t51 vD finish/sign-off | CODEX-S81 |
| S81-TYPES-7 | S81 types + stations + leaf congestion + RCK t16 split | CODEX-S81-TYPES, -RCK |
| S81-SVC-4 | svc_rs H8 R5 form RTL + compiler + SM/H4 + token | CODEX-SVC-RTL, -SVC-SM, -SVC-TOKEN, -TOKEN |
| DIE-HEAD-87 | HEAD LEP/HOST/CTL/TX/HSPLIT | CODEX-HEAD, -HEAD-CTL, -HEAD-TX-HS |
| HEAD-FORMS-3 | HEAD MESH/TILE/SC/SPN | CODEX-HEAD-MESH, -HEAD-SPN-TILE |
| DIE-KV-92 | KV cores: prompt vR ECO (fix the staging), PC43, Eo/Ei, FDI, Wi, SYS_C, e2/e6 structural forms | CODEX-KV, -KV-FDI, -KV-HUBS, -KV-REALIZATION, -KV-WISPLIT, handoff/codex_kv_0222_handback.md |
| KV-TYPES-4 | KV types | CODEX-KV-TYPES |
| AUTOCLEAN-10 | fleet disks: epyc6 root 120 GB (under the 150 floor), scratch2 51 GB; epyc2 root 93%; hub scratch2 94%; finish AUTOCLEAN-9 class c | CODEX-FLEET |
