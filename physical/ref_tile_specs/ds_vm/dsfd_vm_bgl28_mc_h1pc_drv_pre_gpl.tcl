# Keep recipe hold stages and pin locations. Strengthen real output data FFs,
# preserving CLK/D/QN names and every transaction/reset stage.
source /src/physical/ref_tile_specs/ds_vm/dsfd_vm_bgl28_mc_pre_gpl.tcl
set drv3 [[ord::get_db] findMaster DFFHQNx3_ASAP7_75t_R]
if {$drv3 eq "NULL"} {error "BGL_PIN_DRV3 missing actual master"}
set ndrv 0
foreach i [[ord::get_db_block] getInsts] {
    set n [$i getName]
    if {![string match {u.g_pin_copy.qb*} $n] && ![string match {u.rt_d*} $n]} {continue}
    if {[[$i getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {continue}
    if {![$i swapMaster $drv3]} {error "BGL_PIN_DRV3 failed swap $n"}
    incr ndrv
}
# Valid/status FFs have real async reset masters and retain their reset semantics.
if {$ndrv < 5300} {error "BGL_PIN_DRV3 expected at least5300 data FFs, found$ndrv"}
puts "BGL_PIN_DRV3 resized $ndrv output-only data FFs x1->x3; no pin or clock constraint change"
