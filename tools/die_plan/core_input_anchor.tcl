# QC-NK-HOLD A+P (gen_phys core_input_place, plan clock.core_input_lockup pipe > 0): anchor every NK input lockup latch (u_lk_nk_*) and the pipeline register
# that feeds it (u_pc_nk_*) right outside the NK pin it drives, FIRM before global placement (like face_flops.tcl pin
# registers), released to PLACED for DPL by face_flops_release.tcl (names appended to ot_face_flops.txt).  The long
# fabric wire then lands on the pipeline register (full cycle) and reg -> latch -> NK pin is a few-um hop.
set nka_blk [ord::get_db_block]
set nka_lat 0; set nka_reg 0; set nka_miss 0
set nka_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc nka_place {inst x y} {
  $inst setLocation $x $y
  $inst setPlacementStatus FIRM
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
  if {$pin eq ""} { incr nka_miss; continue }
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
  # walk back from the latch D through the QN inverter / buffers of the pipe register to the flop itself and anchor
  # every cell on the way (pilot6 anchored only the QN inverter: the DFF stayed at its source, 1.3 ns reg->latch wire)
  set net $dn; set hops 0
  while {$net ne "" && $net ne "NULL" && $hops < 6} {
    set drv ""
    foreach it [$net getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set drv [$it getInst] } }
    if {$drv eq "" || ![regexp {u_pc_nk_} [$drv getName]]} break
    nka_place $drv $rx $ry; puts $nka_out [$drv getName]; incr hops
    set mn [[$drv getMaster] getName]
    if {[regexp {^(DFF|SDF)} $mn]} { incr nka_reg; break }
    set net ""
    foreach it [$drv getITerms] { if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} { set net [$it getNet] } }
  }
}
close $nka_out
puts "OT_NK_ANCHOR latches $nka_lat pipe_regs $nka_reg unresolved $nka_miss (FIRM outside their NK pin; released for DPL)"
