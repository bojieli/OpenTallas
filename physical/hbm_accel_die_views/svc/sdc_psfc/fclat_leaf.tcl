# svc-fix 2026-10-10: face clock taps (ckw / cke, gen_svc_seg.py --fc) balanced at their LEAVES.
# The caller sets ot_fcl = the segment's boundary-register mean insertion (calibrate CK_<corner>_MEAN).  The tap's own
# tree (port -> buffers -> the one-stage face flops: ~60 ps FF / ~75 ps TT on SE_s5) came on top of it, so the tap
# stages captured ~70 ps after the inputs' reference (SE_s5 psfcpr hm10 GRT hold -70 on c_rs26_1 / c_rs27_1, not
# converging; SW_s6 the same class).  Each tap's source latency is set so its sinks' MEAN clock arrival equals ot_fcl.
# Ideal clocks (synthesis / floorplan) or no measurable sink: the plain ot_fcl source latency stays.  Idempotent: the
# tree is re-measured from ot_fcl on every read.
proc ot_fcl_sinks {port} {
  set out {}; set nets [get_nets -quiet [get_full_name [get_ports -quiet $port]]]
  set seen [dict create]
  for {set hop 0} {$hop < 24 && [llength $nets]} {incr hop} {
    set next {}
    foreach nn $nets {
      foreach pin [get_pins -quiet -of_objects $nn] {
        if {[get_property $pin direction] ne "input"} continue
        set c [get_cells -quiet -of_objects $pin]; if {![llength $c]} continue
        set fn [get_full_name $c]; if {[dict exists $seen $fn]} continue; dict set seen $fn 1
        if {[get_property $pin lib_pin_name] eq "CLK"} { lappend out $pin; continue }
        if {[regexp {^(BUF|HB|INV|CKINV)} [get_property $c ref_name]]} {
          foreach op [get_pins -quiet -of_objects $c] { if {[get_property $op direction] eq "output"} { lappend next [get_nets -quiet -of_objects $op] } }
        }
      }
    }
    set nets $next
  }
  return $out
}
foreach ot_fp {ckw[0] cke[0]} {
  if {![llength [get_ports -quiet $ot_fp]]} continue
  set_clock_latency -source $ot_fcl [get_ports $ot_fp]
  set ot_s 0.0; set ot_n 0
  if {[catch {
    foreach p [ot_fcl_sinks $ot_fp] {
      set a [get_property $p arrival_max_rise]
      if {[string is double -strict $a]} { set ot_s [expr {$ot_s + $a}]; incr ot_n }
    }
  } ot_e]} { puts "OT_FCL_LEAF $ot_fp: $ot_e -- source latency $ot_fcl kept"; continue }
  if {$ot_n == 0} continue
  set ot_tree [expr {$ot_s / $ot_n - $ot_fcl}]
  # ideal clocks report the source latency itself (tree 0): nothing to move
  if {$ot_tree <= 0.5} continue
  set_clock_latency -source [expr {$ot_fcl - $ot_tree}] [get_ports $ot_fp]
  puts [format "OT_FCL_LEAF %s: %d sinks, tap tree %.1f ps -> source latency %.1f (leaf mean = %s)" $ot_fp $ot_n $ot_tree [expr {$ot_fcl - $ot_tree}] $ot_fcl]
}
