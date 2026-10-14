set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*RVT_FF*] {read_liberty $l}
foreach l [glob $plat/lib/NLDM/*_LVT_FF_* $plat/lib/NLDM/*_SLVT_FF_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /work/results/asap7/opentallas_dsfd_mtp_hrow_hub_asap7_ref_gate/base/4_1_cts.odb
read_sdc /work/results/asap7/opentallas_dsfd_mtp_hrow_hub_asap7_ref_gate/base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner ff
read_sdc /src/physical/ref_tile/hrow5_hub_ack1/signoff.sdc
set_propagated_clock [all_clocks]
report_checks -to [all_registers -async_pins] -path_delay min_max -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 4 -group_path_count 20000 > /out/reset_ff.rpt
if {[catch {report_pulse_width_checks -verbose > /out/pulse_ff.rpt} why]} {puts "PULSE_WIDTH_OPEN $why"}
puts "CTS_RESET_DONE ff placementRC diagnostic; global source/phase/routed SSFF OPEN"
exit
