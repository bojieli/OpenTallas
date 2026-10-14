# Genuine forwarding FFs: select a legal native site/row with BOTH actual
# D/input and Q/output Manhattan distances <=100um. Refuse if none exists.
# No extra state, pin change, epoch, center-distance proxy, or threshold waiver.
set mp_block [ord::get_db_block]
set mp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set mp_limit [expr {100*$mp_dbu}]
set mp_map [dict create]
foreach mp_inst [$mp_block getInsts] {
  if {![[$mp_inst getMaster] isSequential]} continue
  regsub -all {\\} [$mp_inst getName] {} mp_name
  if {[regexp {^u_l\.lo\[([0-9]+)\]\$_DFF} $mp_name -> mp_bit]} {
    set mp_key "lo\[$mp_bit\]"
  } elseif {[regexp {^u_l\.co(?:_state)?\[([0-9]+)\]\$_DFF} $mp_name -> mp_bit] && $mp_bit>=212} {
    set mp_key "co\[$mp_bit\]"
  } else {continue}
  if {[dict exists $mp_map $mp_key]} {error "S81_DQ_SITE duplicate used forwarding role $mp_key"}
  dict set mp_map $mp_key $mp_inst
  $mp_inst setDoNotTouch 0
  $mp_inst setPlacementStatus PLACED
}
if {[dict size $mp_map]!=1464} {error "S81_DQ_SITE expected1464 used forwarding FFs, got[dict size $mp_map]"}
set mp_rows [dict create];set mp_segments [dict create]
foreach mp_row [$mp_block getRows] {
  lassign [$mp_row getOrigin] mp_ox mp_oy
  set mp_bb [$mp_row getBBox]
  dict set mp_rows $mp_oy [list [$mp_row getOrient] [[$mp_row getSite] getWidth] [[$mp_row getSite] getHeight]]
  dict lappend mp_segments $mp_oy [list [$mp_bb xMin] [$mp_bb xMax] $mp_ox]
}
# Native row-indexed obstacles: unchanged macro halos and every already-FIRM
# boundary stage/other input-output FF. Add each chosen forwarding footprint.
set mp_obstacles {}
foreach mp_inst [$mp_block getInsts] {
  set mp_master [$mp_inst getMaster];set mp_status [$mp_inst getPlacementStatus]
  if {[$mp_master isBlock]} {
    set mp_bb [$mp_inst getBBox];set mp_halo [expr {round(5.4*$mp_dbu)}]
    lappend mp_obstacles [list [expr {[$mp_bb xMin]-$mp_halo}] [expr {[$mp_bb yMin]-$mp_halo}] [expr {[$mp_bb xMax]+$mp_halo}] [expr {[$mp_bb yMax]+$mp_halo}]]
  } elseif {$mp_status in {FIRM LOCKED}} {
    set mp_bb [$mp_inst getBBox];lappend mp_obstacles [list [$mp_bb xMin] [$mp_bb yMin] [$mp_bb xMax] [$mp_bb yMax]]
  }
}
foreach mp_obs [$mp_block getBlockages] {
  if {[$mp_obs isSoft]} continue
  if {[catch {$mp_obs getMaxDensity} mp_density]==0 && $mp_density>0 && $mp_density<100} continue
  set mp_bb [$mp_obs getBBox];lappend mp_obstacles [list [$mp_bb xMin] [$mp_bb yMin] [$mp_bb xMax] [$mp_bb yMax]]
}
set mp_busy [dict create]
foreach mp_oy [dict keys $mp_rows] {
  lassign [dict get $mp_rows $mp_oy] mp_or mp_sw mp_rh
  foreach mp_box $mp_obstacles {
    lassign $mp_box x0 y0 x1 y1
    if {$mp_oy<$y1 && $mp_oy+$mp_rh>$y0} {dict lappend mp_busy $mp_oy [list $x0 $x1]}
  }
}
set mp_report_file [expr {[info exists ::env(S81_MIDPOINT_REPORT)] ? $::env(S81_MIDPOINT_REPORT) : "/work/s81_midpoint_anchor.tsv"}]
set mp_report [open $mp_report_file w]
puts $mp_report "output\tinput\tflop\tmaster\torient\tx_um\ty_um\tD_x_um\tD_y_um\tQ_x_um\tQ_y_um\tinput_D_manhattan_um\tQ_output_manhattan_um"
set mp_keep [open $::env(RESULTS_DIR)/s81_midpoint_used_cells.txt w]
set mp_pin_cache [dict create];set mp_worst 0.0
# EW windows are narrower: allocate them first in actual bit/ordinate order,
# then let the more flexible N/S forwarding roles use remaining legal rows.
set mp_order {}
for {set bit 0} {$bit<828} {incr bit} {lappend mp_order "lo\[$bit\]"}
for {set bit 212} {$bit<848} {incr bit} {lappend mp_order "co\[$bit\]"}
foreach mp_key $mp_order {
  set mp_inst [dict get $mp_map $mp_key];set mp_master [$mp_inst getMaster]
  regexp {^(lo|co)\[([0-9]+)\]$} $mp_key -> mp_kind mp_bit
  if {$mp_kind eq "lo"} {set mp_input "li\[[expr {$mp_bit+276}]\]"} else {set mp_input "ci\[[expr {$mp_bit-212}]\]"}
  set mp_a [[$mp_block findBTerm $mp_input] getBBox];set mp_b [[$mp_block findBTerm $mp_key] getBBox]
  set ax [expr {([$mp_a xMin]+[$mp_a xMax])/2.0}];set ay [expr {([$mp_a yMin]+[$mp_a yMax])/2.0}]
  set bx [expr {([$mp_b xMin]+[$mp_b xMax])/2.0}];set by [expr {([$mp_b yMin]+[$mp_b yMax])/2.0}]
  set w [$mp_master getWidth];set h [$mp_master getHeight]
  set tx [expr {($ax+$bx-$w)/2.0}];set ty [expr {($ay+$by-$h)/2.0}]
  if {$mp_kind eq "lo"} {set tx [expr {$tx+($mp_bit%4-1.5)*($w+round(.216*$mp_dbu))}]} else {set ty [expr {$ty+($mp_bit%21-10)*round(.27*$mp_dbu)}]}
  set best {};set best_score 1e30
  set ranked_rows {}
  foreach ry [dict keys $mp_rows] {lappend ranked_rows [list [expr {abs($ry-$ty)}] $ry]}
  foreach row_rank [lsort -real -index 0 $ranked_rows] {
    lassign $row_rank row_distance oy
    if {$row_distance>$best_score} break
    lassign [dict get $mp_rows $oy] orient sw rh
    if {$h!=$rh} {error "S81_DQ_SITE non-single-row forwarding master [$mp_master getName]"}
    if {abs($oy-$ty)>40*$mp_dbu} continue
    set cache_key "[$mp_master getName]/$orient"
    if {![dict exists $mp_pin_cache $cache_key]} {
      $mp_inst setOrient $orient;$mp_inst setLocation 0 0
      set dp [$mp_inst findITerm D];set qp [$mp_inst findITerm QN]
      if {$qp eq "NULL"} {set qp [$mp_inst findITerm Q]}
      if {$dp eq "NULL" || $qp eq "NULL"} {error "S81_DQ_SITE missing D/Q $mp_key"}
      lassign [$dp getAvgXY] ok dx dy;if {!$ok} {error "S81_DQ_SITE missing D rectangle center $mp_key"}
      lassign [$qp getAvgXY] ok qx qy;if {!$ok} {error "S81_DQ_SITE missing Q rectangle center $mp_key"}
      dict set mp_pin_cache $cache_key [list $dx $dy $qx $qy]
    }
    lassign [dict get $mp_pin_cache $cache_key] dx dy qx qy
    set xd [expr {$mp_limit-abs($oy+$dy-$ay)}];set xq [expr {$mp_limit-abs($oy+$qy-$by)}]
    if {$xd<0 || $xq<0} continue
    set low [expr {max($ax-$dx-$xd,$bx-$qx-$xq)}];set high [expr {min($ax-$dx+$xd,$bx-$qx+$xq)}]
    if {$low>$high} continue
    foreach segment [dict get $mp_segments $oy] {
      lassign $segment x0 x1 origin
      set first [expr {int(ceil((max($low,$x0)-$origin)/double($sw)))}]
      set last [expr {int(floor((min($high,$x1-$w)-$origin)/double($sw)))}]
      if {$first>$last} continue
      set near [expr {min($last,max($first,int(round(($tx-$origin)/double($sw)))))}]
      set candidates {}
      for {set radius 0} {$radius<=max($near-$first,$last-$near)} {incr radius} {
        set candidates [list [expr {$near-$radius}]]
        if {$radius>0} {lappend candidates [expr {$near+$radius}]}
        if {max(0,$radius*$sw-abs($origin+$near*$sw-$tx))+$row_distance>$best_score && $radius>1} break
        foreach site $candidates {
        if {$site<$first || $site>$last} continue
        set x [expr {$origin+$site*$sw}];set blocked 0
        if {[dict exists $mp_busy $oy]} {
          foreach interval [dict get $mp_busy $oy] {
            lassign $interval u v
            if {$x<$v && $x+$w>$u} {set blocked 1;break}
          }
        }
        if {$blocked} continue
        set md [expr {abs($x+$dx-$ax)+abs($oy+$dy-$ay)}];set mq [expr {abs($x+$qx-$bx)+abs($oy+$qy-$by)}]
        if {$md>$mp_limit || $mq>$mp_limit} continue
        set score [expr {abs($x-$tx)+abs($oy-$ty)+.001*max($md,$mq)}]
        if {$score<$best_score} {set best_score $score;set best [list $x $oy $orient $dx $dy $qx $qy $md $mq]}
        }
      }
    }
  }
  if {$best eq {}} {error "S81_DQ_SITE no legal row/site satisfying BOTH100um D/Q windows for $mp_input->$mp_key"}
  lassign $best x y orient dx dy qx qy md mq
  $mp_inst setOrient $orient;$mp_inst setLocation $x $y
  $mp_inst setPlacementStatus FIRM
  dict lappend mp_busy $y [list $x [expr {$x+$w}]]
  set mp_worst [expr {max($mp_worst,$md/double($mp_dbu),$mq/double($mp_dbu))}]
  puts $mp_keep [$mp_inst getName]
  puts $mp_report "$mp_key\t$mp_input\t[$mp_inst getName]\t[$mp_master getName]\t$orient\t[expr {$x/double($mp_dbu)}]\t[expr {$y/double($mp_dbu)}]\t[expr {($x+$dx)/double($mp_dbu)}]\t[expr {($y+$dy)/double($mp_dbu)}]\t[expr {($x+$qx)/double($mp_dbu)}]\t[expr {($y+$qy)/double($mp_dbu)}]\t[expr {$md/double($mp_dbu)}]\t[expr {$mq/double($mp_dbu)}]"
}
close $mp_report;close $mp_keep
puts "S81_DQ_SITE selected1464 legal used FF sites/rows, both actual D/Q windows<=100um, max $mp_worst um; FIRM (reset remains repairable), no extra state/epoch. CTS verification remains required."
