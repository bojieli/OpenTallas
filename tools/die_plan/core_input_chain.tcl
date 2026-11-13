# QC-NK-HOLD A+P (gen_phys core_input_place), PRE_RESIZE (after GPL, before repair_design buffers the new hops): spread the zero-logic register chain
# that feeds each NK pipe register (u_pc_nk_*) evenly along a macro-avoiding Manhattan route from the chain head to
# the pipe register.  pilot7 measured the class: GPL (wirelength only) left all 10 stages of e.g. u_d10_u_t_3_2_n_y
# within 150 um of the head and paid 1350 um in the last hop (TT -1131 ps at u_pc D).  Same class as S81-RCK-4
# chain_even.tcl, but the route bends around the hard cores instead of a straight line through them.
# No netlist change; stages and their hop buffers only move (PLACED), DPL legalizes.
uplevel #0 {
set nc_blk [ord::get_db_block]
set nc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set nc_core [$nc_blk getCoreArea]
set nc_halo [expr {round(9.0 * $nc_dbu)}]
set nc_mac {}
foreach i [$nc_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend nc_mac [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] } }
# street centre lines: core edges, gaps between macros (both axes)
proc nc_lines {lo hi ivals} {
  set iv [lsort -integer -index 0 $ivals]; set out {}; set cur $lo
  foreach v $iv { lassign $v a b; if {$a > $cur} { lappend out [expr {($cur + $a) / 2}] }; if {$b > $cur} { set cur $b } }
  if {$hi > $cur} { lappend out [expr {($cur + $hi) / 2}] }
  return $out
}
set nc_xi {}; set nc_yi {}
foreach m $nc_mac { lassign $m a b c d; lappend nc_xi [list $a $c]; lappend nc_yi [list $b $d] }
set nc_xs [nc_lines [$nc_core xMin] [$nc_core xMax] $nc_xi]
set nc_ys [nc_lines [$nc_core yMin] [$nc_core yMax] $nc_yi]
proc nc_hit {x1 y1 x2 y2} {
  global nc_mac
  set e 2000
  foreach m $nc_mac {
    lassign $m a b c d
    if {$y1 == $y2} { if {$y1 > $b+$e && $y1 < $d-$e && max($x1,$x2) > $a+$e && min($x1,$x2) < $c-$e} { return 1 } } \
    else { if {$x1 > $a+$e && $x1 < $c-$e && max($y1,$y2) > $b+$e && min($y1,$y2) < $d-$e} { return 1 } }
  }
  return 0
}
proc nc_len {pts} { set l 0; for {set k 1} {$k < [llength $pts]} {incr k} { lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d; set l [expr {$l + abs($c-$a) + abs($d-$b)}] }; return $l }
proc nc_ok {pts} { for {set k 1} {$k < [llength $pts]} {incr k} { lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d; if {[nc_hit $a $b $c $d]} { return 0 } }; return 1 }
# shortest Manhattan route with up to 2 bends (HVH / VHV) or 4 bends (HVHVH via two street lines) that clears macros
proc nc_route {hx hy tx ty} {
  global nc_xs nc_ys
  set best {}; set bl 0
  set cands {}
  foreach x [concat $hx $tx $nc_xs] { lappend cands [list [list $hx $hy] [list $x $hy] [list $x $ty] [list $tx $ty]] }
  foreach y [concat $hy $ty $nc_ys] { lappend cands [list [list $hx $hy] [list $hx $y] [list $tx $y] [list $tx $ty]] }
  foreach x $nc_xs { foreach y $nc_ys {
    lappend cands [list [list $hx $hy] [list $x $hy] [list $x $y] [list $tx $y] [list $tx $ty]]
    lappend cands [list [list $hx $hy] [list $hx $y] [list $x $y] [list $x $ty] [list $tx $ty]]
  } }
  foreach x1 $nc_xs { foreach y $nc_ys { foreach x2 $nc_xs {
    lappend cands [list [list $hx $hy] [list $x1 $hy] [list $x1 $y] [list $x2 $y] [list $x2 $ty] [list $tx $ty]]
  } } }
  foreach y1 $nc_ys { foreach x $nc_xs { foreach y2 $nc_ys {
    lappend cands [list [list $hx $hy] [list $hx $y1] [list $x $y1] [list $x $y2] [list $tx $y2] [list $tx $ty]]
  } } }
  foreach p $cands { if {![nc_ok $p]} continue; set l [nc_len $p]; if {$best eq {} || $l < $bl} { set best $p; set bl $l } }
  if {$best eq {}} { set best [list [list $hx $hy] [list $tx $ty]] }
  return $best
}
proc nc_at {pts f} {
  set L [nc_len $pts]; set want [expr {$f * $L}]; set acc 0
  for {set k 1} {$k < [llength $pts]} {incr k} {
    lassign [lindex $pts [expr {$k-1}]] a b; lassign [lindex $pts $k] c d
    set s [expr {abs($c-$a) + abs($d-$b)}]
    if {$acc + $s >= $want && $s > 0} { set t [expr {double($want-$acc)/$s}]; return [list [expr {$a+($c-$a)*$t}] [expr {$b+($d-$b)*$t}]] }
    set acc [expr {$acc + $s}]
  }
  return [lindex $pts end]
}
proc nc_put {inst x y} {
  global nc_mac nc_halo nc_core
  set w [[$inst getMaster] getWidth]; set h [[$inst getMaster] getHeight]
  foreach m $nc_mac {
    lassign $m a b c d; set a [expr {$a-$nc_halo}]; set b [expr {$b-$nc_halo}]; set c [expr {$c+$nc_halo}]; set d [expr {$d+$nc_halo}]
    if {$x > $a && $x < $c && $y > $b && $y < $d} {
      lassign [lindex [lsort -real -index 0 [list [list [expr {$x-$a}] $a $y] [list [expr {$c-$x}] $c $y] [list [expr {$y-$b}] $x $b] [list [expr {$d-$y}] $x $d]]] 0] _ x y
    }
  }
  set x [expr {max([$nc_core xMin], min([$nc_core xMax]-$w, $x))}]
  set y [expr {max([$nc_core yMin], min([$nc_core yMax]-$h, $y))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  if {[$inst getPlacementStatus] in {UNPLACED FIRM}} { $inst setPlacementStatus PLACED }
}
proc nc_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}] }
# face-anchored registers (face_flops.tcl pin registers, released just before this hook) stay where they are: they
# end a chain like a fixed head
set nc_face {}
if {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/ot_face_flops.txt]} {
  set f [open $::env(RESULTS_DIR)/ot_face_flops.txt]; foreach l [split [read $f] "\n"] { set l [string trim $l]; if {$l ne ""} { dict set nc_face $l 1 } }; close $f
}
proc nc_mov {inst} { global nc_face; return [expr {[$inst getPlacementStatus] ni {FIRM LOCKED COVER} && ![dict exists $nc_face [$inst getName]]}] }
# driver of an input iterm through buffers: {driver_iterm {buffers nearest-first}}
proc nc_back {it} {
  set bufs {}; set net [$it getNet]
  for {set k 0} {$k < 40} {incr k} {
    if {$net eq "NULL" || $net eq ""} { return [list "" $bufs] }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t } }
    if {$drv eq ""} { return [list "" $bufs] }
    set di [$drv getInst]
    if {[[$di getMaster] isBlock] || ![nc_isbuf $di]} { return [list $drv $bufs] }
    lappend bufs $di
    set net ""; foreach t [$di getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [[$t getNet] getSigType] eq "SIGNAL"} { set net [$t getNet] } }
  }
  return [list "" $bufs]
}
proc nc_loads {inst} {
  set n 0
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} {
    set front [list [$t getNet]]
    for {set d 0} {$d < 40 && [llength $front]} {incr d} { set nf {}
      foreach net $front { foreach x [$net getITerms] { if {![$x isInputSignal]} continue; set xi [$x getInst]
        if {![[$xi getMaster] isBlock] && [nc_isbuf $xi]} { foreach o [$xi getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend nf [$o getNet] } } } else { incr n } } }
      set front $nf }
  } }
  return $n
}
proc nc_dpin {inst} { foreach t [$inst getITerms] { if {[[$t getMTerm] getName] eq "D"} { return $t } }; return "" }
proc nc_ctr {o} { set b [$o getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
set nc_corefix 0; set nc_chains 0; set nc_moved 0; set nc_l0 {}; set nc_l1 {}; set nc_rc {}
foreach pc [$nc_blk getInsts] {
  if {![regexp {u_pc_nk_} [$pc getName]] || ![string match "DFF*" [[$pc getMaster] getName]]} continue
  # backward: hops {stage_inst bufs_on_its_D}, stages = movable fanout-1 zero-logic chain registers
  set seq {}; set hopb {}; set cur $pc; set head ""
  while {[llength $seq] < 24} {
    set dp [nc_dpin $cur]; if {$dp eq ""} break
    lassign [nc_back $dp] drv bufs
    lappend hopb $bufs
    if {$drv eq ""} break
    set di [$drv getInst]
    set nm [string map {\\ {}} [$di getName]]
    if {![[$di getMaster] isBlock] && [string match "DFF*" [[$di getMaster] getName]] && [nc_mov $di] \
        && [regexp {(u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_)} $nm] && ![regexp {u_pc_nk_} $nm] && [nc_loads $di] == 1} {
      set seq [linsert $seq 0 $di]; set cur $di; continue
    }
    set head $drv; break
  }
  if {$head eq "" || ![llength $seq]} continue
  # head: driver flop/pin position; tail: the pipe register (anchored at the NK pin)
  if {[[[$head getInst] getMaster] isBlock]} {
    # a hard-core output launches late (NK clk->out ~870 ps TT): its first stage stays where GPL put it, next to the
    # pin (pilot8 moved it 1/5 along the route: TT -1441 at u_d3_*_t_out r[0]); the route starts at that stage
    lassign [nc_ctr [lindex $seq 0]] hx hy
    set seq [lrange $seq 1 end]
    incr nc_corefix
    if {![llength $seq]} continue
  } else { lassign [nc_ctr [$head getInst]] hx hy }
  lassign [nc_ctr $pc] tx ty
  set route [nc_route $hx $hy $tx $ty]
  set hops [expr {[llength $seq] + 1}]
  # before: longest single hop (Manhattan) along head -> stages -> pc
  set prev [list $hx $hy]; set mx 0
  foreach s [concat $seq [list $pc]] { lassign [nc_ctr $s] x y; set mx [expr {max($mx, abs($x-[lindex $prev 0])+abs($y-[lindex $prev 1]))}]; set prev [list $x $y] }
  lappend nc_l0 [expr {$mx/double($nc_dbu)}]
  lappend nc_l1 [expr {[nc_len $route]/double($hops)/$nc_dbu}]
  dict incr nc_rc [expr {[llength $route]-2}]
  for {set j 0} {$j < [llength $seq]} {incr j} {
    lassign [nc_at $route [expr {double($j+1)/$hops}]] x y
    nc_put [lindex $seq $j] $x $y; incr nc_moved
  }
  # buffers: hopb[k] are the buffers on the D of (pc, seq[end], seq[end-1], ...) nearest-first
  set n [llength $seq]
  # (the head hop's buffers may be shared with other loads of the head: left where GPL put them)
  for {set k 0} {$k < min([llength $hopb], $n)} {incr k} {
    set bs [lindex $hopb $k]; set nb [llength $bs]; if {!$nb} continue
    set hopi [expr {$n - $k}]   ;# hop index: from position hopi to hopi+1 (sink side)
    for {set q 0} {$q < $nb} {incr q} {
      set bi [lindex $bs $q]; if {![nc_mov $bi]} continue
      set f [expr {($hopi + 1 - double($q+1)/($nb+1)) / $hops}]
      if {$f < 0} { set f 0 }
      lassign [nc_at $route $f] x y; nc_put $bi $x $y
    }
  }
  incr nc_chains
}
proc nc_pct {l p} { if {![llength $l]} { return na }; set l [lsort -real $l]; return [format %.0f [lindex $l [expr {min([llength $l]-1, int([llength $l]*$p))}]]] }
puts "OT_NK_CHAIN chains $nc_chains core_head_kept $nc_corefix stages_moved $nc_moved bends $nc_rc max_hop_um before p50 [nc_pct $nc_l0 0.5] p90 [nc_pct $nc_l0 0.9] max [nc_pct $nc_l0 1.0] after p50 [nc_pct $nc_l1 0.5] p90 [nc_pct $nc_l1 0.9] max [nc_pct $nc_l1 1.0]"
# CBF-R8-CORRIDOR: an INNER strap bank has a fixed common prefix, a selectable count bank and a final NK pipe.
# The mux is not a register chain: discover it by the kept bank identity, then verify ALL dynamic cone roots.
# Opt-in until the coherent extra PIN-cycle event and its PLACE pilot are accepted. No netlist/latency changes here.
if {[info exists ::env(OT_NK_R8_COUNT_CHAIN)] && $::env(OT_NK_R8_COUNT_CHAIN) eq "1"} {
proc nc_cnt_name {inst} { return [string map {\\ {}} [$inst getName]] }
proc nc_cnt_data_cone {it allowed} {
  set todo [list [$it getNet]]; set seen {}; set roots {}; set gates {}; set static {}; set bad {}
  for {set depth 0} {$depth < 80 && [llength $todo]} {incr depth} {
    set more {}
    foreach net $todo {
      if {$net eq "NULL" || $net eq "" || [dict exists $seen $net]} continue
      dict set seen $net 1
      foreach bt [$net getBTerms] {
        if {![string match "*strap_r8pad_*" [$bt getName]]} { lappend bad "non-count port [$bt getName]" } else { lappend static [$bt getName] }
      }
      foreach drv [$net getITerms] {
        if {![$drv isOutputSignal]} continue
        set di [$drv getInst]; set nm [nc_cnt_name $di]; set mn [[$di getMaster] getName]
        if {[dict exists $allowed $nm]} { dict set roots $nm $di; continue }
        if {[[$di getMaster] isBlock] || [string match "DFF*" $mn] || [string match "*LATCH*" $mn]} { lappend bad "unexpected data root $nm"; continue }
        if {[string match "TIE*" $mn] || [string match "*TIE*" $mn]} continue
        dict set gates $nm $di
        foreach ip [$di getITerms] { if {[$ip isInputSignal] && [$ip getNet] ne "NULL" && [[$ip getNet] getSigType] eq "SIGNAL"} { lappend more [$ip getNet] } }
      }
    }
    set todo $more
  }
  if {[llength $todo]} { lappend bad "count cone exceeds 80 logic levels" }
  return [list $roots $gates $static $bad]
}
# Keep shared static count-decode cells in their existing tree. Move only gates carrying this bit's data.
proc nc_cnt_dynamic_gates {roots gates} {
  set nets {}; set selected {}
  foreach nm [dict keys $roots] { foreach t [[dict get $roots $nm] getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } } }
  for {set pass 0} {$pass < 80} {incr pass} {
    set changed 0
    foreach nm [dict keys $gates] {
      if {[dict exists $selected $nm]} continue
      set i [dict get $gates $nm];set data 0
      foreach t [$i getITerms] { if {[$t isInputSignal] && [dict exists $nets [$t getNet]]} { set data 1 } }
      if {!$data} continue
      dict set selected $nm $i;set changed 1
      foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { dict set nets [$t getNet] 1 } }
    }
    if {!$changed} break
  }
  return $selected
}
proc nc_cnt_route_ok {pts} {
  for {set j 1} {$j < [llength $pts]} {incr j} { lassign [lindex $pts [expr {$j-1}]] a b; lassign [lindex $pts $j] c d; if {$a != $c && $b != $d} { return 0 } }
  return [nc_ok $pts]
}
proc nc_cnt_layout {route fixed span dbu} {
  if {$fixed < 2 || $span < 0 || $span > 16 || ![nc_cnt_route_ok $route]} { error "invalid count-bank corridor" }
  set hop [expr {[nc_len $route]/double($fixed)/$dbu}]
  if {$hop > 405.0} { error "NEED_PIN_CYCLE fixed=$fixed min_count_hop_um=$hop" }
  set fs {};set cs {}
  for {set j 1} {$j < $fixed} {incr j} { lappend fs [nc_at $route [expr {double($j)/$fixed}]] }
  for {set j 0} {$j < $span} {incr j} { lappend cs [nc_at $route [expr {(double($fixed-1)+double($j+1)/($span+1))/$fixed}]] }
  return [dict create max_hop_um $hop fixed $fs count $cs]
}
# Validate every bit before applying ANY of this pass's locations. An under-staged site cannot partially route.
proc nc_cnt_place {inst x y} { global nc_cnt_targets;dict set nc_cnt_targets $inst [list $x $y] }
set nc_cnt_targets {}
# Full banks need row area, not 514 near-coincident points on a route skeleton.
# Per-stage rectangles reserve conservative row demand; the final count/mux bank is shared
# so its data muxes cannot overlap the optional FF bank. Legalization remains mandatory.
proc nc_cnt_bank_add {group inst} { global nc_cnt_bank_groups;dict set nc_cnt_bank_groups $group $inst 1 }
proc nc_cnt_bank_grid {members targets dbu} {
  global nc_mac nc_core nc_halo
  set n [llength $members];set sx 0;set sy 0;set mw 0;set mh 0;set area 0
  foreach i $members {
    lassign [dict get $targets $i] x y;set sx [expr {$sx+$x}];set sy [expr {$sy+$y}]
    set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
    set mw [expr {max($mw,$w)}];set mh [expr {max($mh,$h)}];set area [expr {$area+$w*$h}]
  }
  set cols [expr {min(27,$n)}];set rows [expr {int(ceil(double($n)/$cols))}]
  set px [expr {$mw*1.25}];set py [expr {$mh*2.25}]
  set w [expr {($cols-1)*$px+$mw}];set h [expr {($rows-1)*$py+$mh}]
  set x [expr {$sx/double($n)-$w/2}];set y [expr {$sy/double($n)-$h/2}]
  set xs [list $x];set ys [list $y]
  foreach m $nc_mac {lassign $m a b c d;lappend xs [expr {$a-$nc_halo-$w}] [expr {$c+$nc_halo}];lappend ys [expr {$b-$nc_halo-$h}] [expr {$d+$nc_halo}]}
  set best {};set dist 1e100
  foreach xx $xs {foreach yy $ys {
    if {$xx<[$nc_core xMin] || $yy<[$nc_core yMin] || $xx+$w>[$nc_core xMax] || $yy+$h>[$nc_core yMax]} continue
    set ok 1;foreach m $nc_mac {lassign $m a b c d;if {$xx<$c+$nc_halo && $xx+$w>$a-$nc_halo && $yy<$d+$nc_halo && $yy+$h>$b-$nc_halo} {set ok 0;break}}
    set dd [expr {abs($xx-$x)+abs($yy-$y)}]
    if {$ok && $dd<$dist} {set best [list $xx $yy];set dist $dd}
  }}
  if {$best eq {} || $dist/double($dbu)>60.0} {error "bank rectangle cannot fit near corridor"}
  lassign $best x y;set out {};set k 0
  foreach i $members {dict set out $i [list [expr {$x+($k%$cols)*$px}] [expr {$y+int($k/$cols)*$py}]];incr k}
  return [dict create targets $out bbox [list $x $y [expr {$x+$w}] [expr {$y+$h}]] rows $rows occupancy [expr {$area/double($w*$h)}]]
}
set nc_cnt_bank_groups {};set nc_cnt_bit_paths {}
proc nc_cnt_hop_buffers {sink fa fb route} {
  set dp [nc_dpin $sink]; if {$dp eq ""} return
  lassign [nc_back $dp] _ bs; set n [llength $bs]
  for {set q 0} {$q < $n} {incr q} {
    set bi [lindex $bs $q]; if {![nc_mov $bi]} continue
    set f [expr {$fb - ($fb-$fa)*double($q+1)/($n+1)}]
    lassign [nc_at $route $f] x y; nc_cnt_place $bi $x $y
  }
}
proc nc_cnt_parse_name {nm} {
  # Singleton CBF types have ordinary fixed delays; Binder never invents an INNER count site.
  if {[regexp {^(.*u_d[0-9]+_u_t_1_2_t_out)[./]r\[([0-9]+)\]\[([0-9]+)\]} $nm _ bank st bit]} {return [list fixed $bank $st $bit]}
  if {[regexp {^(.*u_d[0-9]+_u_t_1_2_t_out)[./]q\[([0-9]+)\]} $nm _ bank bit]} {return [list fixedq $bank -1 $bit]}
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+)_f)[./]r\[([0-9]+)\]\[([0-9]+)\]} $nm _ bank site st bit]} { return [list fixed $bank $st $bit] }
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+)_f)[./]q\[([0-9]+)\]} $nm _ bank site bit]} { return [list fixedq $bank -1 $bit] }
  if {[regexp {^(.*u_r8b_(strap_r8pad_.+))[./]r\[([0-9]+)\]\[([0-9]+)\]} $nm _ bank site st bit] && ![string match "*_f" $bank]} { return [list count $bank $st $bit] }
  if {[regexp {^(.*u_pc_nk_.+)[./](?:r\[0\]\[|q\[)([0-9]+)\]} $nm _ bank bit]} { return [list pc $bank 0 $bit] }
  return {}
}
set nc_cnt_all {}; set nc_cnt_fixed {}; set nc_cnt_fixed_q {}; set nc_cnt_count {}; set nc_cnt_pc {}
foreach i [$nc_blk getInsts] {
  if {![string match "DFF*" [[$i getMaster] getName]]} continue
  set nm [nc_cnt_name $i]; dict set nc_cnt_all $nm $i
  set parsed [nc_cnt_parse_name $nm];if {![llength $parsed]} continue
  lassign $parsed kind bank st bit
  switch $kind {
    fixed { dict set nc_cnt_fixed $bank $bit $st $i }
    fixedq { dict set nc_cnt_fixed_q $bank $bit $i }
    count { dict set nc_cnt_count $bank $bit $st $i }
    pc { dict set nc_cnt_pc $bank $bit $i }
  }
}
# Yosys aliases the LAST fixed register to q[bit] (and the one-stage input pipe likewise). Include that stage.
foreach bank [dict keys $nc_cnt_fixed_q] {
  foreach bit [dict keys [dict get $nc_cnt_fixed_q $bank]] {
    set j 0
    if {[dict exists $nc_cnt_fixed $bank $bit]} { set j [dict size [dict get $nc_cnt_fixed $bank $bit]] }
    dict set nc_cnt_fixed $bank $bit $j [dict get $nc_cnt_fixed_q $bank $bit]
  }
}
set nc_cnt_chains 0; set nc_cnt_stages 0; set nc_cnt_mux 0; set nc_cnt_refused 0; set nc_cnt_worst 0; set nc_cnt_seen 0
foreach bank [dict keys $nc_cnt_fixed] {
  set plain_fixed 0;set filter_bank $bank
  if {[regexp {^(.*)u_r8b_strap_r8pad_(u_t_[0-9]+_[0-9]+)_(n_[ab])_in[0-9]*_f$} $bank _ scope rel port]} {
    set countbank [string range $bank 0 end-2];set pcbank ${scope}u_pc_nk_${rel}_${port}
  } elseif {[info exists ::env(OT_NK_CBF_FIXED_CHAIN)] && $::env(OT_NK_CBF_FIXED_CHAIN) eq "1" &&
      [regexp {^(.*)u_d[0-9]+_u_t_1_2_t_out$} $bank _ scope]} {
    set plain_fixed 1;set countbank "";set pcbank ${scope}u_pc_nk_u_t_0_2_n_b
    set filter_bank ${scope}u_r8b_strap_r8pad_u_t_0_2_n_b_in_f
  } else {continue}
  if {[info exists ::env(OT_NK_R8_COUNT_SITE_REGEX)] && ![regexp $::env(OT_NK_R8_COUNT_SITE_REGEX) $filter_bank]} continue
  foreach bit [dict keys [dict get $nc_cnt_fixed $bank]] {
    incr nc_cnt_seen
    set fixed [dict get $nc_cnt_fixed $bank $bit]; set n [dict size $fixed]
    if {$n < 2 || ![dict exists $nc_cnt_pc $pcbank $bit] || (!$plain_fixed && ![dict exists $nc_cnt_count $countbank $bit])} { incr nc_cnt_refused; continue }
    set counts {};if {!$plain_fixed} {set counts [dict get $nc_cnt_count $countbank $bit]}
    set span [dict size $counts];set seq {};set good 1
    for {set j 0} {$j < $n} {incr j} { if {![dict exists $fixed $j]} { set good 0; break }; lappend seq [dict get $fixed $j] }
    for {set j 0} {$j < $span} {incr j} { if {![dict exists $counts $j]} { set good 0; break } }
    if {!$good || (!$plain_fixed && $span < 1) || $span > 16} { incr nc_cnt_refused; continue }
    set first [lindex $seq 0]; set pc [dict get $nc_cnt_pc $pcbank $bit]
    # The improved core_input_anchor must have identified this real PC (including its generic QN inverter).
    # Its face-file identity survives release to PLACED before this hook; a floating old PC is not an endpoint.
    if {![dict exists $nc_face [$pc getName]]} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit missing_verified_core_input_anchor" }
      incr nc_cnt_refused;continue
    }
    # The hard source's first output register is the existing core_out_land anchor. Never move it or the input pipe.
    lassign [nc_back [nc_dpin $first]] source _
    if {$source eq "" || ![[[$source getInst] getMaster] isBlock]} { incr nc_cnt_refused; continue }
    set source_box [$source getBBox]
    lassign [nc_ctr $first] first_x first_y
    set source_gap [expr {(abs($first_x-([$source_box xMin]+[$source_box xMax])/2)+abs($first_y-([$source_box yMin]+[$source_box yMax])/2))/double($nc_dbu)}]
    if {$source_gap > 30.0} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit missing_verified_output_anchor gap_um $source_gap" }
      incr nc_cnt_refused;continue
    }
    set allowed [dict create [nc_cnt_name [lindex $seq end]] [lindex $seq end]]
    foreach j [dict keys $counts] { set ci [dict get $counts $j]; dict set allowed [nc_cnt_name $ci] $ci }
    lassign [nc_cnt_data_cone [nc_dpin $pc] $allowed] roots gates static bad
    if {[llength $bad] || [dict size $roots] != [dict size $allowed]} { incr nc_cnt_refused; continue }
    # Each optional-count register must itself be the actual serial chain fed from the fixed prefix.
    set previous [lindex $seq end]
    for {set j 0} {$j < $span} {incr j} {
      set ci [dict get $counts $j]; lassign [nc_back [nc_dpin $ci]] drv _
      if {$drv eq "" || [$drv getInst] ne $previous} { set good 0; break }; set previous $ci
    }
    if {!$good} { incr nc_cnt_refused; continue }
    lassign [nc_ctr $first] hx hy; lassign [nc_ctr $pc] tx ty
    set route [nc_route $hx $hy $tx $ty]; set hop [expr {[nc_len $route]/double($n)/$nc_dbu}]
    if {[catch {set layout [nc_cnt_layout $route $n $span $nc_dbu]} layout_error]} {
      if {$nc_cnt_refused < 8} { puts "OT_NK_R8_COUNT_REFUSE bank $bank bit $bit fixed $n count_span $span route_um [expr {[nc_len $route]/double($nc_dbu)}] min_count_hop_um $hop NEED_PIN_CYCLE" }
      incr nc_cnt_refused; continue
    }
    # Refuse conflicting firm sites; this pass never overrides a declared immutable placement.
    foreach i [lrange $seq 1 end] { if {![nc_mov $i]} { set good 0 } }
    foreach j [dict keys $counts] { if {![nc_mov [dict get $counts $j]]} { set good 0 } }
    if {!$good} { incr nc_cnt_refused; continue }
    for {set j 1} {$j < $n} {incr j} {
      set i [lindex $seq $j]; lassign [lindex [dict get $layout fixed] [expr {$j-1}]] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:fixed$j $i
      nc_cnt_hop_buffers $i [expr {double($j-1)/$n}] [expr {double($j)/$n}] $route
      incr nc_cnt_stages
    }
    for {set j 0} {$j < $span} {incr j} {
      set f [expr {(double($n-1)+double($j+1)/($span+1))/$n}]
      set i [dict get $counts $j]; lassign [lindex [dict get $layout count] $j] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:count_mux $i
      set prevf [expr {(double($n-1)+double($j)/($span+1))/$n}]
      nc_cnt_hop_buffers $i $prevf $f $route; incr nc_cnt_stages
    }
    # Count decode/mux and its buffers sit inside the final fixed->input hop. Quasi-static strap inputs remain pins.
    set gates [nc_cnt_dynamic_gates $roots $gates]
    set ng [dict size $gates]; set gi 0
    foreach nm [lsort [dict keys $gates]] {
      set i [dict get $gates $nm]; incr gi
      if {[nc_mov $i]} { set gf [expr {(double($n-1)+0.2+0.6*double($gi)/($ng+1))/$n}]; lassign [nc_at $route $gf] x y; nc_cnt_place $i $x $y;nc_cnt_bank_add ${bank}:count_mux $i; incr nc_cnt_mux }
    }
    set countseq {};foreach j [lsort -integer [dict keys $counts]] {lappend countseq [dict get $counts $j]}
    lappend nc_cnt_bit_paths [list $seq $countseq $pc]
    set nc_cnt_worst [expr {max($nc_cnt_worst,$hop)}]; incr nc_cnt_chains
  }
}
if {$nc_cnt_refused} {
  puts "OT_NK_R8_COUNT_BLOCKED eligible_bits $nc_cnt_seen planned_bits $nc_cnt_chains placed_bits 0 refused_bits $nc_cnt_refused"
  error "CBF count-bank corridor requires a coherent PIN-cycle/site event; no locations from this pass applied"
}
set nc_cnt_rects {};set nc_cnt_bank_report {};set nc_cnt_inst_bank {}
foreach group [dict keys $nc_cnt_bank_groups] {
  set members [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} [dict keys [dict get $nc_cnt_bank_groups $group]]]
  set z [nc_cnt_bank_grid $members $nc_cnt_targets $nc_dbu]
  lassign [dict get $z bbox] a b c d
  foreach prev [dict keys $nc_cnt_rects] {
    lassign [dict get $nc_cnt_rects $prev] aa bb cc dd
    if {$a<$cc && $c>$aa && $b<$dd && $d>$bb} {error "overlapping corridor bank rectangles: $group $prev"}
  }
  dict set nc_cnt_rects $group [dict get $z bbox]
  foreach i [dict keys [dict get $z targets]] {dict set nc_cnt_targets $i [dict get $z targets $i];dict set nc_cnt_inst_bank $i $group}
  lappend nc_cnt_bank_report [list $group [llength $members] [dict get $z rows] [dict get $z occupancy] [dict get $z bbox]]
}
proc nc_cnt_target_ctr {inst} {global nc_cnt_targets;if {[dict exists $nc_cnt_targets $inst]} {return [dict get $nc_cnt_targets $inst]};return [nc_ctr $inst]}
proc nc_cnt_envelope {inst} {
  global nc_cnt_inst_bank nc_cnt_rects
  if {![dict exists $nc_cnt_inst_bank $inst]} {return [list [nc_cnt_target_ctr $inst]]}
  lassign [dict get $nc_cnt_rects [dict get $nc_cnt_inst_bank $inst]] a b c d
  return [list [list $a $b] [list $a $d] [list $c $b] [list $c $d]]
}
set nc_cnt_spread_worst 0;set nc_cnt_envelope_worst 0;set nc_cnt_pair_seen {}
foreach bitpath $nc_cnt_bit_paths {
  lassign $bitpath fs cs pc
  # Both the minimum-count bypass and every selected-count serial hop must fit.
  set pairs {};set prev [lindex $fs 0]
  foreach i [concat [lrange $fs 1 end] [list $pc]] {lappend pairs [list $prev $i];set prev $i}
  set prev [lindex $fs end];foreach i [concat $cs [list $pc]] {lappend pairs [list $prev $i];set prev $i}
  foreach pair $pairs {
    lassign $pair src dst;lassign [nc_cnt_target_ctr $src] hx hy;lassign [nc_cnt_target_ctr $dst] tx ty
    set route [nc_route $hx $hy $tx $ty];set hop [expr {[nc_len $route]/double($nc_dbu)}]
    if {![nc_cnt_route_ok $route] || $hop>405.0} {error "bank spread exceeds macro-clear hop bound: $hop um"}
    set nc_cnt_spread_worst [expr {max($nc_cnt_spread_worst,$hop)}]
    set sk $src;set dk $dst
    if {[dict exists $nc_cnt_inst_bank $src]} {set sk [dict get $nc_cnt_inst_bank $src]}
    if {[dict exists $nc_cnt_inst_bank $dst]} {set dk [dict get $nc_cnt_inst_bank $dst]}
    if {![dict exists $nc_cnt_pair_seen [list $sk $dk]]} {
      dict set nc_cnt_pair_seen [list $sk $dk] 1
      foreach sp [nc_cnt_envelope $src] {foreach dp [nc_cnt_envelope $dst] {
        lassign $sp x y;lassign $dp xx yy;set er [nc_route $x $y $xx $yy];set eh [expr {[nc_len $er]/double($nc_dbu)}]
        if {![nc_cnt_route_ok $er] || $eh>405.0} {error "bank corner envelope exceeds macro-clear hop bound: $eh um"}
        set nc_cnt_envelope_worst [expr {max($nc_cnt_envelope_worst,$eh)}]
      }}
    }
  }
}
foreach row $nc_cnt_bank_report {puts "OT_NK_R8_BANK group_cells_rows_occupancy_bbox_dbu $row"}
puts "OT_NK_R8_BANK_HOPS max_um $nc_cnt_spread_worst rectangle_corner_envelope_um $nc_cnt_envelope_worst"
foreach inst [dict keys $nc_cnt_targets] { lassign [dict get $nc_cnt_targets $inst] x y;nc_put $inst $x $y }
puts "OT_NK_R8_COUNT_CHAIN eligible_bits $nc_cnt_seen placed_bits $nc_cnt_chains stages_moved $nc_cnt_stages mux_cells_moved $nc_cnt_mux refused_bits $nc_cnt_refused min_count_max_hop_um $nc_cnt_worst"
}
}
