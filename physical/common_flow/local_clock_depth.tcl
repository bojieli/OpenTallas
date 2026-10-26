# Explicit sparse-local-tree compensation. Source defines procedures only.
# Caller: after local CTS/legalisation and before clock RC measurement,
# ot_local_depth::pad_short_taps $::dt_taps (OT_DTAP_PAD_SPARSE=1).
# Existing tap output -> compact same-polarity buffer chain -> SAME local net.
# No FF/data pin, original clock sink net, RTL cycle or original cell moves.
namespace eval ::ot_local_depth { variable version 1 }
proc ::ot_local_depth::sinks {net {depth 0}} {
  if {$depth > 40} { error "OT_LOCAL_DEPTH clock graph deeper than 40" }
  set out {}
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set m [$i getMaster]
    if {[$m isBlock]} continue
    if {[string match *DFF* [$m getName]]} { lappend out [list $it $depth]; continue }
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} [$m getName]]} {
      error "OT_LOCAL_DEPTH unexpected local clock cell [$i getName] ([$m getName])"
    }
    foreach o [$i getITerms] {
      if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [$o getNet] ne ""} {
        lappend out {*}[sinks [$o getNet] [expr {$depth+1}]]
      }
    }
  }
  return $out
}
proc ::ot_local_depth::site_near {x y radius} {
  # Reuse the planned-clock runtime's actual row/site/orientation/footprint guard.
  # This works on occupied geometry, never on a guessed utilization estimate.
  set candidates {}
  dict for {ry rows} $::ot_dtsh::rows {
    if {abs($ry-$y) > $radius} continue
    foreach row $rows {
      lassign $row rx pitch count rh orient
      set lo [expr {max(0,int(ceil(double($x-$radius-$rx)/$pitch)))}]
      set hi [expr {min($count-1,int(floor(double($x+$radius-$rx)/$pitch)))}]
      for {set k $lo} {$k <= $hi} {incr k} {
        set xx [expr {$rx+$k*$pitch}]
        set d [expr {abs($xx-$x)+abs($ry-$y)}]
        if {$d <= $radius} { lappend candidates [list $d $xx $ry $orient] }
      }
    }
  }
  foreach c [lsort -integer -index 0 $candidates] {
    lassign $c d xx yy orient
    if {![catch {::ot_dtsh::check_site $xx $yy $orient}]} { return [list $xx $yy $orient] }
  }
  error "OT_LOCAL_DEPTH no free legal buffer footprint within compact radius"
}
proc ::ot_local_depth::pad_short_taps {tap_list} {
  if {![info exists ::env(OT_DTAP_PAD_SPARSE)] || $::env(OT_DTAP_PAD_SPARSE) ne "1"} { return 0 }
  if {![info exists ::ot_dtsh::active] || !$::ot_dtsh::active} { error "OT_LOCAL_DEPTH needs the explicit planned-clock runtime" }
  set target [expr {[info exists ::env(OT_DTAP_PAD_DEPTH)] ? $::env(OT_DTAP_PAD_DEPTH) : 2}]
  set maxs [expr {[info exists ::env(OT_DTAP_PAD_MAX_SINKS)] ? $::env(OT_DTAP_PAD_MAX_SINKS) : 16}]
  set radius_um [expr {[info exists ::env(OT_DTAP_PAD_RADIUS_UM)] ? $::env(OT_DTAP_PAD_RADIUS_UM) : 10}]
  if {![string is integer -strict $target] || $target < 1 || $target > 3 || ![string is integer -strict $maxs] || $maxs < 1 || $maxs > 16 || $radius_um <= 0 || $radius_um > 10} {
    error "OT_LOCAL_DEPTH requires depth1..3, sinks1..16, compact radius(0,10]um"
  }
  set blk $::ot_dtsh::blk; set master $::ot_dtsh::master
  if {![string match BUF* [$master getName]]} { error "OT_LOCAL_DEPTH only non-inverting BUF masters are allowed" }
  set dbu [$blk getDbUnitsPerMicron]; set radius [expr {int($radius_um*$dbu)}]
  # Local CTS has added cells since the runtime captured the original placement.
  # Refresh ONLY the occupancy index; original placement/data audits stay intact.
  set ::ot_dtsh::occupied {}
  foreach i [$blk getInsts] {
    if {[$i getPlacementStatus] in {PLACED FIRM LOCKED COVER}} { ::ot_dtsh::occ_add [$i getName] [::ot_dtsh::box $i] }
  }
  set made 0; set records {}
  foreach t $tap_list {
    set name ot_dtap_[lindex $t 0]; set inst [$blk findInst $name]
    if {$inst eq "NULL"} { error "OT_LOCAL_DEPTH missing planned tap $name" }
    set outputs [::ot_dtsh::sigpins $inst OUTPUT]
    if {[llength $outputs] != 1} { error "OT_LOCAL_DEPTH expected one tap output" }
    set op [lindex $outputs 0]; set old [$op getNet]
    if {$old eq "NULL" || $old eq ""} { error "OT_LOCAL_DEPTH disconnected tap output $name" }
    set ss [sinks $old]; set count [llength $ss]
    if {!$count || $count > $maxs} continue
    set mind 100; set maxd 0
    foreach s $ss {set d [lindex $s 1];set mind [expr {min($mind,$d)}];set maxd [expr {max($maxd,$d)}]}
    if {$maxd >= $target} continue
    set stages [expr {$target-$maxd}]
    lassign [$inst getLocation] x y
    # Reserve all sites before touching connectivity (a shortage fails closed).
    set pads {}
    for {set j 0} {$j < $stages} {incr j} {
      set pn ot_local_depth_${name}_$j
      if {[$blk findInst $pn] ne "NULL"} {error "OT_LOCAL_DEPTH repeated application $pn"}
      lassign [site_near $x $y $radius] xx yy orient
      set pi [odb::dbInst_create $blk $master $pn]
      $pi setOrient $orient; $pi setLocation $xx $yy; $pi setPlacementStatus FIRM
      ::ot_dtsh::pg $pi
      ::ot_dtsh::occ_add $pn [::ot_dtsh::box $pi]
      lappend pads $pi
    }
    set prev [odb::dbNet_create $blk ot_local_depth_${name}_in]
    $prev setSigType CLOCK
    $op disconnect; $op connect $prev
    set j 0
    foreach pi $pads {
      set ips [::ot_dtsh::sigpins $pi INPUT];set ops [::ot_dtsh::sigpins $pi OUTPUT]
      if {[llength $ips]!=1 || [llength $ops]!=1} {error "OT_LOCAL_DEPTH buffer pin interface changed"}
      [lindex $ips 0] connect $prev
      if {$j == $stages-1} {set next $old} else {set next [odb::dbNet_create $blk ot_local_depth_${name}_$j];$next setSigType CLOCK}
      [lindex $ops 0] connect $next
      set prev $next;incr j;incr made
      lassign [$pi getLocation] xx yy
      lappend records [list [$pi getName] $name $count $mind $maxd $stages [expr {$xx/double($dbu)}] [expr {$yy/double($dbu)}]]
    }
    puts "OT_LOCAL_DEPTH $name sinks$count prior_depth$mind..$maxd added$stages compact_radius${radius_um}um"
  }
  if {[info exists ::env(OT_DTAP_PAD_OUT)]} {
    set f [open $::env(OT_DTAP_PAD_OUT) w]
    puts $f "name\ttap\tsinks\tdepth_min\tdepth_max\tadded_stages\tx_um\ty_um"
    foreach r $records {puts $f [join $r "\t"]}
    close $f
  }
  puts "OT_LOCAL_DEPTH DONE $made non-inverting compact clock buffers, zero data cycles"
  return $made
}
