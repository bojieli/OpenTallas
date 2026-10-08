# Implement the two modeled local clock/logic islands; source/capture count checked.
# gaps-design 2026-10-08 (DPL-0033 fix): the 20261007 fences were 100.008 um wide at x 150.012 / 570.024, i.e. they
# began 10 um left of each lane's 80-um pin span (x 160-241 / 580-661, both edges) and ended 9 um right of it, so the
# legaliser had no room to spread the lane's port buffers and pin-side repair buffers: every version died in detailed
# placement (overlaps / site-alignment / padding on input*/output*/wire* cells at 3.7 % die utilisation).  The fence is
# A wider fence does NOT fix it (100 / 140 / 200 / 300 um all fail DPL-0033): the fence ran the full core height under
# the lane's own pin rows, so the port buffers of those pins (created after this hook, not fence members) had to leave
# the fence and the legaliser's +/-27-um diamond window could not reach a legal site outside it.  The fence now stops
# HA2_FENCE_YM um (env, default 10.8 = 40 rows; 5.4 still left 2 illegal cells, 2.7 and 10.8 legalise clean) short of the top and bottom core edges: a non-fence band under each pin
# row holds the port buffers right at their pins; the fence keeps the lane's launch / capture logic.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set row [lindex [$b getRows] 0]
lassign [$row getOrigin] row_x row_y
set site [$row getSite]
set site_w [$site getWidth]
set row_h [$site getHeight]
set fw [expr {[info exists ::env(HA2_FENCE_W)] ? $::env(HA2_FENCE_W) : 100.008}]
set ym [expr {[info exists ::env(HA2_FENCE_YM)] ? $::env(HA2_FENCE_YM) : 10.8}]
set ym [expr {round($ym / 0.27) * 0.27}]
set fy0 [expr {1.080 + $ym}]
set fy1 [expr {38.880 - $ym}]
set fw [expr {round($fw / 0.054) * 0.054}]
set starts {}
foreach c {200.448 620.448} { lappend starts [expr {1.080 + round(($c - $fw / 2.0 - 1.080) / 0.054) * 0.054}] }
puts "HA2_RELAY_TX_FENCES width=$fw starts=$starts y=$fy0..$fy1"
foreach lane {0 1} start $starts {
 foreach edge [list $start [expr {$start+$fw}]] {
  if {([expr {round($edge*$dbu)}]-$row_x)%$site_w!=0} {error "off-site region X $edge"}
 }
 foreach edge [list $fy0 $fy1] {
  if {([expr {round($edge*$dbu)}]-$row_y)%$row_h!=0} {error "off-row region Y $edge"}
 }
 set r [odb::dbRegion_create $b local_lane_$lane]
 $r setRegionType INCLUSIVE
 odb::dbBox_create $r [expr {round($start*$dbu)}] [expr {round($fy0*$dbu)}] [expr {round(($start+$fw)*$dbu)}] [expr {round($fy1*$dbu)}]
 set groups($lane) [odb::dbGroup_create $r local_lane_$lane]
 set counts($lane) 0
 set ffs($lane) 0
}
foreach i [$b getInsts] {
 set owner -1
 set candidates [list [$i getName]]
 foreach t [$i getITerms] {
  if {[[$t getMTerm] getIoType] ne "OUTPUT"} {continue}
  set net [$t getNet]
  if {$net ne "NULL"} {lappend candidates [$net getName]}
 }
 foreach n $candidates {
  set n [string map [list {\[} {[} {\]} {]}] $n]
  if {[regexp {u_(launch|tx)\.g_lane\[([01])\]} $n -> who lane]} {set owner $lane}
  if {[regexp {(local_data|send_data|u_tx.send_data|u_launch.d_out)\[([0-9]+)\]} $n -> bus bit]} {set owner [expr {$bit/544}]}
  if {[regexp {(^|\.)send_tag\[([0-9]+)\]} $n -> prefix bit]} {set owner [expr {$bit/16}]}
  if {[regexp {(local_v|send_v|u_tx.send_v|u_launch.v_out)\[([01])\]} $n -> bus lane]} {set owner $lane}
 }
 if {$owner>=0 && $owner<=1} {
  $groups($owner) addInst $i
  incr counts($owner)
  if {[regexp {^(S?DFF)} [[$i getMaster] getName]]} {incr ffs($owner)}
 }
}
puts "HA2_RELAY_TX_REGIONS lane0_cells=$counts(0) lane0_flops=$ffs(0) lane1_cells=$counts(1) lane1_flops=$ffs(1)"
if {$ffs(0)!=1153 || $ffs(1)!=1153} {error "Modeled source/capture/register islands not fully bound"}
