# tools/qwen_rom_fulldie.py die PDN: M8/M9 per-region straps at the r2 coverages (per net)
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {core} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {core} -layer {M8} -width {0.48} -pitch {10.88} -offset {2.0}
add_pdn_stripe -grid {core} -layer {M9} -width {0.48} -pitch {10.88} -offset {2.0}
add_pdn_connect -grid {core} -layers {M8 M9}
set strip_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { foreach pp {qfd_reng qfd_lfifo qfd_ctrl} { if {[string match $pp [$c getName]]} { lappend strip_cells [$c getName] } } } }
define_pdn_grid -macro -cells $strip_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {strip}
add_pdn_stripe -grid {strip} -layer {M8} -width {0.48} -pitch {2.88} -offset {1.0}
add_pdn_stripe -grid {strip} -layer {M9} -width {0.48} -pitch {2.88} -offset {1.0}
add_pdn_connect -grid {strip} -layers {M8 M9}
set hub_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { foreach pp {qfd_hub qfd_sp_* qfd_lst_*} { if {[string match $pp [$c getName]]} { lappend hub_cells [$c getName] } } } }
define_pdn_grid -macro -cells $hub_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hub}
add_pdn_stripe -grid {hub} -layer {M8} -width {0.48} -pitch {19.2} -offset {1.0}
add_pdn_stripe -grid {hub} -layer {M9} -width {0.48} -pitch {19.2} -offset {1.0}
add_pdn_connect -grid {hub} -layers {M8 M9}
set io_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { foreach pp {qfd_io_*} { if {[string match $pp [$c getName]]} { lappend io_cells [$c getName] } } } }
define_pdn_grid -macro -cells $io_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {io}
add_pdn_stripe -grid {io} -layer {M8} -width {0.48} -pitch {19.2} -offset {1.0}
add_pdn_stripe -grid {io} -layer {M9} -width {0.48} -pitch {19.2} -offset {1.0}
add_pdn_connect -grid {io} -layers {M8 M9}

set phy_cells {}
# 2026-10-15 (kvs8-codex-1338 PSM-0039 ucie_rom / serdes_host VDD): the UCIe and host SerDes PHY abstracts carry the same
# single horizontal M4 PG rails as the HBM PHY -> the same M5-strap grid
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { foreach pp {ot_hbm3e_phy* OT_PDN_BBOX_ot_hbm3e_phy* qkd_hbm3e_phy_pc OT_PDN_BBOX_qkd_hbm3e_phy_pc} { if {[string match $pp [$c getName]]} { lappend phy_cells [$c getName] } } } }
set phy_cells [lsort -unique $phy_cells]
if {[llength $phy_cells]} {
  define_pdn_grid -macro -cells $phy_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {phy}
  add_pdn_stripe -grid {phy} -layer {M5} -width {0.12} -pitch {10.88} -offset {1.0}
  add_pdn_connect -grid {phy} -layers {M4 M5}
  add_pdn_connect -grid {phy} -layers {M5 M8}
}
# kv-die it2 (die_iter_1012): bound real element views (exact LEFs) carry their PG pins as full-length horizontal M6
# stripes (layer contract: leaf PG on M6, parent straps one layer up).  M6 and the die's M8 are both horizontal, so the
# die grid never reaches them (it1 die_kvi1: all 132 bound views PSM-0039 unconnected, PSM-0069).  Vertical M7 straps
# over every block master whose VDD pin is on M6: M6 -> M7 at each crossing, M7 -> M8 onto the core grid.
set hv6_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock]} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M6"} { lappend hv6_cells [$c getName] } } }
} }
set hv6_cells [lsort -unique $hv6_cells]
puts "OT_HV6 masters [llength $hv6_cells]: $hv6_cells"
if {[llength $hv6_cells]} {
  define_pdn_grid -macro -cells $hv6_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv6}
  add_pdn_stripe -grid {hv6} -layer {M7} -width {0.288} -pitch {10.88} -offset {2.0}
  add_pdn_connect -grid {hv6} -layers {M6 M7}
  add_pdn_connect -grid {hv6} -layers {M7 M8}
}
# qwen-split kvs1 (PSM-0039 on all 128 head_hs): cluster views whose PG pins are VERTICAL M7 stripes (no M6 PG) only need the
# M7 -> M8 connect onto the core grid (the core M8 straps cross their M7 stripes)
set hv7_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock] || [lsearch -exact $hv6_cells [$c getName]] >= 0} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M7"} { lappend hv7_cells [$c getName] } } }
} }
set hv7_cells [lsort -unique $hv7_cells]
puts "OT_HV7 masters [llength $hv7_cells]: $hv7_cells"
if {[llength $hv7_cells]} {
  define_pdn_grid -macro -cells $hv7_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv7}
  add_pdn_connect -grid {hv7} -layers {M7 M8}
}
# qwen-split kvsys v1.1 (kvs1 PSM-0039 on all 128 qkd_cdc_wleaf; the sl1 write leaf too): M5-capped leaf views whose PG pins
# are VERTICAL M5 stripes (no M6 / M7 PG): the core grid's horizontal M8 straps cross them -> a stacked M5 -> M8 connect
# (M6 / M7 are free over an M5-capped leaf)
set hv5_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock] || [lsearch -exact $hv6_cells [$c getName]] >= 0 || [lsearch -exact $hv7_cells [$c getName]] >= 0} { continue }
  if {[string match ot_hbm3e_phy* [$c getName]] || [string match OT_PDN_BBOX_ot_hbm3e_phy* [$c getName]]} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M5"} { lappend hv5_cells [$c getName] } } }
} }
set hv5_cells [lsort -unique $hv5_cells]
puts "OT_HV5 masters [llength $hv5_cells]: $hv5_cells"
# 2026-10-15 (Q-KVSYS-DIE, kvs8-codex-1338 PSM-0069: 998+ head nb1 / nb2 leaves VDD unconnected): a SHORT M5-PG leaf (the
# 32.4 x 10.8 node-beat stations: one VDD M5 pin spanning y 2.15..8.65) is crossed by a core M8 VDD strap (10.88 pitch) only
# ~60 % of the time.  Leaves shorter than two core pitches get their own M8 straps at 5.44 (each net inside any 5.4-um pin
# span), stacked M5 -> M8 and M8 -> core M9 (the M9 straps cross every leaf >= 10.88 wide).  Fixture: 3 nb leaves R0/MX,
# without: PSM-0069 VDD + VSS; with: check_power_grid VDD / VSS PASS, 0 M8 VDD/VSS overlaps.
set hv5s_cells {}
foreach n $hv5_cells { foreach mst [[ord::get_db] getLibs] { set c [$mst findMaster $n]
  if {$c ne "NULL" && [$c getHeight] < 21760} { lappend hv5s_cells $n } } }
set hv5s_cells [lsort -unique $hv5s_cells]
set hv5_cells [lmap n $hv5_cells { if {[lsearch -exact $hv5s_cells $n] >= 0} continue; set n }]
puts "OT_HV5S short masters [llength $hv5s_cells]: $hv5s_cells"
if {[llength $hv5_cells]} {
  define_pdn_grid -macro -cells $hv5_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv5}
  add_pdn_connect -grid {hv5} -layers {M5 M8}
}
if {[llength $hv5s_cells]} {
  define_pdn_grid -macro -cells $hv5s_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv5s}
  add_pdn_stripe -grid {hv5s} -layer {M8} -width {0.48} -pitch {5.44} -offset {2.4}
  add_pdn_connect -grid {hv5s} -layers {M5 M8}
  add_pdn_connect -grid {hv5s} -layers {M8 M9}
}

# KV die-top tie cells (die_tie_rows.tcl rebuilt the rows around them): literal rails stacked onto the core M9 stripes
add_pdn_stripe -grid {core} -layer {M1} -width {0.018} -followpins
add_pdn_stripe -grid {core} -layer {M2} -width {0.018} -followpins
add_pdn_connect -grid {core} -layers {M1 M2}
add_pdn_connect -grid {core} -layers {M2 M9}
source /work/hbm_pg_interface.tcl
ot_hbm_pg::begin
# Explicit ASSUMED PHY PG access contract v1; source-pinned candidate LEFs required.
source /work/assumed_phy_pg_access.tcl
ot_assumed_phy_pg_grids
