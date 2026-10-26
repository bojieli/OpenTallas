# Source-owned landing placement fences. Release before DPL/CTS with lp_fence_release.tcl.
# Twelve actual D2/K1 pairs; each writer/read pair shares a column in its two regional bands.
set ::lpf_blk [ord::get_db_block]
set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]
array set ::lpf_g {}
array set ::lpf_n {}
array set ::lpf_c {}
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_0"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(507.6*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}]
set ::lpf_g(lk_0) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_0"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_0"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(572.4*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}]
set ::lpf_g(mid_0) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_0"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_1"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(507.6*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}]
set ::lpf_g(lk_1) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_1"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_1"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(572.4*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}]
set ::lpf_g(mid_1) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_1"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_2"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(507.6*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}]
set ::lpf_g(lk_2) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_2"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_2"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(572.4*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}]
set ::lpf_g(mid_2) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_2"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_3"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(507.6*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}]
set ::lpf_g(lk_3) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_3"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_3"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(572.4*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}]
set ::lpf_g(mid_3) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_3"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_4"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}]
set ::lpf_g(lk_4) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_4"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_4"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}]
set ::lpf_g(mid_4) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_4"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_5"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}]
set ::lpf_g(lk_5) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_5"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_5"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}]
set ::lpf_g(mid_5) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_5"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_6"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}]
set ::lpf_g(lk_6) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_6"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_6"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}]
set ::lpf_g(mid_6) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_6"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_7"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(522.0*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}]
set ::lpf_g(lk_7) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_7"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_7"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(586.8*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}]
set ::lpf_g(mid_7) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_7"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_8"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(550.8*$::lpf_dbu)}]
set ::lpf_g(lk_8) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_8"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_8"]
odb::dbBox_create $::lpf_r [expr {round(54.0*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}] [expr {round(145.8*$::lpf_dbu)}] [expr {round(615.6*$::lpf_dbu)}]
set ::lpf_g(mid_8) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_8"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_9"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(550.8*$::lpf_dbu)}]
set ::lpf_g(lk_9) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_9"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_9"]
odb::dbBox_create $::lpf_r [expr {round(145.8*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}] [expr {round(237.6*$::lpf_dbu)}] [expr {round(615.6*$::lpf_dbu)}]
set ::lpf_g(mid_9) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_9"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_10"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(550.8*$::lpf_dbu)}]
set ::lpf_g(lk_10) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_10"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_10"]
odb::dbBox_create $::lpf_r [expr {round(237.6*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}] [expr {round(329.4*$::lpf_dbu)}] [expr {round(615.6*$::lpf_dbu)}]
set ::lpf_g(mid_10) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_10"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_11"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(536.4*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(550.8*$::lpf_dbu)}]
set ::lpf_g(lk_11) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_11"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_11"]
odb::dbBox_create $::lpf_r [expr {round(329.4*$::lpf_dbu)}] [expr {round(601.2*$::lpf_dbu)}] [expr {round(421.2*$::lpf_dbu)}] [expr {round(615.6*$::lpf_dbu)}]
set ::lpf_g(mid_11) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_11"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_rst"]
odb::dbBox_create $::lpf_r [expr {round(432*$::lpf_dbu)}] [expr {round(507.6*$::lpf_dbu)}] [expr {round(464.4*$::lpf_dbu)}] [expr {round(550.8*$::lpf_dbu)}]
set ::lpf_g(lk_rst) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_rst"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_mid_rst"]
odb::dbBox_create $::lpf_r [expr {round(432*$::lpf_dbu)}] [expr {round(572.4*$::lpf_dbu)}] [expr {round(464.4*$::lpf_dbu)}] [expr {round(615.6*$::lpf_dbu)}]
set ::lpf_g(mid_rst) [odb::dbGroup_create $::lpf_r "lp_fence_grp_mid_rst"]
array set ::lpf_own {u_lpl_0_r lk_0 u_lpl_0_w mid_0 u_lpl_10_r mid_10 u_lpl_10_w lk_10 u_lpl_11_r mid_11 u_lpl_11_w lk_11 u_lpl_1_r lk_1 u_lpl_1_w mid_1 u_lpl_2_r lk_2 u_lpl_2_w mid_2 u_lpl_3_r lk_3 u_lpl_3_w mid_3 u_lpl_4_r lk_4 u_lpl_4_w mid_4 u_lpl_5_r mid_5 u_lpl_5_w lk_5 u_lpl_6_r mid_6 u_lpl_6_w lk_6 u_lpl_7_r mid_7 u_lpl_7_w lk_7 u_lpl_8_r mid_8 u_lpl_8_w lk_8 u_lpl_9_r mid_9 u_lpl_9_w lk_9 u_lpr_lk_c0 lk_rst u_lpr_lk_c1 lk_rst u_lpr_lk_c2 lk_rst u_lpr_lk_c3 lk_rst u_lpr_lk_p lk_rst u_lpr_mid_c0 mid_rst u_lpr_mid_c1 mid_rst u_lpr_mid_c2 mid_rst u_lpr_mid_c3 mid_rst u_lpr_mid_p mid_rst u_lprc_u_l0 lk_rst u_lprc_u_l1 mid_rst u_lprc_u_l2 mid_rst}
proc lpf_seq {m} {
  foreach mt [$m getMTerms] { if {[$mt getSigType] eq "CLOCK"} { return 1 } }
  return 0
}
set ::lpf_reads {}
foreach i [$::lpf_blk getInsts] {
  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne "CORE"} continue
  regsub -all {\\} [$i getName] {} n
  if {![regexp {(?:^|[./])(u_lpl_[0-9]+_[wr]|u_lpr_(?:lk|mid)_(?:p|c[0-9]+)|u_lprc_u_l[0-2])[./]} $n -> h]} continue
  if {![info exists ::lpf_own($h)]} { error "LP_FENCE: $n has no landing owner" }
  if {[$i getGroup] ne "NULL"} continue
  set r $::lpf_own($h)
  $::lpf_g($r) addInst $i
  incr ::lpf_n($r)
  if {[string match *_r $h] && [lpf_seq [$i getMaster]]} { lappend ::lpf_reads [list $i $r] }
}
# read-mux cone: walk back from every read-half register's data inputs through ungrouped combinational cells
foreach ir $::lpf_reads {
  lassign $ir i r
  set front [list $i]
  for {set d 0} {$d < 16 && [llength $front]} {incr d} {
    set nxt {}
    foreach x $front {
      foreach it [$x getITerms] {
        if {![$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} continue
        set net [$it getNet]
        if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
        foreach dt [$net getITerms] {
          if {![$dt isOutputSignal]} continue
          set di [$dt getInst]
          set dm [$di getMaster]
          if {[$dm isBlock] || [$dm getType] ne "CORE" || [$di getGroup] ne "NULL" || [lpf_seq $dm]} continue
          $::lpf_g($r) addInst $di
          incr ::lpf_c($r)
          lappend nxt $di
        }
      }
    }
    set front $nxt
  }
}
foreach r {lk_0 mid_0 lk_1 mid_1 lk_2 mid_2 lk_3 mid_3 lk_4 mid_4 lk_5 mid_5 lk_6 mid_6 lk_7 mid_7 lk_8 mid_8 lk_9 mid_9 lk_10 mid_10 lk_11 mid_11 lk_rst mid_rst} {
  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error "LP_FENCE: region $r got no landing cells" }
  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }
  puts "LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)"
}
