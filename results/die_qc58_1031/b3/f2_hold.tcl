# offline FF hold classes on the raw post-CTS ODB (FF libs, route SDC + vclk_ff.sdc, propagated, placement RC)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_FF_nldm_*] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_ff.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
read_sdc /work/vclk_ff.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
if {[info exists ::env(OT_F2_LATE)]} { source /work/f2_form2.tcl; ot_f2_late }
if {[info exists ::env(OT_F2_ECO)] && $::env(OT_F2_ECO) eq "1"} { source /work/f2_form2.tcl; ot_f2_report p; if {[info exists ::env(OT_F2_MODE)] && $::env(OT_F2_MODE) eq "clone"} { ot_f2_clone } else { ot_f2_eco }; ot_f2_report q; estimate_parasitics -placement }
proc cls {n} { regsub -all {\[[0-9]+\]} $n {[*]} n; regsub -all {[0-9]+} $n {#} n; return $n }
set h {}
set n 0; set w 1e9
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
  set s [get_property $p slack]; incr n; if {$s < $w} { set w $s }
  set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
  set k "[cls $sp] -> [cls $ep]"
  if {![dict exists $h $k]} { dict set h $k [list 0 1e9 "" ""] }
  lassign [dict get $h $k] c m e1 e2
  incr c; if {$s < $m} { set m $s; set e1 $sp; set e2 $ep }
  dict set h $k [list $c $m $e1 $e2]
}
puts [format "F2HOLD ws %.2f failing endpoints %d" $w $n]
set l {}; dict for {k v} $h { lappend l [list $k {*}$v] }
foreach r [lrange [lsort -real -index 2 $l] 0 40] { lassign $r k c m e1 e2; puts [format "F2HOLD %5d %8.2f %s | %s -> %s" $c $m $k $e1 $e2] }
set ff 0
foreach r [lrange [lsort -real -index 2 $l] 0 10] {
  lassign $r k c m e1 e2
  sta::redirect_string_begin
  if {[catch {report_checks -path_delay min -from [get_pins $e1] -to [expr {[string first / $e2] < 0 ? [get_ports $e2] : [get_pins $e2]}] -format full_clock_expanded -digits 1} m]} { puts "rpt err $m" }
  set t [sta::redirect_string_end]
  puts "F2PATH ===== $k"; puts $t
}
