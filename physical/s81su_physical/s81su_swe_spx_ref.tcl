# Codex physical specification: preserve the measured short internal capture classes.
# Real delay cells, unchanged clocks/boundary obligations; zero cycles added.
set ::env(OT_INHOLD_MASTER) HB4xp67_ASAP7_75t_R
set ::env(OT_INHOLD_DRV) BUFx4f_ASAP7_75t_R
source /src/physical/dsrom_window_source/leaf_inhold.tcl
set su_hd_block [ord::get_db_block]
set su_hd_master [[ord::get_db] findMaster HB1xp67_ASAP7_75t_R]
if {$su_hd_master eq "NULL"} {error "SUHOLD delay master missing"}
set su_hd_drv [[ord::get_db] findMaster BUFx4f_ASAP7_75t_R]
if {$su_hd_drv eq "NULL"} {error "SUHOLD driver missing"}
set su_hd_n 0
set su_hd_guardnets {}
foreach su_hd_ff [$su_hd_block getInsts] {
 set su_hd_name [string map {\\ ""} [$su_hd_ff getName]]
 if {![regexp {^u_e\.u_l\.(u_div\.g_rec\[[0-9]+\]\.qin\[|u_den\..*u_k1\.g_r\.r\[|u_exp\..*\.g_line\.line\[)} $su_hd_name]} continue
 if {![string match DFF* [[$su_hd_ff getMaster] getName]]} continue
 set su_hd_d [$su_hd_ff findITerm D]
 if {$su_hd_d eq "NULL"} continue
 set su_hd_net [$su_hd_d getNet]
 if {$su_hd_net eq "NULL"} continue
 set su_hd_c [odb::dbInst_create $su_hd_block $su_hd_master [format su_hold_%05d $su_hd_n]]
 set su_hd_out [odb::dbNet_create $su_hd_block [format su_hold_n%05d $su_hd_n]]
 $su_hd_d disconnect
 set su_hd_pre [odb::dbInst_create $su_hd_block $su_hd_drv [format su_hpre_%05d $su_hd_n]]
 set su_hd_post [odb::dbInst_create $su_hd_block $su_hd_drv [format su_hpost_%05d $su_hd_n]]
 set su_hd_before [odb::dbNet_create $su_hd_block [format su_hpre_n%05d $su_hd_n]]
 set su_hd_after [odb::dbNet_create $su_hd_block [format su_hpost_n%05d $su_hd_n]]
 [$su_hd_pre findITerm A] connect $su_hd_net
 [$su_hd_pre findITerm Y] connect $su_hd_before
 [$su_hd_c findITerm A] connect $su_hd_before
 [$su_hd_c findITerm Y] connect $su_hd_out
 [$su_hd_post findITerm A] connect $su_hd_out
 [$su_hd_post findITerm Y] connect $su_hd_after
 $su_hd_d connect $su_hd_after
 lappend su_hd_guardnets $su_hd_before $su_hd_out
 lassign [$su_hd_ff getLocation] su_hd_x su_hd_y
 $su_hd_c setLocation $su_hd_x $su_hd_y
 $su_hd_c setPlacementStatus PLACED
 foreach su_hd_buf [list $su_hd_pre $su_hd_post] {$su_hd_buf setLocation $su_hd_x $su_hd_y; $su_hd_buf setPlacementStatus PLACED}
 incr su_hd_n
}

# Measured SRAM wd_in capture obligation, preserved against the actual macro FF hold arc.
foreach su_hd_ff [$su_hd_block getInsts] {
 if {[[$su_hd_ff getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} continue
 foreach su_hd_d [$su_hd_ff getITerms] {
  if {![string match {wd_in*} [[$su_hd_d getMTerm] getName]]} continue
 set su_hd_net [$su_hd_d getNet]
 if {$su_hd_net eq "NULL"} continue
 set su_hd_c [odb::dbInst_create $su_hd_block $su_hd_master [format su_hold_%05d $su_hd_n]]
 set su_hd_out [odb::dbNet_create $su_hd_block [format su_hold_n%05d $su_hd_n]]
 $su_hd_d disconnect
 set su_hd_pre [odb::dbInst_create $su_hd_block $su_hd_drv [format su_hpre_%05d $su_hd_n]]
 set su_hd_post [odb::dbInst_create $su_hd_block $su_hd_drv [format su_hpost_%05d $su_hd_n]]
 set su_hd_before [odb::dbNet_create $su_hd_block [format su_hpre_n%05d $su_hd_n]]
 set su_hd_after [odb::dbNet_create $su_hd_block [format su_hpost_n%05d $su_hd_n]]
 [$su_hd_pre findITerm A] connect $su_hd_net
 [$su_hd_pre findITerm Y] connect $su_hd_before
 [$su_hd_c findITerm A] connect $su_hd_before
 [$su_hd_c findITerm Y] connect $su_hd_out
 [$su_hd_post findITerm A] connect $su_hd_out
 [$su_hd_post findITerm Y] connect $su_hd_after
 $su_hd_d connect $su_hd_after
 lappend su_hd_guardnets $su_hd_before $su_hd_out
 lassign [$su_hd_ff getLocation] su_hd_x su_hd_y
 $su_hd_c setLocation $su_hd_x $su_hd_y
 $su_hd_c setPlacementStatus PLACED
 foreach su_hd_buf [list $su_hd_pre $su_hd_post] {$su_hd_buf setLocation $su_hd_x $su_hd_y; $su_hd_buf setPlacementStatus PLACED}
 incr su_hd_n
 }
}
if {$su_hd_n < 1} {error "SUHOLD no measured internal endpoint matched"}
set_dont_touch [get_cells su_hold_*]
foreach su_hd_net $su_hd_guardnets {$su_hd_net setDoNotTouch 1}
puts "SUHOLD: $su_hd_n internal capture delay cells HB1xp67, no latency/clock changes"
