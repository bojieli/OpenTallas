# Native59 P4: density buffers for shared shallow_clock_multi.
# After clock_taps.tcl. No private trunk or CTS wrapper; preview performs no CTS.
global n59st_blk n59st_dbu n59st_subtaps n59st_trunk n59st_blocks n59st_halo n59st_tmaster n59st_seq
set n59st_blk [ord::get_db_block]
set n59st_dbu [$n59st_blk getDefUnits]
proc n59st_env {k d} { return [expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d}] }
set n59st_port_re [n59st_env N59_ST_PORT_RE {^clk(_t[0-9]+)?$}]
set n59st_target  [n59st_env N59_ST_TARGET 400]
set n59st_cap     [n59st_env N59_ST_CAP 500]
set n59st_rlim    [expr {[n59st_env N59_ST_RADIUS_UM 100] * $n59st_dbu}]
set n59st_fan     [n59st_env N59_ST_FANOUT 4]
set n59st_halo    [expr {int([n59st_env N59_ST_HALO_UM 5.4] * $n59st_dbu)}]
set n59st_smaster [[ord::get_db] findMaster [n59st_env N59_ST_BUF BUFx12f_ASAP7_75t_R]]
set n59st_tmaster [[ord::get_db] findMaster [n59st_env N59_ST_TRUNK_BUF BUFx16f_ASAP7_75t_R]]
if {$n59st_smaster eq "NULL" || $n59st_tmaster eq "NULL"} { error "OT_N59ST buffer master missing" }
set n59st_blocks {}
foreach inst [$n59st_blk getInsts] { if {[[$inst getMaster] isBlock]} { lappend n59st_blocks [$inst getBBox] } }
set n59st_core [$n59st_blk getCoreArea]
set n59st_subtaps {}   ;# list of dicts: name port kind inst innet outnet x y n
set n59st_trunk {}     ;# trunk buffer insts
set n59st_seq 0
set n59st_roots {}

proc n59st_cent {us} {
  set sx 0.0; set sy 0.0; set w 0
  foreach u $us { set n [llength [lindex $u 2]]; set sx [expr {$sx + $n*[lindex $u 0]}]; set sy [expr {$sy + $n*[lindex $u 1]}]; incr w $n }
  return [list [expr {$sx/$w}] [expr {$sy/$w}]]
}
proc n59st_w {us} { set w 0; foreach u $us { incr w [llength [lindex $u 2]] }; return $w }
proc n59st_rad {us} {
  lassign [n59st_cent $us] cx cy; set r 0
  foreach u $us { set d [expr {abs([lindex $u 0]-$cx)+abs([lindex $u 1]-$cy)}]; if {$d > $r} { set r $d } }
  return $r
}
# split units into exactly k parts of proportional weight along the longer extent (recursive)
proc n59st_splitk {us k} {
  if {$k <= 1 || [llength $us] <= 1} { return [list $us] }
  set w [n59st_w $us]
  set xs [lmap u $us {lindex $u 0}]; set ys [lmap u $us {lindex $u 1}]
  set ax [expr {([tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs]) >= ([tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys]) ? 0 : 1}]
  set srt [lsort -real -index $ax $us]
  set k1 [expr {$k / 2}]; set goal [expr {$w * $k1 / double($k)}]
  set acc 0; set cut 0
  foreach u $srt { if {$acc >= $goal} break; incr acc [llength [lindex $u 2]]; incr cut }
  if {$cut <= 0} { set cut 1 }; if {$cut >= [llength $srt]} { set cut [expr {[llength $srt]-1}] }
  return [concat [n59st_splitk [lrange $srt 0 [expr {$cut-1}]] $k1] [n59st_splitk [lrange $srt $cut end] [expr {$k-$k1}]]]
}
# density clusters: k = ceil(W/target) proportional parts; a part over cap or radius splits again (weight >= 2)
proc n59st_bisect {us target cap rlim} {
  set w [n59st_w $us]
  set k [expr {int(ceil($w / double($target)))}]
  if {$k <= 1 && $w <= $cap && ($w < 2 || [n59st_rad $us] <= $rlim)} { return [list $us] }
  if {$k <= 1} { set k 2 }
  set out {}
  foreach p [n59st_splitk $us $k] {
    # k proportional parts of ~W/k; a part over cap or radius splits again
    set out [concat $out [n59st_bisect $p $target $cap $rlim]]
  }
  return $out
}
# a legal-ish location (lower-left, dbu) for a cell of master m near (x,y): out of every macro + halo, inside the core
proc n59st_site {x y m} {
  global n59st_blocks n59st_halo n59st_core
  set w [$m getWidth]; set h [$m getHeight]
  set x [expr {int($x - $w/2)}]; set y [expr {int($y - $h/2)}]
  for {set it 0} {$it < 4} {incr it} {
    set hit 0
    foreach b $n59st_blocks {
      set x0 [expr {[$b xMin]-$n59st_halo-$w}]; set x1 [expr {[$b xMax]+$n59st_halo}]
      set y0 [expr {[$b yMin]-$n59st_halo-$h}]; set y1 [expr {[$b yMax]+$n59st_halo}]
      if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} {
        set c [lsort -real -index 0 [list [list [expr {$x-$x0}] $x0 $y] [list [expr {$x1-$x}] $x1 $y] [list [expr {$y-$y0}] $x $y0] [list [expr {$y1-$y}] $x $y1]]]
        lassign [lindex $c 0] - x y
        set hit 1
      }
    }
    set x [expr {max([$n59st_core xMin], min([$n59st_core xMax]-$w, $x))}]
    set y [expr {max([$n59st_core yMin], min([$n59st_core yMax]-$h, $y))}]
    if {!$hit} break
  }
  return [list [expr {int($x)}] [expr {int($y)}]]
}
proc n59st_buf {name m x y innet outnet} {
  global n59st_blk
  set inst [odb::dbInst_create $n59st_blk $m $name]
  foreach t [$inst getITerms] {
    set mt [$t getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $innet } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $outnet }
  }
  lassign [n59st_site $x $y $m] lx ly
  $inst setLocation $lx $ly
  $inst setPlacementStatus PLACED
  return $inst
}

# Merge small remainders only when the full joined group stays within cap/reach.
proc n59st_merge_small {groups cap radius} {
  set minimum [n59st_env N59_ST_MIN 100]
  set changed 1
  while {$changed} {
    set changed 0
    for {set i 0} {$i < [llength $groups]} {incr i} {
      set a [lindex $groups $i]
      if {[n59st_w $a] >= $minimum} continue
      set best -1; set cost Inf; lassign [n59st_cent $a] ax ay
      for {set j 0} {$j < [llength $groups]} {incr j} {
        if {$j == $i} continue
        set b [lindex $groups $j]; set joined [concat $a $b]
        if {[n59st_w $joined] > $cap || [n59st_rad $joined] > $radius} continue
        lassign [n59st_cent $b] bx by
        set distance [expr {abs($ax-$bx)+abs($ay-$by)}]
        if {$distance < $cost} { set cost $distance; set best $j }
      }
      if {$best < 0} continue
      set groups [lreplace $groups $best $best [concat $a [lindex $groups $best]]]
      set groups [lreplace $groups $i $i]
      set changed 1
      break
    }
  }
  return $groups
}
set n59st_rows {}
foreach bt [$n59st_blk getBTerms] {
  set port [$bt getName]
  if {![regexp $n59st_port_re $port]} continue
  set pnet [$bt getNet]; if {$pnet eq "NULL"} continue
  set regs {}; set macs {}
  foreach it [$pnet getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set inst [$it getInst]; set b [$inst getBBox]
    if {[[$inst getMaster] isBlock]} {
      set ib [$it getBBox]
      lappend macs [list [expr {([$ib xMin]+[$ib xMax])/2.0}] [expr {([$ib yMin]+[$ib yMax])/2.0}] [list $it]]
    } else {
      lappend regs [list [expr {([$b xMin]+[$b xMax])/2.0}] [expr {([$b yMin]+[$b yMax])/2.0}] [list $it]]
    }
  }
  if {![llength $regs] && ![llength $macs]} continue
  set leaves {}
  set port_taps {}
  foreach {kind us} [list reg $regs mac $macs] {
    if {![llength $us]} continue
    set j 0
    set groups [n59st_bisect $us $n59st_target $n59st_cap $n59st_rlim]
    if {$kind eq "reg"} { set groups [n59st_merge_small $groups $n59st_cap $n59st_rlim] }
    foreach g $groups {
      incr j
      set id [incr n59st_seq]
      set nm "ot_dtap_$id"
      lassign [n59st_cent $g] cx cy
      set outn [odb::dbNet_create $n59st_blk "${nm}_ck"]; $outn setSigType CLOCK
      set inn $pnet
      set inst [n59st_buf $nm $n59st_smaster $cx $cy $inn $outn]
      set dmax 0.0; set dsum 0.0; set k 0; set members {}
      foreach u $g {
        foreach it [lindex $u 2] { $it disconnect; $it connect $outn; lappend members $it }
        set d [expr {(abs([lindex $u 0]-$cx)+abs([lindex $u 1]-$cy))/double($n59st_dbu)}]
        set dmax [expr {max($dmax,$d)}]; set dsum [expr {$dsum+$d}]; incr k
      }
      lappend n59st_subtaps [dict create name $nm port $port kind $kind inst $inst outnet $outn n $k members $members]
      lappend n59st_rows [format "%s\t%s\t%s\t%.2f\t%.2f\t%d\t%.1f\t%.1f" $nm $port $kind [expr {$cx/$n59st_dbu}] [expr {$cy/$n59st_dbu}] $k [expr {$dsum/$k}] $dmax]
      lappend leaves [list $cx $cy [list $inst]]
      lappend port_taps [list $id [expr {int($cx)}] [expr {int($cy)}] $outn]
    }
  }
  dict set n59st_roots $port [dict create root_net $pnet tap_list $port_taps]
  puts "OT_N59_DENSITY port $port: [llength $regs] registers + [llength $macs] macro clock pins -> [llength $port_taps] existing density-tap buffers"
}

# Report every displacement; only new buffers are intended to need row sites.
set n59st_before {}
foreach i [$n59st_blk getInsts] {
  if {![[$i getMaster] isBlock] && ![string match ot_dtap_* [$i getName]]} {
    dict set n59st_before [$i getName] [$i getLocation]
  }
}
detailed_placement
set moved 0; set maxmove 0
dict for {name xy} $n59st_before {
  lassign [[$n59st_blk findInst $name] getLocation] x y
  set d [expr {abs($x-[lindex $xy 0])+abs($y-[lindex $xy 1])}]
  if {$d} { incr moved; set maxmove [expr {max($maxmove,$d)}] }
}
puts "OT_N59_DENSITY DPL existing_cells_moved $moved max_um [expr {$maxmove/double($n59st_dbu)}]"
set dir [n59st_env N59_ST_REPORT_DIR [n59st_env RESULTS_DIR /work]]
file mkdir $dir
set fh [open [file join $dir actual_subtaps.tsv] w]
puts $fh "inst\towner_root\tx_um\ty_um\tload_sinks\tradius_um\tcap_sinks\tradius_limit_um\tcoordinate_basis\tkind"
set policy_failures 0
foreach tap $n59st_subtaps {
  set inst [dict get $tap inst]; set bb [$inst getBBox]
  set x [expr {([$bb xMin]+[$bb xMax])/2.0}]
  set y [expr {([$bb yMin]+[$bb yMax])/2.0}]
  set radius 0.0
  foreach pin [dict get $tap members] {
    set pb [$pin getBBox]
    set px [expr {([$pb xMin]+[$pb xMax])/2.0}]
    set py [expr {([$pb yMin]+[$pb yMax])/2.0}]
    set radius [expr {max($radius,abs($x-$px)+abs($y-$py))}]
  }
  puts $fh "[dict get $tap name]\t[dict get $tap port]\t[expr {$x/$n59st_dbu}]\t[expr {$y/$n59st_dbu}]\t[dict get $tap n]\t[expr {$radius/$n59st_dbu}]\t$n59st_cap\t[expr {$n59st_rlim/$n59st_dbu}]\tactual_odb\t[dict get $tap kind]"
  if {[dict get $tap n] > $n59st_cap || $radius > $n59st_rlim} { incr policy_failures }
  $inst setPlacementStatus FIRM
}
close $fh
puts "OT_N59_DENSITY actual_policy_failures $policy_failures"
if {[n59st_env N59_ST_PREVIEW_ONLY 0] ne "1"} {
  if {$policy_failures} { error "OT_N59_DENSITY actual cap/radius policy failed; review geometry before CTS" }
  set ff_reg [n59st_env N59_ST_FF_REG_TARGET ""]
  set ff_mac [n59st_env N59_ST_FF_MACRO_TARGET ""]
  if {![string is double -strict $ff_reg] || ![string is double -strict $ff_mac]} {
    error "OT_N59_DENSITY explicit per-corner FF budgets required; never infer from TT"
  }
  foreach tap $n59st_subtaps {
    set macro [expr {[dict get $tap kind] eq "mac"}]
    set tt [expr {$macro ? 232.5 : 250.0}]
    set ff [expr {$macro ? $ff_mac : $ff_reg}]
    dict set n59st_roots [dict get $tap port] sink_targets_ps [dict get $tap name] [dict create tt $tt ff $ff basis BUDGET]
  }
  source /work/shallow_clock.tcl
  source /work/shallow_clock_multi.tcl
  ::ot_dtsh_multi::setup $n59st_blk $n59st_roots [n59st_env N59_ST_TRUNK_BUF BUFx16f_ASAP7_75t_R]
}
