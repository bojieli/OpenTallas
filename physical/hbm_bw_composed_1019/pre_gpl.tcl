# Preserve recipe-3 boundary semantics in their original order, then constrain
# only the remaining movable core cells. No generated duplicate hooks run.
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
set ::ot_bw_composed_boundary {}
foreach inst [[ord::get_db_block] getInsts] {
  if {[$inst getPlacementStatus] in {FIRM LOCKED COVER}} {
    dict set ::ot_bw_composed_boundary [$inst getName] 1
  }
}
source /src/physical/hbm_bw_composed_1019/core_band.tcl
