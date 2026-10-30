set corner $::env(CORNER)
set lp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach stem {INVBUF SIMPLE SEQ AO OA} {
 set rev [expr {$stem eq "INVBUF" ? "220122" : $stem eq "SEQ" ? "220123" : "211120"}]
 foreach l [glob $lp/asap7sc7p5t_${stem}_RVT_${corner}_nldm_${rev}.lib*] {read_liberty $l}
}
set macrocorner [expr {$corner eq "FF" ? "ff" : "tt"}]
foreach l [glob /work/macros/*_${macrocorner}.lib] {read_liberty $l}
read_db /work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb
read_sdc /work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.sdc
set_propagated_clock [get_clocks clk]
source /work/vclk_corner.tcl
ot_vclk_bind $macrocorner
source /work/setRC_rcx.tcl
estimate_parasitics -placement
puts "PROBE_CORNER $corner"
report_checks -path_delay min -group_count 16 -format full_clock_expanded -fields {slew cap input_pin net fanout} -digits 3
report_checks -path_delay max -group_count 8 -format full_clock_expanded -fields {slew cap input_pin net fanout} -digits 3
