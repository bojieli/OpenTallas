read_db /work/run/results/asap7/dp_kv3_sys_SD/base/1_synth.odb
set f [open /work/mapped_ff_census.tsv w]
puts $f "instance\tmaster\tclock_net\tclock_pin"
set counts [dict create]
foreach i [[ord::get_db_block] getInsts] {
 set m [$i getMaster];set mn [$m getName]
 if {![regexp {^(DFF|DHL|DLL|SDF|ASYNC)} $mn]} {continue}
 set cps {}
 foreach it [$i getITerms] {
  set mt [$it getMTerm];set pn [$mt getName]
  if {$pn in {CLK CK C GATE}} {
   set n [$it getNet];set nn "__UNCONNECTED__";if {$n ne "NULL"} {set nn [$n getName]}
   lappend cps [list $nn $pn]
  }
 }
 if {[llength $cps] != 1} {error "FF clock pin ambiguous [$i getName] $cps"}
 lassign [lindex $cps 0] nn pn
 puts $f "[$i getName]\t$mn\t$nn\t$pn"
 dict incr counts $nn
}
close $f
puts "ACTUAL_MAPPED_FF_CLOCK_NET_COUNTS $counts"
