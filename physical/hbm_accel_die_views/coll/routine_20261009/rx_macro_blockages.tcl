# Physical-only reservation around the existing48 receive-ring SRAMs.
# Does not move a macro, cell, pin, clock or change any logical connection.
set ot_rx_block [ord::get_db_block]
set ot_rx_dbu [$ot_rx_block getDbUnitsPerMicron]
set ot_rx_core [$ot_rx_block getCoreArea]
set ot_rx_master ot_sram_1r1w_128x256_m1_r2c2
if {[info exists ::env(OT_RX_EXPECTED_MASTER)]} {set ot_rx_master $::env(OT_RX_EXPECTED_MASTER)}
set ot_rx_macros {}
foreach ot_rx_inst [$ot_rx_block getInsts] {
 set ot_rx_name [$ot_rx_inst getName]
 if {![string match {*g_rx*.u_rb/*u_sram} $ot_rx_name]} {continue}
 set ot_rx_m [$ot_rx_inst getMaster]
 if {![$ot_rx_m isBlock] || [$ot_rx_m getName] ne $ot_rx_master} {
  error "RX blockage wrong macro master: $ot_rx_name / [$ot_rx_m getName]"
 }
 lappend ot_rx_macros $ot_rx_inst
}
if {[llength $ot_rx_macros] != 48} {error "RX blockage needs full48macros, found [llength $ot_rx_macros]"}
set ot_rx_rows [$ot_rx_block getRows]
if {[llength $ot_rx_rows] == 0} {error "RX blockage needs actual placement rows"}
set ot_rx_site [[lindex $ot_rx_rows 0] getSite]
set ot_rx_sx [$ot_rx_site getWidth]
set ot_rx_sy [$ot_rx_site getHeight]
# Match the existing4x6um macroplacer halo, now as literal hard placement
# reservations. Snap outwards to the actual site grid and clip to the core.
set ot_rx_hx [expr {round(4.0*$ot_rx_dbu)}]
set ot_rx_hy [expr {round(6.0*$ot_rx_dbu)}]
foreach ot_rx_inst $ot_rx_macros {
 set ot_rx_box [$ot_rx_inst getBBox]
 set ot_rx_x0 [expr {max([$ot_rx_core xMin],int(floor(double([$ot_rx_box xMin]-$ot_rx_hx)/$ot_rx_sx))*$ot_rx_sx)}]
 set ot_rx_y0 [expr {max([$ot_rx_core yMin],int(floor(double([$ot_rx_box yMin]-$ot_rx_hy)/$ot_rx_sy))*$ot_rx_sy)}]
 set ot_rx_x1 [expr {min([$ot_rx_core xMax],int(ceil(double([$ot_rx_box xMax]+$ot_rx_hx)/$ot_rx_sx))*$ot_rx_sx)}]
 set ot_rx_y1 [expr {min([$ot_rx_core yMax],int(ceil(double([$ot_rx_box yMax]+$ot_rx_hy)/$ot_rx_sy))*$ot_rx_sy)}]
 if {$ot_rx_x0 >= $ot_rx_x1 || $ot_rx_y0 >= $ot_rx_y1} {error "RX blockage invalid rectangle"}
 odb::dbBlockage_create $ot_rx_block $ot_rx_x0 $ot_rx_y0 $ot_rx_x1 $ot_rx_y1
 puts "RX_HARD_HALO [$ot_rx_inst getName] $ot_rx_x0 $ot_rx_y0 $ot_rx_x1 $ot_rx_y1"
}
puts "RX_HARD_HALO_COMPLETE count48 site=$ot_rx_sx,$ot_rx_sy halo_um=4,6"
