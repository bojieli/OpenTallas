# SU-side CP block: the canonical CP pin coordinates (physical/hbm_cp_pin_margin_20261006/pins.tcl) minus the two
# native_launch pins (native steering now sits beside the cmdproc). Every die/seat pin lands on its own pin flop.
source /src/physical/hbm_su_cp_side_20261006/pins.tcl
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
