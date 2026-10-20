# vms_inplace_hold.tcl -- VM hub-glue g7d (L2H-PGVM-G7 2026-10-19), PRE_GLOBAL_PLACE (kit pin_hook_before_flops), the
# FALLBACK variant of g7 (gated in parallel, different kit names *_g7d).  g7 puts every REACH relay on its lattice point
# (vms_relay_lattice.tcl); the remaining pure flop -> flop hops are IN-PLACE alignment delays whose launch and capture sit
# in the same lane band / hub region by construction (g6 census: band ln_m / ln p50 9-50 um, hub req_grp qr_g1 / qr_g
# p50 2-70 um): the ring-stop lane data waits two edges in its band while the header decode crosses <= ~700 um (stage A
# -> M -> B), the hub request copies wait for the registered one-hot bank select.  Their hold need is known before
# placement (zero wire, ~0 ps logic, 25 ps uncertainty + 30 ps margin), so g7d inserts the hold delay deterministically:
# one HB4xp67 (~37 ps FF / ~50 ps TT) in front of each such D pin -- the cell the CTS hold repair would add one buffer at
# a time (g6: ~40k buffers in > 3 h) -- placed by GPL beside its flop.  These hops carry ~800 ps of setup
# slack (no logic, no wire), so the delay costs no setup.  Only D pins driven directly by a flop (QN through <= 3 INV / BUF) of
# the listed classes; every other path is left to the normal flow.  0 cycles, no function change.
set ih_blk [ord::get_db_block]
set ih_db [ord::get_db]
set ih_hb [$ih_db findMaster [expr {[info exists ::env(OT_IH_CELL)] ? $::env(OT_IH_CELL) : "HB4xp67_ASAP7_75t_R"}]]
if {$ih_hb eq "NULL"} { error "OT_IHOLD: hold cell master missing" }
set ih_re {^u_core\.u_c?cw\.band\[[0-9]\]\.(ln_m|ln)\[[0-9]+\]|^u_core\.u_hub\.req_grp\[[0-9]\]\.(qr_g1|qr_g|sq_g1|sq_g)\[[0-9]+\]}
proc ih_flop_driven {net} {
  for {set k 0} {$k < 4} {incr k} {
    set d ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set d $it; break } }
    if {$d eq ""} { return 0 }
    set m [[[$d getInst] getMaster] getName]
    if {[string match "DFF*" $m]} { return 1 }
    if {![string match "BUF*" $m] && ![string match "INV*" $m]} { return 0 }
    set net [[[$d getInst] findITerm A] getNet]
    if {$net eq "NULL"} { return 0 }
  }
  return 0
}
set ih_n 0; set ih_skip 0; set ih_seq 0
set ih_cls [dict create]
set ih_todo {}
foreach inst [$ih_blk getInsts] {
  if {![string match "DFF*" [[$inst getMaster] getName]]} continue
  set clean [string map {"\\" ""} [$inst getName]]
  if {![regexp $ih_re $clean -> a b]} continue
  lappend ih_todo [list $inst "$a$b"]
}
foreach e $ih_todo {
  lassign $e inst cls
  set it [$inst findITerm D]
  if {$it eq "NULL"} { incr ih_skip; continue }
  set n [$it getNet]
  if {$n eq "NULL" || ![ih_flop_driven $n]} { incr ih_skip; continue }
  set h [odb::dbInst_create $ih_blk $ih_hb [format "ot_vih_%06d" $ih_seq]]
  set nn [odb::dbNet_create $ih_blk [format "ot_vih_n%06d" $ih_seq]]
  incr ih_seq
  $it disconnect
  [$h findITerm A] connect $n
  [$h findITerm Y] connect $nn
  $it connect $nn
  incr ih_n
  dict incr ih_cls $cls
}
# NOT dont_touch (g7d r1 e / nw: timing-driven GPL RSZ-3006 "failed to insert buffer before loads" on the launch nets
# that also feed these cells): ordinary buffers to the resizer; only a setup-violating path could unbuffer them, and these
# hops carry ~800 ps of setup slack
dict for {k v} $ih_cls { puts "OT_IHOLD $k $v" }
puts "OT_IHOLD inserted $ih_n in-place hold cells ([$ih_hb getName]); $ih_skip class flops not flop-driven (left to the flow)"
if {$ih_n < 1000} { error "OT_IHOLD: only $ih_n in-place hold cells (netlist / naming changed?)" }
