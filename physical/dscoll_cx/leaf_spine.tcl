# Leaf clock repair for the 24k-sink collective engine. Preserve the ref_tile
# IO reference switch around the spine, which replaces TritonCTS on this port.
set cx_caller [dict get [info frame -1] file]
puts "CX_COLL leaf spine hook caller $cx_caller"
if {[string match {*pre_cts.tcl} [file tail $cx_caller]]} {
  source /src/physical/common_flow/clock_spine.tcl
  rename clock_tree_synthesis cx_spine_cts
  proc clock_tree_synthesis {args} {
    cx_spine_cts {*}$args
    estimate_parasitics -placement
    read_sdc $::env(QDM_SDC_DIR)/io_ref_skew.sdc
    puts "CX_COLL boundary referenced after balanced leaf spine"
  }
}
