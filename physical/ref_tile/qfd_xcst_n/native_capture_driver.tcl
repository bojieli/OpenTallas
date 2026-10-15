# xn9 actual native ETM capture miss: b_d[256] 190.7 ps >190 ps.
# Preserve the HB2 hold pad and the boundary flop. Resize ONLY this pad's
# following wire driver; actual FF hold and native capture must re-close.
set ot_nc_blk [ord::get_db_block]
set ot_nc_bt [$ot_nc_blk findBTerm {b_d[256]}]
if {$ot_nc_bt eq "NULL"} { error "native capture repair: b_d\[256\] missing" }
set ot_nc_master [[ord::get_db] findMaster BUFx8_ASAP7_75t_R]
if {$ot_nc_master eq "NULL"} { error "native capture repair: BUFx8 master missing" }
set ot_nc_net [$ot_nc_bt getNet]
set ot_nc_count 0
foreach ot_nc_padpin [$ot_nc_net getITerms] {
    if {[$ot_nc_padpin getIoType] ne "INPUT"} { continue }
    set ot_nc_pad [$ot_nc_padpin getInst]
    if {![string match {HB2xp67_*} [[$ot_nc_pad getMaster] getName]]} { continue }
    foreach ot_nc_pout [$ot_nc_pad getITerms] {
        if {[$ot_nc_pout getIoType] ne "OUTPUT"} { continue }
        foreach ot_nc_drvpin [[$ot_nc_pout getNet] getITerms] {
            if {[$ot_nc_drvpin getIoType] ne "INPUT"} { continue }
            set ot_nc_driver [$ot_nc_drvpin getInst]
            if {[[$ot_nc_driver getMaster] getName] ne "BUFx4f_ASAP7_75t_R"} { continue }
            if {![$ot_nc_driver swapMaster $ot_nc_master]} { error "native capture repair: swap failed" }
            incr ot_nc_count
            puts "NATIVE_CAPTURE_DRIVER b_d\[256\] [$ot_nc_driver getName] BUFx4f->BUFx8; HB2 retained"
        }
    }
}
if {$ot_nc_count != 1} { error "native capture repair: expected one driver, resized $ot_nc_count" }
