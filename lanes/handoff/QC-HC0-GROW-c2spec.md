# QC-HC0-GROW: C1 master mismatch + C2 core-wave spec (11-25 18:2x)
## Param check (R6 bind rtl epyc10 .../qwen_compute_c1p_r6_1125_bind/rtl/<hc0 type>.sv vs cb master param_wrap)
hc0 ring instances: ot_dp_clk_landing_cas #(W 515, DEPTH 4, STATUS_REG 1, WFALL 1, WREG 1, DSREP 8, RSTREP 19, PLACEREP 1) u_cland_rsn_i / u_cland_rsf_i; x_hc1_st_a_i W 517 same extras.
cb master sle_cland_w515_n(_300) = ot_dp_clk_landing_cas {W 515, DEPTH 4, WFALL 1, WREG 1, DSREP 1} (no STATUS_REG, RSTREP, PLACEREP). => NOT drop-in (ports ready/fault + rst replicas differ, 12,902 vs 11,606 cells, pin tables per master). C1 as built (existing masters) is INVALID; needs NEW masters.
## New masters (full kit each, unpinned epyc10/11, same recipe form as cbn_ring_split_1106/kits_recipes.json: plan_pins_contract, util 0.45, max_layer M5, land_slots d form hold_mux D4, strap_ports strap_k)
- sle_cland_w515_n_hc0n  (rsn_i, N face, 88.56 x ~51.84 est; params above; pin table = hc0 rsn_i N window order)
- sle_cland_w515_n_hc0f  (rsf_i; its own pin order, like w515_n_300 differs from w515_n in 359 positions)
- sle_cland_w517_e_hc0   (x_hc1_st_a_i, E face; no E-face master exists; C2)
Needs: pins_file per master from the hc0 plan pin table (plan_pins_contract), recipes row, kit gen (gen_core_kit_qc.py --module M --recipes R --plan P), core kit to sign-off, view export (qcviews). Cells per master ~12.9k. ETA: spec + pin tables 22:00; kit sign-off +6-12 h per master (est.).
## C2 per-type cut needed (cells FLAGS-CELLCHECK, area 446,106 um2): cut for 0.60 / 0.50; after 3 rings (38.7k) density; lane cores (29.6k each, u_u_xl, est size 0.026 mm2) needed beyond rings for 0.60 / 0.50
sle_hc0 cl05696ed1 104.9k/149.5k  0.748  3/4
sle_hc0 cl38badc56 97.0k/141.6k  0.731  2/4
sle_hc0 pv48712631 98.5k/143.2k  0.734  3/4
sle_hc0 pv6e886d59 98.5k/143.2k  0.734  3/4
sle_hc0 pvcaa93304 102.2k/146.8k  0.742  3/4
slw_hc0 cl1bc59e1c 104.1k/148.7k  0.747  3/4
slw_hc0 pvd0aa3ddc 94.4k/139.0k  0.725  2/4
slw_hc0 pvde134a90 99.9k/144.5k  0.737  3/4
Lane core spec (u_u_xl0_0..7, 29.2-30.0k cells each, 237.1k total): need pins_file from the instance boundary (lane<->u_u_xh0 bus width UNMEASURED), recipe family 'hc0_lane' to be added to qc_core_wave.py, port-register check (lane boundary regs by construction, 0 cycles). xh0 (55.2k) alternative.
