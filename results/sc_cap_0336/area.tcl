read_db /work/1_synth.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set sums {};set nums {};set seqs {}
foreach i [$b getInsts] {
 set nm [$i getName];set m [$i getMaster];set master [$m getName]
 set group [expr {[string match {u_bound.u_core*} $nm] ? "core" : "wrapper"}]
 set area [expr {double([$m getWidth])*[$m getHeight]/$u/$u}]
 dict incr nums $group
 dict set sums $group [expr {[dict exists $sums $group] ? [dict get $sums $group]+$area : $area}]
 if {[regexp {DFF|SDF|DHL|DLL|LQN} $master]} {dict incr seqs $group}
}
set f [open /work/native_area.tsv w]
foreach group {core wrapper} {puts $f "$group\t[dict get $nums $group]\t[dict get $seqs $group]\t[dict get $sums $group]"}
close $f
