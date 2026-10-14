# q13-tile CTS diagnostic: classify FF hold and setup endpoints after CTS, before any repair
if {[info exists ::env(TRI_ORIG_POST_CTS)] && $::env(TRI_ORIG_POST_CTS) ne ""} { source $::env(TRI_ORIG_POST_CTS) }
estimate_parasitics -placement
if {[catch {ot_mm_sync} m]} { puts "Q13 sync err $m" }
proc q13_cls {n} {
  regsub -all {\[[0-9]+\]} $n {[*]} n
  regsub -all {\$_[A-Z0-9_]+_} $n {} n
  regsub -all {_[0-9]+_?$} $n {_N} n
  regsub -all {[0-9]+} $n {#} n
  return $n
}
proc q13_scan {check scene smax tag} {
  set ps [find_timing_paths -path_delay $check -scenes $scene -group_path_count 400000 -endpoint_path_count 1 -slack_max $smax]
  array set cnt {}; array set wst {}; set n 0
  foreach p $ps {
    set s [get_property $p slack]; if {$s eq "INF"} continue
    set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
    set k "[q13_cls $sp] -> [q13_cls $ep]"
    incr n
    if {![info exists cnt($k)]} { set cnt($k) 0; set wst($k) $s }
    incr cnt($k); if {$s < $wst($k)} { set wst($k) $s }
  }
  puts "Q13 $tag endpoints $n classes [array size cnt]"
  set rows {}; foreach k [array names cnt] { lappend rows [list $cnt($k) $wst($k) $k] }
  foreach r [lrange [lsort -integer -decreasing -index 0 $rows] 0 44] { puts [format "Q13 %s n=%d worst=%.1f %s" $tag {*}$r] }
  puts "Q13 $tag by worst:"
  foreach r [lrange [lsort -real -index 1 $rows] 0 14] { puts [format "Q13 %sW n=%d worst=%.1f %s" $tag {*}$r] }
}
q13_scan min BC 0 HOLD
q13_scan max [ot_mm_sc] 0 SETUP
puts "Q13 === worst hold path"
report_checks -path_delay min -scenes BC -group_path_count 1 -format full_clock_expanded -fields {fanout cap slew} -digits 1
puts "Q13 === worst setup paths"
report_checks -path_delay max -scenes [ot_mm_sc] -group_path_count 2 -format full_clock_expanded -digits 1
puts "Q13 === tx rung hold"
catch {report_checks -path_delay min -scenes BC -to [get_pins {u_tile.u_logic.u_me.g_hier.g_sl[1].g_hd.g_tx.g_r[1].u_tx/q[384]$_DFF_P_/D}] -format full_clock_expanded -digits 1}
# clock arrival per class at FF
array set lo {}; array set hi {}; array set cn {}
foreach p [all_registers -clock_pins] {
  set a [ot_mm_arrival_bc $p arrival_max_rise]; if {$a eq "" || $a eq "INF"} continue
  set k [q13_cls [get_full_name $p]]; set k [join [lrange [split $k .] 0 4] .]
  if {![info exists cn($k)]} { set cn($k) 0; set lo($k) $a; set hi($k) $a }
  incr cn($k); if {$a<$lo($k)} {set lo($k) $a}; if {$a>$hi($k)} {set hi($k) $a}
}
foreach k [lsort [array names cn]] { catch {puts [format "Q13 CLK n=%d ff_arr %.1f..%.1f %s" $cn($k) $lo($k) $hi($k) $k]} }
puts "Q13 done"
