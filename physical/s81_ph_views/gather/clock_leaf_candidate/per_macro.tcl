# Candidate only: eight actual SRAM clock pins each get one real local BUF.
# Loaded by pre_cts_extra after the deployed CTS wrappers, no shared mutations.
proc s81_mc_local_leaves {} {
 set b [ord::get_db_block];set tech [ord::get_db_tech];set dbu [$tech getDbUnitsPerMicron]
 set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
 if {$master eq "NULL"} {error "S81_MACRO_LEAF missing genuine clock buffer"}
 set width [$master getWidth];set height [$master getHeight]
 set rows {};set occupancy {}
 foreach row [$b getRows] {
  lassign [$row getOrigin] ox oy
  set bb [$row getBBox]
  dict lappend rows $oy [list $ox [$bb xMin] [$bb xMax] [$row getOrient] [[$row getSite] getWidth] [[$row getSite] getHeight]]
 }
 foreach inst [$b getInsts] {
  if {[$inst getPlacementStatus] eq "UNPLACED"} continue
  set bb [$inst getBBox];set halo [expr {[[$inst getMaster] isBlock] ? round(5.4*$dbu) : 0}]
  dict for {ry segments} $rows {
   if {$ry+$height>[$bb yMin]-$halo && $ry<[$bb yMax]+$halo} {
    dict lappend occupancy $ry [list [expr {[$bb xMin]-$halo}] [expr {[$bb xMax]+$halo}]]
   }
  }
 }
 set actual {}
 foreach inst [$b getInsts] {dict set actual [string map {\\ ""} [$inst getName]] $inst}
 set report [open $::env(RESULTS_DIR)/s81_macro_local_leaves.tsv w]
 puts $report "macro\tclock_pin\told_clock_net\tnew_buffer\tnew_net\tx_um\ty_um\tBUF_Y_to_macro_CLK_manhattan_um"
 set count 0
 foreach root {0 1 2 3} {
  foreach role {bm qm} {
   set path [expr {$role eq "bm" ? "u_l.g_r\[$root\].u_root.u_bm.genblk1.genblk1.g_b8.u_m" : "u_l.g_r\[$root\].u_root.u_qm.g_q.u_m"}]
   if {![dict exists $actual $path]} {error "S81_MACRO_LEAF missing exact assigned macro $path"}
   set macro [dict get $actual $path];set pin [$macro findITerm clk]
   if {$pin eq "NULL" || ![$pin isInputSignal]} {error "S81_MACRO_LEAF missing actual macro clock input $path/clk"}
   set old [$pin getNet];if {$old eq "NULL" || [$old getSigType] ne "CLOCK"} {error "S81_MACRO_LEAF unconstrained actual clock $path/clk"}
   set name s81_macro_clock_leaf_${root}_${role}
   if {[$b findInst $name] ne "NULL"} {error "S81_MACRO_LEAF refuses duplicate topology $name"}
   lassign [$pin getAvgXY] valid px py;if {!$valid} {error "S81_MACRO_LEAF no actual clock geometry"}
   set best {};set best_score 1e30
   dict for {ry segments} $rows {
    set blocked [expr {[dict exists $occupancy $ry] ? [lsort -integer -index 0 [dict get $occupancy $ry]] : {}}]
    foreach segment $segments {
     lassign $segment ox left right orient sitew siteh
     if {$height!=$siteh} continue
     set cursor $left;set gaps {}
     foreach interval $blocked {
      lassign $interval a z
      if {$z<=$cursor || $a>=$right} continue
      if {$a>$cursor} {lappend gaps [list $cursor [expr {min($a,$right)}]]}
      set cursor [expr {max($cursor,$z)}]
      if {$cursor>=$right} break
     }
     if {$cursor<$right} {lappend gaps [list $cursor $right]}
     foreach gap $gaps {
      lassign $gap a z
      set first [expr {int(ceil(($a-$ox)/double($sitew)))}]
      set last [expr {int(floor(($z-$width-$ox)/double($sitew)))}]
      if {$first>$last} continue
      set site [expr {max($first,min($last,int(round(($px-$width/2.0-$ox)/$sitew))))}]
      set x [expr {$ox+$site*$sitew}]
      set score [expr {abs($x+$width/2.0-$px)+abs($ry+$height/2.0-$py)}]
      if {$score<$best_score} {set best_score $score;set best [list $x $ry $orient]}
     }
    }
   }
   if {![llength $best] || $best_score>20*$dbu} {error "S81_MACRO_LEAF no native unoccupied site within20um $path ($best_score DBU)"}
   lassign $best x y orient
   set inst [odb::dbInst_create $b $master $name];$inst setOrient $orient;$inst setLocation $x $y;$inst setPlacementStatus FIRM
   set input [$inst findITerm A];set output [$inst findITerm Y]
   if {$input eq "NULL" || $output eq "NULL"} {error "S81_MACRO_LEAF unexpected actual buffer ABI"}
   set net [odb::dbNet_create $b ${name}_clock];$net setSigType CLOCK
   $pin disconnect;$input connect $old;$output connect $net;$pin connect $net
   set_dont_touch [get_cells $name]
   dict lappend occupancy $y [list $x [expr {$x+$width}]]
   lassign [$output getAvgXY] valid qx qy
   set distance [expr {(abs($qx-$px)+abs($qy-$py))/double($dbu)}]
   puts $report "$path\tclk\t[$old getName]\t$name\t[$net getName]\t[expr {$x/double($dbu)}]\t[expr {$y/double($dbu)}]\t$distance"
   incr count
  }
 }
 close $report
 if {$count!=8} {error "S81_MACRO_LEAF expected8 real physical clock leaf buffers, got$count"}
 puts "S81_MACRO_LEAF actual8 macroCLK pins now each have one genuine BUFx24 native site; source clock/period/uncertainties unchanged"
}
if {[info commands s81_mc_original_cts] ne ""} {error "S81_MACRO_LEAF refuses duplicate wrapper"}
rename clock_tree_synthesis s81_mc_original_cts
proc clock_tree_synthesis {args} {
 uplevel 1 [list s81_mc_original_cts {*}$args]
 s81_mc_local_leaves
}
