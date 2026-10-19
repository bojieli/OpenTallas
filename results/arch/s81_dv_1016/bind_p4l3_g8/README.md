# p4l3 + G1 + G2 + G3 + G8 bind (S81-LBGAP/G8, 10-18)

= bind_p4l3_g123 (claude/lb2-s81-l0-1018 6bbd1e2c7) with the G8 bundle-age landing straps.
Land plan `results/arch/s81_dv_1016/landing/p4l3/land_plan.json` = `dv_land_pilot.py agebundle --plan-in landing/p4l2 --out landing/p4l3`:
per multi-lane bundle `<stem>_l<i>` -> one receiver, K_l = E_l + (A - age_l), age = ceil(N/2) + K + 1 (gate calendar R0 = G + N mod 2),
window re-checked at K per corner (F = ceil(-S1/T) in [K-D+1, K-1]).
`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4l/plan.json --out <scratch>/bind --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3.json` (12 min local).
Strict die_port_bind **PASS**. die.v differs from bind_p4l3_g123 ONLY in 44 landing `.k` straps (15 xr line bundles: E4 lanes -> K5; jw_E_l0 K 11 -> 12); no new cells, all windows fit D 4 / D 8.
bind_case.json landings.bundle_age_unequal = 1: hf_7N (seqhost host plane, N 58/59/59, E 28, D 8): l0 needs K 29 but its FF flight (21 cycles) is outside [22, 28] -> needs equal N per bundle in the plan (one more half-cycle station on l0) or a D 16 tile.
Not covered here (audit only, landing/p4l3 agebundle.frame_age_unequal): 24 x_frame bundles with N 6/6/6/7 lanes (frame lk straps, one D 4 crs4 ring per lane): K cannot equalise the age in D 4 -> plan (equal N) or frame RTL owner; frame lanes also have no hop-0 gate (G1 not applied to frames).
sim_kit_sources.f / die_kit_sources.f copied unchanged from bind_p4l3_g123 (module set identical).
