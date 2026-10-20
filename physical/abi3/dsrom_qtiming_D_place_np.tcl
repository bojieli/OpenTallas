# S81-QXPQ3 NP (2026-10-20): the q-frame macro hook (dsrom_qtiming_D_place.tcl, unchanged: the four ROMs FIRM on the
# joint site / M4-track grid, capture flops fixed, RTL-MP blockages removed) plus the two segment-tree held-operand
# SRAMs (ot_sram_1r1w_128x64_m1_p192, 33.696 x 27.54 um), one per macro half, directly above its ROM stack on the
# inner edge, pins (LEF west face) turned toward the frame centre (g_mac[0] MY, g_mac[1] R0), same track snap.
source /src/physical/abi3/dsrom_qtiming_D_place.tcl
set ot_np_srams {
    {u_e.g_mac[0].g_tr7.u_tree.u_hst} 96.984 146.880 MY
    {u_e.g_mac[1].g_tr7.u_tree.u_hst} 380.160 146.880 R0
}
set ot_np_n 0
foreach {name mx my orient} $ot_np_srams {
    set inst [ot_find $block $name]
    set px [ot_snap_joint $mx $xgrid0 $xpitch 0.0 0.054]
    set py [ot_snap_joint $my $ygrid0 $ypitch 0.0 0.048]
    $inst setPlacementStatus PLACED
    place_inst -name [$inst getName] -location [format "%.3f %.3f" $px $py] -orientation $orient -status FIRM
    incr ot_np_n
}
puts "OT_QXPQ_NP_PLACE srams=$ot_np_n"
