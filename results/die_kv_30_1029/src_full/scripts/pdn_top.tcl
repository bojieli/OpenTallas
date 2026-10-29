read_db /n/pg_grid/grid_ready.odb
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VDDPHY} -inst_pattern {.*} -pin_pattern {^VDDPHY$} -power
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n [$b findNet VDD]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VDD] }
$n setSigType POWER; $n setSpecial
set n [$b findNet VDDPHY]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VDDPHY] }
$n setSigType POWER; $n setSpecial
set n [$b findNet VSS]
if {$n eq "NULL"} { set n [odb::dbNet_create $b VSS] }
$n setSigType GROUND; $n setSpecial
global_connect
set_voltage_domain -name Core -power VDD -ground VSS -secondary_power {VDDPHY}
set region [odb::dbRegion_create $b ot_pg_0]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(0*$dbu)}] [expr {round(11076.48*$dbu)}] [expr {round(26058.24*$dbu)}]
set_voltage_domain -name ot_pg_0 -region ot_pg_0 -power VDD -ground VSS
define_pdn_grid -name ot_pg_0 -voltage_domains {ot_pg_0}
add_pdn_stripe -grid ot_pg_0 -layer M8 -width 0.48 -pitch 4.32 -offset 2.16 -spacing 1.68 -starts_with POWER
add_pdn_stripe -grid ot_pg_0 -layer M9 -width 12.96 -pitch 39.96 -offset 13.77 -spacing 7.02 -starts_with POWER
add_pdn_connect -grid ot_pg_0 -layers {M8 M9}
set region [odb::dbRegion_create $b ot_pg_1]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(26058.24*$dbu)}] [expr {round(5140.8*$dbu)}] [expr {round(26853.12*$dbu)}]
set_voltage_domain -name ot_pg_1 -region ot_pg_1 -power VDD -ground VSS
define_pdn_grid -name ot_pg_1 -voltage_domains {ot_pg_1}
add_pdn_stripe -grid ot_pg_1 -layer M8 -width 0.48 -pitch 4.32 -offset 2.16 -spacing 1.68 -starts_with POWER
add_pdn_stripe -grid ot_pg_1 -layer M9 -width 12.96 -pitch 39.96 -offset 13.77 -spacing 7.02 -starts_with POWER
add_pdn_connect -grid ot_pg_1 -layers {M8 M9}
set region [odb::dbRegion_create $b ot_pg_2]
odb::dbBox_create $region [expr {round(5140.8*$dbu)}] [expr {round(26058.24*$dbu)}] [expr {round(5935.68*$dbu)}] [expr {round(26853.12*$dbu)}]
set_voltage_domain -name ot_pg_2 -region ot_pg_2 -power VDDPHY -ground VSS
define_pdn_grid -name ot_pg_2 -voltage_domains {ot_pg_2}
add_pdn_stripe -grid ot_pg_2 -layer M8 -width 0.48 -pitch 8.64 -offset 4.32 -spacing 3.84 -starts_with POWER
add_pdn_stripe -grid ot_pg_2 -layer M9 -width 0.48 -pitch 8.64 -offset 4.32 -spacing 3.84 -starts_with POWER
add_pdn_connect -grid ot_pg_2 -layers {M8 M9}
set region [odb::dbRegion_create $b ot_pg_3]
odb::dbBox_create $region [expr {round(5935.68*$dbu)}] [expr {round(26058.24*$dbu)}] [expr {round(11076.48*$dbu)}] [expr {round(26853.12*$dbu)}]
set_voltage_domain -name ot_pg_3 -region ot_pg_3 -power VDD -ground VSS
define_pdn_grid -name ot_pg_3 -voltage_domains {ot_pg_3}
add_pdn_stripe -grid ot_pg_3 -layer M8 -width 0.48 -pitch 4.32 -offset 2.16 -spacing 1.68 -starts_with POWER
add_pdn_stripe -grid ot_pg_3 -layer M9 -width 12.96 -pitch 39.96 -offset 12.15 -spacing 7.02 -starts_with GROUND
add_pdn_connect -grid ot_pg_3 -layers {M8 M9}
set region [odb::dbRegion_create $b ot_pg_4]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(26853.12*$dbu)}] [expr {round(11076.48*$dbu)}] [expr {round(27043.2*$dbu)}]
set_voltage_domain -name ot_pg_4 -region ot_pg_4 -power VDD -ground VSS
define_pdn_grid -name ot_pg_4 -voltage_domains {ot_pg_4}
add_pdn_stripe -grid ot_pg_4 -layer M8 -width 0.48 -pitch 4.32 -offset 2.16 -spacing 1.68 -starts_with POWER
add_pdn_stripe -grid ot_pg_4 -layer M9 -width 12.96 -pitch 39.96 -offset 13.77 -spacing 7.02 -starts_with POWER
add_pdn_connect -grid ot_pg_4 -layers {M8 M9}

pdngen
source /n/pg_grid/restore_obs.tcl
write_db /n/pg_grid/native_grid.odb
puts KV_PG_TOP_MATERIALIZED
