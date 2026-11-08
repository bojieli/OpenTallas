proc root2 {inst} {
  set p [get_pins -quiet $inst/CLK]
  if {![llength $p]} {return "?"}
  set f [get_fanin -to $p -startpoints_only -flat]
  set r {}
  foreach x $f { set n [get_full_name $x]; if {[llength [get_ports -quiet $n]]} {lappend r $n} }
  return [join [lsort -unique $r] ,]
}
set f [open /out/hold_roots.tsv w]
set paths [find_timing_paths -path_delay min -slack_max 0 -group_path_count 20000 -endpoint_path_count 1]
set cache [dict create]
foreach p $paths {
  set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
  set sl [get_property $p slack]
  set si [regsub {/[^/]+$} $sp {}]; set ei [regsub {/[^/]+$} $ep {}]
  foreach v {si ei} { set i [set $v]; if {[set $v] eq [set [string index $v 0]p]} {set r($v) PORT} elseif {[dict exists $cache $i]} {set r($v) [dict get $cache $i]} else {set r($v) [root2 $i]; dict set cache $i $r($v)} }
  puts $f "$sl\t$sp\t$r(si)\t$ep\t$r(ei)"
}
close $f
report_check_types -max_slew -max_capacitance -violators -max_count 400 > /out/slew.rpt
puts "PROBE2_DONE [llength $paths]"
