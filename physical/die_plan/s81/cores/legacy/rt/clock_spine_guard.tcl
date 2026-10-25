# COPY for gen_core_kit_legacy.py regional_taps (KITS-SPARE/S81C 10-25) of physical/die_plan/s81/cores/split_clock/clock_spine_guard.tcl
# @ codex/s81-physical-0719 6e336af2ba (S81-CORES/SPLIT + Codex planned-spine protection / guard).
# Fail closed before post-CTS balancing if CTS changed a planned clock arm.
# Names and nets are an exact manifest from regional_taps.tcl; no RTL/netlist change.
uplevel #0 {
if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} {
  if {![file exists /work/ot_rt_spine.tsv]} { error "OT_RT_SPINE missing manifest" }
  set sg_b [ord::get_db_block]; set sg_f [open /work/ot_rt_spine.tsv]; set sg_bad {}; set sg_n 0
  foreach line [split [string trim [read $sg_f]] "\n"] {
    lassign [split $line "\t"] name pin net
    set i [$sg_b findInst $name]
    if {$i eq "NULL"} { lappend sg_bad "missing $name"; continue }
    set t [$i findITerm $pin]
    if {$t eq "NULL" || [$t getNet] eq "NULL"} { lappend sg_bad "missing $name/$pin"; continue }
    set actual [[$t getNet] getName]
    if {$actual ne $net} { lappend sg_bad "$name/$pin expected $net actual $actual" }
    incr sg_n
  }
  close $sg_f
  if {[llength $sg_bad]} { error "OT_RT_SPINE FAIL [llength $sg_bad]: $sg_bad" }
  puts "OT_RT_SPINE PASS $sg_n unchanged planned connections"
}
}
