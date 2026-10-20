# Placement only: exact production first CE-capture banks; no timing exception or state change.
# Ordinary helper anchors reader output FFs and both native first reset publications first.
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
set ot_extra {}; set qp_width 0
foreach bt [$ot_blk getBTerms] {
 if {[regexp {^i\[([0-9]+)\]$} [$bt getName] -> bit]} {set qp_width [expr {max($qp_width,$bit+1)}]}
}
if {$qp_width ni {257 258}} {error "CBPAIR_ANCHOR wrong production width $qp_width"}
set qp_seen [dict create]
foreach inst [$ot_blk getInsts] {
 set name [string map [list "\\" ""] [$inst getName]]
 if {![regexp {g_slice\[([0-9]+)\]\.u_w[/\.]g_bank\[([0-9]+)\]\.b(?:\[([0-9]+)\])?\$_DFFE_} $name -> group slot bit]} continue
 if {$bit eq ""} {set bit 0}
 set global [expr {$group*15+$bit}]
 if {$global >= $qp_width || $slot>3 || ![ot_of_isff $inst]} {error "CBPAIR_ANCHOR foreign firstcapture $name"}
 set key "$global,$slot"
 if {[dict exists $qp_seen $key]} {error "CBPAIR_ANCHOR duplicate $key"}
 dict set qp_seen $key 1
 set port [format {i[%d]} $global];set bt [$ot_blk findBTerm $port]
 if {$bt eq "NULL"} {error "CBPAIR_ANCHOR missing real data BTerm $port"}
 lappend ot_extra [list $port [$inst getName] $bt $inst]
}
if {[llength $ot_extra] != 4*$qp_width} {error "CBPAIR_ANCHOR expected4banks/bit, found [llength $ot_extra]"}
set ot_extra [lsort -dictionary $ot_extra]
  set ot_rows {}
  foreach row [$ot_blk getRows] {
    set box [$row getBBox]
    lappend ot_rows [list [$box yMin] [$box xMin] [$box xMax] [$box yMax] \
      [$row getSpacing] [$row getOrient]]
  }
  set ot_rows [lsort -integer -index 0 $ot_rows]
  # Reserve all firm/fixed footprints, including existing pin anchors and stages.
  set ot_occupied [dict create]
  foreach inst [$ot_blk getInsts] {
    if {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set box [$inst getBBox]
    set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {[$box yMin] < $ey && [$box yMax] > $ry} {
        dict lappend ot_occupied $ri [list [$box xMin] [$box xMax]]
      }
      incr ri
    }
  }
  foreach blockage [$ot_blk getBlockages] {
    set box [$blockage getBBox]
    set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {[$box yMin] < $ey && [$box yMax] > $ry} {
        dict lappend ot_occupied $ri [list [$box xMin] [$box xMax]]
      }
      incr ri
    }
  }
  foreach request $ot_extra {
    lassign $request port name bt ff
    set box [$bt getBBox]
    set px [expr {([$box xMin] + [$box xMax]) / 2.0}]
    set py [expr {([$box yMin] + [$box yMax]) / 2.0}]
    set width [[$ff getMaster] getWidth]; set height [[$ff getMaster] getHeight]
    set best {}; set score Inf; set ri 0
    foreach row $ot_rows {
      lassign $row ry rx ex ey pitch orient
      if {$height != $ey - $ry || $pitch <= 0} { incr ri; continue }
      set blocks {}
      if {[dict exists $ot_occupied $ri]} { set blocks [lsort -integer -index 0 [dict get $ot_occupied $ri]] }
      lappend blocks [list $ex $ex]
      set start $rx
      foreach block $blocks {
        lassign $block lo hi
        set low [expr {$rx + int(ceil(double($start - $rx) / $pitch)) * $pitch}]
        set high [expr {$rx + int(floor(double(min($lo, $ex) - $width - $rx) / $pitch)) * $pitch}]
        if {$high >= $low} {
          set x [expr {max($low, min($high, $rx + round(($px - $width / 2.0 - $rx) / $pitch) * $pitch))}]
          set cost [expr {abs($x + $width / 2.0 - $px) + abs($ry + $height / 2.0 - $py)}]
          if {$cost < $score} { set score $cost; set best [list $ri $x $ry $orient] }
        }
        set start [expr {max($start, $hi)}]
      }
      incr ri
    }
    if {$best eq ""} { error "OT_IOFLOP: no legal capture site for $name ($port)" }
    lassign $best ri x y orient
    $ff setOrient $orient
    if {[[$ff getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
    $ff setLocation $x $y
    $ff setPlacementStatus FIRM
    dict lappend ot_occupied $ri [list $x [expr {$x + $width}]]
    lappend ot_list $name
    incr ot_ni
    puts "OT_IOFLOP extra capture $port -> $name at ($x, $y) DBU"
  }
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list {puts $fh $n};close $fh
puts "CBPAIR_FIRST_CAPTURE_ANCHOR PASS width=$qp_width actual_banks=[llength $ot_extra] no_state_or_timing_change"
