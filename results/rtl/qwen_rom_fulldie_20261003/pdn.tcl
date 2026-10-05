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
