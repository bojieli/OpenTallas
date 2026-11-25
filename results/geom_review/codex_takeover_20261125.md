# OpenTallas geometry review, 2026-11-25

## HEAD W9 without C27, 84a700abf5bf

Viewed the die and nine changed type renders in epyc12 /srv/opentallas-scratch2/claude/head-w9-fp/gate_hold_c27_1125/{lean,heat}. The submitted plan republished and passed PRE with zero findings. The array remains symmetric around the centre spine, with the north and south PHY/PG reservations visible. The plan-scale PG outlines do not demonstrate continuity through the placed macro rails or seam pin order.

- hd_mesh_e has no macro obstruction. The 65-bit m_rx_ft bank readback has a 400.47 µm worst bit, with zero over 405 µm. PASS-COND for a placed review.
- hd_ctl has two overlapping west bands and another band touching a south SRAM corner. Peak estimated utilization 1.04. FAIL for routing until the overlap and corner are cleared on the placed view.
- hd_lep0N and hd_lep0N_w have narrow macro-edge corridors, with estimated peaks 1.33 east and 1.04 west. FAIL for routing. The known dsel cone and the crowded pin regions still need their scoped placement work.
- hd_tile has a 1.44 estimated peak at the south face of the upper core along the horizontal channel. The five macro sites stay fixed. FAIL for routing at the screened channel.
- hd_host_e leaves an open centre street beside the eastern hard core. hd_host_w has usable column gaps, with the prior SRAM seam clock finding still open. hd_mesh still shows the long unused end bands and narrow SRAM gaps from the prior placed FAIL. hd_spn_wshim_rx has open plan area with a single shown tap. Existing exact placed clock, pin, and PG requirements apply.

C27 stays held. Both reset-root moves put some reselected raw exports beyond reach. The plan-only candidate proceeds through bind, LATCHECK and G0.

## S81 c11leaf v4

Viewed epyc12 /srv/opentallas-scratch2/claude/FP-S81/render/c9s_tmpl/v4/type_ot_s81sl_leaf__{t35,t57,t70}.png.

- t35 FAIL. The 31-bit direct c_s connection spans 406.1 µm and the plot shows four narrow slots. The seeded move failed placement scoring and exposes CLK tap seats over 70 µm away from their owning cores.
- t57 PASS-COND for static work. Data legs stay within 403.1 µm. Several buses converge in the east vertical street beside three narrow macro gaps, so an exact placed pin, routing-density, and PG check is required.
- t70 BLOCKED. Data legs are within 404 µm, with one narrow macro gap in the central corridors. Four local reset consumers move from baseline depth 17 to 16. A separate depth-17 candidate remains in PRE.
