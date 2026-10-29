read_db /work/kit/run/results/asap7/hbc_ot_hgi_sm_xload_cl2_ctlx/base/3_place.odb
set ::ctlx_block [ord::get_db_block]
source /work/guide_spec.tcl
set ::ctlx_move {}
foreach {n prefixes x0 y0 x1 y1} $::ot_mrg_spec {foreach p $prefixes {dict set ::ctlx_move $p 1}}
set ::ctlx_temporarily_firm {}
foreach i [$::ctlx_block getInsts] {
 if {[$i getPlacementStatus] in {FIRM LOCKED}} continue
 if {![regexp {^(DFF|SDF|DHL|DLL)} [[$i getMaster] getName]]} continue
 set n [string map {"\\" ""} [$i getName]]
 if {![dict exists $::ctlx_move $n]} {lappend ::ctlx_temporarily_firm $i;$i setPlacementStatus FIRM}
}
puts "CTLX preserve [llength $::ctlx_temporarily_firm] existing sequential locations during GPL; release before DPL"
source /work/macro_reg_guide.tcl
# Existing placement is reused; no synthesis, RTL or clock operation occurs.
global_placement -incremental -density 0.50
write_db /work/3_3_guided.odb
source /work/macro_reg_guide_release.tcl
foreach i $::ctlx_temporarily_firm {$i setPlacementStatus PLACED}
detailed_placement
check_placement -verbose
write_db /work/3_place_guided.odb
set ::env(OT_GEOM_OUT) /work/geom.tsv
source /work/geom_dump.tcl
