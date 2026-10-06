# Body-only, ps/fF ASAP7 units. No failed76158 generator is present.
# Supply a source-pinned dictionary BEFORE sourcing this file. No timing defaults.
# Modes are characterized or research_assumption; the latter yields conditional
# body timing only, never clock-source/PLL qualification.
# Owner's later explicit ideal-input BODY option is already installed by the
# owner SDC that Zeno sources first. It intentionally supplies NO IP numbers.
# Keep this separate from the numeric characterization/research binder below.
if {[info exists wfc_clock_boundary_mode] && $wfc_clock_boundary_mode eq "owner_ideal_input_body"} {
 if {![info exists wfc_evidence_class] || $wfc_evidence_class ne "IDEAL_EXTERNAL_INPUT_DIAGNOSTIC"} {
  error "Missing explicit ideal external input diagnostic evidence class"
 }
 foreach {flag required} {wfc_body_conditional 1 wfc_clock_source_qualified 0 wfc_other_engine_IO_bound 0 wfc_headline_allowed 0} {
  if {![info exists $flag] || [set $flag] != $required} {
   error "Ideal-input BODY conditional flag missing or changed: $flag"
  }
 }
 foreach c {clk_fast clk_serial} {
  if {[llength [get_clocks -quiet $c]] != 1} {error "Missing ideal-input BODY clock $c"}
 }
 foreach p {fast_clk slow_clk clock_source_fault cold_n fast_rst_n slow_rst_n} {
  if {[llength [get_ports -quiet $p]] != 1} {error "Missing ideal-input BODY port $p"}
 }
 puts "WFC_BINDER IDEAL_EXTERNAL_INPUT_DIAGNOSTIC NO_IP_NUMBERS_OR_SOURCE_QUALIFICATION"
 return
}
if {![info exists wfc_clock_ip_binding]} {
 error "Missing wfc_clock_ip_binding: actual IP terminals/latency/slew/jitter/reset/fault required"
}
proc wfc_required {d k} {
 if {![dict exists $d $k] || [dict get $d $k] eq ""} {error "Missing clock-IP field $k"}
 return [dict get $d $k]
}
proc wfc_number {d k} {
 set v [wfc_required $d $k]
 if {![string is double -strict $v] || $v < 0 || $v != $v || $v == Inf} {
  error "Invalid nonnegative finite clock-IP field $k: $v"
 }
 return $v
}
proc wfc_range {d lo hi} {
 set a [wfc_number $d $lo]; set b [wfc_number $d $hi]
 if {$a > $b} {error "Clock-IP range reversed: $lo > $hi"}
}
proc wfc_one_port {name} {
 set p [get_ports -quiet $name]
 if {[llength $p] != 1} {error "Missing unique body port $name"}
 return $p
}
set b $wfc_clock_ip_binding
set mode [wfc_required $b evidence_class]
if {$mode ni {characterized research_assumption}} {error "Invalid clock-IP evidence_class"}
foreach k {source_record source_sha256 coherent_edge_contract fault_policy_record} {wfc_required $b $k}
if {[dict get $b coherent_edge_contract] ne "fast_1_4_7_slow_1_5_9"} {
 error "Unsupported phase/duty change"
}
# Validate EVERYTHING before installing any constraints.
foreach domain {fast slow} {
 set d [wfc_required $b $domain]
 wfc_required $d source_terminal
 foreach edge {rise fall} {
  wfc_range $d ${edge}_latency_min_ps ${edge}_latency_max_ps
  wfc_range $d ${edge}_slew_min_ps ${edge}_slew_max_ps
 }
 wfc_number $d extra_setup_uncertainty_ps
 wfc_number $d extra_hold_uncertainty_ps
}
foreach name {clock_source_fault cold_n fast_rst_n slow_rst_n} {
 set d [wfc_required $b $name]
 wfc_required $d source_terminal
 set c [wfc_required $d launch_clock]
 if {$c ni {clk_fast clk_serial}} {error "Unbound launch clock for $name"}
 wfc_range $d arrival_min_ps arrival_max_ps
 wfc_range $d slew_min_ps slew_max_ps
 wfc_one_port $name
}
wfc_one_port fast_clk
wfc_one_port slow_clk
# The common source is OUTSIDE the body. These two synchronous input clocks
# carry the same nominal common epoch, exact3:4 ratio and50% duty. Their actual
# insertion bounds are source latency below; they are not a qualified PLL.
create_clock -name clk_fast -period 833.333333333333 -waveform {0 416.666666666667} [get_ports fast_clk]
create_clock -name clk_serial -period 1111.111111111111 -waveform {0 555.555555555556} [get_ports slow_clk]
foreach domain {fast slow} c {clk_fast clk_serial} {
 set d [dict get $b $domain]
 foreach edge {rise fall} {
  set_clock_latency -source -early -$edge [dict get $d ${edge}_latency_min_ps] [get_clocks $c]
  set_clock_latency -source -late -$edge [dict get $d ${edge}_latency_max_ps] [get_clocks $c]
  set_clock_transition -min -$edge [dict get $d ${edge}_slew_min_ps] [get_clocks $c]
  set_clock_transition -max -$edge [dict get $d ${edge}_slew_max_ps] [get_clocks $c]
 }
 # Additional bounds must cover source/relative phase uncertainty, not silently
 # replace the mandatory60/25 policy. Common-source correlation is not assumed.
 set_clock_uncertainty -setup [expr {60+[dict get $d extra_setup_uncertainty_ps]}] [get_clocks $c]
 set_clock_uncertainty -hold [expr {25+[dict get $d extra_hold_uncertainty_ps]}] [get_clocks $c]
}
foreach name {clock_source_fault cold_n fast_rst_n slow_rst_n} {
 set d [dict get $b $name]
 set p [get_ports $name]
 set_input_delay -min [dict get $d arrival_min_ps] -clock [get_clocks [dict get $d launch_clock]] $p
 set_input_delay -max [dict get $d arrival_max_ps] -clock [get_clocks [dict get $d launch_clock]] $p
 set_input_transition -min [dict get $d slew_min_ps] $p
 set_input_transition -max [dict get $d slew_max_ps] $p
}
# Zeno owns actual network CTS/propagation and all other body IO bindings.
# No IO false paths, asynchronous clock groups, network-latency budgets, reset
# exceptions, generic data loads, PLL slew defaults, or jitter=0 are inserted.
