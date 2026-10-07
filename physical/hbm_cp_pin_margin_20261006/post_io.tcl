# CP pin-margin: the canonical 236 CP pin coordinates (results/physical/hbm_cp_pin_access_20261006/pins_only.tcl,
# place_pin lines only; no body fences: every pin now lands on its own pin flop).
source /src/physical/hbm_cp_pin_margin_20261006/pins.tcl
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
