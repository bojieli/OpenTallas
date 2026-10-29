# WPIPE2 exact logical register-to-bank guides. Default production untouched.
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set groups [dict create]
foreach inst [$blk getInsts] {
 if {[$inst getPlacementStatus] in {FIRM LOCKED}} {continue}
 set nm [string map {"\\" ""} [$inst getName]]
 if {[regexp {\.g_write_pipe\.(we|wa|wd)([01])\[([0-9]+)\]} $nm -> field stage bit]} {
  if {$field eq "we"} {set bank $bit} elseif {$field eq "wa"} {set bank [expr {$bit/6}]} else {set bank [expr {$bit/512}]}
  if {$bank<0 || $bank>7} {error "WPIPE2 invalid register bank $nm"}
  set key "s${stage}r[expr {$bank%4}]"
 } elseif {[regexp {\.line_r\[[0-9]+\]} $nm]} {set key native_line} else {continue}
 dict lappend groups $key $inst
}
set expected 0
foreach {key rect} $::topk_write_boxes {
 if {![dict exists $groups $key]} {error "WPIPE2 empty guide $key"}
 lassign $rect x0 y0 x1 y1
 set reg [odb::dbRegion_create $blk "ot_mrg_topk_$key"]
 $reg setRegionType INCLUSIVE
 odb::dbBox_create $reg [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
 set grp [odb::dbGroup_create $reg "ot_mrg_topk_$key"]
 $grp setType VOLTAGE_DOMAIN
 set area 0
 foreach inst [dict get $groups $key] {$grp addInst $inst;set m [$inst getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]}
 set fill [expr {$area/(($x1-$x0)*($y1-$y0))}]
 if {$fill>0.60} {error "WPIPE2 guide $key actual fill $fill >0.60"}
 puts "OT_TOPK_WRITE_GUIDE $key cells [llength [dict get $groups $key]] fill $fill rect $rect"
 incr expected [llength [dict get $groups $key]]
}
puts "OT_TOPK_WRITE_GUIDE_TOTAL $expected actual mapped FF, GPL guides released before DPL"
