# Separate exact-lib corner process: no default-corner ambiguity in multi-mode ORFS.
foreach f $::env(PT_LIBS) {read_liberty $f}
read_db /work/parent_clusters.odb
read_sdc /work/parent_clusters.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/parent_clusters.tcl
set fh [open /work/parent_cluster_$::env(PT_CORNER).txt w]
foreach c $CL {
 lassign $c name x y ung regs
 set p [get_pins ${name}_root/A]
 set t [get_property $p arrival_max_fall]
 foreach r $regs {
  set q [get_pins -quiet [list ${r}/CLK]]
  if {[llength $q]!=1} {error "parent measure missing register clock $r"}
  puts $fh "$name [expr {[get_property $q arrival_max_rise]-$t}]"
 }
}
close $fh
exit
