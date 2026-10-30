set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [concat [glob $P/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] [glob -nocomplain $P/asap7sc7p5t_SEQ_RVT_TT*]] { read_liberty $f }
read_liberty /work/macros/ot_sram_1r1w_32x128_m1_tt.lib
read_db /res/4_1_cts.odb
read_sdc /res/4_cts.sdc
source /work/setRC_rcx.tcl
set ::env(OT_ISLBAL_REPORT_ONLY) [expr {[info exists ::env(RO)] ? $::env(RO) : 0}]
set t0 [clock seconds]
uplevel #0 {source /work/island_balance.tcl}
puts "DRY elapsed [expr {[clock seconds]-$t0}] s"
