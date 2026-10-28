# Explicit, opt-in road sites. No netlist edits and no inferred cell identities.
# CELL TSV rows carry integer DBU origins; PIN rows freeze every non-PG ITerm.
# Source again after repair only with a regenerated complete contract: inserted
# buffers change the checked pin/net bindings and invalidate the old contract.
proc ot_rr_bins {x0 y0 x1 y1 width} {
  set keys {}
  for {set x [expr {int(floor(double($x0)/$width))}]} {$x <= int(floor(double($x1)/$width))} {incr x} {
    for {set y [expr {int(floor(double($y0)/$width))}]} {$y <= int(floor(double($y1)/$width))} {incr y} { lappend keys "$x,$y" }
  }
  return $keys
}
proc ot_relay_roads {path} {
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set fh [open $path r]; set data [read $fh]; close $fh
  set cells {}; set pins {}; set header 0
  foreach line [split $data "\n"] {
    if {$line eq "" || [string index $line 0] eq "#"} continue
    set f [split $line "\t"]
    switch -- [lindex $f 0] {
      DBU {
        if {$header || [llength $f] != 2 || [lindex $f 1] ne "$dbu"} { error "RELAY_ROADS DBU/header mismatch" }
        set header 1
      }
      CELL {
        if {[llength $f] != 7} { error "RELAY_ROADS malformed CELL" }
        lassign [lrange $f 1 end] n m x y o halo
        if {[dict exists $cells $n]} { error "RELAY_ROADS duplicate cell $n" }
        if {![string is integer -strict $x] || ![string is integer -strict $y] || ![string is integer -strict $halo] || $halo < round(8.64*$dbu)} { error "RELAY_ROADS coordinates must be integer DBU" }
        dict set cells $n [list $m $x $y $o $halo]
      }
      PIN {
        if {[llength $f] != 4} { error "RELAY_ROADS malformed PIN" }
        lassign [lrange $f 1 end] n p net
        if {[dict exists $pins $n $p]} { error "RELAY_ROADS duplicate pin $n/$p" }
        dict set pins $n $p $net
      }
      default { error "RELAY_ROADS unknown record" }
    }
  }
  if {!$header || ![dict size $cells]} { error "RELAY_ROADS empty/unversioned contract" }
  foreach n [dict keys $pins] { if {![dict exists $cells $n]} { error "RELAY_ROADS orphan pins $n" } }
  set boxes {}; set plan {}; set rowmap {}; set bins {}; set obstacles {}
  set binw [expr {int(10*$dbu)}]
  foreach row [$blk getRows] {
    lassign [$row getOrigin] rx ry
    set site [$row getSite]
    dict lappend rowmap $ry [list $rx [$site getWidth] [$site getHeight] [$row getSiteCount] [$row getOrient]]
  }
  foreach other [$blk getInsts] {
    set on [$other getName]
    if {[dict exists $cells $on]} continue
    set om [$other getMaster]
    # This is a PRE_GLOBAL_PLACE contract: GPL/DPL still places soft cells.
    if {![$om isBlock] && [$other getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set b [$other getBBox]
    dict set obstacles $on [list [$b xMin] [$b yMin] [$b xMax] [$b yMax] [$om isBlock]]
    foreach key [ot_rr_bins [$b xMin] [$b yMin] [$b xMax] [$b yMax] $binw] { dict lappend bins $key $on }
  }
  # Validate the entire transaction before changing any placement.
  dict for {n spec} $cells {
    lassign $spec master x y orient halo
    set i [$blk findInst $n]
    if {$i eq "NULL" || $i eq ""} { error "RELAY_ROADS missing cell $n" }
    set m [$i getMaster]
    if {[$m getName] ne $master || [$m isBlock] || ![regexp {^(.*DFF.*|BUF.*|INV.*|HB.*)$} $master]} { error "RELAY_ROADS unsupported/changed master $n" }
    set actual {}
    foreach it [$i getITerms] {
      if {[$it getSigType] in {POWER GROUND}} continue
      set net [$it getNet]
      dict set actual [[$it getMTerm] getName] [expr {$net in {NULL {}} ? "-" : [$net getName]}]
    }
    if {![dict exists $pins $n] || [dict size $actual] != [dict size [dict get $pins $n]]} { error "RELAY_ROADS incomplete pin coverage $n" }
    dict for {p net} $actual {
      if {![dict exists $pins $n $p] || [dict get $pins $n $p] ne $net} { error "RELAY_ROADS changed connectivity $n/$p" }
    }
    set w [$m getWidth]; set h [$m getHeight]
    if {$orient ni {R0 MX}} { error "RELAY_ROADS unsupported orientation $n" }
    set rowok 0
    if {[dict exists $rowmap $y]} {
      foreach row [dict get $rowmap $y] {
        lassign $row rx sw sh count ro
        if {$h == $sh && $x >= $rx && ($x-$rx)%$sw == 0 && $x+$w <= $rx+$count*$sw && $orient eq $ro} { set rowok 1; break }
      }
    }
    if {!$rowok} { error "RELAY_ROADS illegal row/site $n" }
    set box [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
    set nearby {}
    foreach key [ot_rr_bins [expr {$x-$halo}] [expr {$y-$halo}] [expr {$x+$w+$halo}] [expr {$y+$h+$halo}] $binw] {
      if {[dict exists $bins $key]} { foreach on [dict get $bins $key] { dict set nearby $on 1 } }
    }
    foreach on [dict keys $nearby] {
      lassign [dict get $obstacles $on] a b c d macro
      set pad [expr {$macro ? $halo : 0}]
      if {$x < $c+$pad && $x+$w > $a-$pad && $y < $d+$pad && $y+$h > $b-$pad} { error "RELAY_ROADS body/halo collision $n with $on" }
    }
    dict set obstacles $n [concat $box 0]
    foreach key [ot_rr_bins {*}$box $binw] { dict lappend bins $key $n }
    dict set boxes $n $box
    dict set plan $n [list $i $x $y $orient]
  }
  set out [open $::env(RESULTS_DIR)/ot_relay_road_fixed.txt w]
  dict for {n spec} $plan {
    lassign $spec i x y orient
    $i setOrient $orient; $i setLocation $x $y; $i setPlacementStatus FIRM
    puts $out $n
  }
  close $out
  puts "OT_RELAY_ROADS applied [dict size $plan] exact sites; pin/net identity unchanged; FIRM through DPL"
}
if {[info exists ::env(OT_RELAY_ROAD_FILE)] && $::env(OT_RELAY_ROAD_FILE) ne ""} { ot_relay_roads $::env(OT_RELAY_ROAD_FILE) }
