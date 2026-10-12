# POST_MACRO_PLACE (el1011-hbm-coll 2026-10-11, route_ps.sh INTERIOR=4): the hierarchical hfd_coll DIE TILE.
# Same dataflow rows as interior_macros_df.tcl with g_m[0] (bits 0..255) LEFTMOST: in the die tile every core-side pin
# (qp/qr in, rb_d out, control) is on the left face and the link side (ph_rx in, ph_tx out) on the right face
# (interior_pins_df4.tcl), so the 256-bit slices sit beside the core face.
set ::ot_hcoll_m0_left 1
source /src/physical/hbm_accel_die_views/coll/rtl_ps/interior_macros_df.tcl
