# 2026-10-06 option B: the M2-M6 leaf (routes_l/lb_u45_m6) has rst_n setup 1,833 ps at SS; a 3-cycle path left -103.6 ps in the
# option-B quad (qb1_bd150), so the leaf reset is a 4-cycle path and the tile rst_n holds every value >= 4 cycles.
# H16 registered tile (ot_attn_tile_m6h1r): the hardened leaf ot_attn_hgrp_m6h1's rst_n (asynchronous reset of its
# valid / pipeline state) has setup 1,062.4 ps and hold 454.8 ps against the leaf's clk pin at SS
# (physical/hbm_attn_tile_r/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1_ss.lib): the leaf's internal reset distribution is
# longer than one 833 ps cycle, so no single-cycle parent path can meet it (the top-pin leaf: setup 1,638.6 ps).  The tile drives every leaf rst_n from its
# HC register and requires its own rst_n to hold each value for >= 3 cycles (a quasi-static reset; asserted in
# simulation by ot_attn_tile_m6h1r), so the leaf reset is a 3-cycle path.  Data, clock and uncertainty are unchanged.
set ot_leaf_rst {}
foreach ot_c [get_cells -hierarchical -filter "ref_name == ot_attn_hgrp_m6h1"] {
  foreach ot_p [get_pins -of_objects $ot_c -filter "direction == input"] {
    if {[get_property $ot_p lib_pin_name] eq "rst_n"} { lappend ot_leaf_rst $ot_p }
  }
}
if {[llength $ot_leaf_rst] == 0} { error "leaf_reset_mcp: no leaf rst_n pins found" }
set_multicycle_path -setup 4 -to $ot_leaf_rst
set_multicycle_path -hold 3 -to $ot_leaf_rst
