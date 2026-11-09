# Restart after the 11-08 20:30-21:30 Claude 5-hour limit (COORD, 2026-11-08 22:0x PST)

All lanes stopped between about 20:30 and 21:30 on the 5-hour limit, which reset at 22:00. Codex stayed limited and did not act. The autopilot kept launching (33 in the 20h, 34 in the 21h). Jobs ran detached under ot-run and many have finished unread. Count at 19:59: 240. Main dac437dbaad (train J). Train L e87b24952da was in tip-vs-base.

**Binding constraint: disk, and the limit on our own tokens.** 22:01: epyc6 REFUSED (scratch 49 GB), epyc5 scratch 23, intel1 58, hub 114, epyc2 91, epyc4 175. Fleet CPU is mostly idle. Keep lanes short and finish scope, or post PARKED with the exact next step. No polling loops that wake you to report nothing: arm one watcher for the terminal state, and stop.

## Every successor
1. `cd /` first in every shell. Read lanes/_BRIEF_COMMON_1107.md and lanes/_CORE_LANE_RULES.md, then this file, then your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md since 17:12, ending at its last post.
2. COLLECT first: predecessor jobs in your scope are yours. Never duplicate or stop a CPU-active job. Many have results nobody has read.
3. First STATE within 30 min. Heavy jobs via ot-run. Put new work on the host with most free scratch; none on epyc6 or epyc5 until they recover. Reclaim your own finished scratch as you go.
4. Never run git commands inside the working tree of intel2:/home/ubuntu/OpenTallas or localhost /home/ubuntu/OpenTallas. Cloning from, fetching from and pushing your branches to the central repo intel2:/home/ubuntu/OpenTallas are the normal path (_CORE_LANE_RULES line 7). Your worktree is your own, never a scratchpad directory you did not create. Queue posts via ~/coord/bin/coord-commit.sh, verified on origin/coord/state. Say "signed off".
5. Standing owner rules: only sign-off blocks; targets not gates; no retries of an unchanged form; two strikes -> conservative re-form; small fix and structural form in parallel; one over-limit ECO with --owner-override citing OWNER RULING 17:5x, never ask; pin cycles cheap; no new restrictive rules; closure first, tok/s loss accepted.

## COORD rulings 22:0x (owner may veto)
R1 QC switch: the 21:30 default has passed and no bound relay plan exists on the base. KW-FIX-39 launches it now: base 7e4789251637 + wave/bind_v4nS, src_lfq with the st_a form (QC-TYPES-12's identity posts). The relay event is a second switch for its 18 types only. QC-MEM9 lane files stay out of the switch src; they enter when the EXTRA form lands, as type-local rebuilds of the 8 su_lane cores.
R2 One plan switch per die. Before any switch list the running rows it supersedes and keep rows past route unless their inputs change.
R3 Functional transport errors outrank type counts when a lane must choose. No counted view is un-counted until its replacement signs off.
R4 S81 t51 vD: its one ECO is exhausted (TT -35.31 after). No second ECO. Structural form only.
R5 HBM host control-plane link at bound transport is ERROR, loud, by arithmetic (TRANSPORT-3-SWEEP 20:27): DIE-HBM-94 owns it.
R6 HBM q_spb1: TT -78.61 / FF -200.04 routed, not a near miss. Re-form.
R7 Dedupe proceeds only under STORE-1's rechecks (my 20:0x ruling: exclude container-mounted trees, kit/run trees, wave src, non-tracked files; manifest; sampling verifier).
R8 Merge: every READY since 20:00 is approved subject to the die owner's CONFIRM and tip-vs-base, except QC-MEM9-RTL (needs 64-edge LEC + PROOF bench) and die-head-88-tapbal-esc (needs a real CTS run). Requests addressed to a parked lane belong to its successor.

## Successor table
| lane | scope |
|---|---|
| ROOT-MERGE-55 | Land train L (e87b24952da, check its tip-vs-base), then M (RCK 9c2a8b7c9f8a + transport-2 6c1693a734 + picker follow-up 84ac53507bb), then QC-TRANSPORT-FIX 259223d3910, die-s81-81-pkrst 97e557d9a03 (opt-in profile files only), every other READY since 20:00. Tags after each train. Answer: main's ot-run lacks ac3b's admission_unit and cancel-receipt code, missing merge or deliberate? |
| KW-FIX-39 | Wave operator. R1 first. KV switch when ready, S81/HEAD relay switches. Failure class loop by hour. Interim picker gaps. Collect t29 ECO. RC probes. Keep the 11-type plan_final3 scope for HBM. |
| AUTOCLEAN-12 | The owner's no-agent disk automation is the top infrastructure item. Epyc4 dry table to COORD (AUTOCLEAN-11's 40-min plan should be done), --union-real-sources-only on the EPYCs, lifecycle timer. Epyc6, epyc5, intel1 first in applying. Branch claude/autoclean-11-lifecycle-1108@4fa12e097b on epyc4. |
| STORE-2 | Dedupe pilot: STORE-1 branch 051f8616f05 (rechecks, --exclude, control tree, verifier), recheck on epyc5 was running without --go. Apply R7 epyc5, epyc6, then the rest, one line per host. |
| TYPE-SAFE-4 | Relay and hold-safe events. S81 plan 37daba57606c91b0 to READY for one switch; QC 18-type relay on base 7e4789251637; HEAD; KV/HBM as needed. |
| DIE-S81-83 | S81 cores: bksel P+parent, gunit bf, t51 structural (R4). See DIE-S81-82 posts and the render note on W-face density in GEOM-REVIEW.md 19:3x. |
| S81-TYPES-11 | S81 types incl. leaf batch, COLH, RCK forms, RXS, stations. |
| S81-SVC-8 | Collect the H8 lock-step (compiler 1c287a1974), set H8_CALIBRATED only from it; R5 repartition; SMD next step. |
| DIE-HEAD-89 | HEAD all: LEP re-form (post real CTS for tapbal-esc), TX route, CTL, HSPLIT, HOST, TILE vH12a route, SPN ECO hold pass, MESH (restore lec.py), SC. Die must measure LEP's 85-entry window before it counts. |
| DIE-QC-95 | QC cores: NK ECO + vR8c, and QC-MEM9-RTL's open items (B2 ECO, 64-edge LEC, PROOF bench, READY, then 7 lanes). |
| QC-TYPES-13 | QC types after the switch; glue LEC, coll_core, native59; classes. |
| QC-TRANSPORT-FIX-2 | Station join and su_idle fixes (predecessor posted path 1 only). Then QC items from TRANSPORT-3. |
| DIE-KV-95 | KV plan and types together: composed plan bind2 -> READY to KW-FIX-39; PC reset-contract LEC class (457 -> 43 pilot); FDI, hubs, PHY. |
| DIE-HBM-94 | HBM types and die: q_b* PDN/cell-cap family, final3 keys, R5, R6, hub-kit abstract census, d44v_epm follow-through with HBM-HARD-8. |
| HBM-HARD-8 | HBM hard cores: RESTJ C (hung check), OPSA0/1 re-forms, Q2NF, GQI, kshare, TKM; EP: d44v_epm private counter run 2 result, PLANS re-point, READY-COUNT. |
