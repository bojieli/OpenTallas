# DSROM QPIPE sign-off STA (2026-10-03): one corner (CORNER = SS | FF) on an ORFS stage database with the run's own
# SDC (60 ps setup / 25 ps hold uncertainty, multicycle ROM paths), parasitics from SPEF when given, else placement
# estimates.  Reports setup (SS) or hold (FF) WNS/TNS/violating endpoints and the worst paths.
set C $::env(CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty $L/$f }
read_liberty [lindex [glob $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_*.lib*] 0]
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { estimate_parasitics -placement }
set_propagated_clock [all_clocks]
set kind [expr {$C eq "FF" ? "min" : "max"}]
check_setup -verbose
report_checks -unconstrained -path_delay min_max -group_path_count 5
