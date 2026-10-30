read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/3_place.odb
set b [ord::get_db_block];set before {}
foreach i [$b getInsts] {dict set before [$i getName] [list [[$i getMaster] getName] [$i getOrient] [$i getLocation] [$i getPlacementStatus]]}
pdngen -ripup
source /work/pdn_m4.tcl
pdngen
source /work/pg_connect.tcl
ot_pg_connect_all phy103_pdn_m4
ot_pg_require_bound phy103_pdn_m4
foreach i [$b getInsts] {
 set now [list [[$i getMaster] getName] [$i getOrient] [$i getLocation] [$i getPlacementStatus]]
 if {![dict exists $before [$i getName]] || $now ne [dict get $before [$i getName]]} {error "PDN changed cell placement/master"}
}
write_db /work/3_place_pg_m4.odb
puts PHY103_PDN_M4_GEOMETRY_IDENTITY_PASS_NO_CTS_GRT_STA
