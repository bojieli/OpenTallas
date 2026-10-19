# HH-11 2026-10-19 (qcore r6 sector grouping; route r5-1a1108053 NEEDS_RTL TT -314.4): one INCLUSIVE placement region
# per RF sector instance g_sec[s].u_s (ot_hbm_su_qcore_r6_sec, keep_hierarchy): its 8 banks x 4 rows, its raw writer
# copies + write decode, its read-address copies and its gated k+1 read registers stay together, so the writer copies
# sit beside the banks they feed and the per-sector read registers beside the words they select.
# Layout (outline 280.8^2, reducer SRAMs at (86.4,43.2) and (86.4,172.8), 94.824 x 41.04, halo 5.4): the RF uses the
# three full-width bands the SRAM rows leave free (S 2.16-37.8, middle 89.64-167.4, N 219.24-278.64), two sectors per
# band row (W half / E half), so every E->W data path (writer pins E -> copies -> banks -> read regs -> k+2 OR -> W pins)
# runs inside a band, never across an SRAM (no H layer over a macro). The SRAM rows' sides stay free for the reducer.
# Membership: every instance named g_sec[s].u_s/... (the kept module's flops AND its ABC cells keep the prefix).
# Sourced as a pin_hook_before_flops (PRE_GLOBAL_PLACE, before the pin flops are fixed).
set ot_blk [ord::get_db_block]
set ot_dbu [$ot_blk getDbUnitsPerMicron]
# s -> {x0 y0 x1 y1} um
set ot_sec_box {
 0 {8.64 2.16 140.4 37.8}     1 {140.4 2.16 272.16 37.8}
 2 {8.64 89.64 140.4 128.52}  3 {140.4 89.64 272.16 128.52}
 4 {8.64 128.52 140.4 167.4}  5 {140.4 128.52 272.16 167.4}
 6 {8.64 219.24 140.4 278.64} 7 {140.4 219.24 272.16 278.64}
}
set ot_sec_grp [dict create]
foreach {s box} $ot_sec_box {
 lassign $box x0 y0 x1 y1
 set r [odb::dbRegion_create $ot_blk "rf_sec$s"]
 $r setRegionType INCLUSIVE
 odb::dbBox_create $r [expr {round($x0*$ot_dbu)}] [expr {round($y0*$ot_dbu)}] [expr {round($x1*$ot_dbu)}] [expr {round($y1*$ot_dbu)}]
 set g [odb::dbGroup_create $r "rf_sec$s"]
 dict set ot_sec_grp $s [list $g 0]
}
foreach i [$ot_blk getInsts] {
 if {[$i isFixed]} {continue}
 if {[regexp {^g_sec\\?\[([0-7])\\?\]\.u_s/} [$i getName] -> s]} {
  lassign [dict get $ot_sec_grp $s] g n
  $g addInst $i
  dict set ot_sec_grp $s [list $g [expr {$n+1}]]
 }
}
set ot_sec_counts {}
foreach s {0 1 2 3 4 5 6 7} {
 set n [lindex [dict get $ot_sec_grp $s] 1]
 if {$n < 1000} {error "OT_RF_SECTOR_REGIONS: sector $s has only $n member cells (expected ~2k flops + logic); instance names changed?"}
 lappend ot_sec_counts "rf_sec$s=$n"
}
puts "OT_RF_SECTOR_REGIONS [join $ot_sec_counts { }]"
