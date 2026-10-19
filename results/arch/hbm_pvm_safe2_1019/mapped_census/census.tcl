set r /srv/opentallas-scratch/claude/codex-pvm-mirror-census
set odb [lindex [glob /work/results/asap7/*/base/1_synth.odb] 0]
read_db $odb
set b [ord::get_db_block]
set f [open /work/actual_fanout.tsv w]
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
exit
