source /src/tools/ref_tile/path_classes.tcl
puts "DIAG_BOUNDARY reference=[get_full_name $qdm_ref] Lmax=$qdm_lmax Lmin=$qdm_lmin skew=$ot_sk hold=$ot_hk"
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
proc diag_point {p} {
 global block dbu
 set name [get_full_name $p]
 set cs [get_cells -quiet -of_objects $p]
 if {[llength $cs]==1} {
  set cn [get_full_name $cs];set inst [$block findInst $cn]
  if {$inst eq "NULL"} {set inst [$block findInst [string map [list {[} {\[} {]} {\]}] $cn]]}
  if {$inst ne "NULL"} {
   set bbox [$inst getBBox];puts "DIAG_INST $cn ref=[get_property $cs ref_name] bbox_um=[expr {[$bbox xMin]/double($dbu)}],[expr {[$bbox yMin]/double($dbu)}],[expr {[$bbox xMax]/double($dbu)}],[expr {[$bbox yMax]/double($dbu)}]"
  }
  set ck [get_pins -quiet "$cn/CLK"]
  if {[llength $ck]} {puts "DIAG_CLOCK $cn max=[get_property $ck arrival_max_rise] min=[get_property $ck arrival_min_rise]"}
 }
}

set targets {}
foreach p [find_timing_paths -path_delay max -group_path_count 1000 -endpoint_path_count 1 -sort_by_slack] {
 set ep [get_property $p endpoint];set en [get_full_name $ep]
 if {$en eq {wl[145]} || [string first {vr2q[512]} $en]>=0 || [string first {vr2q\[512\]} $en]>=0} {
  lappend targets [list $ep [get_property $p startpoint] $en [get_property $p slack]]
 }
}
foreach row $targets {
 lassign $row ep sp en slack
 puts "DIAG_PATH $en slack=$slack start=[get_full_name $sp]"
 diag_point $sp;diag_point $ep
}
foreach name {place32912 wire36534 place32911 _078854_ ot_ohdrv_02288_0 ot_outhold_02288_1 ot_ohdrv_02288_2 output6689} {
 set inst [$block findInst $name]
 if {$inst ne "NULL"} {set box [$inst getBBox];puts "DIAG_BUFFER $name bbox_um=[expr {[$box xMin]/double($dbu)}],[expr {[$box yMin]/double($dbu)}],[expr {[$box xMax]/double($dbu)}],[expr {[$box yMax]/double($dbu)}]"}
}
set bp [$block findBTerm {wl[145]}]
if {$bp ne "NULL"} {
 foreach pin [$bp getBPins] {foreach box [$pin getBoxes] {puts "DIAG_OUTPUT wl145 layer=[[$box getTechLayer] getName] bbox_um=[expr {[$box xMin]/double($dbu)}],[expr {[$box yMin]/double($dbu)}],[expr {[$box xMax]/double($dbu)}],[expr {[$box yMax]/double($dbu)}]"}}
}
exit
