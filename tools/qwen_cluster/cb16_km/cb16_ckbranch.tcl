# CODEX-CB16 2026-10-21: shared regional binary clock branches.
# Reuse the committed child-insertion tables, macro channel geometry, leaf tracing,
# and measured arrival reader. No RTL, clock-port, exception or schedule changes.
# The ring coordinate describes free channels, NOT a serial distribution ring.
# Each subtree shares its feed; local sibling compensation precedes one shared
# compensation per region. Never copy the global insertion deficit to every leaf.
source /src/tools/qwen_cluster/cb16_km/cb16_ckring3.tcl

proc ot_ckb_route {name master R from to drv} {
  set P [expr {2.0 * ([lindex $R 2]-[lindex $R 0]+[lindex $R 3]-[lindex $R 1])}]
  set d [expr {fmod($to-$from+2*$P,$P)}]
  if {$d > $P/2} {set d [expr {$d-$P}]}
  # Coincident branch points need no wire repeater. The node itself already
  # provides the binary split; adding another stage here creates artificial depth.
  if {abs($d) < 0.01} {return $drv}
  set n [expr {max(1,int(ceil(abs($d)/[ot_ckr_env OT_CKR_STEP_UM 150.0])))}]
  for {set k 1} {$k <= $n} {incr k} {
    set drv [ot_ckr_chainbuf ${name}_w$k $master $R [expr {$from+$d*$k/double($n)}] $drv]
  }
  return $drv
}
proc ot_ckb_node {port R members from drv} {
  set id [incr ::ot_ckb_id]
  set name ot_ckb_${port}_n$id
  set mids [lsort -real [lmap m $members {lindex $m 3}]]
  set mid [lindex $mids [expr {[llength $mids]/2}]]
  set mb [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx16f_ASAP7_75t_R]]
  set mr [[ord::get_db] findMaster [ot_ckr_env OT_CKR_ROOT BUFx8_ASAP7_75t_R]]
  set drv [ot_ckb_route $name $mb $R $from $mid $drv]
  lassign [ot_ckr_ring_pt $R $mid] x y side
  lassign [ot_ckr_mkbuf $name $mr $x $y] b net
  [$b findITerm A] connect $drv
  dict set ::ot_ckb_side $name $side
  set xs [lsort -real [lmap m $members {lindex $m 1}]]
  set ys [lsort -real [lmap m $members {lindex $m 2}]]
  set ins [lsort -real [lmap m $members {lindex $m 4}]]
  set span [expr {[lindex $xs end]-[lindex $xs 0]+[lindex $ys end]-[lindex $ys 0]}]
  set ispan [expr {[lindex $ins end]-[lindex $ins 0]}]
  if {[llength $members] == 1 || ($span <= [ot_ckr_env OT_CKR_DMAX_UM 150.0] && $ispan <= 30.0 && [llength $members] <= 8)} {
    foreach m $members {set it [lindex $m 0]; $it disconnect; $it connect $net}
    dict set ::ot_ckr_grp $name [list $port $side]
    dict set ::ot_ckb_children $name {}
    return $name
  }
  # Spatial order keeps siblings beside each other. Split on child insertion
  # when locations coincide, so a hard child never drags a distant soft cluster.
  if {$span < 1.0} {set sorted [lsort -real -index 4 $members]} else {set sorted [lsort -real -index 3 $members]}
  set half [expr {[llength $sorted]/2}]
  set left [ot_ckb_node $port $R [lrange $sorted 0 [expr {$half-1}]] $mid $net]
  set right [ot_ckb_node $port $R [lrange $sorted $half end] $mid $net]
  dict set ::ot_ckb_children $name [list $left $right]
  return $name
}
proc ot_ckr_build {port ignored} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set plan $::ot_ckr_plan($port); set R [dict get $plan R]
  set pnet [[$blk findBTerm $port] getNet]; set members {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    if {[[[$it getInst] getMaster] isBlock]} {
      set b [$it getBBox]; set x [expr {([$b xMin]+[$b xMax])/2.0/$u}]; set y [expr {([$b yMin]+[$b yMax])/2.0/$u}]
    } else {lassign [[$it getInst] getLocation] x y; set x [expr {$x/double($u)}]; set y [expr {$y/double($u)}]}
    lappend members [list $it $x $y [ot_ckr_ring_s $R $x $y] [ot_ckr_child_ins $it]]
  }
  if {![llength $members]} {error "CKB: no sinks for $port"}
  set mb [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx16f_ASAP7_75t_R]]
  set drv $pnet; set k 0
  foreach p [dict get $plan tr] {
    lassign [ot_ckr_mkbuf ot_ckb_${port}_tr[incr k] $mb {*}$p] b nn
    [$b findITerm A] connect $drv; set drv $nn
  }
  set before [dict size $::ot_ckr_grp]
  set root [ot_ckb_node $port $R $members [dict get $plan sE] $drv]
  dict set ::ot_ckb_roots $port $root
  puts "CKB BUILD $port sinks=[llength $members] leaves=[expr {[dict size $::ot_ckr_grp]-$before}] shared_root=$root trunk=$k"
}
# Reconnect a whole subtree at its input, so one correction is shared by all of
# its leaf roots. Original pad helper also follows any CTS clones of the node.
proc ot_ckb_pad {node count master hop} {
  set added 0
  if {![dict exists $::ot_ckr_grp $node]} {
    dict set ::ot_ckr_grp $node [list shared [dict get $::ot_ckb_side $node]]
    set added 1
  }
  ot_ckr_pad $node $count $master $hop
  if {$added} {dict unset ::ot_ckr_grp $node}
}
proc ot_ckb_need {node arrivals} {
  set kids [dict get $::ot_ckb_children $node]
  if {![llength $kids]} {return [dict get $arrivals $node]}
  set vals {}; set t -1e30; set f -1e30
  foreach child $kids {
    set v [ot_ckb_need $child $arrivals]; lappend vals $v
    set t [expr {max($t,[lindex $v 0])}]; set f [expr {max($f,[lindex $v 1])}]
  }
  foreach child $kids v $vals {ot_ckb_request $child $t $f $v}
  return [list $t $f]
}
proc ot_ckb_request {node t f v} {
  # TT + recorded FF estimate is guidance only; final gate independently checks
  # real TT/FF arrivals at hard-child flops. Acceptance thresholds are unchanged.
  set need [expr {0.5*($t-[lindex $v 0])+0.5*($f-[lindex $v 1])/$::ot_ckb_rho}]
  if {$need > [ot_ckr_env OT_CKR_TOL_PS 15.0]} {dict set ::ot_ckb_requests $node $need}
}
proc ot_ckr_balance {{iterations ""} {mode coarse}} {
  set blk [ord::get_db_block]; set ::ot_ckr_leaf [dict create]
  dict for {g pl} $::ot_ckr_grp {
    set pins {}
    foreach i [ot_ckr_gdrv $g] {foreach o [$i getITerms] {
      if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {lappend pins {*}[ot_ckr_leafpins [$o getNet]]}
    }}
    dict set ::ot_ckr_leaf $g $pins
  }
  set_propagated_clock [all_clocks]
  set limit [ot_ckr_env OT_CKR_ITERS 12]; if {$iterations ne ""} {set limit $iterations}
  set coarse [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx16f_ASAP7_75t_R]]
  set fine [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
  set prev {}; set previous {}; set stage 45.0; set fstage 12.0; set ::ot_ckb_rho 0.75
  for {set iteration 0} {$iteration <= $limit} {incr iteration} {
    set a [ot_ckr_arrivals]
    # Learn the effect at descendants of each corrected branch (not at all
    # groups). Simultaneous nested pads are accounted for by ancestor counts.
    if {[dict size $previous]} {
      set gl {}; set ratios {}
      dict for {leaf v} $a {
        set c 0; set n $leaf
        while {$n ne ""} {
          if {[dict exists $previous $n]} {incr c [dict get $previous $n]}
          set n [expr {[dict exists $::ot_ckb_parent $n] ? [dict get $::ot_ckb_parent $n] : ""}]
        }
        if {!$c} continue
        set dt [expr {[lindex $v 0]-[lindex [dict get $prev $leaf] 0]}]
        set df [expr {[lindex $v 1]-[lindex [dict get $prev $leaf] 1]}]
        if {$dt > 1.0} {lappend gl [expr {$dt/$c}]; lappend ratios [expr {$df/$dt}]}
      }
      set learned [expr {max(3.0,[ot_ckr_med $gl 12.0])}]
      if {$mode eq "coarse"} {set stage $learned} else {set fstage $learned}
      set ::ot_ckb_rho [expr {min(1.0,max(0.2,[ot_ckr_med $ratios $::ot_ckb_rho]))}]
    }
    set ::ot_ckb_requests {}; set rootvals {}; set t -1e30; set f -1e30
    dict for {port node} $::ot_ckb_roots {
      set v [ot_ckb_need $node $a]; dict set rootvals $node $v
      set t [expr {max($t,[lindex $v 0])}]; set f [expr {max($f,[lindex $v 1])}]
    }
    dict for {node v} $rootvals {ot_ckb_request $node $t $f $v}
    puts "CKB BALANCE iteration=$iteration mode=$mode leaf_groups=[dict size $a] shared_corrections=[dict size $::ot_ckb_requests] pads=$::ot_ckr_npad target_tt=$t target_ff_est=$f"
    if {$iteration == $limit || ![dict size $::ot_ckb_requests]} break
    set prev $a; set previous {}
    dict for {node need} $::ot_ckb_requests {
      set st [expr {$mode eq "coarse" ? $stage : $fstage}]
      set count [expr {min(4,max(0,int(floor(0.8*$need/$st))))}]
      if {!$count} continue
      ot_ckb_pad $node $count [expr {$mode eq "coarse" ? $coarse : $fine}] [expr {$mode eq "coarse" ? [ot_ckr_env OT_CKR_STEP_UM 150.0] : 0.0}]
      dict set previous $node $count
    }
    if {![dict size $previous]} break
  }
  detailed_placement
}
# Initialize before the inherited CTS wrapper plans/builds regional trees.
set ::ot_ckb_id 0
set ::ot_ckb_children {}; set ::ot_ckb_side {}; set ::ot_ckb_roots {}; set ::ot_ckb_parent {}
# Record parents as the recursive builder returns; needed only by gain learning.
rename ot_ckb_node ot_ckb_node_impl
proc ot_ckb_node {args} {
  set node [ot_ckb_node_impl {*}$args]
  foreach child [dict get $::ot_ckb_children $node] {dict set ::ot_ckb_parent $child $node}
  return $node
}
