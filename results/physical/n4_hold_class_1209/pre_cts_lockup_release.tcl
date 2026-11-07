# Only the exactdeclarednew DLLs; no globalDNTrelaxation.
set n4_n 0
set b [ord::get_db_block]
for {set n 0} {$n<9923} {incr n} {
 set i [$b findInst "codex_n4lk_$n"]
 if {$i eq "NULL" || $i eq "" || [[$i getMaster] getName] ne "DLLx1_ASAP7_75t_R"} {error "N4_PRE_CTS missing/unexpected declared latch$n"}
 if {[[$i findITerm CLK] getNet] eq "NULL"} {error "N4_PRE_CTS unclockedlatch$n"}
 $i setDoNotTouch 0
 incr n4_n
}
puts "N4_PRE_CTS exact_latches_released $n4_n PIN_CYCLES 0"
source /work/core_density_taps.tcl
