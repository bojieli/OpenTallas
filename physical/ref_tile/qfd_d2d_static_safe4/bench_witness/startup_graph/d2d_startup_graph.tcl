# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_FF*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w]} {set w [string map {_tt.lib _ff.lib} $w];if {![file exists $w]} {error "missingactualFFlib $w"};read_liberty $w}
  }
}

read_db /data/eclock_control16_sramclk_hold_final_ff.odb
set audit_block [ord::get_db_block]
if {![info exists ::ot_control_copy_aliases]} {set ::ot_control_copy_aliases {}}
proc control_root {name} {
 set seen {};while {[dict exists $::ot_control_copy_aliases $name]} {
  if {$name in $seen} {error "independent alias loop$name"}
  lappend seen $name;set name [dict get $::ot_control_copy_aliases $name]
 };return $name
}
proc control_transparent {master} {expr {[string match BUF* $master] || [string match *INV* $master] || $master in {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}}}
proc control_canon {net {alias 1} {seen {}}} {
 if {$net eq "NULL" || $net eq ""} {return OPEN}
 if {$net in $seen} {error "independent bufferloop"};lappend seen $net
 set drivers {};foreach t [$net getITerms] {if {[$t isOutputSignal]} {lappend drivers $t}}
 if {![llength $drivers]} {
  set ports {};foreach t [$net getBTerms] {if {[$t getIoType] eq "INPUT"} {lappend ports [$t getName]}}
  if {[llength $ports]!=1} {return [list UNDRIVEN [$net getName]]}
  return [list PORT [lindex $ports 0] 0]
 }
 if {[llength $drivers]!=1} {error "independent multidriver[$net getName]"}
 set t [lindex $drivers 0];set i [$t getInst];set m [[$i getMaster] getName]
 if {[control_transparent $m]} {
  set ins {};foreach x [$i getITerms] {if {[$x isInputSignal]} {lappend ins $x}}
  if {[llength $ins]!=1} {error "independent unexpectedtransparent ABI$m"}
  set r [control_canon [[lindex $ins 0] getNet] $alias $seen]
  if {[string match *INV* $m]} {lset r end [expr {1-[lindex $r end]}]}
  return $r
 }
 set name [$i getName];if {$alias} {set name [control_root $name]}
 return [list CELL $name [[$t getMTerm] getName] 0]
}

set f [open /data/control16_actual_startup_equations.tsv w]
foreach i [$audit_block getInsts] {
 set m [[$i getMaster] getName]
 if {[control_transparent $m]} continue
 puts $f [join [list MASTER [$i getName] $m] \t]
 foreach t [$i getITerms] {
  if {![$t isInputSignal]} continue
  puts $f [join [list INPUT [$i getName] [[$t getMTerm] getName] [control_canon [$t getNet] 0]] \t]
 }
}
foreach t [$audit_block getBTerms] {
 if {[$t getIoType] eq "OUTPUT"} {puts $f [join [list OUTPUT [$t getName] [control_canon [$t getNet] 0]] \t]}
}
close $f
puts "STARTUP_GRAPH actual_unaliased_nontransparent_equations=1 timing_rerun=0 mutation=0"
exit
