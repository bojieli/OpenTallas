# Separate exact-lib corner process: no default-corner ambiguity in multi-mode ORFS.
foreach f $::env(PT_LIBS) {read_liberty $f}
read_db /work/parent_clusters.odb
read_sdc /work/parent_clusters.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/parent_clusters.tcl
# Map clock pins through OpenDB identities, so escaped generated instance names
# are literal names instead of STA glob expressions.
set clockpins [dict create]
foreach p [get_pins -hierarchical *] {
 set it [sta::sta_to_db_pin $p]
 if {$it ne "NULL" && [[$it getMTerm] getName] eq "CLK"} {
  dict set clockpins [[$it getInst] getName] $p
 }
}
set fh [open /work/parent_cluster_$::env(PT_CORNER).txt w]
foreach c $CL {
 lassign $c name x y ung regs
 set p [get_pins ${name}_root/A]
 set t [get_property $p arrival_max_fall]
 foreach r $regs {
  if {![dict exists $clockpins $r]} {error "parent measure missing OpenDB register $r"}
  set q [dict get $clockpins $r]
  if {[llength $q]!=1} {error "parent measure missing register clock $r"}
  puts $fh "$name [expr {[get_property $q arrival_max_rise]-$t}]"
 }
}
close $fh
exit
