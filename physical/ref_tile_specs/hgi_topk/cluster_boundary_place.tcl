# The cluster's dedicated ingress flops capture each input data pin once.
# Preserve the receiver hold delay locally, then place existing transmit relay
# flops beside the hard lane pins instead of at the shared source centroid.
source /src/physical/dsrom_window_source/leaf_inhold.tcl
source /src/physical/ref_tile_specs/hgi_topk/cluster_control_hold.tcl
set ::env(OT_MPFLOP_PINS) {}
set mp {}
foreach i [[ord::get_db_block] getInsts] {
  if {![[$i getMaster] isBlock]} continue
  if {[[$i getMaster] getName] ne "ot_hgi_topk_lane_tile"} continue
  foreach it [$i getITerms] {
    set n [[$it getMTerm] getName]
    if {[regexp {^(pd|kin|ph)(\[|$)|^(clr|pv|mcr)$} $n]} { lappend mp $n }
  }
}
set ::env(OT_MPFLOP_PINS) [join [lsort -unique $mp] ,]
set ::env(OT_OFLOP_COLS) 8
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
