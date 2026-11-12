# HBM-GEOM-2 chain on t40w (5129a5aab081), 11-12

One compose-format delta: `hg2_t40w_chain_1112.json.gz`, base `hbm-vsn-xtap-t40w/plan_t40w`, giving t40c `87a764bcdc86`.
It applies in this order:

1. `hg2_1_phy_flip_mcb_resite`: PHY_NC and PHY_NW u_phy_Q move to y 889.92 with MX. The q_mcb_nw E face is re-laid (W window <= 880) and its bit sites are remapped.
2. `hg2_2_qb010_lift`: the q_b010 bottom macro group is lifted 17.28 um, and 8 stage regs are re-sited.
3. `hg2_3_m2_face_layer`: face_layers [M6, M4, M2] on q_mcb_nw.E and PHY_NW.W, and the 4 E-face slots of q_mcb_nw are on 3 layers.
4. `hg2_4_neio_ep_e52r_t40w`: d12_neio_ep_e52r rebased. NE_io internal_stations[14] (L8006_o) no longer exists in t40w, so its 1 op is dropped. d11_nwio_ep_w52 is already in t40w: all 59 of its ops are no-ops.

Conflicts: compose.py conflicts against l3011_dlhbm_1112 finds 0 overlaps. Apart from the 4 types above, t40w differs from the de3584 base only in q_hub_nw, PHY_NE, clock.ft_hop_lockup and latency.lanes.

G0 (tools/die_plan on main b35eaa100a + pinface):
- t40c: 567 E / 1841 W. t40w: 567 / 1841. No new ERROR.
- The 2 face-density errors from the 2-layer form (PHY_NW.W / NW_mcb.E, 7.0/um) clear with M2.
- WARN: 17 new / 17 gone. These are the same q_b010 lattice and reach warnings at the lifted y.

Strict two-pass bind (t40w recipe, src kw45/src_hbm_main_9fc09952cd_q0g_p18) on epyc9 t40cb:
- 92 / 420 / 0 errors, stale 0, uncovered 0. bind_report 72ba7c76d18d.
- R8 landing is the same file as t40w's (baeb6ad3b3d3).
- ot_dp_lk instances: 5253, the same as t40w, so no ft_hop_lockup is invalidated. The EQ control matches t40w (diff_vs_nophys 105, latency/names same).
- RTL against the t40w bind: only hbm_arch_NE_io.sv and hbm_arch_q_b010.sv differ, and only in reset relays (rrelay positions and depth: NE_io relays 24 -> 23). Nothing in the datapath changes.

M2 pin-access probe (m2probe/, OpenROAD asap7lock):
- Setup: 200 W-face M2 pins, one per 0.27 row (3.7/um), each to a boundary DFF. The die is 4.32 um and 8.64 um wide, so every cell sits within that distance of the pins.
- Result: detailed route ends with 0 violations and no pin-access errors.
- ppl snaps M2 IO pins to one track per row: offset 0.045, pitch 0.27. So M2 IO capacity is 3.7 pins/um. The event needs about 2.3/um on M2 (70 pins in 10 um over 3 layers).

Separate, not part of the chain:
- `hg2_kshare_refc.json`: kshare pin-file re-face (abcr v8e478a + pfr v700685) plus the 8 parent pins_file paths. It applies after the chain.
- `hg2_pvmw43_fallback.json`: pvm_W with the pv-pv channel at 51.84 and groups re-pitched to 717.12. This is a FALLBACK and is not in the event.
