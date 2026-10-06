# GENERATED (CLAUDE S81-RERUN): POST_MACRO_PLACE hook of the die-context vehicle
source /src/physical/common/ot_macro_track_snap.tcl
set _blk [ord::get_db_block]
set _dbu [ot_mts::get_dbu]
set _sg [ot_mts::site_grid]
set i [$_blk findInst u_blk]; set m [$i getMaster]
lassign $_sg gx gw gy gh; set r [ot_mts::rule $m R0]
lassign [dict get $r x] Px Sx; lassign [dict get $r y] Py Sy
set px [ot_mts::snap_axis [expr {round(50.4*$_dbu)}] $gx $gw $Px $Sx "u_blk x"]
set py [ot_mts::snap_axis [expr {round(50.220000000000006*$_dbu)}] $gy $gh $Py $Sy "u_blk y"]
$i setOrient R0; $i setLocation $px $py; $i setPlacementStatus FIRM
foreach b [$_blk getBlockages] { odb::dbBlockage_destroy $b }
set fence [dict create]
dict set fence bN11 {270.4 237.34 290.4 257.34}
dict set fence bN12 {290.4 237.34 310.4 257.34}
dict set fence bN13 {310.4 237.34 330.4 257.34}
dict set fence bS11 {270.4 20.22 290.4 40.22}
dict set fence bS12 {290.4 20.22 310.4 40.22}
dict set fence bS13 {310.4 20.22 330.4 40.22}
set regs [dict create]
dict for {nm box} $fence { set rg [odb::dbRegion_create $_blk fence_$nm]; lassign $box a b c d
  odb::dbBox_create $rg [expr {round($a*$_dbu)}] [expr {round($b*$_dbu)}] [expr {round($c*$_dbu)}] [expr {round($d*$_dbu)}]
  dict set regs $nm $rg }
set nf 0; foreach inst [$_blk getInsts] { if {[[$inst getMaster] isBlock]} { continue }
  set p [lindex [split [string map {\\ {}} [$inst getName]] ./] 0]
  if {[dict exists $regs $p]} { [dict get $regs $p] addInst $inst; incr nf } }
puts "OT_CTX_PLACE fenced=$nf regions=[dict size $regs]"
