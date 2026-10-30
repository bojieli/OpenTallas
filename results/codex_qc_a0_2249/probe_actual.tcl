# Actual corrected-CTS snapshot diagnostic. No IO/source-latency rebinding, no signoff claim.
set C $::env(OT_CORNER);set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db /work/diag/cts_prehold.odb
set np2p 0
foreach i [[ord::get_db_block] getInsts] {if {[string match mp_p2p_* [$i getName]]} {incr np2p}}
if {$np2p<10000} {error "REFUSE_STALE_OR_INCOMPLETE_CTS np2p=$np2p"}
puts "ACTUAL_AD2PR1_CELLS $np2p"
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] {read_liberty $f}
foreach f [glob -nocomplain /work/macros/*_${c}.lib] {read_liberty $f}
read_sdc $::env(PLACE_SDC)
if {$C eq "FF"} {read_sdc /work/vclk_ff.sdc}
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "ACTUAL_WS $C setup [expr {[sta::worst_slack_cmd max]*1e12}] hold [expr {[sta::worst_slack_cmd min]*1e12}]"
set ::ot_ps_lib_only 1
source /src/pair_skew.tcl
unset ::ot_ps_lib_only
set regs {};set data {};set async {};set boundary {}
foreach p [all_registers -clock_pins] {
 set i [get_cells -of_objects $p];set m [get_property $i ref_name]
 if {![regexp {^(DFF|SDFF)} $m]} continue
 dict set regs [get_full_name $i] $p
}
foreach p [all_registers -async_pins] {dict set async [get_full_name $p] 1}
foreach p [all_registers -data_pins] {set n [get_full_name $p];if {![dict exists $async $n]} {dict set data $n 1}}
set din {}
foreach p [all_inputs] {if {[get_full_name $p] ni {ck rst_n}} {lappend din $p}}
foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
 set n [get_full_name $p];set i [regsub {/[^/]+$} $n {}]
 if {[dict exists $data $n] && [dict exists $regs $i]} {dict set boundary $i 1}
}
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
 set i [regsub {/[^/]+$} [get_full_name $p] {}]
 if {[dict exists $regs $i]} {dict set boundary $i 1}
}
set fh [open /out/pins_${c}.tsv w];puts $fh "kind\tinstance\tclock_pin\tactive_edge\tarrival_min_ps\tarrival_max_ps"
dict for {i p} $regs {
 set edge [ot_ps_edge $p];set amin [get_property $p arrival_min_$edge];set amax [get_property $p arrival_max_$edge]
 set kind [expr {[dict exists $boundary $i]?"face_ff":"body_ff"}]
 puts $fh "$kind\t$i\t[get_full_name $p]\t$edge\t$amin\t$amax"
}
proc literal_pin {n} {string map {[ \[ ] \]} $n}
source /src/macro_clocks.tcl
foreach name $macro_clock_pins {
 set p [get_pins -quiet [literal_pin $name]]
 if {$p eq ""} {error "MISSING_MACRO_CLOCK $name"}
 puts $fh "macro_clk\t[regsub {/[^/]+$} $name {}]\t$name\trise\t[get_property $p arrival_min_rise]\t[get_property $p arrival_max_rise]"
}
close $fh
set tf /work/core_latency.txt
if {$C eq "FF"} {set tf /work/core_latency_ff.txt}
if {[file exists $tf]} {ot_ps_load_targets $tf}
ot_ps_zero_unc
set M [ot_ps_measure 5000]
ot_ps_write $M /out/pairs_${c}.tsv $C
puts "ACTUAL_PAIRS $C max [dict get $M max worst] min [dict get $M min worst]"
