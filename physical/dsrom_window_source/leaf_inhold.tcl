# Hardened-leaf input hold stage (el1011-ds-misc 2026-10-11, PRE_GLOBAL_PLACE of route_leaf.sh INHOLD=1).  land8 a7247ecfa-f
# closed TT +325.95 / DRC 0 and missed FF hold by -24.5 ps on 2,023 input-pin -> capture-flop D pins (reg2reg -6.4).
# Deterministic fix (OWNER 10-10 "hold-only miss -> delay stage at inputs; no ECO loops") applied to EVERY data input
# uniformly: one dont_touch hold buffer (OT_INHOLD_MASTER, default HB4xp67) between each input port and its single
# capture-flop D pin.  Same insertion as io_flop_at_pins_inhold.tcl (cb2978cc5) without the pin anchoring.
set ot_ih_master [expr {[info exists ::env(OT_INHOLD_MASTER)] ? $::env(OT_INHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ot_ih_blk [ord::get_db_block]
set ot_ih_m [[ord::get_db] findMaster $ot_ih_master]
if {$ot_ih_m eq "NULL"} { error "INHOLD: $ot_ih_master missing" }
set ot_ih_n 0; set ot_ih_skip 0
foreach bt [$ot_ih_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {[$net getSigType] ne "SIGNAL"} { incr ot_ih_skip; continue }
  set its [$net getITerms]
  if {[llength $its] != 1} { incr ot_ih_skip; continue }
  set d [lindex $its 0]; set ff [$d getInst]
  if {![string match "DFF*" [[$ff getMaster] getName]] || [[$d getMTerm] getName] ne "D"} { incr ot_ih_skip; continue }
  set name [format "ot_inhold_%05d" $ot_ih_n]; set nn [format "ot_inhold_n%05d" $ot_ih_n]
  set cell [odb::dbInst_create $ot_ih_blk $ot_ih_m $name]
  set n2 [odb::dbNet_create $ot_ih_blk $nn]
  $d disconnect
  [$cell findITerm A] connect $net
  [$cell findITerm Y] connect $n2
  $d connect $n2
  lassign [$ff getLocation] x y
  $cell setOrient [$ff getOrient]; $cell setLocation $x $y; $cell setPlacementStatus PLACED
  incr ot_ih_n
}
if {$ot_ih_n > 0} { set_dont_touch [get_cells ot_inhold_*] }
puts "INHOLD: $ot_ih_n input hold cells ($ot_ih_master, dont_touch), $ot_ih_skip inputs skipped (clock / reset / multi-sink / non-DFF)"
