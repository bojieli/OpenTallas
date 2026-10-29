# TOK-HBM-6 (HBM whole-die token pass, 8 SM; successor of TOK-HBM-5)

## 2026-10-28 23:27 PDT START: base claude/tok-hbm-5-1028@a6cb3a86fd, worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2 (sparse). No live jobs inherited. Waiting for DIE-HBM-10 C25c + strict bind 0 (C25b strict = 463). Meanwhile: vehicle bench (no `<= #d`), calendar with host_to_provider = 4 cyc declared static boot path (COORD 23:23), mutant list. Park deadline 06:00 10-29.

## 2026-10-28 23:32 PDT PROGRESS (claude/tok-hbm-6-1028@b8172a5486)
- host_write_interval 5 edges [CHECKED own sim]; DRYRUN calendar C25b 4180334c + h2p 4: MISSING only plan commit; PRE rgap >= 24 needed (legs 53/44, 53/45). Mutant list M1..M6 (primary M1 pk5 off by one) in results/tok_hbm_6_1028/README.md. ASK to DIE-HBM-10 on valid pulses vs multicycle (DEFAULT 4-flop valid chain).
- Polling for C25c + strict 0 every 15 min (deadline 06:00 10-29).

## CODEX notes 2026-10-28 23:47 PDT
CODEX took over: bound PRE spacing and C25c programme readiness on codex/tokens-hbm-1028@fbb6ffeb5 (own sparse WT /srv/opentallas-scratch/claude/wt/codex-tokens-hbm-ready-1028). No live inherited token jobs; strict C25b463 blocks whole vehicle, C25c owned by CODEX HBM. Fixed real next-step gap: opt-in calendar --schedule-rgap and emitter --calendar-rgap now carry bound PRE spacing into emitted job217; defaults unchanged, numeric fields unchanged.25 focused compiler tests PASS, boundary rgap23 and4 damaged overrides fail closed. Actual161record C25b RT98 ->81PRE rgap24, +9720cycles/FUSED pass; no full token claim. HBM plans host transport20edges over6929um (old4 violates405um reach), +16bootcycles only. Inherited SM gin/qin seed-tie claim corrected by bind owner: intentional boundaries; mutant must hit interior link. READY shared compiler/root merge; next: committed C25c+side+strict0 ->actual calendar/programme/finite bound vehicle.
