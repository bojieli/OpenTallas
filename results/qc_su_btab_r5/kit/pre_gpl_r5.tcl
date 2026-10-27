# QC-SU-BTAB-R5 PRE_GLOBAL_PLACE (GEOM-REVIEW-6 16:23 structural fix (2), "spread the E-column logic into x 255-340"):
# r4 hooks unchanged (pushdown, face pin registers, macro-pin flops anchored FIRM at their SRAM pins), then an INCLUSIVE
# placement region (members must sit inside it, other cells may too) over the empty E area x OT_R5_EL_X0..X1 (255..340),
# y = SRAM rows +- 4.32, for the E-column READ-MUX LOGIC: every combinational cell (not a flop, not INV/BUF/HB: those stay
# with their pin flops) whose input is driven, through at most 2 INV/BUF/HB hops, by an E-face macro-pin capture flop and
# by no W-face one.  r4 measured: 2.4k cells in the one 10-um bin x 230-240 (2010 INVx1 at the pin flops + 512 AO22/AO221
# bank-select read mux); the mux has no reason to sit on the pin column.  Placement only: no netlist / SDC / clock change.
# (r5 try 1 used a partial density blockage at x 237.6-254.9: no effect, the logic sits at x 229-237 among the pin flops.)
source /work/pre_gpl_m0.tcl
set r5b [ord::get_db_block]; set r5u [[ord::get_db_tech] getDbUnitsPerMicron]
proc r5env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set r5x0 [r5env OT_R5_EL_X0 255.0]; set r5x1 [r5env OT_R5_EL_X1 340.0]
set r5ylo 1e9; set r5yhi -1e9; set r5mx 0
foreach i [$r5b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set bb [$i getBBox]; set r5mx [expr {max($r5mx, [$bb xMax])}]
  set r5ylo [expr {min($r5ylo, [$bb yMin] / double($r5u) - 4.32)}]; set r5yhi [expr {max($r5yhi, [$bb yMax] / double($r5u) + 4.32)}]
}
proc r5_isbuf {i} { regexp {^(INV|BUF|HB)} [[$i getMaster] getName] }
proc r5_isff {i} { string match "*DFF*" [[$i getMaster] getName] }
set r5side [dict create]
set f [open $::env(RESULTS_DIR)/ot_macro_pin_flops.txt]
foreach n [split [read $f] "\n"] {
  if {$n eq ""} continue
  set i [$r5b findInst $n]; if {$i eq "NULL"} continue
  set x [lindex [$i getLocation] 0]
  dict set r5side $n [expr {$x > $r5mx ? "E" : "W"}]
}
close $f
# downstream of every macro-pin flop: through <=2 INV/BUF/HB to combinational cells; record the side(s) feeding each cell
set r5feed [dict create]
dict for {n s} $r5side {
  set i [$r5b findInst $n]
  set front {}
  foreach it [$i getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { lappend front [list [$it getNet] 0] } }
  while {[llength $front]} {
    lassign [lindex $front end] net d; set front [lrange $front 0 end-1]
    if {[$net getSigType] in {CLOCK POWER GROUND}} continue
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set j [$it getInst]; if {[[$j getMaster] isBlock] || [r5_isff $j]} continue
      if {[r5_isbuf $j]} {
        if {$d < 2} { foreach o [$j getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [list [$o getNet] [expr {$d + 1}]] } } }
        continue
      }
      dict lappend r5feed [$j getName] $s
    }
  }
}
set r5mem {}
dict for {n ss} $r5feed {
  if {[lsearch $ss W] >= 0} continue
  set j [$r5b findInst $n]; if {[$j getPlacementStatus] in {FIRM LOCKED}} continue
  lappend r5mem $j
}
# snap the region to the site / row grid (core origin 4.32, site 0.054, row 0.27): r5 try 2 failed the DPL region check
# for 42 cells at the off-grid x 255.0 / y 244.10 edges
set r5x0 [expr {4.32 + ceil(($r5x0 - 4.32) / 0.054) * 0.054}]; set r5x1 [expr {4.32 + floor(($r5x1 - 4.32) / 0.054) * 0.054}]
set r5ylo [expr {4.32 + ceil(($r5ylo - 4.32) / 0.27 - 1e-6) * 0.27}]; set r5yhi [expr {4.32 + floor(($r5yhi - 4.32) / 0.27 + 1e-6) * 0.27}]
if {[llength $r5mem]} {
  set r [odb::dbRegion_create $r5b r5_e_logic]
  $r setRegionType INCLUSIVE
  odb::dbBox_create $r [expr {round($r5x0 * $r5u)}] [expr {round($r5ylo * $r5u)}] [expr {round($r5x1 * $r5u)}] [expr {round($r5yhi * $r5u)}]
  set g [odb::dbGroup_create $r r5_e_logic]
  $g setType VOLTAGE_DOMAIN
  foreach j $r5mem { $g addInst $j }
}
set fo [open $::env(RESULTS_DIR)/r5_e_logic.txt w]; foreach j $r5mem { puts $fo [$j getName] }; close $fo
puts [format "R5_E_LOGIC region x %.2f-%.2f y %.2f-%.2f INCLUSIVE: %d read-mux cells fed only by E-face pin flops (%d E / %d W pin flops; %d mixed-side cells left free)" $r5x0 $r5x1 $r5ylo $r5yhi [llength $r5mem] [llength [lsearch -all [dict values $r5side] E]] [llength [lsearch -all [dict values $r5side] W]] [expr {[dict size $r5feed] - [llength $r5mem]}]]
