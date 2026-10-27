# Local ECO DPL only. Original kit is mounted read-only at /src.
read_db /src/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.odb
set rr_b [ord::get_db_block]
set rr_target {u_ls.g_lrst2.g_rt\[1\].u_rt.q$_DFF_PN0_}
# A global DPL trial moved other cells. Hold them only during local legalization,
# then restore every original status; no unrelated placement is permitted to move.
array set rr_status {}
array set rr_location {}
array set rr_orient {}
foreach rr_cell [$rr_b getInsts] {
 set rr_n [$rr_cell getName]
 set rr_status($rr_n) [$rr_cell getPlacementStatus]
 set rr_location($rr_n) [$rr_cell getLocation]
 set rr_orient($rr_n) [$rr_cell getOrient]
 if {$rr_n ne $rr_target} { $rr_cell setPlacementStatus LOCKED }
}
source /out/rawleaf_reset_anchor.tcl
set rr_i [$rr_b findInst $rr_target]
$rr_i setPlacementStatus PLACED
detailed_placement
set rr_u [[ord::get_db_tech] getDbUnitsPerMicron]
if {[$rr_i getLocation] ne [list [expr {round(31.860*$rr_u)}] [expr {round(129.060*$rr_u)}]] || [$rr_i getOrient] ne "R0"} { error "RAWLEAF_RESET_DPL moved target away from approved anchor" }
foreach rr_cell [$rr_b getInsts] {
 set rr_n [$rr_cell getName]
 if {$rr_n eq $rr_target} { $rr_cell setPlacementStatus FIRM; continue }
 if {[$rr_cell getLocation] ne $rr_location($rr_n) || [$rr_cell getOrient] ne $rr_orient($rr_n)} { error "RAWLEAF_RESET_DPL moved unrelated cell $rr_n" }
 $rr_cell setPlacementStatus $rr_status($rr_n)
}
check_placement -verbose
write_db /out/3_place.odb
puts RAWLEAF_RESET_DPL_DONE_EXACT_ONE
