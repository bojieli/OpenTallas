# nbr_in_ref.tcl ([cg] 2026-10-10): the abutting-input IO reference measured on THIS session's clock tree, without
# -reference_pin (whose Sim edge handling SEGVs OpenROAD on front_c).  The neighbour's flop sits at this block's
# input pin-flop insertion in every corner, so the virtual clock nbr_clk_i (hbm_accel_smh_physical.py --io-vclk) gets
# set_clock_latency -source = the MEDIAN clock arrival of the input pin flops (ports -> D directly or through <= 2
# buffers; pinflop_ref.tcl ot_pf_clks), per scene: -max from the setup scene, -min from the hold scene (one value in a
# single-scene session: corner_sta / hold ECO).  Ideal clocks / no nbr_clk_i: no change (the static values stay).
# 41d42c804 front_c i8ob: the static median (TT 667.5 / FF 548.2, measured on another run's tree) put the fx_b pin flops
# (u_xld, FF 638) 90 ps late against the reference -> hold flood -258.
proc ot_nir_scene_arr {p sc} {
  if {$sc eq ""} { set v [get_property $p arrival_max_rise]; return [expr {[string is double -strict $v] ? $v : ""}] }
  sta::redirect_string_begin
  catch {report_arrival -scene $sc -digits 4 $p}
  set r [sta::redirect_string_end]
  set v ""
  foreach {- ck e rv fv} [regexp -all -inline {\((\S+) ([\^v])\)\s+r\s+(\S+)\s+f\s+(\S+)} $r] {
    if {$e ne "^"} continue
    set x [lindex [split $rv :] end]
    if {[string is double -strict $x] && ($v eq "" || $x > $v)} { set v $x }
  }
  return $v
}
proc ot_nir_median {pins sc} {
  set a {}
  foreach p $pins { set v [ot_nir_scene_arr $p $sc]; if {$v ne ""} { lappend a $v } }
  if {![llength $a]} { return "" }
  set a [lsort -real $a]
  return [list [lindex $a [expr {[llength $a] / 2}]] [lindex $a 0] [lindex $a end] [llength $a]]
}
proc ot_nir_apply {tag} {
  set ci [get_clocks -quiet nbr_clk_i]
  set ck [get_clocks -quiet core_clk]
  if {![llength $ci] || ![llength $ck]} { puts "OT_NIR $tag: no nbr_clk_i -> unchanged"; return }
  if {[catch {get_property $ck is_propagated} prop] || !$prop} { puts "OT_NIR $tag: clocks ideal -> static latencies kept"; return }
  if {![llength [info procs ot_pf_clks]]} { source /src/physical/qwen_die_masters/pinflop_ref.tcl }
  set ports {}
  foreach p [all_inputs -no_clocks] { if {![string match rst* [get_full_name $p]]} { lappend ports $p } }
  set pins [ot_pf_clks $ports]
  if {![llength $pins]} { puts "OT_NIR $tag: no input pin flops -> unchanged"; return }
  catch {sta::worst_slack_cmd max}
  set ms 0
  catch {set ms [sta::multi_scene]}
  if {$ms} {
    set su [expr {[info exists ::env(OT_NIR_SETUP_SCENE)] ? $::env(OT_NIR_SETUP_SCENE) : "WC"}]
    set ho [expr {[info exists ::env(OT_NIR_HOLD_SCENE)] ? $::env(OT_NIR_HOLD_SCENE) : "BC"}]
    set mx [ot_nir_median $pins $su]; set mn [ot_nir_median $pins $ho]
  } else {
    set mx [ot_nir_median $pins ""]; set mn $mx
  }
  if {$mx eq "" || $mn eq ""} { puts "OT_NIR $tag: no arrivals -> unchanged"; return }
  set_clock_latency -source -max [format %.1f [lindex $mx 0]] $ci
  set_clock_latency -source -min [format %.1f [lindex $mn 0]] $ci
  puts [format "OT_NIR %s: %d input pin flops, median max %.1f (%.1f..%.1f) min %.1f (%.1f..%.1f) -> nbr_clk_i source latency" \
    $tag [lindex $mx 3] [lindex $mx 0] [lindex $mx 1] [lindex $mx 2] [lindex $mn 0] [lindex $mn 1] [lindex $mn 2]]
}
