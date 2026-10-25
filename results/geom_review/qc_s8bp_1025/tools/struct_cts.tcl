# QC-S8BP structured core clock (GEOM fix F5/F3, owner 10-23 industry rule) for the QC 4-SRAM hard cores
# (qfd_dv_s8x_btab / qfd_dv_s8x_prog).  Replaces ORFS CTS on the Codex south4 3_place.odb:
#   ck port (south face) -> root buffer -> one repeated feed chain per regional tap, routed in the logic channels
#   (south channel y<SRAM row 0, west strip x<SRAM west edge, east column x>SRAM east edge; never over an SRAM)
#   -> regional tap buffer at its region's sink centroid -> local CTS tree of that region only (clock_tree_synthesis
#   -clk_nets, no macro/register split, -delay_buffer_derate 0: no root delay-buffer chain)
#   each SRAM clk pin: own leaf buffer next to the pin, fed by the tap of the region that holds its interface regs
#   taps: mean sink arrival balanced to <= OT_TAP_BAL_PS (20) by delay buffers at the tap input (feed-chain end);
#   SRAM leaf matched to its tap's register mean.  Netlist: clock buffers only; data, pins, SDC, RTL unchanged.
# env: OT_STAGE_IN (3_place.odb), OT_SDC_IN, OT_OUT_ODB, OT_OUT_SDC, OT_SRAM_LIB (tt lib path), OT_DUMP (prefix)
proc env {k d} { if {[info exists ::env($k)]} { return $::env($k) }; return $d }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*] { read_liberty $l }
read_liberty $::env(OT_SRAM_LIB)
read_db $::env(OT_STAGE_IN)
read_sdc $::env(OT_SDC_IN)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M2-M5 -clock M2-M5
# (hold_budget.tcl part) CTS rewires the CLK of POST_SYNTH capture / constant flops: lift their dont_touch
foreach i [[ord::get_db_block] getInsts] { if {[regexp {^ot_fc(ap|onst)_} [$i getName]] && [$i isDoNotTouch]} { $i setDoNotTouch 0 } }
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set db [ord::get_db]
proc um {v} { return [expr {$v / double($::dbu)}] }
proc du {v} { return [expr {round($v * $::dbu)}] }
set BAL [env OT_TAP_BAL_PS 20]
set REP_UM [env OT_FEED_REP_UM 45]
set feed_m [$db findMaster [env OT_FEED_BUF BUFx12f_ASAP7_75t_R]]
set tap_m  [$db findMaster [env OT_TAP_BUF BUFx16f_ASAP7_75t_R]]
set leaf_m [$db findMaster [env OT_LEAF_BUF BUFx8_ASAP7_75t_R]]
set dly_m  [$db findMaster [env OT_DLY_BUF BUFx2_ASAP7_75t_R]]
foreach m [list $feed_m $tap_m $leaf_m $dly_m] { if {$m eq "NULL"} { error "S8BP missing buffer master" } }

# ---- geometry: SRAM bounding box (rows stacked at the same x), core, clock port
set macros {}
foreach i [$blk getInsts] { if {[[$i getMaster] isBlock]} { lappend macros $i } }
set mx0 1e9; set mx1 -1e9; set my0 1e9; set my1 -1e9
foreach m $macros { set b [$m getBBox]
  set mx0 [expr {min($mx0,[um [$b xMin]])}]; set mx1 [expr {max($mx1,[um [$b xMax]])}]
  set my0 [expr {min($my0,[um [$b yMin]])}]; set my1 [expr {max($my1,[um [$b yMax]])}] }
set die [$blk getDieArea]; set DX [um [$die xMax]]; set DY [um [$die yMax]]
set ckbt [$blk findBTerm ck]; set cknet [$ckbt getNet]
set pb [$ckbt getBBox]; set px [um [expr {([$pb xMin]+[$pb xMax])/2}]]; set py [um [expr {([$pb yMin]+[$pb yMax])/2}]]
set ymid [expr {($my0+$my1)/2.0}]
set wch [expr {$mx0 - 6.0}];   # west channel x (just west of the SRAM west edge)
set ech [expr {$mx1 + 6.0}];   # east channel x
set sch [expr {$my0 - 12.0}];  # south channel y (between pin-reg band and SRAM row 0)
puts "S8BP geom sram x $mx0..$mx1 y $my0..$my1 die $DX x $DY ck port ($px,$py) channels W$wch E$ech S$sch"

# ---- region of a sink (by position)
proc region {x y} {
  global mx0 mx1 my0 ymid DX
  if {$y < $my0 - 4} { return [expr {$x < ($mx0+$mx1)/2.0 ? "SW" : "SE"}] }
  set hl [expr {$y < $ymid ? "lo" : "hi"}]
  if {$x <= $mx0 + 2} { return "W$hl" }
  if {$x >= $mx1 - 2} { return "E$hl" }
  # row gaps between SRAMs: nearer side
  return [expr {($x - $mx0) < ($mx1 - $x) ? "W$hl" : "E$hl"}]
}
set sinks {}; set msinks {}
foreach it [$cknet getITerms] {
  if {[$it isOutputSignal]} { error "S8BP ck net already driven by a cell: CTS input must be the unbuffered 3_place" }
  set i [$it getInst]; set b [$i getBBox]
  set x [um [expr {([$b xMin]+[$b xMax])/2}]]; set y [um [expr {([$b yMin]+[$b yMax])/2}]]
  if {[[$i getMaster] isBlock]} { lappend msinks $it; continue }
  dict lappend sinks [region $x $y] [list $it $x $y]
}
# ---- SRAM leaf region: the region holding the SRAM's west-edge interface (its clk pin corner)
proc place_at {inst x y} { $inst setLocation [du $x] [du $y]; $inst setPlacementStatus PLACED }
set n 0
proc mkbuf {m name x y} { set i [odb::dbInst_create $::blk $m $name]; place_at $i $x $y; return $i }
proc mknet {name} { set nt [odb::dbNet_create $::blk $name]; $nt setSigType CLOCK; return $nt }
proc pinA {i} { return [$i findITerm A] }
proc pinY {i} { return [$i findITerm Y] }

# ---- root buffer at the port
set root [mkbuf $feed_m s8bp_root [expr {$px}] [expr {$py + 6}]]
foreach it [$cknet getITerms] { $it disconnect }
[pinA $root] connect $cknet
set rootnet [mknet s8bp_ck_root]; [pinY $root] connect $rootnet

# ---- taps and their feed paths (Manhattan, via channels)
set taps {}
dict for {r lst} $sinks {
  set sx 0; set sy 0
  foreach e $lst { set sx [expr {$sx+[lindex $e 1]}]; set sy [expr {$sy+[lindex $e 2]}] }
  set cx [expr {$sx/[llength $lst]}]; set cy [expr {$sy/[llength $lst]}]
  # waypoints: port -> (south channel) -> channel column -> tap
  set wp [list [list $px [expr {$py+6}]]]
  switch -glob $r {
    SW - SE { lappend wp [list $px $sch] [list $cx $sch] [list $cx $cy] }
    W*      { set cx [expr {min($cx,$wch)}]; lappend wp [list $px $sch] [list $wch $sch] [list $wch $cy] [list $cx $cy] }
    E*      { lappend wp [list $px $sch] [list $ech $sch] [list $ech $cy] [list $cx $cy] }
  }
  dict set taps $r [list $cx $cy $wp $lst]
}
proc pathpts {wp step} {
  # points every $step um along the polyline (excluding start, including the last full step)
  set seg {}; set tot 0.0
  for {set k 1} {$k < [llength $wp]} {incr k} {
    lassign [lindex $wp [expr {$k-1}]] x0 y0; lassign [lindex $wp $k] x1 y1
    set L [expr {abs($x1-$x0)+abs($y1-$y0)}]
    lappend seg [list $tot $L $x0 $y0 $x1 $y1]; set tot [expr {$tot+$L}]
  }
  set pts {}
  for {set d $step} {$d < $tot - 5.0} {set d [expr {$d+$step}]} {
    foreach sg $seg { lassign $sg s0 L x0 y0 x1 y1
      if {$L > 0 && $d >= $s0 && $d <= $s0+$L} { set f [expr {($d-$s0)/$L}]
        lappend pts [list [expr {$x0+($x1-$x0)*$f}] [expr {$y0+($y1-$y0)*$f}]]; break } }
  }
  return $pts
}
set tapinst {}; set tapnet {}; set tapin {}
dict for {r t} $taps {
  lassign $t cx cy wp lst
  set prev $rootnet; set k 0
  foreach p [pathpts $wp $REP_UM] {
    lassign $p x y
    set b [mkbuf $feed_m s8bp_feed_${r}_$k $x $y]; [pinA $b] connect $prev
    set prev [mknet s8bp_feed_${r}_$k]; [pinY $b] connect $prev; incr k
  }
  set tb [mkbuf $tap_m s8bp_tap_$r $cx $cy]; [pinA $tb] connect $prev
  dict set tapin $r $prev
  set tn [mknet s8bp_tap_$r]; [pinY $tb] connect $tn
  foreach e $lst { [lindex $e 0] connect $tn }
  dict set tapinst $r $tb; dict set tapnet $r $tn
  puts "S8BP tap $r sinks [llength $lst] at ([format %.1f $cx],[format %.1f $cy]) feed bufs $k"
}
# ---- SRAM leaves: own buffer next to the clk pin, fed from the W tap of its row (F3)
set mleaf {}
foreach it $msinks {
  set m [$it getInst]; set b [$m getBBox]
  set x [expr {[um [$b xMin]] - 7.0}]; set y [expr {[um [$b yMin]] + 1.0}]
  set r [expr {$y < $ymid ? "Wlo" : "Whi"}]
  if {![dict exists $tapnet $r]} { set r [lindex [dict keys $tapnet] 0] }
  set lb [mkbuf $leaf_m s8bp_mleaf_[$m getName] $x $y]
  [pinA $lb] connect [dict get $tapnet $r]
  set ln [mknet s8bp_mleaf_[$m getName]]; [pinY $lb] connect $ln; $it connect $ln
  dict set mleaf [$m getName] [list $lb $ln $r $it]
  puts "S8BP sram [$m getName] leaf at ([format %.1f $x],[format %.1f $y]) from tap $r"
}
detailed_placement
# ---- local CTS per tap (each tap net is a root); SRAM leaf nets are not CTS roots
set cts_nets [join [lmap r [dict keys $tapnet] {set _ s8bp_tap_$r}] " "]
set_propagated_clock [all_clocks]
estimate_parasitics -placement
clock_tree_synthesis -clk_nets $cts_nets -sink_clustering_enable -sink_clustering_size 20 -sink_clustering_max_diameter 40 \
  -balance_levels -delay_buffer_derate 0 -root_buf [$tap_m getName] -buf_list {BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R}
detailed_placement
# ---- measure mean sink arrival per tap region (+ SRAM clk) on the requested estimate
proc measure {} {
  if {[env OT_EST placement] eq "grt"} { estimate_parasitics -global_routing } else { estimate_parasitics -placement }
  set res {}
  dict for {r t} $::taps {
    set v {}
    foreach e [lindex $t 3] { set it [lindex $e 0]
      set p [get_pins -quiet "[[$it getInst] getName]/[[$it getMTerm] getName]"]
      if {[llength $p]} { set a ""; catch {set a [get_property $p arrival_max_rise]}; if {$a ne ""} { lappend v $a } } }
    if {[llength $v]} { dict set res $r [expr {[tcl::mathop::+ {*}$v]/[llength $v]}] }
  }
  dict for {m l} $::mleaf { set it [lindex $l 3]
    set p [get_pins -quiet "$m/[[$it getMTerm] getName]"]; set a ""; catch {set a [get_property $p arrival_max_rise]}
    dict set res "M:$m" $a }
  return $res
}
foreach k [all_clocks] { if {[llength [get_property $k sources]]} { set_clock_latency -source 0 $k } }
set GRT [expr {[env OT_EST placement] eq "grt"}]
if {$GRT} { set_global_routing_layer_adjustment * 0.0; set_macro_extension 2; global_route -congestion_iterations 30 }
# ---- tap balance: delay buffers at the end of each early tap's feed chain; SRAM leaves matched to their tap
set cnt 0
for {set iter 0} {$iter < 6} {incr iter} {
  set M [measure]
  set tv [dict filter $M key {[SEW]*}]
  set late [tcl::mathfunc::max {*}[dict values $tv]]
  puts "S8BP balance iter $iter [dict map {k v} $M {if {[string is double -strict $v]} {format %.1f $v} else {set v NA}}]"
  set done 1
  if {$GRT} { global_route -start_incremental }
  dict for {r v} $tv {
    set gap [expr {$late - $v}]
    if {$gap <= $BAL / 2.0} continue
    set done 0
    set nb [expr {max(1, int($gap / 14.0))}]
    set tb [dict get $tapinst $r]; set in [[pinA $tb] getNet]; set b [$tb getBBox]
    set x [um [$b xMin]]; set y [um [$b yMin]]
    for {set j 0} {$j < $nb} {incr j} {
      set d [mkbuf $dly_m s8bp_dly_${r}_$cnt [expr {$x - 1.0}] $y]; incr cnt
      [pinA $tb] disconnect; set nn [mknet s8bp_dly_${r}_$cnt]
      [pinY $d] connect $nn; [pinA $d] connect $in; [pinA $tb] connect $nn; set in $nn
    }
  }
  dict for {m l} $mleaf {
    lassign $l lb ln r it
    set gap [expr {[dict get $M $r] - [dict get $M "M:$m"]}]
    if {$gap <= $BAL / 2.0} continue
    set done 0
    set nb [expr {max(1, int($gap / 14.0))}]
    set in [[pinA $lb] getNet]; set b [$lb getBBox]
    for {set j 0} {$j < $nb} {incr j} {
      set d [mkbuf $dly_m s8bp_mdly_${cnt} [um [$b xMin]] [expr {[um [$b yMin]] + 1.0}]]; incr cnt
      [pinA $lb] disconnect; set nn [mknet s8bp_mdly_$cnt]
      [pinY $d] connect $nn; [pinA $d] connect $in; [pinA $lb] connect $nn; set in $nn
    }
  }
  detailed_placement
  if {$GRT} { global_route -end_incremental }
  if {$done} break
}
set M [measure]
puts "S8BP FINAL [env OT_EST placement] [dict map {k v} $M {if {[string is double -strict $v]} {format %.1f $v} else {set v NA}}] delay_bufs $cnt"
check_placement -verbose
if {$GRT && [info exists ::env(OT_OUT_GUIDE)]} { write_guides $::env(OT_OUT_GUIDE) }
write_db $::env(OT_OUT_ODB)
write_sdc -no_timestamp $::env(OT_OUT_SDC)
puts S8BP_CTS_DONE
