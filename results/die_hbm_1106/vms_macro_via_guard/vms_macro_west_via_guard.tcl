# Candidate only: derive/review with vms_access_guard_prepare.py.
# M4 ports/OBS remain unchanged; a minimum-width M5 obstruction forces west escape.
set b [ord::get_db_block]
set i [$b findInst {u_fcore.u_core.u_ot_pr_core.bank.u_a}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "ot_sram_1r1w_1024x256_m2_r2c2" || [$i getOrient] ne "R0"} {
  error "VMS_VIA_GUARD: unexpected bank A master/orientation"
}
if {[$i getLocation] ne "47616 76380"} { error "VMS_VIA_GUARD: unexpected actual origin" }
set l [[ord::get_db_tech] findLayer M5]
if {[$l getWidth] != 24 || [$l getSpacing] != 24} { error "VMS_VIA_GUARD: technology mismatch" }
odb::dbObstruction_create $b $l 47664 76356 47688 146892
puts "VMS_VIA_GUARD M5 (47.664, 76.356, 47.688, 146.892), zero cycles, M4 escape unchanged"
