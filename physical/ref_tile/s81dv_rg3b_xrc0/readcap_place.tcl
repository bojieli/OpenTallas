# Place kept SRAM read capture banks on the macro read face before GPL.
# Local pipeline placement, no clock or data exceptions.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set count 0
set rec [open $::env(RESULTS_DIR)/xrc_capture_placed.txt w]
foreach inst [$block getInsts] {
    set n [string map {\\ {}} [$inst getName]]
    if {![regexp {g_land\[([0-3])\][./]g_readcap[./]q\[([0-9]+)\]} $n -> row bit]} continue
    # 16 by 16 bit groups in the west read channel, clear of macro halo.
    set x [expr {5.4 + ($bit % 16) * 1.35}]
    set y [expr {43.2 + $row * 90.72 + 24.84 + int($bit / 16) * 1.08}]
    $inst setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]
    $inst setPlacementStatus FIRM
    puts $rec [$inst getName]
    incr count
}
close $rec
puts "XRC_READCAP_PLACED $count"
if {$count != 1024} { error "XRC: expected 1024 retained capture flops, found $count" }
