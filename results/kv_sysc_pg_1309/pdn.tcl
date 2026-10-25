# SYS_C actual separate PHY supply; replaces generic partition pdn.tcl.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set phy [$b findInst {u_bound.u_ucie_rom}]
if {$phy eq "NULL"} {error "SYS_C PHY macro absent: cannot invent PHY supply"}
set n [$b findNet VDD]
if {$n eq "NULL"} {set n [odb::dbNet_create $b VDD]}
$n setSigType POWER; $n setSpecial
set n [$b findNet VDDPHY]
if {$n eq "NULL"} {set n [odb::dbNet_create $b VDDPHY]}
$n setSigType POWER; $n setSpecial
set n [$b findNet VSS]
if {$n eq "NULL"} {set n [odb::dbNet_create $b VSS]}
$n setSigType GROUND; $n setSpecial
add_global_connection -net VDD -inst_pattern {^(?!u_bound\.u_ucie_rom$).*$} -pin_pattern {^VDD$} -power
add_global_connection -net VDDPHY -inst_pattern {^u_bound\.u_ucie_rom$} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name Core -power VDD -ground VSS -secondary_power {VDDPHY}
set region [odb::dbRegion_create $b sysc_pg_0]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(0*$dbu)}] [expr {round(2160*$dbu)}] [expr {round(17.28*$dbu)}]
set_voltage_domain -name sysc_pg_0 -region sysc_pg_0 -power VDD -ground VSS
define_pdn_grid -name sysc_pg_0 -voltage_domains {sysc_pg_0} -pins {M7} -starts_with GROUND
add_pdn_connect -grid sysc_pg_0 -layers {M2 M5}
add_pdn_stripe -grid sysc_pg_0 -layer M5 -width 0.12 -spacing 0.072 -pitch 4.32 -offset 2.064000
add_pdn_stripe -grid sysc_pg_0 -layer M6 -width 0.288 -spacing 0.096 -pitch 4.32 -offset 1.968000
add_pdn_stripe -grid sysc_pg_0 -layer M7 -width 0.288 -spacing 0.096 -pitch 8.64 -offset 4.128000
add_pdn_connect -grid sysc_pg_0 -layers {M5 M6}
add_pdn_connect -grid sysc_pg_0 -layers {M6 M7}
set region [odb::dbRegion_create $b sysc_pg_1]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(17.28*$dbu)}] [expr {round(691.2*$dbu)}] [expr {round(794.88*$dbu)}]
set_voltage_domain -name sysc_pg_1 -region sysc_pg_1 -power VDD -ground VSS
define_pdn_grid -name sysc_pg_1 -voltage_domains {sysc_pg_1} -pins {M7} -starts_with GROUND
add_pdn_connect -grid sysc_pg_1 -layers {M2 M5}
add_pdn_stripe -grid sysc_pg_1 -layer M5 -width 0.12 -spacing 0.072 -pitch 4.32 -offset 2.064000
add_pdn_stripe -grid sysc_pg_1 -layer M6 -width 0.288 -spacing 0.096 -pitch 4.32 -offset 1.968000
add_pdn_stripe -grid sysc_pg_1 -layer M7 -width 0.288 -spacing 0.096 -pitch 8.64 -offset 4.128000
add_pdn_connect -grid sysc_pg_1 -layers {M5 M6}
add_pdn_connect -grid sysc_pg_1 -layers {M6 M7}
set region [odb::dbRegion_create $b sysc_pg_2]
odb::dbBox_create $region [expr {round(691.2*$dbu)}] [expr {round(17.28*$dbu)}] [expr {round(1468.8*$dbu)}] [expr {round(794.88*$dbu)}]
set_voltage_domain -name sysc_pg_2 -region sysc_pg_2 -power VDDPHY -ground VSS
define_pdn_grid -name sysc_pg_2 -voltage_domains {sysc_pg_2} -pins {M7} -starts_with GROUND
add_pdn_stripe -grid sysc_pg_2 -layer M6 -width 0.288 -spacing 0.096 -pitch 4.32 -offset 1.968000
add_pdn_stripe -grid sysc_pg_2 -layer M7 -width 0.288 -spacing 0.096 -pitch 8.64 -offset 4.128000
add_pdn_connect -grid sysc_pg_2 -layers {M6 M7}
set region [odb::dbRegion_create $b sysc_pg_3]
odb::dbBox_create $region [expr {round(1468.8*$dbu)}] [expr {round(17.28*$dbu)}] [expr {round(2160*$dbu)}] [expr {round(794.88*$dbu)}]
set_voltage_domain -name sysc_pg_3 -region sysc_pg_3 -power VDD -ground VSS
define_pdn_grid -name sysc_pg_3 -voltage_domains {sysc_pg_3} -pins {M7} -starts_with GROUND
add_pdn_connect -grid sysc_pg_3 -layers {M2 M5}
add_pdn_stripe -grid sysc_pg_3 -layer M5 -width 0.12 -spacing 0.072 -pitch 4.32 -offset 2.064000
add_pdn_stripe -grid sysc_pg_3 -layer M6 -width 0.288 -spacing 0.096 -pitch 4.32 -offset 1.968000
add_pdn_stripe -grid sysc_pg_3 -layer M7 -width 0.288 -spacing 0.096 -pitch 8.64 -offset 4.128000
add_pdn_connect -grid sysc_pg_3 -layers {M5 M6}
add_pdn_connect -grid sysc_pg_3 -layers {M6 M7}
set region [odb::dbRegion_create $b sysc_pg_4]
odb::dbBox_create $region [expr {round(0*$dbu)}] [expr {round(794.88*$dbu)}] [expr {round(2160*$dbu)}] [expr {round(1036.8*$dbu)}]
set_voltage_domain -name sysc_pg_4 -region sysc_pg_4 -power VDD -ground VSS
define_pdn_grid -name sysc_pg_4 -voltage_domains {sysc_pg_4} -pins {M7} -starts_with GROUND
add_pdn_connect -grid sysc_pg_4 -layers {M2 M5}
add_pdn_stripe -grid sysc_pg_4 -layer M5 -width 0.12 -spacing 0.072 -pitch 4.32 -offset 2.064000
add_pdn_stripe -grid sysc_pg_4 -layer M6 -width 0.288 -spacing 0.096 -pitch 4.32 -offset 1.968000
add_pdn_stripe -grid sysc_pg_4 -layer M7 -width 0.288 -spacing 0.096 -pitch 8.64 -offset 4.128000
add_pdn_connect -grid sysc_pg_4 -layers {M5 M6}
add_pdn_connect -grid sysc_pg_4 -layers {M6 M7}
define_pdn_grid -name core_rails -voltage_domains {sysc_pg_0 sysc_pg_1 sysc_pg_3 sysc_pg_4} -starts_with GROUND
add_pdn_stripe -grid core_rails -layer M1 -width .018 -pitch .54 -offset 0 -followpins
add_pdn_stripe -grid core_rails -layer M2 -width .018 -pitch .54 -offset 0 -followpins
add_pdn_connect -grid core_rails -layers {M1 M2}
define_pdn_grid -macro -cells {d2d_sram_1r1w_64x137_m1_r2c2_p288} -name sysc_sram -voltage_domains {sysc_pg_1} -halo {2 2} -grid_over_boundary
add_pdn_connect -grid sysc_sram -layers {M4 M5}
define_pdn_grid -macro -cells {ot_qkvd_ucie_x64_phy} -name sysc_phy_macro -voltage_domains {sysc_pg_2} -halo {0 0} -grid_over_boundary
add_pdn_connect -grid sysc_phy_macro -layers {M6 M7}
# Fail closed on wrong physical supply assignment before generating straps.
foreach i [$b getInsts] {
  foreach it [$i getITerms] {
    set pn [[$it getMTerm] getName]
    if {$pn ne "VDD"} {continue}
    set expected [expr {$i eq $phy ? "VDDPHY" : "VDD"}]
    set actual [$it getNet]
    if {$actual eq "NULL" || [$actual getName] ne $expected} {error "SYS_C supply mismatch [$i getName]/$pn expected=$expected"}
  }
}
