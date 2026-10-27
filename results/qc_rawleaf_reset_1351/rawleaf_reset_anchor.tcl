# Exact diagnosed local placement correction; no RTL, ports or cycle change.
# Baseline QC rawleaf kit23a47eb989d590c7 has one reset capture at150.963um.
# Actual empty ROW_462 R0 site gives144.915um to the same rst_n pin.
set rr_b [ord::get_db_block]
set rr_u [[ord::get_db_tech] getDbUnitsPerMicron]
set rr_name {u_ls.g_lrst2.g_rt\[1\].u_rt.q$_DFF_PN0_}
set rr_i [$rr_b findInst $rr_name]
if {$rr_i eq "NULL"} { error "RAWLEAF_RESET_ANCHOR missing exact capture $rr_name" }
if {[[$rr_i getMaster] getName] ne "DFFASRHQNx1_ASAP7_75t_R"} { error "RAWLEAF_RESET_ANCHOR unexpected master" }
set rr_row "NULL"
foreach rr_r [$rr_b getRows] { if {[$rr_r getName] eq "ROW_462"} { set rr_row $rr_r; break } }
if {$rr_row eq "NULL" || [$rr_row getOrient] ne "R0"} { error "RAWLEAF_RESET_ANCHOR missing expected R0 destination row" }
# Orientation must precede location: setting it after location can shift the box.
$rr_i setOrient [$rr_row getOrient]
$rr_i setLocation [expr {round(31.860*$rr_u)}] [expr {round(129.060*$rr_u)}]
$rr_i setPlacementStatus FIRM
set rr_xy [$rr_i getLocation]
if {[lindex $rr_xy 0] != round(31.860*$rr_u) || [lindex $rr_xy 1] != round(129.060*$rr_u)} { error "RAWLEAF_RESET_ANCHOR location readback mismatch" }
puts "RAWLEAF_RESET_ANCHOR $rr_name R0 31.860 129.060 FIRM"
