# p4m G8R bind (TOK-S81-GAPS/G8R2, 10-19)

Plan p4m = p4l + equal station count N per multi-lane bundle (`tools/s81_dv/dv_plan_eqn.py`, 73 half-cycle stations on
73 lanes of 25 bundles: hf_7N_l0 58->59 and the 24 x_frame bundles 6/6/6/7 -> 7).  Station at the arc-length midpoint of
the lane's longest wire interval (Codex G8R recovery: two stations may straddle a turn).
Land plan `landing/p4m` = `dv_land_pilot.py agebundle --plan-in landing/p4m_in` (p4m_in = p4l2 + the padded lanes):
age_unequal 0 (p4l3: 1, hf_7N), frame_age_unequal 0 (p4l3: 24), window_fail none.  The padded lanes' S1 are ESTIMATED
(one more half-cycle station), not die STA: die STA on this die is owed.
Bind table `bind/bind_table_p4m.json` (= p4l3 + land plan p4m, `bind/mk_table_p4m.py`).

`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4m/plan.json --out <scratch>/bind --bind real
 --bind-table results/arch/s81_dv_1016/bind/bind_table_p4m.json --land-plan results/arch/s81_dv_1016/landing/p4m/land_plan.json`
(~5 min local).  Strict die_port_bind **PASS**: 40 masters / 9,343 instances, every structural counter 0.
die.v sha256 d4d4d808464d19dcd6bcea87e4d6d116a4177dabd2edf8bc59ca1d34e0ceabc9.

Generator changes (dv_bind.py):
* frame hop-0 gates: 364 frame x lanes (landing inside the receiving frame's dsfd_cfifo_crs4) get the G1 hop-0 ICG with
  the gate calendar R0 = frame rst_n depth + 2 (crs4 rsync), G = R0 - N mod 2 (`frame_hop0_gates`).
* frame read epochs after the reset tree: receivers released before their x source are delayed by calendar stations
  on the frame reset pin, resolved source-first along the x chain (`frame_release_epochs`, cycle = error):
  29 frames delayed, max 15 edges, 238 stations.  Die-top landings use the source frame's actual (possibly delayed) reset.
* frame lk straps derived from the supplied land plan K (`frame_lk`): 122 frames, 0 differ from the table's static values.
dv_layer_compile.py: an x_frame lane without a die-top landing ages ceil(N/2) + K + 1 with K from the receiver lk strap.

Versus bind_p4l3_g8: +1,127 / -175 / 836 changed instance lines (also carries codex/s81-recovery-2323: PHY ck_hbm 900 ps,
16 ctrl ckh).  sim_kit_sources.f / die_kit_sources.f copied unchanged from bind_p4l3_g8 (same 40 masters).
