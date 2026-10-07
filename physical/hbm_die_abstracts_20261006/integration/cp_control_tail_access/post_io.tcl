# Canonical CP control-tail candidate: selected47.52um core, four body boxes.
# Harvey sole launch; pin override must precede placement/routing.
source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_post_io.tcl
source /src/results/physical/hbm_cp_pin_access_20261006/pins_only.tcl
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
