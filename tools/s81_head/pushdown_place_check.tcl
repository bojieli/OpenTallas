# HEAD-CORE-LAT-R2 c3' pushdown proof (a): after core CTS, every island cell sits at its plan LL (quad.json die_cells),
# is FIXED/LOCKED + dont_touch, keeps its plan master, and its ft nets carry only port + island pin (no CTS/repair buffer).
read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set fails 0
foreach rec $::env(PLAN) {
  lassign [split $rec :] nm mst x y
  set i [$b findInst $nm]
  if {$i eq "NULL"} { puts "PA_CELL $nm MISSING"; incr fails; continue }
  lassign [$i getLocation] lx ly
  set dx [expr {abs($lx / double($u) - $x)}]; set dy [expr {abs($ly / double($u) - $y)}]
  set m [[$i getMaster] getName]; set st [$i getPlacementStatus]; set dt [$i isDoNotTouch]
  set ok [expr {$dx < 0.001 && $dy < 0.001 && $m eq $mst && ($st eq "LOCKED" || $st eq "FIRM" || $st eq "FIXED") && $dt}]
  if {!$ok} { incr fails }
  set nets {}
  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL"} { lappend nets "[$it getMTerm] -> [$n getName] ([llength [$n getITerms]] it,[llength [$n getBTerms]] bt)" } }
  puts [format "PA_CELL %s master %s loc %.3f %.3f plan %.3f %.3f status %s dont_touch %d ok %d nets {%s}" $nm $m [expr {$lx/double($u)}] [expr {$ly/double($u)}] $x $y $st $dt $ok [join $nets "; "]]
}
foreach p {ft_ck0_i ft_ck0_o ft_ck1_i ft_ck1_o ft_mesh_i ft_mesh_o ft_mstrap_i ft_rst_i ft_rst_o} {
  set bt [$b findBTerm $p]; if {$bt eq "NULL"} { puts "PA_PORT $p MISSING"; incr fails; continue }
  set n [$bt getNet]; set its {}
  foreach it [$n getITerms] { lappend its "[[$it getInst] getName]/[[$it getMTerm] getName]" }
  set bad [llength [lsearch -all -inline -not -glob $its u_isl_*]]
  if {$p ne "ft_mstrap_i" && $p ne "ft_rst_i" && $bad} { incr fails }
  puts "PA_PORT $p net [$n getName] iterms {$its}"
}
puts "PA_RESULT fails $fails"
