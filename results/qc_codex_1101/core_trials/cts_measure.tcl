# Diagnostic only: real CTS geometry, calibrated placement RC. No signoff or timing abstracts are written.
set C $::env(OT_CORNER)
set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
set source [lindex [glob /work/run/results/asap7/*/base/4_cts.odb] 0]
read_db $source
if {$C eq "FF"} { read_sdc /work/vclk_ff.sdc } else { read_sdc /work/constraint.sdc }
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set_propagated_clock [get_clocks clk]
source /work/vclk_measured_hold.tcl
lassign [ot_vmh_pinreg_mean] mean n bad clocks
if {$n < 1 || $bad || ![string is double -strict $mean]} { error "CTS boundary clock mean unavailable" }
set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
set hs [expr {[sta::worst_slack_cmd min] * 1e12}]
set f [open /work/cts_frame_${c}.json w]
puts $f [format {{"scope":"CTS geometry diagnostic","rc":"calibrated placement estimate, NOT routed signoff","corner":"%s","pinreg_mean_ps":%.6f,"samples":%d,"missing":%d,"clocks":%d,"setup_wns_ps":%.6f,"hold_wns_ps":%.6f}} $C $mean $n $bad $clocks $ws $hs]
close $f
puts "CODEX_CTS_FRAME corner=$C mean=$mean samples=$n bad=$bad clocks=$clocks setup=$ws hold=$hs"
