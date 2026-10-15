# kvsys-elements r6 2026-10-15: HBM-controller clock (pll_hbm) of the static KV return ring qkd_static_kv_return_slots
# for the REFERENCE TILE FLOW (spec sdc_extra, inlined at the end of clock.sdc and signoff.sdc; core_clk = ck is created
# by ref_tile and is NOT relaxed here).  Same constraint form as the closed write-side CDC leaf
# (physical/qwen_stream4_cdc/qkd_cdc_wleaf_ref.sdc): two asynchronous roots, core ck 833.333 ps and the HBM controller
# clock pll_hbm 1,024 ps; NO clock groups and NO false paths on the crossings: every ck <-> pll_hbm arc (published /
# consumed toggle -> first synchroniser flop, ring storage read mux -> actual_* capture) is a datapath budget = core
# period - setup uncertainty in BOTH directions, hold = non-negative datapath delay; each boundary port 0.2 T outside
# the block in its OWN domain; after CTS the pll_hbm ports are referenced to the propagated pll_hbm tree (median
# pll_hbm input pin flop) exactly as io_ref_skew.sdc does for core_clk.  hrst / rsi are captured by one flop in their
# own domain (that flop is the async clear of the domain's state), so they stay normal timed boundary inputs.
create_clock -name hclk -period 1024.000 [get_ports pll_hbm]
set_clock_uncertainty -setup 60 [get_clocks hclk]
set_clock_uncertainty -hold 25 [get_clocks hclk]

# Final hold repair may insert more than three buffers before an input capture.
# STA's actual combinational endpoints stop at the first sequential element;
# do not infer register reach from a fixed number of buffer hops.
proc ot_rs_input_clks {ports clock_name} {
  set owned [dict create]
  foreach pin [all_registers -clock $clock_name -clock_pins] {dict set owned [get_full_name $pin] 1}
  set seen [dict create];set result {}
  foreach port $ports {
    foreach endpoint [get_fanout -flat -endpoints_only -from $port] {
      set cells [get_cells -quiet -of_objects $endpoint]
      if {[llength $cells]!=1} {error "QKD_RETURN_DOMAIN: unregistered boundary endpoint [get_full_name $endpoint]"}
      set cell [get_full_name [lindex $cells 0]]
      set pins [get_pins -quiet "$cell/CLK"]
      if {[llength $pins]!=1} {error "QKD_RETURN_DOMAIN: endpoint has no unique actual register clock $cell"}
      set pin [lindex $pins 0];set name [get_full_name $pin]
      if {![dict exists $owned $name]} {error "QKD_RETURN_DOMAIN: boundary capture $name is not owned by $clock_name"}
      if {![dict exists $seen $name]} {dict set seen $name 1;lappend result $pin}
    }
  }
  return $result
}

set ot_rs_prop 0
catch {set ot_rs_prop [get_property [get_clocks core_clk] is_propagated]}
if {$ot_rs_prop} { set_propagated_clock [get_clocks hclk] }
set ot_rs_x [expr {[get_property [get_clocks core_clk] period] - 60.0}]
set_max_delay -ignore_clock_latency $ot_rs_x -from [get_clocks core_clk] -to [get_clocks hclk]
set_max_delay -ignore_clock_latency $ot_rs_x -from [get_clocks hclk] -to [get_clocks core_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks hclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks hclk] -to [get_clocks core_clk]
set ot_rs_hi [get_ports {controller_co[*] controller_epoch[*] compiled_hbm_put hrst}]
set ot_rs_ho [get_ports {fault_hbm}]
catch {unset_input_delay [get_ports pll_hbm]}
unset_input_delay $ot_rs_hi
unset_output_delay $ot_rs_ho
set ot_rs_lmax 0.0; set ot_rs_lmin 0.0
set ot_rs_sk 0.0; set ot_rs_hk 0.0; set ot_rs_hki 0.0
if {$ot_rs_prop} {
  set ot_rs_sk  [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set ot_rs_hk  [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set ot_rs_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  catch {sta::worst_slack_cmd max}
  set ot_rs_ck {}
  if {[llength [info procs ot_rs_input_clks]]} { set ot_rs_ck [ot_rs_input_clks $ot_rs_hi hclk] }
  if {![llength $ot_rs_ck]} { set ot_rs_ck [lrange [all_registers -clock hclk -clock_pins] 0 255] }
  set ot_rs_pf {}
  foreach p $ot_rs_ck {
    set a [get_property $p arrival_max_rise]
    if {[string is double -strict $a]} { lappend ot_rs_pf [list $a $p] }
  }
  if {[llength $ot_rs_pf]} {
    set ot_rs_m [lindex [lsort -real -index 0 $ot_rs_pf] [expr {[llength $ot_rs_pf] / 2}]]
    set ot_rs_lmax [lindex $ot_rs_m 0]
    set ot_rs_lmin [get_property [lindex $ot_rs_m 1] arrival_min_rise]
    if {![string is double -strict $ot_rs_lmin]} { set ot_rs_lmin $ot_rs_lmax }
    puts "QKD_RETURN_SLOTS hclk reference [get_full_name [lindex $ot_rs_m 1]] of [llength $ot_rs_pf] pin flops: clock arrival max $ot_rs_lmax min $ot_rs_lmin skew $ot_rs_sk hold $ot_rs_hk"
  } else {
    puts "QKD_RETURN_SLOTS hclk reference: no hclk register arrival (ideal boundary kept)"
  }
  set_input_delay  [expr {204.8 + $ot_rs_lmax + $ot_rs_sk}] -max -clock hclk $ot_rs_hi
  set_input_delay  [expr {$ot_rs_lmin - $ot_rs_hki}]         -min -clock hclk $ot_rs_hi
  set_output_delay [expr {204.8 - $ot_rs_lmax + $ot_rs_sk}] -max -clock hclk $ot_rs_ho
  set_output_delay [expr {0.0 - $ot_rs_lmin - $ot_rs_hk}]    -min -clock hclk $ot_rs_ho
} else {
  set_input_delay  204.800 -clock hclk $ot_rs_hi
  set_output_delay 204.800 -clock hclk $ot_rs_ho
}

# r2: core inputs must use their own clock tree, rather than the global input
# median dominated by 291 hclk capture flops. Keep the same 90/50 ps skew
# envelope and all cross-clock checks. Every selected pin is checked against
# the actual owning clock's register census; swapped domains fail closed.
proc ot_rs_owned_ref {clock_name ports} {
  set owned [dict create]
  foreach pin [all_registers -clock $clock_name -clock_pins] {
    dict set owned [get_full_name $pin] 1
  }
  set candidates {}
  foreach pin [ot_rs_input_clks $ports $clock_name] {
    if {![dict exists $owned [get_full_name $pin]]} {
      error "QKD_RETURN_DOMAIN: boundary capture [get_full_name $pin] is not owned by $clock_name"
    }
    set a [get_property $pin arrival_max_rise]
    set b [get_property $pin arrival_min_rise]
    if {![string is double -strict $a] || ![string is double -strict $b]} {
      error "QKD_RETURN_DOMAIN: missing propagated clock arrival $clock_name [get_full_name $pin]"
    }
    lappend candidates [list $a $b [get_full_name $pin]]
  }
  if {![llength $candidates]} {error "QKD_RETURN_DOMAIN: no owned boundary captures for $clock_name"}
  set m [lindex [lsort -real -index 0 $candidates] [expr {[llength $candidates]/2}]]
  puts "QKD_RETURN_DOMAIN $clock_name n=[llength $candidates] max=[lindex $m 0] min=[lindex $m 1] reference=[lindex $m 2]"
  return [lrange $m 0 1]
}
set ot_rs_ci [get_ports {expected_put expected_sector[*] expected_epoch[*] expected_layer[*] rsi}]
set ot_rs_co [get_ports {actual_valid actual_sector[*] actual_epoch[*] actual_layer[*] actual_data[*] fault_core}]
if {$ot_rs_prop} {
  lassign [ot_rs_owned_ref core_clk $ot_rs_ci] ot_rs_cmax ot_rs_cmin
  unset_input_delay $ot_rs_ci
  unset_output_delay $ot_rs_co
  set ot_rs_cb [expr {0.2*[get_property [get_clocks core_clk] period]}]
  set_input_delay [expr {$ot_rs_cb+$ot_rs_cmax+$ot_rs_sk}] -max -clock core_clk $ot_rs_ci
  set_input_delay [expr {$ot_rs_cmin-$ot_rs_hki}] -min -clock core_clk $ot_rs_ci
  set_output_delay [expr {$ot_rs_cb-$ot_rs_cmax+$ot_rs_sk}] -max -clock core_clk $ot_rs_co
  set_output_delay [expr {-$ot_rs_cmin-$ot_rs_hk}] -min -clock core_clk $ot_rs_co
}
