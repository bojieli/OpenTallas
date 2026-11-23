# FABLE-FIX-KV-HG handoff (Fable lane restarted by COORD 11-22 20:2x PST; older 11-19 content: git log -- this file)
Goal: sign off kv3_hg (8 types: hg, hg_v1, v1p2..v1p6, hg_v3) + kv3_hgi (11: hgi, v1 x2, v2 x2, v3..v8). D29 rows to KV-PLAN-R6 by 01:45 PST 11-23 (cut 02:00), else D30.
Base: D28 plan 44c3cbf51e50, tree epyc8 /srv/opentallas-scratch2/claude/kv-plan-r6/d28/isolated_seal_takeover/rh12_rebind/selected_candidate, base json epyc8 kv-plan-r6/d29/base_d28.json. rt/current 8e110789fbee.
Peer: OPUS-FIX-KV-HGI-R6 (epyc8 opus-fix-kv-hgi-r6) runs builds I ask for. Do not overlap TAP-GRID-R5 (D29 softflop tap row covers hg x7), SINKSPREAD (pv), HROOT-R1, KV-PLAN-R6 ECTLRL row (hg ectl 37/26).
## State 20:3x
- Read: HGI-R6/R5/R4 handoffs, KV-PLAN-R6 + TAP-GRID-R5 + PRECHECK posts. D28 wave just started hg_v1p6, hg_v3, hgi_v4, hgi_v5 (no result yet).
- PRECHECK D28 hops for my types are 311-366 um (< 405) except hgi_v1 x2 i_ectl_Q_N_tN 482 um (stale to_um (133,935), real sinks hst2_g/hst3_g).
## Next
1. probe kits (OT_PROBE_THROUGH=1, --goal route) hgi_v2__cle0015330 + hg rep; measure old placed/GRT DBs; list all classes; D29 rows.
