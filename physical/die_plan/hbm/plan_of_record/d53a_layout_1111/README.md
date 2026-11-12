# HBM next-event plan d53a_layout_1111 (HBM-COMPOSE-2 for DIE-HBM-100, 2026-11-11) DO_NOT_COUNT

Plan die_plan.json.gz sha256 746e88cc6a358d2f85244c55c020db0fdc5c5a8bbdad34524a8c116361e29817 = d52 9a52537c5f06 + in order (one delta at a time, G0 against the previous step, pure main fe0002fac6):
(a) opsa_b form B (DIE-LAYOUT-HBM 7869ac8d590e; opsa_b.py re-run on d52, all asserts passed, pins file provisional): types q_b113, q_b113__physical_v1. G0 551 -> 551, 0 new. Strict bind BIND_OK.
(b) q_spt0 + pv1 form E1 (VISLAYOUT2-HBM e1c0017ca4, ladder delta spt0_e1, positions only): q_spt0, q_spt0__physical_v1. G0 551 -> 551, 0 new. Bind OK, pad_flops 945867.
(c) E1b = E1 + L5076 +1 station on q_spt0__physical_v1 (4 -> 5, hops 343) and latency.lanes.L5076 41 -> 42 cycles, no latency-group member: q_spt0__physical_v1. G0 551 -> 549, 0 new, the two L5076 reach errors cleared. Bind OK, pad_flops 945214.
(svgr) DIE-LAYOUT-HBM svgr_top place fix (3b96fb9f16, 3 ops in core_macros.json, u_program_lo MOVE (116.64,8.64)->(116.64,434.7)): die_plan.json unchanged, core_macros.json.gz here; ot_svgr_top is instantiated by u_svg_Q{0..3}__t in q_hub_nw, q_hub_ne. Bind OK on this exact state (bind_t32): 92 partitions, 420 crossings, n_errors 0, stale 0, uncovered 0, pad_flops 945214.
Pending, not included: (d) option C +1 cycle on remaining seam-hop lanes (no explicit DIE-LAYOUT-HBM rows yet), (e) q_su30 +1-cycle relay split (VISLAYOUT2-HBM READY pending). stscan / route_supply were not re-run for d53.
