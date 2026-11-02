# PREP only: one data-driver upgrade and one real SRAM south-edge routing clearance.
# Apply only to retained forceB 5_2_route.odb in a fresh owned warm ECO.
# The native clock-freeze check and standard DPL/DRT/signoff/own-final LEC remain mandatory.
set qb_blk [ord::get_db_block]
set qb_u [[ord::get_db_tech] getDbUnitsPerMicron]
set qb_name codex_q2_force_B_4_buf12022
set qb_i [$qb_blk findInst $qb_name]
if {$qb_i eq "NULL" || $qb_i eq "" || [[$qb_i getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {
 error "Q2B_PREP expected exact existing row252 data BUFx2"
}
set qb_out [[$qb_i findITerm Y] getNet]
if {[$qb_out getSigType] eq "CLOCK"} {error "Q2B_PREP refuses clock net"}
set qb_target 0
foreach qb_it [$qb_out getITerms] {
 set qb_in [string map [list "\\" ""] [[$qb_it getInst] getName]]
 if {$qb_in eq {u_ref.u_leaf.u_a.u.u.row1[252]$_DFF_P_} && [[$qb_it getMTerm] getName] eq "D"} {incr qb_target}
}
if {$qb_target != 1} {error "Q2B_PREP row252 output connectivity mismatch"}
set qb_macro {}
foreach qb_j [$qb_blk getInsts] {
 set qb_in [string map [list "\\" ""] [$qb_j getName]]
 if {$qb_in eq {u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro[0].u_s}} {set qb_macro $qb_j; break}
}
if {$qb_macro eq "" || [[$qb_macro getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} {error "Q2B_PREP SRAM identity mismatch"}
set qb_bb [$qb_macro getBBox]
if {abs(double([$qb_bb xMin])/$qb_u-15.120)>0.001 || abs(double([$qb_bb yMin])/$qb_u-13.260)>0.001} {
 error "Q2B_PREP stale SRAM geometry"
}
# Actual VIA23 at M2 y13.230 extends M3 to13.260, touching the SRAM's solid M3 OBS.
# A 36nm M3 south lip removes that illegal access track; y13.149 is an actual legal M2 row track.
# The fixed SRAM's M4 west/east signal ports and the entire native LEF remain unchanged.
set qb_lip [list [$qb_bb xMin] [expr {round(13.224*$qb_u)}] [$qb_bb xMax] [$qb_bb yMin]]
odb::dbObstruction_create $qb_blk [[ord::get_db_tech] findLayer M3] {*}$qb_lip
set qb_lib [get_lib_cells -quiet */BUFx4_ASAP7_75t_R]
if {[llength $qb_lib] != 1} {error "Q2B_PREP missing/ambiguous BUFx4"}
replace_cell [get_cells -quiet $qb_name] [lindex $qb_lib 0]
puts "Q2B_PREP row252 BUFx2->BUFx4; M3 SRAM south lip 15.120,13.224..109.944,13.260; no RTL/clock/pin ABI change"
