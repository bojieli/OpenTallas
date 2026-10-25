# PATH-QC-SU prog_s6 PRE_CTS: kit hold_budget.tcl (unchanged), the pin-register list the s5 GRT I / gate tools read
# (RESULTS_DIR/ot_face_flops.txt; prog_t2 3_place was staged without it: registers whose D is fed by an input port
# through at most one buffer, or whose Q drives an output port through at most one buffer), then the structured clock.
source /work/hold_budget.tcl
proc s6p_seq {i} { set m [[$i getMaster] getName]; return [string match "DFF*" $m] }
proc s6p_buf {i} { set m [[$i getMaster] getName]; return [regexp {^(BUF|HB)} $m] }
set s6p_f [open $::env(RESULTS_DIR)/ot_face_flops.txt w]; set s6p_n 0; array set s6p_seen {}
foreach bt [[ord::get_db_block] getBTerms] {
  set n [$bt getNet]; if {$n eq "NULL" || [$n getSigType] in {CLOCK POWER GROUND}} continue
  set port [$bt getName]; if {$port in {ck rst_n}} continue
  set front [list $n]; set hits {}
  for {set d 0} {$d < 2} {incr d} {
    set nxt {}
    foreach net $front {
      foreach it [$net getITerms] {
        set i [$it getInst]
        if {[s6p_seq $i]} { lappend hits $i; continue }
        if {[s6p_buf $i]} { foreach o [$i getITerms] { if {[$o getNet] ne "NULL" && [$o getNet] ne $net && [$o getSigType] eq "SIGNAL"} { lappend nxt [$o getNet] } } }
      }
    }
    set front $nxt
  }
  foreach i $hits { set nm [$i getName]; if {[info exists s6p_seen($nm)]} continue; set s6p_seen($nm) 1
    set b [$i getBBox]; puts $s6p_f "[string map {\[ \\\[ \] \\\]} $nm]\t-\t[expr {[$b xMin]/1000.0}]\t[expr {[$b yMin]/1000.0}]\t$port"; incr s6p_n }
}
close $s6p_f
puts "S6P_FACE_FLOPS $s6p_n written $::env(RESULTS_DIR)/ot_face_flops.txt"
source /work/cf/mscts_core.tcl
ot_ms_build
