read_db /w/3_place.odb
set ::env(OT_CKR_STEP_UM) $::env(SMK_STEP)
set ::env(OT_CKR_DMAX_UM) $::env(SMK_SPAN)
source /w/src/tools/qwen_cluster/cb16_km/cb16_ckbranch.tcl
set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set die [$blk getDieArea]
set ::ot_ckr_W [expr {[$die xMax] / double($u)}]; set ::ot_ckr_H [expr {[$die yMax] / double($u)}]
set ::ot_ckr_grp [dict create]; set ::ot_ckr_nblocked 0; set ::ot_ckr_npad 0; set ::ot_ckr_padk [dict create]
set ports [ot_ckr_ports]
set Tg 0
foreach p $ports { set ::ot_ckr_plan($p) [ot_ckr_plan $p]; set Tg [expr {max($Tg, [dict get $::ot_ckr_plan($p) tot])}]; puts "PLAN $p [dict remove $::ot_ckr_plan($p) tr ent]" }
foreach p $ports { ot_ckr_build $p $Tg }
puts "SMOKE groups [dict size $::ot_ckr_grp] pads $::ot_ckr_npad blocked $::ot_ckr_nblocked"
set n 0; foreach i [$blk getInsts] { if {[string match ot_ckr_* [$i getName]]} { incr n } }
puts "SMOKE ckr insts $n"
# check every clock sink still driven via a chain from its port: walk back from sinks
set bad 0
foreach p $ports {
  set net [[$blk findBTerm $p] getNet]
  set cnt 0; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} { set nn [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {[dict exists $seen [$nn getName]]} continue; dict set seen [$nn getName] 1
    foreach it [$nn getITerms] { if {![$it isInputSignal]} continue; set m [[$it getInst] getMaster]
      if {[$m isSequential] || [$m isBlock]} { incr cnt; continue }
      foreach o [[$it getInst] getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } } } }
  puts "SMOKE $p leaf sinks $cnt"
}
set hist [dict create]
dict for {g pl} $::ot_ckr_grp {
  set i [$blk findInst $g]; set d 0
  while {1} { set n [[$i findITerm A] getNet]; set drv ""
    foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst] } }
    if {$drv eq ""} break; incr d; set i $drv }
  dict incr hist $d
}
puts "SMOKE root depth histogram (stages port->group root): $hist"
set failures 0
set branches [dict size $::ot_ckb_children]
dict for {node kids} $::ot_ckb_children {
  if {[llength $kids] ni {0 2}} {incr failures}
}
if {$::ot_ckr_nblocked != 0} {incr failures}
puts "BRANCH_SMOKE ports=[llength $ports] branches=$branches leaves=[dict size $::ot_ckr_grp] pads=$::ot_ckr_npad failures=$failures"
if {$failures || [llength $ports] != 16} {error "branch smoke failed"}
exit
