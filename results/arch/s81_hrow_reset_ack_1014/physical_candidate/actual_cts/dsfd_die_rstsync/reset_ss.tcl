set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*RVT_SS*] {read_liberty $l}
foreach l [glob $plat/lib/NLDM/*_LVT_SS_* $plat/lib/NLDM/*_SLVT_SS_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /work/results/asap7/opentallas_dsfd_die_rstsync_asap7_ref_gate/base/4_1_cts.odb
read_sdc /work/results/asap7/opentallas_dsfd_die_rstsync_asap7_ref_gate/base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner ss
read_sdc /src/physical/ref_tile/dsfd_die_rstsync_m5_ack1/signoff.sdc
set_propagated_clock [all_clocks]
report_checks -to [all_registers -async_pins] -path_delay min_max -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 4 -group_path_count 20000 > /out/reset_ss.rpt
if {[catch {report_pulse_width_checks -verbose > /out/pulse_ss.rpt} why]} {puts "PULSE_WIDTH_OPEN $why"}
puts "CTS_RESET_DONE ss placementRC diagnostic; global source/phase/routed SSFF OPEN"
exit
