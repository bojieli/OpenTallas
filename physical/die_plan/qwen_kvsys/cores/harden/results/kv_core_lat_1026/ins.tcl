# KV-CORE-LAT-HEAD probe: TT clock arrival at every register CK pin, grouped (lane taps / rest / face pin flops) + 2 expanded clock paths
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/$f }
foreach l [glob -nocomplain /k/rtl/*tt*.lib /k/*_tt.lib] { catch {read_liberty $l} }
read_db $::env(ODB)
read_sdc $::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { source $::env(SETRC); estimate_parasitics -placement }
set_propagated_clock [all_clocks]
set face [dict create]
if {[file exists $::env(FACE)]} { set fh [open $::env(FACE)]; foreach ln [split [read $fh] "\n"] { set f [split $ln "\t"]; if {[llength $f]>=2} {dict set face [lindex $f 0] [lindex $f 1]} }; close $fh }
set pf [dict create]
set din {}
foreach p [all_inputs] { set nm [get_full_name $p]; if {![regexp {clk} $nm]} { lappend din $p } }
if {[llength $din]} { foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] { dict set pf [regsub {/[^/]+$} [get_full_name $p] {}] 1 } }
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] { dict set pf [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set out [open $::env(OUT) w]
foreach p [get_pins -hierarchical */CLK] {
  set ci [get_cells -of_objects $p]
  set inst [get_full_name $ci]
  set ref [get_property $ci ref_name]
  if {![regexp {^(DFF|ASYNC|SDF|DHL|DLL)} $ref]} continue
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  set n ""; catch {set n [get_full_name [get_nets -of_objects $p]]}
  set fc [expr {[dict exists $pf $inst] ? "P" : "-"}]
  puts $out "$inst\t$fc\t$n\t$a"
}
foreach p [get_pins -hierarchical {ot_lane_tap_*/A ot_pv_tap_*/A}] {
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  puts $out "TAPIN:[get_full_name $p]\tT\t-\t$a"
}
close $out
report_checks -path_delay max -format full_clock_expanded -digits 1 -group_path_count 1
