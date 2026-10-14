# Ratio-CDC crossing hold stage for dsfd_vm_be_sl (claude s81-grpA r3, 2026-10-14; sourced from the recipe-2 kit-local
# pre_gpl.tcl via spec "pin_hook_before_flops").
# r3 71536bfc4 TT +7.85 / FF -6.57 and r4 8d0114042 TT +8.88 / FF -9.13: the ONLY FF hold violators (9 endpoints) are the
# str_clk -> core_clk pointer / state hops of the two ratio FIFOs (u_rc0/u_rc1: rp -> rp_w, r_st -> r_st_w), single
# flop-to-flop hops at the 4:3 coincident edge (hold relation 0) with the cks launch leaf ~39 ps earlier than the ck
# capture leaf at FF.  Their setup slack is +23.9 ps (208 ps window), so the route hold ECO skips them; r4's two-sided
# tree balance moved the skew the wrong way (-6.57 -> -9.13).  Deterministic fix, targeted: ONE dont_touch HB1xp67 delay
# cell (NLDM single-D load: ~15 ps FF / ~20 ps TT) in series on the D of EVERY str->core crossing flop (rp_w[*], r_st_w[*]
# of u_rc0 and u_rc1: 2 x (4 + 2) = 12 flops).  Functional netlist unchanged (buffer only, same cycle).  Port of the
# same mechanism as besl_rhold.tcl (cells and nets dont_touch so repair passes neither remove nor split them).
set ot_xh_master [expr {[info exists ::env(OT_XHOLD_MASTER)] ? $::env(OT_XHOLD_MASTER) : "HB1xp67_ASAP7_75t_R"}]
set ot_xh_expect [expr {[info exists ::env(OT_XHOLD_EXPECT)] ? $::env(OT_XHOLD_EXPECT) : 12}]
set ot_xh_blk [ord::get_db_block]
set ot_xh_m [[ord::get_db] findMaster $ot_xh_master]
if {$ot_xh_m eq "NULL"} { error "XHOLD: $ot_xh_master missing" }
set ot_xh_n 0; set ot_xh_dtn {}; set ot_xh_cells {}
foreach inst [$ot_xh_blk getInsts] {
  set nm [string map {"\\" ""} [$inst getName]]
  if {![regexp {(^|[./])u_rc[01][./](rp_w|r_st_w)(\[[0-9]+\])?(\$|_reg|$)} $nm]} continue
  if {![string match "DFF*" [[$inst getMaster] getName]]} continue
  set d [$inst findITerm D]; if {$d eq "NULL"} continue
  set net [$d getNet]; if {$net eq "NULL"} continue
  lassign [$inst getLocation] x y
  $d disconnect
  set cell [odb::dbInst_create $ot_xh_blk $ot_xh_m [format "ot_xhold_%02d" $ot_xh_n]]
  set n2 [odb::dbNet_create $ot_xh_blk [format "ot_xhold_n%02d" $ot_xh_n]]
  [$cell findITerm A] connect $net
  [$cell findITerm Y] connect $n2
  $cell setOrient [$inst getOrient]; $cell setLocation $x $y; $cell setPlacementStatus PLACED
  $d connect $n2
  lappend ot_xh_dtn $n2; lappend ot_xh_cells [format "ot_xhold_%02d" $ot_xh_n]
  puts "XHOLD: $nm"
  incr ot_xh_n
}
if {$ot_xh_n > 0} { set_dont_touch [get_cells $ot_xh_cells] }
# nets last: odb refuses (ODB-0373) to connect an iterm to a net already marked dont_touch
foreach n $ot_xh_dtn { $n setDoNotTouch 1 }
puts "XHOLD: $ot_xh_n str->core crossing flops, 1 x $ot_xh_master on each D (cell + output net dont_touch)"
if {$ot_xh_n != $ot_xh_expect} { error "XHOLD: expected $ot_xh_expect crossing flops (u_rc0/u_rc1 rp_w[*], r_st_w[*]), matched $ot_xh_n" }
