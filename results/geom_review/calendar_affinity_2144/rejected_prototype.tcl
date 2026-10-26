# Opt-in physical clock affinity for an existing captured->calendar pipeline.
# Source defines procedures only. Call ot_calclk::rebuild AFTER local CTS and
# before balancing/RC. It preserves all data/control pins and original placement.
# Old INFO-calendar test vehicle only until physically qualified on its successor.
namespace eval ::ot_calclk {}
proc ::ot_calclk::pin {i name} {
  foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq $name} {return $t}}
  return ""
}
proc ::ot_calclk::root_of {net {depth 0}} {
  if {$depth > 40} {error "OT_CALCLK clock ancestry depth >40"}
  if {[llength [$net getBTerms]]} {return [lsort [lmap b [$net getBTerms] {$b getName}]]}
  set driver ""
  foreach t [$net getITerms] {if {[$t isOutputSignal]} {if {$driver ne ""} {error "OT_CALCLK multi-driver clock"};set driver [$t getInst]}}
  if {$driver eq "" || ![regexp {^(BUF|INV|CKBUF|CKINV|HB)} [[$driver getMaster] getName]]} {error "OT_CALCLK clock has no buffer ancestry"}
  set inputs [ot_dtsh::sigpins $driver INPUT]
  if {[llength $inputs] != 1} {error "OT_CALCLK ambiguous clock buffer input"}
  return [root_of [[lindex $inputs 0] getNet] [expr {$depth+1}]]
}
proc ::ot_calclk::successors {inst {depth 0}} {
  set out {}
  foreach o [$inst getITerms] {
    if {![$o isOutputSignal]} continue
    set n [$o getNet];if {$n eq "NULL" || $n eq ""} continue
    foreach d [$n getITerms] {
      if {![$d isInputSignal]} continue
      set di [$d getInst];set m [[$di getMaster] getName]
      if {[string match DFF* $m] && [[$d getMTerm] getName] eq "D"} {lappend out $di}
      if {$depth < 1 && [regexp {^(BUF|INV)} $m]} {lappend out {*}[successors $di [expr {$depth+1}]]}
    }
  }
  return [lsort -unique $out]
}
proc ::ot_calclk::xy {it} {
  set b [$it getBBox]
  return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]]
}
proc ::ot_calclk::choose_site {points source_xy dbu} {
  # Balance opposite macro faces from a legal channel, instead of putting the
  # pair driver on a forbidden macro midpoint or extending a distant leaf wire.
  set xs [lsort -integer [lmap p $points {lindex $p 0}]]
  set ys [lsort -integer [lmap p $points {lindex $p 1}]]
  set cx [expr {([lindex $xs 0]+[lindex $xs end])/2}]
  set cy [expr {([lindex $ys 0]+[lindex $ys end])/2}]
  set w [$::ot_dtsh::master getWidth];set h [$::ot_dtsh::master getHeight]
  set best {};set score 1e99
  dict for {y rows} $::ot_dtsh::rows {
    if {abs($y-$cy) > 5*$dbu} continue
    set rowkey [expr {int(floor(double($y-$::ot_dtsh::ymin)/$::ot_dtsh::rowheight))}]
    set occ {}
    if {[dict exists $::ot_dtsh::occupied $rowkey]} {
      foreach b [dict get $::ot_dtsh::occupied $rowkey] {lappend occ [list [lindex $b 1] [lindex $b 3]]}
      set occ [lsort -integer -index 0 $occ]
    }
    foreach row $rows {
      lassign $row rx pitch count rh orient
      if {$h > $rh} continue
      set cursor $rx;set end [expr {$rx+$pitch*$count}]
      foreach iv [concat $occ [list [list $end $end]]] {
        lassign $iv a b
        if {$b <= $cursor} continue
        if {$a > $cursor} {
          set lo [expr {$rx+int(ceil(double($cursor-$rx)/$pitch))*$pitch}]
          set hi [expr {$rx+int(floor(double(min($a,$end)-$w-$rx)/$pitch))*$pitch}]
          if {$lo <= $hi} {
            set x [expr {max($lo,min($hi,$rx+int(round(double($cx-$rx)/$pitch))*$pitch))}]
            set mn 1e99;set mx 0
            foreach p $points {
              set d [expr {abs($x+[expr {$w/2}]-[lindex $p 0])+abs($y+[expr {$h/2}]-[lindex $p 1])}]
              set mn [expr {min($mn,$d)}];set mx [expr {max($mx,$d)}]
            }
            set src [expr {abs($x-[lindex $source_xy 0])+abs($y-[lindex $source_xy 1])}]
            set cost [expr {$mx+4*($mx-$mn)+0.25*$src}]
            if {$mx <= 200*$dbu && $src <= 200*$dbu && $cost < $score} {
              if {![catch {ot_dtsh::check_site $x $y $orient}]} {set score $cost;set best [list $x $y $orient $mx $src]}
            }
          }
        }
        set cursor [expr {max($cursor,$b)}]
        if {$cursor >= $end} break
      }
    }
  }
  return $best
}
proc ::ot_calclk::rebuild {} {
  if {![info exists ::env(OT_CALCLK_AFFINITY)] || $::env(OT_CALCLK_AFFINITY) ne "1"} {return 0}
  set b [ord::get_db_block];set dbu [$b getDbUnitsPerMicron]
  set ::ot_dtsh::blk $b
  set ::ot_dtsh::master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  if {$::ot_dtsh::master eq "NULL"} {error "OT_CALCLK missing BUF24"}
  ot_dtsh::capture
  set caps {};set cals {}
  foreach i [$b getInsts] {
    if {![string match DFF* [[$i getMaster] getName]]} continue
    set n [string map {\\ ""} [$i getName]]
    if {[regexp {^(.*\.u_programme)\.captured\[([0-9]+)\]} $n -> prefix bit]} {dict set caps [list $prefix $bit] $i}
    if {[regexp {^(.*\.u_programme)\.calendar\[([0-9]+)\]} $n -> prefix bit]} {dict set cals [list $prefix $bit] $i}
  }
  if {![dict size $cals]} {error "OT_CALCLK no captured/calendar pipeline in this vehicle"}
  set moved {};set records {};set skipped {};set source_nets {};set k 0
  dict for {key cal} $cals {
    if {![dict exists $caps $key]} {error "OT_CALCLK calendar has no same-bit captured source"}
    set cap [dict get $caps $key];set members [list $cap $cal]
    foreach s [successors $cal] {if {$s ni $members} {lappend members $s}}
    if {[llength $members] > 4} {lappend skipped [list $key too_many_direct_sinks];continue}
    set ck [pin $cap CLK];set old_leaf [$ck getNet];set root [root_of $old_leaf]
    # Replace the leaf level rather than append another clock stage.  The new
    # shared pair driver is attached to the old captured-leaf driver's parent.
    set leaf_driver ""
    foreach t [$old_leaf getITerms] {if {[$t isOutputSignal]} {set leaf_driver [$t getInst];break}}
    if {$leaf_driver eq "" || ![regexp {^(BUF|INV|CKBUF|CKINV|HB)} [[$leaf_driver getMaster] getName]]} {error "OT_CALCLK missing captured leaf driver"}
    set lip [ot_dtsh::sigpins $leaf_driver INPUT]
    if {[llength $lip] != 1} {error "OT_CALCLK captured leaf parent not unique"}
    set source [[lindex $lip 0] getNet]
    set points {};set valid 1
    foreach i $members {
      set cp [pin $i CLK]
      if {$cp eq "" || [root_of [$cp getNet]] ne $root || [dict exists $moved [$i getName]]} {set valid 0;break}
      lappend points [xy $cp]
    }
    if {!$valid} {lappend skipped [list $key root_or_membership_conflict];continue}
    set source_driver ""
    foreach it [$source getITerms] {if {[$it isOutputSignal]} {set source_driver $it;break}}
    if {$source_driver eq ""} {error "OT_CALCLK missing actual source leaf driver"}
    set site [choose_site $points [xy $source_driver] $dbu]
    if {![llength $site]} {puts "OT_CALCLK NO_SITE bit[lindex $key 1] points$points source[xy $source_driver] dbu$dbu";lappend skipped [list $key no_balanced_legal_channel_site];continue}
    lassign $site x y orient maxleg inleg
    set name ot_calclk_pair_$k
    if {[$b findInst $name] ne "NULL"} {error "OT_CALCLK repeated application"}
    set i [odb::dbInst_create $b $::ot_dtsh::master $name]
    $i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
    if {[lrange [ot_dtsh::box $i] 0 1] ne [list $x $y]} {error "OT_CALCLK checked/actual footprint mismatch"}
    ot_dtsh::pg $i
    set net [odb::dbNet_create $b ${name}_Y];$net setSigType CLOCK
    set ip [lindex [ot_dtsh::sigpins $i INPUT] 0];set op [lindex [ot_dtsh::sigpins $i OUTPUT] 0]
    set src_dnt [$source isDoNotTouch];if {$src_dnt} {$source setDoNotTouch false}
    $ip connect $source;$op connect $net
    foreach member $members {
      set cp [pin $member CLK];set old [$cp getNet];set dnt [$old isDoNotTouch]
      if {$dnt} {$old setDoNotTouch false}
      $cp disconnect;$cp connect $net
      if {$dnt} {$old setDoNotTouch true}
      dict set moved [$member getName] 1
    }
    if {$src_dnt} {$source setDoNotTouch true}
    $i setDoNotTouch true;$net setDoNotTouch true
    dict set source_nets [$source getName] $source
    ot_dtsh::occ_add $name [ot_dtsh::box $i]
    lappend records [list $name [lindex $key 1] [llength $members] [expr {$x/double($dbu)}] [expr {$y/double($dbu)}] [expr {$maxleg/double($dbu)}] [expr {$inleg/double($dbu)}] [[$source_driver getInst] getName]]
    puts "OT_CALCLK PAIR $name bit[lindex $key 1] [llength $members] clocks at [expr {$x/double($dbu)}],[expr {$y/double($dbu)}] maxleg[expr {$maxleg/double($dbu)}]um"
    incr k
  }
  dict for {name n} $source_nets {
    set count 0;foreach it [$n getITerms] {if {[$it isInputSignal]} {incr count}}
    puts "OT_CALCLK SOURCE_FANOUT $name $count"
  }
  # Cell identity/placement and every data/control connection stay immutable.
  dict for {name state} $::ot_dtsh::original {
    set i [$b findInst $name]
    if {[list [ot_dtsh::box $i] [$i getOrient] [[$i getMaster] getName]] ne $state} {error "OT_CALCLK moved/resized original $name"}
  }
  dict for {key expected} $::ot_dtsh::ff_data {
    lassign $key name pin
    set n [[$b findInst $name] findITerm $pin];set n [$n getNet]
    set got [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}]
    if {$got ne $expected} {error "OT_CALCLK changed original FF data/control $name/$pin"}
  }
  if {[info exists ::env(OT_CALCLK_OUT)]} {
    set f [open $::env(OT_CALCLK_OUT) w]
    puts $f "driver\tbit\tmembers\tx_um\ty_um\tmax_leg_um\tsource_leg_um\tsource_driver"
    foreach r $records {puts $f [join $r "\t"]};close $f
    set f [open $::env(OT_CALCLK_OUT).skipped w];foreach r $skipped {puts $f $r};close $f
  }
  puts "OT_CALCLK AUDIT PASS: $k paired branches [dict size $moved] clock sinks, [llength $skipped] skipped, all original placements/data/control unchanged; zero data cycles"
  return $k
}
