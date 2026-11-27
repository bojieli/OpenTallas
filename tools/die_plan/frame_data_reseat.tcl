# Authenticate only FRAME D/Q data paths and reseat their exclusive BUF/INV
# cells. Both resize stages can insert or replace repeaters, so match native
# connectivity on each invocation instead of copying names from an old ODB.
namespace eval ot_frame_reseat {}

proc ot_frame_reseat::fixed {inst} {
  return [expr {[$inst getPlacementStatus] in {FIRM LOCKED FIXED COVER}}]
}

proc ot_frame_reseat::pin_name {pin} {
  return [[$pin getMTerm] getName]
}

proc ot_frame_reseat::trace {src dst polarity} {
  foreach inst [list $src $dst] {
    if {![string match DFF* [[$inst getMaster] getName]]} {
      error "FRAME reseat requires sequential endpoints: [$inst getName]"
    }
  }
  set end [$dst findITerm D]
  if {$end eq "NULL" || ![$end isInputSignal]} {
    error "FRAME reseat missing actual D pin on [$dst getName]"
  }
  set walk $end
  set reverse {}
  set visited {}
  set inv 0
  while {1} {
    set net [$walk getNet]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]] ||
        [dict exists $visited $net]} {
      error "FRAME reseat reached nonlocal, missing or cyclic data net on [$dst getName]"
    }
    dict set visited $net 1
    set driver {}
    set loads {}
    foreach term [$net getITerms] {
      if {[$term isOutputSignal]} {
        lappend driver $term
      } elseif {[$term isInputSignal]} {
        lappend loads $term
      } else {
        error "FRAME reseat encountered an unsupported terminal on [$net getName]"
      }
    }
    if {[llength $driver] != 1 || $walk ni $loads} {
      error "FRAME reseat requires one driver and actual downstream pin on [$net getName]"
    }
    set driver [lindex $driver 0]
    set inst [$driver getInst]
    if {$inst eq $src} {
      set out {}
      foreach term [$src getITerms] {
        if {[$term isOutputSignal]} { lappend out $term }
      }
      if {$out ne [list $driver] || [pin_name $driver] ni {Q QN} || $inv != $polarity} {
        error "FRAME reseat Q pin or inversion parity changed on [$dst getName]"
      }
      return [lreverse $reverse]
    }
    if {$loads ne [list $walk] || [fixed $inst] || [llength $reverse] >= 64} {
      error "FRAME reseat encountered shared, fixed or oversized path on [$dst getName]"
    }
    set master [[$inst getMaster] getName]
    if {![regexp {^(BUF|INV)x[0-9A-Za-z]+_ASAP7_75t_[A-Za-z]+$} $master -> kind]} {
      error "FRAME reseat encountered nontransparent cell [$inst getName] ($master)"
    }
    set inputs {}
    set outputs {}
    foreach term [$inst getITerms] {
      if {[$term isInputSignal]} { lappend inputs $term }
      if {[$term isOutputSignal]} { lappend outputs $term }
    }
    if {[llength $inputs] != 1 || $outputs ne [list $driver]} {
      error "FRAME reseat encountered non-unary cell [$inst getName]"
    }
    lappend reverse $inst
    if {$kind eq "INV"} { set inv [expr {!$inv}] }
    set walk [lindex $inputs 0]
  }
}

proc ot_frame_reseat::bbox {obj {margin 0}} {
  set b [$obj getBBox]
  return [list [expr {[$b xMin]-$margin}] [expr {[$b yMin]-$margin}] \
               [expr {[$b xMax]+$margin}] [expr {[$b yMax]+$margin}]]
}

proc ot_frame_reseat::center {inst} {
  lassign [bbox $inst] x y X Y
  return [list [expr {($x+$X)/2.0}] [expr {($y+$Y)/2.0}]]
}

proc ot_frame_reseat::block_rows {busyVar rect y0 height} {
  upvar 1 $busyVar busy
  lassign $rect x y X Y
  for {set row [expr {int(floor(double($y-$y0)/$height))*$height+$y0}]} {$row < $Y} {incr row $height} {
    dict lappend busy $row [list $x $X]
  }
}

proc ot_frame_reseat::free {row x end} {
  foreach interval $row {
    lassign $interval a b
    if {$x < $b && $end > $a} { return 0 }
  }
  return 1
}

proc ot_frame_reseat::atlas {block dbu endpoints reserved} {
  set rows {}
  set all_rows [$block getRows]
  if {![llength $all_rows]} { error "FRAME reseat has no placement rows" }
  set site [[lindex $all_rows 0] getSite]
  set pitch [$site getWidth]
  set height [$site getHeight]
  set y0 [lindex [[lindex $all_rows 0] getOrigin] 1]
  if {$pitch <= 0 || $height <= 0} { error "FRAME reseat invalid placement lattice" }
  foreach r $all_rows {
    set site [$r getSite]
    lassign [$r getOrigin] x y
    set orient [$r getOrient]
    set spacing [$r getSpacing]
    if {[$r getDirection] ne "HORIZONTAL" || [$site getWidth] != $pitch ||
        [$site getHeight] != $height || $spacing ni [list 0 $pitch] ||
        ($y-$y0)%$height || $orient ni {R0 MX}} {
      error "FRAME reseat encountered unsupported placement row [$r getName]"
    }
    set limit [expr {$x + $pitch*[$r getSiteCount]}]
    dict lappend rows $y [list $x $limit $orient]
  }
  set busy {}
  foreach b [$block getBlockages] {
    block_rows busy [bbox $b] $y0 $height
  }
  set halo [expr {round(4.32*$dbu)}]
  dict for {i _} $endpoints {
    block_rows busy [bbox $i] $y0 $height
  }
  foreach i [$block getInsts] {
    if {[[$i getMaster] isBlock]} {
      block_rows busy [bbox $i $halo] $y0 $height
    } elseif {[fixed $i] && ![dict exists $endpoints $i]} {
      block_rows busy [bbox $i] $y0 $height
    }
  }
  foreach box $reserved {
    block_rows busy [lmap v $box {expr {round($v*$dbu)}}] $y0 $height
  }
  return [list $rows $busy $pitch $height $y0]
}

proc ot_frame_reseat::seat {rows busyVar pitch height y0 wantX wantY width low high} {
  upvar 1 $busyVar busy
  set yr [expr {round(($wantY-$height/2.0-$y0)/$height)*$height+$y0}]
  set best {}
  set cost Inf
  # Bounded displacement around the reviewed interpolation. Fail rather than
  # move these cells into another corridor or backtrack a same-bit chain.
  for {set dy 0} {$dy <= 28 && $dy*$height <= $cost+$height} {incr dy} {
    foreach y [lsort -unique [list [expr {$yr+$dy*$height}] [expr {$yr-$dy*$height}]]] {
      if {![dict exists $rows $y]} continue
      set occupied {}
      if {[dict exists $busy $y]} { set occupied [dict get $busy $y] }
      foreach segment [dict get $rows $y] {
        lassign $segment a b orient
        set i [expr {round(($wantX-$width/2.0-$a)/$pitch)}]
        for {set dx 0} {$dx <= 65} {incr dx} {
          set found 0
          foreach index [lsort -unique [list [expr {$i+$dx}] [expr {$i-$dx}]]] {
            set x [expr {$a+$index*$pitch}]
            set X [expr {$x+$width}]
            set ctr [expr {($x+$X)/2.0}]
            if {$x < $a || $X > $b || $ctr < $low || $ctr > $high || ![free $occupied $x $X]} continue
            set score [expr {abs($ctr-$wantX)+abs($y+$height/2.0-$wantY)}]
            if {$score < $cost} {
              set cost $score
              set best [list $x $y $orient]
            }
            set found 1
          }
          if {$found} break
        }
      }
    }
  }
  if {![llength $best]} {
    error "FRAME reseat has no disjoint row site by ${wantX},${wantY}"
  }
  lassign $best x y _
  dict lappend busy $y [list $x [expr {$x+$width}]]
  return $best
}

proc ot_frame_reseat::run {phase} {
  variable paths
  variable reserved
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  if {$phase ni {resize detail} || [llength $paths] != 4664 || $dbu <= 0} {
    error "FRAME reseat missing reviewed path inventory or stage"
  }
  set index {}
  foreach inst [$block getInsts] {
    set name [string map {\\ {}} [$inst getName]]
    if {[regexp {^u_bound[.]u_(u_lpl_(5|10|11|12|13)_w[.]|ist_frame_int_o0_|bout_frame_int_o0[./])} $name]} {
      if {[dict exists $index $name]} { error "FRAME reseat ambiguous native endpoint $name" }
      dict set index $name $inst
    }
  }
  set endpoints {}
  set selected {}
  set native {}
  foreach row $paths {
    lassign $row bit hop source target parity site
    if {![dict exists $index $source] || ![dict exists $index $target]} {
      error "FRAME reseat missing reviewed endpoint at bit $bit hop $hop"
    }
    set src [dict get $index $source]
    set dst [dict get $index $target]
    if {$hop < 3} {
      set pin [lmap c $site {expr {round($c*$dbu)}}]
      if {[$dst getLocation] ne $pin} {
        error "FRAME reseat station moved off its reviewed seat at bit $bit hop $hop"
      }
    }
    set chain [trace $src $dst $parity]
    foreach i $chain {
      if {[dict exists $selected $i]} { error "FRAME reseat intermediate belongs to two payloads" }
      dict set selected $i 1
    }
    dict set endpoints $src 1
    dict set endpoints $dst 1
    lappend native [list $src $dst $chain]
  }
  lassign [atlas $block $dbu $endpoints $reserved] rows busy pitch height y0
  set moves {}
  foreach corridor $native {
    lassign $corridor src dst chain
    lassign [center $src] sx sy
    lassign [center $dst] tx ty
    if {$tx > $sx || abs($tx-$sx)+abs($ty-$sy) > 405*$dbu} {
      error "FRAME reseat endpoint hop exceeds reviewed westbound corridor: [$src getName] to [$dst getName]"
    }
    set count [expr {[llength $chain]+1}]
    set prior $sx
    set ordinal 0
    foreach i $chain {
      incr ordinal
      set m [$i getMaster]
      set width [$m getWidth]
      if {$width <= 0 || $width % $pitch || [$m getHeight] != $height} {
        error "FRAME reseat unsupported native footprint: [$i getName]"
      }
      set x [expr {$sx+($tx-$sx)*$ordinal/double($count)}]
      set y [expr {$sy+($ty-$sy)*$ordinal/double($count)}]
      lassign [seat $rows busy $pitch $height $y0 $x $y $width $tx $prior] ax ay orient
      set prior [expr {$ax+$width/2.0}]
      lappend moves [list $i $ax $ay $orient]
    }
  }
  # Every path and proposed body validates before the first database edit.
  foreach move $moves {
    lassign $move inst x y orient
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
  }
  puts "OT_FRAME_DATA_RESEAT phase=$phase authenticated_paths=[llength $native] moved_cells=[llength $moves]"
}
