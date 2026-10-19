# Pure Tcl structural proof: real kit builder/emitter, fake DB buffers record
# actual parent-net depth independently of the estimator. No OpenROAD or STA.
proc clock_tree_synthesis {args} {}
source [lindex $argv 0]
rename ot_sv_buf ot_sv_buf_real
rename ot_sv_legal ot_sv_legal_real
proc ot_sv_legal {x y} {return [list [expr {int($x)}] [expr {int($y)}]]}
proc fake_buf {id cmd args} {
 if {$cmd ne "findITerm"} {error "unexpected buffer method $cmd"}
 return P$id
}
proc fake_pin {id cmd args} {
 if {$cmd eq "connect"} {set ::depth(N$id) [expr {$::depth([lindex $args 0])+1}];return}
 error "unexpected pin method $cmd"
}
proc ot_sv_buf {x y} {
 incr ::ot_sv_nb
 set i $::ot_sv_nb
 interp alias {} B$i {} fake_buf $i
 interp alias {} P$i {} fake_pin $i
 return [list B$i N$i]
}
proc sink {id cmd args} {
 if {$cmd eq "disconnect"} return
 if {$cmd eq "connect"} {lappend ::measured $::depth([lindex $args 0]);return}
 error "unexpected sink method $cmd"
}
proc run_case {name count} {
 set ::ot_sv_nb 1;set ::ot_sv_ns 0;set ::depth(root) 1;set ::measured {}
 set ss {}
 for {set i 0} {$i<$count} {incr i} {
  interp alias {} S$i {} sink $i
  # Sparse isolated points and two dense bands make deliberately unequal tree depths.
  if {$i==0} {set x 430000;set y 340000} elseif {$i<4} {set x [expr {400000-$i*110000}];set y 325000} else {
   set x [expr {20000+(($i*7919)%390000)}];set y [expr {10000+(($i*31)%60000)}]
  }
  lappend ss [list S$i $x $y]
 }
 set t [ot_sv_build $ss $::ot_sv_depth]
 ot_sv_emit_root $t root 230000 340000
 set d [lsort -integer $::measured];set mn [lindex $d 0];set mx [lindex $d end]
 puts "CLOCK_STAGE_CASE $name sinks=[llength $d] min=$mn max=$mx buffers=$::ot_sv_nb"
 if {$mn!=$mx||[llength $d]!=$count} {error "CLOCK_STAGE_NONUNIFORM $name $mn/$mx"}
}
run_case sparse_singletons 19
run_case planned_fullshape 26118
puts CLOCK_STAGE_PROOF_PASS
