set r /srv/opentallas-scratch/claude/codex-pvm-mirror-census
set odb [lindex [glob /work/results/asap7/*/base/1_synth.odb] 0]
read_db $odb
foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*SIMPLE*RVT_TT*.lib*] {read_liberty $lib}
proc tie_bindings {path} {
 set f [open $path w];set rows {}
 foreach inst [[ord::get_db_block] getInsts] {
  set master [[$inst getMaster] getName]
  if {$master ni {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
  set val [expr {$master eq "TIEHIx1_ASAP7_75t_R"}]
  foreach it [$inst getITerms] {
   if {[[$it getMTerm] getIoType] ne "OUTPUT" || [$it getNet] eq "NULL"} continue
   foreach sink [[$it getNet] getITerms] {
    if {[[$sink getMTerm] getIoType] eq "INPUT"} {lappend rows "[[$sink getInst] getName]/[[$sink getMTerm] getName]\t$val"}
   }
  }
 }
 foreach row [lsort $rows] {puts $f $row};close $f
}
tie_bindings /work/tie_bindings_before.tsv
foreach pin {TIEHIx1_ASAP7_75t_R/H TIELOx1_ASAP7_75t_R/L} {repair_tie_fanout -separation 1 -max_fanout 1 $pin}
tie_bindings /work/tie_bindings_after.tsv
set b [ord::get_db_block]
set f [open /work/actual_fanout_after_tie.tsv w]
puts $f "net\tloads\tdrivers\tsample_sinks"
foreach n [$b getNets] {
 set load 0;set dr {};set sk {}
 foreach i [$n getITerms] {
  set inst [$i getInst];set mt [$i getMTerm];set label "[$inst getName]/[$mt getName]([[$inst getMaster] getName])"
  if {[$mt getIoType] eq "INPUT"} {incr load;if {[llength $sk]<8} {lappend sk $label}}
  if {[$mt getIoType] eq "OUTPUT"} {lappend dr $label}
 }
 foreach bt [$n getBTerms] {if {[$bt getIoType] eq "OUTPUT"} {incr load};if {[$bt getIoType] eq "INPUT"} {lappend dr "port:[$bt getName]"}}
 if {$load>16} {puts $f "[$n getName]\t$load\t[join $dr ,]\t[join $sk ,]"}
}
close $f
write_db /work/1_synth_tie_split.odb
exit
