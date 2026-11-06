set p /OpenROAD-flow-scripts/flow/platforms/asap7
set ::env(PLATFORM_DIR) $p
foreach pat {AO INVBUF OA SIMPLE SEQ} {
 set fs [glob -nocomplain $p/lib/NLDM/asap7sc7p5t_${pat}_RVT_FF*.lib*]
 if {$pat eq "SIMPLE"} {set fs [glob $p/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz]}
 if {[llength $fs] != 1} {error "FF library ambiguity $pat $fs"}
 read_liberty [lindex $fs 0]
}
foreach f [glob /kit/macros/*_ff.lib] {read_liberty $f}
read_db /kit/run/results/asap7/hbc_ot_hfd_coll_q3_body_ctl/base/4_cts.odb
read_sdc /kit/run/results/asap7/hbc_ot_hfd_coll_q3_body_ctl/base/4_cts.sdc
source /kit/setRC_rcx.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
source /kit/vclk_ff.sdc
set ::env(OT_BODY_CHAIN_CANARY) 1
set ::env(OT_BODY_CHAIN_DIR) /out
source /out/body_chain_clock_canary.tcl
exit
