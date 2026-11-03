# HBM plan event d44t (DIE-HBM-59/G0C, 2026-11-03)

d44s (die_plan a28b88a14d72, = d44q + hub tap_window 120) + the normal-FT real-S0 class fix (54687a1ee class:
check.py/G2 build S0 of a normal FT slot at the real input site, so plans sited against a moved-in S0 had
S0->S1 hops of 400-950 um). Plan dir sidecars = d44q/d44s (DIE-HBM-53 d44o_cm + d44q die_plan); die_plan sha in SHA256SUMS.

Change: for the 118 (type, slot) pairs flagged by G0 stations/hops or G0C reach on d44c/d44q (flagged_slots.json),
tools/die_plan/ft_s0_resite.py re-sites the internal stations S1..S(k-1) along the in->out path from the real
input site (ft_corridor DP, obstacles = placement_obstacles.placement_boxes + 1.08 um keep-off, other slots'
bit sites reserved); regs_um[1:] = per-stage medoid bit site. 95 slots re-sited (61 keep the station count,
34 get +1..+3 stations -> latency.lanes rewritten by gen.py latency --inplace; latency check 0 errors); 23 slots
KEPT unchanged (no chain within 364.5 um): q_su31(+pv1) L5/L34/L35/L6b r0_1, q_su00/01/10(+pv1) L730x*, q_b112(+pv1)
L700/L701, q_su30(+pv1) L736x3, q_b101_nw L12x1, q_su11_pv1 L31x1, root L4x1 -> need window/pin moves (next event).
Ledger: ft_s0_resite_ledger.json (per slot: stations before/after, hop before/after, added cycles).
Windows, pins, outlines, cores and other slots are unchanged. NO core-kit change (partition types only).
OWED: the added stations change lane latencies (hbm_arch_b2o_lat_pkg.sv) -> TOK-HBM source/schedule event before
any HBM type build (types are held, OWNER 11-02).

G0+G0C (tools/die_plan/check.py --completeness, origin/main 7cf44d5c0 tools), errors / clean types (release g0c_split):
  d44c 250 / 44 of 81;  d44q 250 / 44 (identical message set);  d44s 250 / 44 (identical);  d44t 74 / 59 of 81.
  by class d44s -> d44t: reach 56->22, stations 117->22, hops 63->16, core_faces 8->8, geometry 4->4,
  street_die_leg 2->2, merged_clock_view PENDING-VIEW 128->128, latency 0->0. 15 new messages (neighbour-seam
  reach 371-392 um in q_b011/q_b112, L6b/L700 S0, L736 hop 13) listed in g0/g0c_report_d44t.json.gz.
