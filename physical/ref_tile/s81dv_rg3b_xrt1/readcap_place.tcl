# Place kept SRAM read capture banks on the macro read face before GPL.
# Local pipeline placement, no clock or data exceptions.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set count 0
set rec [open $::env(RESULTS_DIR)/xrc_capture_placed.txt w]
foreach inst [$block getInsts] {
    set n [string map {\\ {}} [$inst getName]]
    if {![regexp {g_land\[([0-3])\][./]g_readcap[./]q\[([0-9]+)\]} $n -> bank bit]} continue
    # 16 by 16 bit groups in the east read channel, clear of macro halo.
    set row [expr {$bank%2}]
    set col [expr {$bank/2}]
    set x [expr {220.32+16.2*$col+($bit%16)*1.08}]
    set y [expr {43.2+90.72*$row+10.8+30.24*$col+int($bit/16)*1.08}]
    $inst setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]
    $inst setPlacementStatus FIRM
    puts $rec [$inst getName]
    incr count
}
close $rec
puts "XRC_READCAP_PLACED $count"
if {$count != 1024} { error "XRC: expected 1024 retained capture flops, found $count" }
