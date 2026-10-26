# el1011-q-kvd 2026-10-11 (PINKO=1 in jobs/route_master.sh): hard-tile pin-access keepout.  A parent route of hardened
# tiles died in pin access (qkd_d2d_h-305021c34 / -04612c41b: DRT-0073 u_rb/rst_n of ot_qkvd_sbuf): the tile routed
# its own M5 jog 12 nm beside the 84 nm M4 pin stub, so the parent had no up-via and only a phase-dependent planar
# access.  Before the tile's global route every signal pin gets an obstruction on the layer ABOVE its pin layer from its edge 0.60 um inward
# (+-0.06 um about the pin centre) so the tile routes nothing over its own stubs; post_drt_pinko.tcl deletes them
# after detail route so the exported abstract shows the gap (recipe: physical/hbm_accel_die_views/su/lane_pin_keepout_*).
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
source /src/physical/qwen_die_masters/pinko_add.tcl
