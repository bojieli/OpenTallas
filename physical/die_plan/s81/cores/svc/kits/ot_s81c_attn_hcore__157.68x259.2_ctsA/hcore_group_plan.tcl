foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_*.lib*]] {read_liberty $f}
read_db /work/run/results/asap7/hc_ot_s81c_attn_hcore_swr/base/3_place.odb
read_sdc /work/constraint.sdc
set ::env(OT_LEAF_AFF_REPORT_ONLY) 1
source /work/leaf_affinity.tcl
proc norm {n} {string map [list [format %c 92] ""] $n}
set NM [dict create]
dict for {n it} $la_ck {dict set NM [norm $n] $n}
set fd [open /work/hold_target_pairs.tsv];set lines [split [read $fd] \n];close $fd
set roots [dict create]
foreach line $lines {
 if {[string trim $line] eq ""} continue
 lassign [split $line \t] a b
 set names {}
 foreach z [list $a $b] {
  if {![dict exists $NM $z]} {error "HCORE_PLAN target missing $z"}
  set n [dict get $NM $z];lappend names $n
  if {[info exists la_par($n)]} {set r [la_find $n];dict set roots $r [dict get $la_groups $r]} else {dict set roots $n [list $n]}
 }
 lassign $names a b
 puts "HCORE_PLAN TARGET $a -> $b"
}
set fd [open /work/hcore_target_components.tsv w];puts $fd "group\tname\tx_um\ty_um"
set k 0
set U [[ord::get_db_block] getDbUnitsPerMicron]
dict for {r mem} $roots {
 set sx 0.;set sy 0.
 foreach n $mem {lassign [la_xy [[dict get $la_ck $n] getInst]] x y;set sx [expr {$sx+$x}];set sy [expr {$sy+$y}];puts $fd "$k\t$n\t[expr {$x/double($U)}]\t[expr {$y/double($U)}]"}
 set cx [expr {$sx/[llength $mem]}];set cy [expr {$sy/[llength $mem]}];set md 0
 foreach n $mem {lassign [la_xy [[dict get $la_ck $n] getInst]] x y;set d [expr {(abs($x-$cx)+abs($y-$cy))/double($U)}];if {$d>$md} {set md $d}}
 puts "HCORE_PLAN COMPONENT $k count [llength $mem] radius_um $md centre [expr {$cx/$U}] [expr {$cy/$U}] root $r"
 incr k
}
close $fd
puts "HCORE_PLAN CENSUS allFF [dict size $la_ck] target_components [dict size $roots]"
