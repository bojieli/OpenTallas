source /probe/hold_decomp_head.tcl
set vec {}; foreach pt [all_inputs -no_clocks] { if {[regexp {\[} [get_full_name $pt]]} {lappend vec $pt} }
foreach s {12.5 27.5 40 55} {
 set_input_delay -min $s -clock vclk $vec
 foreach thr {0 15} {
  set paths [find_timing_paths -path_delay min -slack_max $thr -group_path_count 20000 -endpoint_path_count 1]
  set n 0; set nv 0; foreach p $paths { set sp [get_full_name [get_property $p startpoint]]; if {[string first / $sp]<0} {incr n; if {[regexp {\[} $sp]} {incr nv}} }
  puts "HIST2 sender $s slack<$thr total [llength $paths] input $n vector $nv"
 }
}
exit
