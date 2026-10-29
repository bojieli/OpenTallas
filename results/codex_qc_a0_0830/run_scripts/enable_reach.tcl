# Geometry-only K0/K2 enable source reach from actual cells; no timing constraints changed.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
proc cen {i dbu} {set q [$i getBBox];return [list [expr {([$q xMin]+[$q xMax])/2.0/$dbu}] [expr {([$q yMin]+[$q yMax])/2.0/$dbu}]]}
proc starts {net} {
 set todo [list $net]; set seen {}; set out {}
 while {[llength $todo]} {
  set n [lindex $todo 0];set todo [lrange $todo 1 end]
  if {$n eq "NULL" || [dict exists $seen [$n getName]]} {continue}
  dict set seen [$n getName] 1
  foreach t [$n getITerms] {
   if {[[$t getMTerm] getIoType] ne "OUTPUT"} {continue}
   set i [$t getInst];set m [[$i getMaster] getName]
   if {[regexp {^(DFF|SDFF|ICG)} $m] || [regexp {^ot_qwen_tile} $m]} {dict set out [$i getName] $i;continue}
   foreach p [$i getITerms] {if {[[$p getMTerm] getIoType] eq "INPUT" && [$p getNet] ne "NULL"} {lappend todo [$p getNet]}}
  }
 }
 return [dict values $out]
}
set f [open /out/enable_reach.tsv w]
puts $f "gate\tmaster\tk\tx\ty\tsource\tsx\tsy\tdistance_um"
foreach i [$b getInsts] {
 set nm [$i getName];set m [[$i getMaster] getName]
 if {![string match *g_icg.g_hop*u_icg $nm] || ![string match ICG* $m]} {continue}
 set t [$i findITerm ENA];if {$t eq "NULL"} {error "missing ENA: $nm"}
 lassign [cen $i $dbu] x y
 set src [starts [$t getNet]]
 foreach d $src {
  lassign [cen $d $dbu] sx sy
  set k [expr {[string match *g_hop*u_hop_ck/* $nm] || [string match *g_hop*u_hop_node/* $nm] || [string match *g_hop*u_hop_fa3/* $nm] ? 0 : -1}]
  puts $f "$nm\t$m\t$k\t$x\t$y\t[$d getName]\t$sx\t$sy\t[expr {abs($x-$sx)+abs($y-$sy)}]"
 }
}
close $f
puts "ENABLE_REACH_DONE"
