foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /work/macros/*_tt.lib] {read_liberty $f}
source /work/f6_3place.tcl
set E {};set f [open /work/f6_expected_synth.tsv r]
foreach l [lrange [split [read $f] "\n"] 1 end] {if {$l eq ""} continue;lassign [split $l "\t"] m p d c ff mm;if {$c eq "CAPTURE"} {dict set E [list $m $p] $ff}}
close $f
proc cone {net depth} {
 if {$depth > 12} {lappend ::bad depth;return}
 set nm [$net getName];if {[dict exists $::seen $nm]} return;dict set ::seen $nm 1
 if {[llength [$net getBTerms]]} {lappend ::bad top_port}
 foreach it [$net getITerms] {
  if {![$it isInputSignal]} continue
  set i [$it getInst];set m [$i getMaster]
  if {[string match DFF* [$m getName]]} {
   if {[[$it getMTerm] getName] eq "D"} {dict set ::ends [$i getName] 1} else {lappend ::bad [list nondata_ff [$i getName]]}
  } elseif {[$m isBlock] || [$m isSequential]} {lappend ::bad [list unregistered_endpoint [$i getName]]} else {
   foreach o [$i getITerms] {if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [$o getNet] ne ""} {cone [$o getNet] [expr {$depth+1}]}}
  }
 }
}
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set f [open /work/f6_connectivity.tsv r];set rows [split [read $f] "\n"];close $f
set out [open /work/f6_cone_proof.tsv w];puts $out "macro\tpin\texpected_ff\tactual_ends\tbad\tdistance_um\tverdict"
set n 0;set fails 0
foreach l [lrange $rows 1 end] {
 if {$l eq ""} continue
 lassign [split $l "\t"] mac pin dir cls ff master
 if {$cls ne "UNPROTECTED"} continue
 incr n;set expect [dict get $E [list $mac $pin]]
 set mi [$b findInst $mac];set it [$mi findITerm $pin]
 set ::ends {};set ::seen {};set ::bad {}
 cone [$it getNet] 0
 set got [lsort [dict keys $::ends]]
 set v [expr {![llength $::bad] && $got eq [list $expect] ? "PASS":"FAIL"}]
 if {$v ne "PASS"} {incr fails}
 set a [ot_mpf_xy $it $u];set q [ot_mpf_xy [[$b findInst $expect] findITerm D] $u]
 set dist [expr {abs([lindex $a 0]-[lindex $q 0])+abs([lindex $a 1]-[lindex $q 1])}]
 puts $out "$mac\t$pin\t$expect\t$got\t$::bad\t$dist\t$v"
}
close $out
puts "F6_FULL_CONE_PROOF checked$n failed$fails"
if {$fails} {error "real F6 source-to-capture proof failed"}
