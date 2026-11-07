# Exact scope: declared 1246 low-phase lockups only. Original failed CTS preserved.
set lkr_blk [ord::get_db_block]
set lkr_count 0
for {set lkr_i 0} {$lkr_i < 1246} {incr lkr_i} {
 set lkr_name "codex_lk_$lkr_i"
 set lkr_inst [$lkr_blk findInst $lkr_name]
 if {$lkr_inst eq "NULL"} {error "LOCKUP_DNT_RELEASE missing $lkr_name"}
 if {[[$lkr_inst getMaster] getName] ne "DLLx1_ASAP7_75t_R"} {error "LOCKUP_DNT_RELEASE wrongmaster $lkr_name"}
 $lkr_inst setDoNotTouch 0
 incr lkr_count
}
if {$lkr_count != 1246} {error "LOCKUP_DNT_RELEASE count $lkr_count"}
puts "LOCKUP_DNT_RELEASE exact_count $lkr_count other_instances_unchanged"
