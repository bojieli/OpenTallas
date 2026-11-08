source /work/rck_tx_compact.tcl
source /work/face_flops_release.tcl
rck_tx_compact_regions
rck_tx_pin_positions
source /work/chain_even_cfg.tcl
lappend ::ot_chain_res [list {u_bin_coll_i0[./]q} {u_tx_pin[./]pin_q}]
lappend ::ot_chain_res [list {u_tx_pin[./]u_enc[./]p_d} {u_txl[./]}]
lappend ::ot_chain_res [list {u_tx_pin[./]u_enc[./]p_v} {u_txl[./]}]
source /work/chain_even.tcl
rck_tx_pose_controls
source /work/clock_taps.tcl
rck_tx_assert_cohort
rck_tx_release_regions
