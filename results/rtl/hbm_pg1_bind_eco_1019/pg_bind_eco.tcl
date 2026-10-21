# PG-binding-only ECO on a CLOSED final ODB (LEAD2-S81/NATIVE 10-19).
# Cause (OpenROAD dbGlobalConnect.cpp:163): global_connect skips dont_touch instances, so CTS/wire/place buffers
# inserted after the PDN-time global_connect and then protected never received VDD/VSS ITerm bindings.
# This ECO binds exactly those terminals (expected net from the block's own global-connect rules), restores each
# instance's dont_touch flag, proves the signal netlist + placement + dont_touch set are unchanged, and audits all terminals.
source /out/native_pg_binding.tcl
read_db /input/6_final.odb
set block [ord::get_db_block]
proc sigfp {block path} {
  set fh [open $path w]
  foreach net [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} [$block getNets]] {
    if {[$net getSigType] in {POWER GROUND}} continue
    set its {}; foreach it [$net getITerms] {lappend its "[[$it getInst] getName]/[[$it getMTerm] getName]"}
    set w [$net getWire]; set wl [expr {$w eq "NULL" ? -1 : [$w length]}]
    puts $fh "N [$net getName] [$net getSigType] wl=$wl [lsort $its]"
  }
  foreach inst [$block getInsts] {
    puts $fh "I [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] dnt=[$inst isDoNotTouch]"
  }
  close $fh
}
sigfp $block /out/pre_signal.txt
ot_pg_audit_snapshot $block /out/pre_audit.json
set mapping [ot_pg_prepare $block]
set bound 0; set insts 0; set dnt 0
set fh [open /out/bound_terminals.tsv w]
foreach inst [$block getInsts] {
  set pend {}
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "$why [$inst getName]"}
    set exp [ot_pg_expected $mapping $inst $term]
    set act [$term getNet]
    if {$act eq "NULL"} {lappend pend [list $term $exp]} elseif {$act ne $exp} {error "OT_PG_WRONG_NET [$inst getName]"}
  }
  if {![llength $pend]} continue
  incr insts
  set was [$inst isDoNotTouch]; if {$was} {incr dnt; $inst setDoNotTouch 0}
  foreach p $pend {lassign $p term net; $term connect $net; incr bound
    puts $fh "[$inst getName]\t[[$inst getMaster] getName]\t[[$term getMTerm] getName]\t[$net getName]\tdnt=$was"}
  $inst setDoNotTouch $was
}
close $fh
puts "OT_PG_ECO bound_terminals=$bound instances=$insts dont_touch_instances=$dnt"
sigfp $block /out/post_signal.txt
set rep [ot_pg_audit_snapshot $block /out/post_audit.json]
if {[dict get $rep failure_count]} {puts "OT_PG_ECO_POST_FAIL [dict get $rep failure_count]"; exit 2}
puts "OT_PG_ECO_POST_PASS checked=[dict get $rep checked]"
write_db /out/6_final_pgbound.odb
foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} e]} {puts "OT_PG_GRID_$n FAIL $e"} else {puts "OT_PG_GRID_$n PASS $e"} }
exit 0
