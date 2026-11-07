proc n4_root {pin} {
  set net [$pin getNet];set seen [dict create];set count 0
  while {$net ne "NULL" && $net ne ""} {
    if {[dict exists $seen [$net getName]] || [llength [$net getBTerms]]} {error "LOCKUP_FORM cycle/port in chain"}
    dict set seen [$net getName] 1
    set dr {}
    foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend dr $t}}
    if {[llength $dr] != 1} {error "LOCKUP_FORM nonunique driver"}
    set it [lindex $dr 0];set i [$it getInst];set mn [[$i getMaster] getName]
    if {[regexp {^DFFHQN} $mn] && [[$it getMTerm] getName] eq "QN"} {return $i}
    if {![regexp {^(BUF|INV|HB)} $mn] || [incr count]>8} {error "LOCKUP_FORM arithmetic/non-direct chain: $mn"}
    set ins {}
    foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] eq "SIGNAL" && [[$t getMTerm] getIoType] eq "INPUT"} {lappend ins $t}}
    if {[llength $ins]!=1} {error "LOCKUP_FORM multiinput buffer"}
    set net [[lindex $ins 0] getNet]
  }
  error "LOCKUP_FORM disconnected chain"
}
set out [open /out/eligible.tsv w]
set skip [open /out/skipped.tsv w]
set count 0;set seen 0
foreach p [all_registers -data_pins] {
 set it [sta::sta_to_db_pin $p]
 if {$it eq "NULL" || $it eq ""} continue
 set di [$it getInst];set dn [string map {\\ {}} [$di getName]]
 if {![string match u_fcore.u_native.* $dn] || ![regexp {^DFFHQN} [[$di getMaster] getName]] || [[$it getMTerm] getName] ne "D"} continue
 incr seen
 if {[catch {set si [n4_root $it]} why]} {puts $skip "$dn\t$why";continue}
 set sn [string map {\\ {}} [$si getName]]
 if {![string match u_fcore.u_native.* $sn]} {puts $skip "$dn\tnonnative_source";continue}
 set paths [find_timing_paths -to $p -path_delay max -group_path_count 1 -endpoint_path_count 1]
 if {[llength $paths]!=1} {puts $skip "$dn\tno_unique_setup";continue}
 set sl [get_property [lindex $paths 0] slack]
 if {$sl<500} {puts $skip "$dn\tsetup_guard\t$sl";continue}
 set u [[ord::get_db_block] getDbUnitsPerMicron]
 set sb [$si getBBox];set db [$di getBBox]
 puts $out "$sn\t$dn\t$sl\t[expr {([$sb xMin]+[$sb xMax])*0.5/$u}]\t[expr {([$sb yMin]+[$sb yMax])*0.5/$u}]\t[expr {([$db xMin]+[$db xMax])*0.5/$u}]\t[expr {([$db yMin]+[$db yMax])*0.5/$u}]"
 incr count
}
close $out;close $skip
set m [[ord::get_db] findMaster DLLx1_ASAP7_75t_R];set u [[ord::get_db_block] getDbUnitsPerMicron]
puts "N4_LOCKUP_SELECT nativeFF $seen accepted $count DLLarea [expr {double([$m getWidth])*[$m getHeight]/$u/$u}] setup_guard500"
exit
