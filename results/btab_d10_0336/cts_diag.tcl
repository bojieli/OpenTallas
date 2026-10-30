set c $::env(OT_DIAG_CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db /work/run/results/asap7/codex_btab_mif1_1847/base/4_cts.odb
foreach pat {AO_*211120.lib.gz INVBUF_*220122.lib.gz OA_*211120.lib.gz SEQ_*220123.lib SIMPLE_*211120.lib.gz} { set pat [string map [list _* _RVT_${c}_nldm_] $pat]; foreach f [glob $L/asap7sc7p5t_$pat] {read_liberty $f} }
foreach f [glob /work/macros/*_[string tolower $c].lib] {read_liberty $f}
read_sdc /work/constraint.sdc
if {$c eq "FF"} {read_sdc /work/vclk_ff.sdc}
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
puts "DIAG_FRAME $c existing golden constraint, FF overlay only; actual CTS placement RC, NOT SIGNOFF"
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded -fields {slew cap fanout}
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded -fields {slew cap fanout}
puts [format "DIAG_RESULT %s setup_ps %.3f hold_ps %.3f" $c [expr {[sta::worst_slack_cmd max]*1e12}] [expr {[sta::worst_slack_cmd min]*1e12}]]
