# Bind new repair/CTS cells by actual logical sinks before native legalization.
if {[llength [info commands ot_w2_original_detailed_placement]]==0} {
 rename detailed_placement ot_w2_original_detailed_placement
 proc detailed_placement {args} {
  source /src/physical/hbm_w2_parent_physical_20261005/membership.tcl
  ot_w2_original_detailed_placement {*}$args
 }
}
