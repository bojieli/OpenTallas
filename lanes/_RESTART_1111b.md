# Restart table 11-11 b (second limit, 04:23 PST)

Every lane on the previous account stopped at about 04:23 PST with a 429 weekly limit. The owner logged in on a new account at 04:5x and said "continue". Codex never started the 04:23 handoff: there are no queue posts, and the only codex process is defunct. COORD set the autoswitch state back to `claude`.

Rule (owner 10-25): no mass resume. Fresh, short successors that COLLECT first and launch no duplicates (check ot-run/ps/docker first). Each successor reads its predecessor's last queue posts. Models (owner 11-11): Sonnet for die owners, merge, collect and ops lanes; Opus only for visual layout, geometry review and RTL. The Opus lanes used up the last account in about 45 min, so wave 2 is SMALLER and limited to work due at the 11:15 cut.

## Not stopped (alive, idle on waiters): KW-FIX-45 ab5dfa8d917e1dfee, TOOLS-2 ad4b3e1805056ebb3, CPL-HBM-3 a9b29b926bd6411b9, HBM-GEOM-2 a5bef7e85a448969c, QC over-reach a1f1c396e8f7f0ff6, cland/fe_v2 a97a81ad7fdc4d203, DIE-QC-97 (superseded, told to stop).

## Wave 1 (Sonnet, the 12:00 cut critical path)
| lane | predecessor | next step |
|---|---|---|
| ROOT-MERGE-59 | ROOT-MERGE-58 a6f7a2458edfdab0f | Trains on epyc8 (QC stdir, vsn6b-s7, KV reset-types cae1a9d9, KV cut 1eaac3b9af, then c1x 9736c44f, core-place dfd84bfc8a, kw-fix-46 fe9567210b94 plus REAP-DEAD). Die events go before tooling. |
| DIE-QC-99 | DIE-QC-98 a99adf02026293d75 | G0/G0C on s8/s9_reach (epyc4 die-qc-98/ev), EQ, lint, route_supply, then READY by 11:45. |
| DIE-HBM-100 | DIE-HBM-99 aff4a66904877ff43 | t10 plan e6bb764f (epyc7 hbm-cut-1111), strict bind, PHY_NC gen dry run, then READY with the S2 list (COORD 04:1x holds) by 11:45. |
| DIE-S81-87 | DIE-S81-86 ab6d37e816d6a96ad | Compose on BASE_1200 b5faa1ba with the dead-input delta last, collecting inputs at 11:15, then READY. |
| HEAD-94 | HEAD-93 a93ce40dcefc890b4 | lepB+S03 + hd_ctl C1 + start_q + H2 + 50 ps hd_serdes window + 10 ps margins, then READY. |
| DIE-KV-99 | DIE-KV-98 a24e827b363f0e3f8 | READY is posted and approved. Owes the strict-bind digest on bfe4c242 and the hg launch rows once cae1a9d9 lands. |
| S81-BIND-2 | strict binds a1c6e12355d54669f | Collect the dead-input re-prove (intel1) and the two binds (intel1). Deliver the proof sha and plan shas to DIE-S81-87. |

## Wave 2 (Opus, only what is due by 11:15; the rest post-cut)
CPL-KV-HG-2: ring_H veto review of 5 hgi types by 11:30. S81-GEOM-3: s_4N ft-lane deltas by 11:15. CPL-S81-LEAF-2: 27 ADOPT leaf deltas plus GRT probes. CPL-S81-SLICE-2. CPL-QC-4: cb* deltas plus cbn_q11/cbf_q00_s2 hold class.

## Wave 3 (post-cut, later): S81-ARCH-RTL, HBM-VSN-XTAP, HBM-HUB-ARCH, DIE-VIS-S81, VIS-TRIAGE-S81, CPL-S81-MISC (station/t51), CPL-KV-PV, KW-FIX-46 (stub-trim, REAP-DEAD), HBM-CORES (collect), DIE-PROTO (HEAD re-judge with count-align).
