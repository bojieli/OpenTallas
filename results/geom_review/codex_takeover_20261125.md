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

## 11:33 PST follow-up

- HEAD C27 private hd_st_n4 root-only, epyc12:head-w9-fp/c27_alt_1125/fixed_ports_1125/geometry/{die,type_hd_st_n4}.png. Opened both. Fixed seam positions and 146.832 µm worst raw export hop. Four full-width feedthrough drawings still require seeing the stage sites in the exact placed checkpoint. Candidate is held for the coupled hd_tile reset gate and placed review.
- HEAD SerDes R1/R2, epyc12:head-serdes-refloor/r1_r2_1125/geometry/type_hd_serdes.png. Opened. East dmem has a clear flank. The cmem above the channel macro still makes the lone sub-28 µm throat. Move cmem a further 8.64 µm north and rederive the reset and clock references. Route held.
- S81 slice_station t26 attempt_7 (epyc8) and t42 cl4bd1432c attempt_9 (epyc2), exact kit run/layout_review/place/{layout,density}.png opened. Pin-track use 0.179/0.176 and no wrong-face pins. t26 has two dense northern landing groups and 521.1 µm reset/START fanout footprint. t42 has multiple northern density bands and 489.2 µm reset fanout footprint. Hold both for a precise source-to-sink reset-leg check and structural update where reach fails.
- QC sle_hc0 cl929603c0 cl38badc56 attempt_3 (epyc2), exact kit run/layout_review/place/{layout,density}.png opened. Peak local density 0.871 in north/west corner and right lower edge, continuous compact central/south placement plume, and absent computed fanout and clock checks. Hold for structural corridor and exact pin/tap-to-load review.

## 11:54 PST follow-up

- HEAD hd_tile, epyc12:head-w9-fp/tile_resite_1125, plan 96f94e38b8d4. Opened the type render. One existing station moved and the worst modeled wide-chain hop shrank from 573.1 to 398.2 µm. The central north–south corridor is continuous. Edge density still needs the exact placed checkpoint. PRE passes and route remains held.
- HEAD hd_serdes R3, epyc12:head-serdes-refloor/r3_straps_1125/geometry/type_hd_serdes.png. Opened. Three front-end macros have physical clearance. The blank zone from y400 to y1227 is reserved for PHY. Strap relocation passes PRE. Local u_hold placement and exact clock/reset distribution remain open.
- S81 t35, epyc12:FP-S81/tmpl/t35_leafdn_resite_1125, plan 248e79140d49. Opened exact render. The unchanged-width and unchanged-stage direct leg measures 371.582 µm. Four leafdown chains now clear the 405 µm modeled limit. Nine narrow slots remain, concentrated inside the central and south banks. Route held.
- QC slw_fe_v1 clfe325744 cl08d14f0d, epyc10:QC-C1O-COMPOSE/slwfe_drt_1125/geometry/type_slw_fe_v1__clfe325744__cl08d14f0d.png. Opened. Four redistributed x_stm_o stages use the interior channel, with worst modeled bit leg 240.464 µm. One west-edge feed-through still renders red; establish its exact station layout and west pin access before considering a route.
