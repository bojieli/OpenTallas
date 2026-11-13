# QC-NK-HOLD A+P (gen_phys core_input_place, plan clock.core_input_lockup pipe > 0): anchor every NK input lockup latch (u_lk_nk_*) and the pipeline register
# that feeds it (u_pc_nk_*) right outside the NK pin it drives, FIRM before global placement (like face_flops.tcl pin
# registers), released to PLACED for DPL by face_flops_release.tcl (names appended to ot_face_flops.txt).  The long
# fabric wire then lands on the pipeline register (full cycle) and reg -> latch -> NK pin is a few-um hop.
set nka_blk [ord::get_db_block]
set nka_lat 0; set nka_reg 0; set nka_miss 0; set nka_pipe_miss 0
set nka_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc nka_place {inst x y} {
  $inst setLocation $x $y
  $inst setPlacementStatus FIRM
}
# Discover the complete bounded fanin before moving anything. Yosys' QN
# inverter can have a generic name: only unary BUF/INV masters are transparent,
# and the terminal DFF must still be the named NK pipeline register. Reset
# latch fanin and unrelated logic therefore produce no placement side effects.
proc nka_pipe_chain {net {limit 6}} {
  set chain {}; set seen_nets {}; set seen_insts {}
  for {set hop 0} {$hop < $limit} {incr hop} {
    if {$net eq "" || $net eq "NULL" || [dict exists $seen_nets $net]} { return {} }
    dict set seen_nets $net 1
    set drivers {}
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] eq "OUTPUT"} { lappend drivers [$it getInst] }
    }
    if {[llength $drivers] != 1} { return {} }
    set drv [lindex $drivers 0]
    if {[dict exists $seen_insts $drv]} { return {} }
    dict set seen_insts $drv 1
    set mn [[$drv getMaster] getName]
    if {[regexp {^(DFF|SDF)} $mn]} {
      if {![regexp {u_pc_nk_} [$drv getName]]} { return {} }
      lappend chain $drv
      return $chain
    }
    if {![regexp {^(BUF|INV)} $mn]} { return {} }
    set inputs {}
    foreach it [$drv getITerms] {
      if {[[$it getMTerm] getIoType] eq "INPUT"} {
        set n [$it getNet]
        if {$n ne "" && $n ne "NULL"} { lappend inputs $n }
      }
    }
    if {[llength $inputs] != 1} { return {} }
    lappend chain $drv
    set net [lindex $inputs 0]
  }
  return {}
}
# Some mapped latch Q pins reach the hard face through a generic buffer.
# Accept only one sink per net and a unary BUF/INV chain ending at one hard
# macro pin. Discovery has no side effects; ambiguous or non-unary paths stop.
proc nka_macro_path {net {limit 6}} {
  set chain {}; set seen {}
  for {set hop 0} {$hop < $limit} {incr hop} {
    if {$net eq "" || $net eq "NULL" || [dict exists $seen $net]} { return {} }
    dict set seen $net 1
    set sinks {}
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] eq "INPUT"} { lappend sinks $it }
    }
    if {[llength $sinks] != 1} { return {} }
    set pin [lindex $sinks 0]; set cell [$pin getInst]; set master [$cell getMaster]
    if {[$master isBlock]} { return [list $pin $chain] }
    if {![regexp {^(BUF|INV)} [$master getName]]} { return {} }
    set inputs {}; set outputs {}
    foreach it [$cell getITerms] {
      set n [$it getNet]
      if {$n eq "" || $n eq "NULL"} continue
      switch -- [[$it getMTerm] getIoType] {
        INPUT { lappend inputs $n }
        OUTPUT { lappend outputs $n }
      }
    }
    if {[llength $inputs] != 1 || [llength $outputs] != 1} { return {} }
    lappend chain $cell
    set net [lindex $outputs 0]
  }
  return {}
}
foreach inst [$nka_blk getInsts] {
  set nm [$inst getName]
  if {![regexp {u_lk_nk_} $nm]} continue
  if {![string match "DLL*" [[$inst getMaster] getName]]} continue
  set qn ""; set dn ""
  foreach it [$inst getITerms] {
    set mt [[$it getMTerm] getName]
    if {$mt eq "Q"} { set qn [$it getNet] }
    if {$mt eq "D"} { set dn [$it getNet] }
  }
  if {$qn eq "" || $qn eq "NULL"} { incr nka_miss; continue }
  set pin ""
  foreach it [$qn getITerms] {
    if {[[$it getInst] getMaster] ne "" && [[[$it getInst] getMaster] isBlock]} { set pin $it; break }
  }
  set qchain {}
  if {$pin eq ""} {
    set path [nka_macro_path $qn]
    if {![llength $path]} { incr nka_miss; continue }
    lassign $path pin qchain
  }
  set mac [$pin getInst]
  set mb [$mac getBBox]
  set pb [$pin getBBox]
  set px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2}]
  set dx0 [expr {$px - [$mb xMin]}]; set dx1 [expr {[$mb xMax] - $px}]
  set dy0 [expr {$py - [$mb yMin]}]; set dy1 [expr {[$mb yMax] - $py}]
  set m [lindex [lsort -integer [list $dx0 $dx1 $dy0 $dy1]] 0]
  set g [expr {2 * [$nka_blk getDbUnitsPerMicron]}]
  set g2 [expr {6 * [$nka_blk getDbUnitsPerMicron]}]
  if {$m == $dx0} { set lx [expr {[$mb xMin] - $g}]; set ly $py; set rx [expr {[$mb xMin] - $g2}]; set ry $py
  } elseif {$m == $dx1} { set lx [expr {[$mb xMax] + $g}]; set ly $py; set rx [expr {[$mb xMax] + $g2}]; set ry $py
  } elseif {$m == $dy0} { set lx $px; set ly [expr {[$mb yMin] - $g}]; set rx $px; set ry [expr {[$mb yMin] - $g2}]
  } else { set lx $px; set ly [expr {[$mb yMax] + $g}]; set rx $px; set ry [expr {[$mb yMax] + $g2}] }
  nka_place $inst $lx $ly; puts $nka_out $nm; incr nka_lat
  foreach qcell $qchain {
    nka_place $qcell $lx $ly
    puts $nka_out [$qcell getName]
  }
  set chain [nka_pipe_chain $dn]
  if {![llength $chain]} { incr nka_pipe_miss; continue }
  foreach drv $chain {
    nka_place $drv $rx $ry
    puts $nka_out [$drv getName]
  }
  incr nka_reg

}
close $nka_out
puts "OT_NK_ANCHOR latches $nka_lat pipe_regs $nka_reg unresolved $nka_miss pipe_unresolved $nka_pipe_miss (FIRM outside their NK pin; released for DPL)"
