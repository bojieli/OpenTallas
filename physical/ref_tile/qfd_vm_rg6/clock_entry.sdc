# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {ot_qfd_vm_rr4_t/clk} {tt {113.1 121.9 129.7} ff {92.0 100.8 108.6} ss {148.0 156.6 164.8}} {ot_qfd_vm_rr2_t/clk} {tt {100.9 106.7 112.9} ff {80.3 86.6 92.7} ss {135.6 141.0 147.7}} {ot_qwen_tree_delay2_t/clk} {tt {85.1 89.9 96.5} ff {67.3 72.2 78.9} ss {116.8 121.5 128.4}} {ot_qfd_vm_bank_t/clk} {tt {293.9 319.3 430.9} ff {242.4 266.2 368.5} ss {373.7 401.9 523.8}} {ot_qfd_vm_bctl_t/clk} {tt {52.9 53.8 54.7} ff {40.0 41.0 41.8} ss {75.2 76.2 77.2}} {ot_qwen_tree_delay1_t/clk} {tt {81.1 84.1 87.0} ff {64.2 67.3 70.1} ss {111.3 114.2 117.3}} {ot_qfd_vm_xfifo8_t/clk} {tt {136.4 143.4 149.2} ff {110.4 117.5 123.4} ss {181.0 188.0 193.5}} {ot_qfd_vm_su1024_t/clk} {tt {96.1 104.6 112.5} ff {76.2 85.0 93.1} ss {131.0 139.2 146.7}} {ot_qfd_vm_su_t/clk} {tt {337.3 371.2 433.2} ff {277.1 310.7 364.6} ss {433.5 466.3 539.5}} {ot_qfd_vm_sctl_t/clk} {tt {51.0 51.9 53.0} ff {38.4 39.3 40.4} ss {72.8 73.7 74.9}} {ot_qfd_vm_xpad2_t/clk} {tt {93.7 98.5 102.6} ff {75.4 80.3 84.3} ss {125.8 130.3 134.4}} {ot_qfd_vm_xrelay_t/clk} {tt {88.9 94.7 100.1} ff {70.8 76.7 81.9} ss {120.5 126.2 131.8}} {ot_qfd_vm_xrelay_w/clk} {tt {90.0 95.7 99.9} ff {71.7 77.6 81.9} ss {121.8 127.3 131.4}}]
set ::ot_ce_counts [dict create {ot_qfd_vm_rr4_t} 2 {ot_qfd_vm_rr2_t} 1 {ot_qwen_tree_delay2_t} 14 {ot_qfd_vm_bank_t} 8 {ot_qfd_vm_bctl_t} 8 {ot_qwen_tree_delay1_t} 8 {ot_qfd_vm_xfifo8_t} 16 {ot_qfd_vm_su1024_t} 3 {ot_qfd_vm_su_t} 6 {ot_qfd_vm_sctl_t} 6 {ot_qfd_vm_xpad2_t} 26 {ot_qfd_vm_xrelay_t} 34 {ot_qfd_vm_xrelay_w} 17]
set ::ot_ce_ports {{ck_c0} {ck_c1} {ck_c2} {ck_c3} {ck_c4} {ck_c5} {ck_c6} {ck_c7} {ck_c8} {ck_c9} {ck_c10} {ck_c11} {ck_c12} {ck_c13} {ck_c14} {ck_c15} {ck_c16} {ck_c17} {ck_c18} {ck_c19} {ck_c20} {ck_c21} {ck_c22} {ck_c23} {ck_c24} {ck_c25} {ck_c26} {ck_c27} {ck_c28} {ck_c29} {ck_c30} {ck_c31} {ck_c32} {ck_c33} {ck_c34} {ck_c35} {ck_c36} {ck_c37} {ck_c38} {ck_c39} {ck_c40} {ck_c41} {ck_c42} {ck_c43} {ck_c44} {ck_c45} {ck_c46} {ck_c47} {ck_c48} {ck_c49} {ck_c50} {ck_c51} {ck_c52} {ck_c53} {ck_c54} {ck_c55} {ck_c56} {ck_c57} {ck_c58} {ck_c59} {ck_c60} {ck_c61} {ck_c62} {ck_c63} {ck_c64} {ck_c65} {ck_c66} {ck_c67} {ck_c68} {ck_c69} {ck_c70} {ck_c71} {ck_t0} {ck_t1} {ck_t2} {ck_t3} {ck_t4} {ck_t5} {ck_t6} {ck_t7} {ck_t8} {ck_t9} {ck_t10} {ck_t11} {ck_t12} {ck_t13} {ck_t14} {ck_t15} {ck_t16} {ck_t17} {ck_t18} {ck_t19} {ck_t20} {ck_t21} {ck_t22} {ck_t23} {ck_t24} {ck_t25} {ck_t26} {ck_t27} {ck_t28} {ck_t29} {ck_t30} {ck_t31} {ck_t32} {ck_t33} {ck_t34} {ck_t35} {ck_t36} {ck_t37} {ck_t38} {ck_t39} {ck_t40} {ck_t41} {ck_t42} {ck_t43} {ck_t44} {ck_t45} {ck_t46} {ck_t47} {ck_t48} {ck_t49} {ck_t50} {ck_t51} {ck_t52} {ck_t53} {ck_t54} {ck_t55} {ck_t56} {ck_t57} {ck_t58} {ck_t59} {ck_t60} {ck_t61} {ck_t62} {ck_t63} {ck_t64} {ck_t65} {ck_t66} {ck_t67} {ck_t68} {ck_t69} {ck_t70} {ck_t71} {ck_t72} {ck_t73} {ck_t74} {ck_t75} {ck_t76}}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  foreach key {OT_MM_SETUP_CORNER CORNER} {
    if {[info exists ::env($key)]} {
      switch -nocase -- $::env($key) { TC - tt {return tt} BC - ff {return ff} WC - ss {return ss} }
    }
  }
  error "OT_ENTRIES: actual library corner is unknown (set ot_ce_corner tt/ff/ss)"
}
proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set wire [get_property $pin arrival_max_rise]
      if {![string is double -strict $wire]} { error "OT_ENTRIES: missing entry wire clock arrival on [get_full_name $pin]" }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean
    if {$ttmean > 300} { lappend highclocks $clock } else { lappend lowclocks $clock }
    set latency [expr {$ref - $wire - $mean}]
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  set_clock_uncertainty -setup 150 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  set_clock_uncertainty -hold 75 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  if {[llength $lowclocks] && [llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $lowclocks -to $highclocks
    set_clock_uncertainty -setup 210 -from $highclocks -to $lowclocks
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set_input_delay [expr {166.667+$lmax+$sk}] -max -clock $clk [all_inputs -no_clocks]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set_input_delay [expr {$lmin-$hki}] -min -clock $clk [all_inputs -no_clocks]
  set_output_delay [expr {166.667-$lmax+$sk}] -max -clock $clk [all_outputs]
  set_output_delay [expr {-$lmin-$hk}] -min -clock $clk [all_outputs]
  if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
    foreach pattern [split $::env(OT_IO_INTER) ","] {
      set_input_delay [expr {166.667+$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == input"]
      set_output_delay [expr {166.667-$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == output"]
    }
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
