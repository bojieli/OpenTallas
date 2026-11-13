# HOLD-TAP-1 diagnostic: FF reg->reg hold violators of a post-CTS (tap-balanced) DB, classified by tap pair.
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
if {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne ""} { source $::env(LAYER_PARASITICS_FILE) } else { source $::env(PLATFORM_DIR)/setRC.tcl }
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { estimate_parasitics -placement }
set blk [ord::get_db_block]
proc is_buf {m} { expr {[string match BUF* $m] || [string match INV* $m] || [string match CKINV* $m] || [string match HB* $m]} }
# tap port of a clock iterm: walk drivers back to a BTerm
set tapc [dict create]
proc tap_of {it} {
  global tapc
  set net [$it getNet]; set hops 0; set chain {}
  while {$net ne "NULL" && $hops < 200} {
    set nn [$net getName]
    if {[dict exists $tapc $nn]} { set r [dict get $tapc $nn]; break }
    lappend chain $nn
    set bts [$net getBTerms]
    if {[llength $bts]} { set r [[lindex $bts 0] getName]; break }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
    if {$drv eq ""} { set r "?"; break }
    set di [$drv getInst]; set nxt "NULL"
    foreach t [$di getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set mn [[$t getMTerm] getName]; if {$mn in {A CLK D}} { set nxt [$t getNet]; break } } }
    set net $nxt; incr hops
    set r "?"
  }
  foreach c $chain { dict set tapc $c $r }
  return $r
}
set ck [all_registers -clock_pins]; set d [all_registers -data_pins]
set lim [expr {[info exists ::env(SLACK_MAX)] ? $::env(SLACK_MAX) : 0}]
set ps [find_timing_paths -path_delay min -from $ck -to $d -group_path_count 2000000 -endpoint_path_count 1 -slack_max $lim]
set f [open $::env(OUT) w]
puts $f "slack\tlaunch\tcapture\tltap\tctap\tnlogic\tnbuf\tl_ck\tc_ck\tclk_skew\tmargin\trequired\tdata\tdist_um"
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach pe $ps {
  set s [sta::time_sta_ui [$pe slack]]
  set path [$pe path]
  set pins [$path pins]
  set p0 [get_property $pe startpoint]; set pN [get_property $pe endpoint]
  set lit [sta::sta_to_db_pin $p0]; set cdt [sta::sta_to_db_pin $pN]
  if {$lit eq "NULL" || $cdt eq "NULL"} continue
  set li [$lit getInst]; set ci [$cdt getInst]
  set cit ""
  foreach t [$ci getITerms] { if {[[$t getMTerm] getName] in {CLK CLKN} } { set cit $t } }
  set lt [tap_of $lit]; set ct [expr {$cit eq "" ? "?" : [tap_of $cit]}]
  set nl 0; set nb 0; set seen {}
  set go 0
  foreach p $pins {
    set it [sta::sta_to_db_pin $p]; if {$it eq "NULL"} continue
    if {$it eq $lit} { set go 1; continue }
    if {!$go} continue
    set i [$it getInst]; set n [$i getName]
    if {[dict exists $seen $n] || $n eq [$li getName] || $n eq [$ci getName]} continue
    if {[string match DFF* [[$i getMaster] getName]] || [string match DLL* [[$i getMaster] getName]] || [string match DHL* [[$i getMaster] getName]]} continue
    dict set seen $n 1
    if {[is_buf [[$i getMaster] getName]]} { incr nb } else { incr nl }
  }
  set lb [$li getBBox]; set cb [$ci getBBox]
  set dist [expr {(abs([$lb xMin]-[$cb xMin]) + abs([$lb yMin]-[$cb yMin])) / double($dbu)}]
  set lck [sta::time_sta_ui [$pe source_clk_latency]]
  set tck [sta::time_sta_ui [$pe target_clk_delay]]
  set sl [sta::time_sta_ui [$pe clk_skew]]
  set tl [sta::time_sta_ui [$pe margin]]
  set cr [sta::time_sta_ui [$pe data_required_time]]
  set da [sta::time_sta_ui [$pe data_arrival_time]]
  puts $f [format "%.2f\t%s\t%s\t%s\t%s\t%d\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%s\t%.2f\t%.1f" $s [$li getName] [$ci getName] $lt $ct $nl $nb $lck $tck $sl $tl $cr $da $dist]
}
close $f
puts "XTAP_DIAG paths [llength $ps] ws [sta::time_sta_ui [sta::worst_slack_cmd min]]"
