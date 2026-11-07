plan_qc53 candidate v3 (DIE-QC-85, 2026-11-06 16:3x). Candidate only; plan_qc52 POR untouched.
= Codex START4 plan_qc53_candidate_v2 (sha256 6641f0fd..., intel2 /srv/opentallas-scratch2/claude/codex-qc-start-1106;
  copy epyc5 /srv/opentallas-scratch3/claude/dq84/qc53root/qc53v2.json)
  + SU2 south-channel event (su2_channel_1106, slw_su_l1 x2): GRT0 PASS on clcc vA, clcc vB, cla2 vB (Codex pre-START4 kits
    + gen geometry); clcc vA/vB then FAIL G2 setup_tt -182.8/-182.1 on the pre-START4 START broadcast class
    (u_cland_origin -> u_cland_fstart_rsn_o D, ~1100 um single cycle, QC-SETUP-RF1 class (c)) which START4 removes.
  + tap class qc53 (tap_density_class_1106/qc53, 50 types).
  + CBN ring split (delta_cbn_ring_split_1106.py, cbn_q00 x2): cbn_report.json. Their tap patch was measured pre-split:
    re-measure on their first 3_place (per tap README).
Reproduce: compose.sh <qc53v2 base>  -> sha256 63f66d25fcfb59845ac689ca3220e7eb8c8105febb61b7eca820c7372fcc592b.
Check: schema load + gen.py phys of slw_su_l1 x2, cbn_q00__cl622f65d2, slw_fw_v3 rc 0 (lane4 y 60.48, cl_rsn_i (4.32,25.92),
5 cbn ring children, fw_v3 tap_max_sinks 1200 density). Not composed: Codex delta_sul1_ring_split_1106 (alternative SU-l1
form for the same 2 types, dormant); su_l0 per-lane bin replica rule (DQ85-SUL0, building).
Adoption: ONE native re-bind (KW-FIX) + parent clock composition, then ONE batch relaunch.
