# Implement the two modeled local clock/logic islands; source/capture count checked.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
foreach lane {0 1} start {150.012 570.012} {
 set r [odb::dbRegion_create $b local_lane_$lane]
 $r setRegionType INCLUSIVE
 odb::dbBox_create $r [expr {round($start*$dbu)}] [expr {round(1.080*$dbu)}] [expr {round(($start+100.008)*$dbu)}] [expr {round(39.096*$dbu)}]
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
