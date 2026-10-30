# Revised selector placement-only FF roles, sourced after fixed face/clock islands.
# No RTL, constraints or cycles change. Exact register maps + FF-only single pass.
source /work/selector_roles_data.tcl
namespace eval ::ot_sel_role {
set blk [ord::get_db_block]
set unit [[ord::get_db_tech] getDbUnitsPerMicron]
array set boxes $::ot_sel_boxes
array set roles $::ot_sel_roles
array set rects $::ot_sel_regions
array set members {}; array set area {}; array set seen {}
set count 0
foreach inst [$blk getInsts] {
  set master [$inst getMaster]
  if {![regexp {^DFF} [$master getName]]} continue
  if {[$inst getPlacementStatus] in {FIRM LOCKED}} continue
  set nm [string map {"\\" ""} [$inst getName]]
  # Yosys appends $_DFF*/$_DFFE* to the original packed-bit register name.
  set base [lindex [split $nm {$}] 0]
  set group {}
  if {[info exists roles($base)]} {
    set group $roles($base);set seen($base) 1
  } elseif {[regexp {^u_fcore\.core\.gthreshold\[([0-3])\]\.local_copy\.value\[} $base -> q]} {
    set group threshold$q
  } elseif {[regexp {^u_fcore\.core\.ties\[([0-3])\]} $base -> q]} {
    # Per-quarter tie budget also reaches packed_next -> SRAM WD directly.
    set group threshold$q
  } elseif {[regexp {^u_fcore\.core\.gq\[([0-3])\]\.buf_q\[} $base -> q]} {
    set group q$q
  } elseif {[regexp {^u_fcore\.core\.gq\[([0-3])\]\.} $base -> q]} {
    # fill/rv/rop/ties/pack controls also reach the combinational WD cone.
    set group q$q
  } elseif {[regexp {^u_fcore\.core\.hist\[([0-9]+)\]} $base -> b]} {
    set group q[expr {$b / 64}]
  } elseif {[regexp {^u_fcore\.core\.selected_line\[([0-9]+)\]} $base -> b]} {
    set group q[expr {$b / 592}]
  } elseif {[regexp {^u_fcore\.core\.(selected|selected_v|qfault)\[([0-3])\]} $base -> field q]} {
    set group q$q
  } elseif {[regexp {^u_fcore\.core\.} $base]} {
    set group root
  } elseif {[regexp {^u_fcore\.} $base]} {
    error "OT_SEL_ROLE_UNCLASSIFIED: $base"
  } else {continue}
  if {![info exists boxes($group)]} {error "OT_SEL_ROLE_NO_BOX $group $base"}
  lappend members($group) $inst
  if {![info exists area($group)]} {set area($group) 0.0}
  set area($group) [expr {$area($group)+double([$master getWidth])*[$master getHeight]/$unit/$unit}]
  incr count
}
# Control/reset captures must survive individually. Data FF elimination/merging is
# permitted but reported by counts; no invented register can satisfy this check.
foreach reg [array names roles] {
 if {[regexp {^u_fcore\.(grctrl|grst|rst_sync|rst_core_n)} $reg] && ![info exists seen($reg)]} {
  error "OT_SEL_ROLE_MISSING_MANDATORY $reg"
 }
}
set fixed {}
foreach i [$blk getInsts] {
 if {[$i getPlacementStatus] ni {FIRM LOCKED}} continue
 set bb [$i getBBox]
 lappend fixed [list [expr {double([$bb xMin])/$unit}] [expr {double([$bb yMin])/$unit}] [expr {double([$bb xMax])/$unit}] [expr {double([$bb yMax])/$unit}]]
}
foreach group [array names members] {
 lassign $boxes($group) x0 y0 x1 y1
 set fixedarea 0.0;set unionarea 0.0
 foreach rect $rects($group) {
 lassign $rect rx0 ry0 rx1 ry1
 set unionarea [expr {$unionarea+($rx1-$rx0)*($ry1-$ry0)}]
 foreach b $fixed {
  lassign $b a c d e
  set dx [expr {min($rx1,$d)-max($rx0,$a)}];set dy [expr {min($ry1,$e)-max($ry0,$c)}]
  if {$dx>0 && $dy>0} {set fixedarea [expr {$fixedarea+$dx*$dy}]}
 }
 }
 if {$unionarea<=0} {error "OT_SEL_ROLE_EMPTY_UNION $group"}
 set fill [expr {($area($group)+$fixedarea)/$unionarea}]
 if {$fill>=0.80} {error "OT_SEL_ROLE_CAPACITY $group $fill >= .80"}
 set r [odb::dbRegion_create $blk ot_mrg_sel_$group];$r setRegionType INCLUSIVE
 foreach rect $rects($group) {
 lassign $rect rx0 ry0 rx1 ry1
 odb::dbBox_create $r [expr {round($rx0*$unit)}] [expr {round($ry0*$unit)}] [expr {round($rx1*$unit)}] [expr {round($ry1*$unit)}]
 }
 set g [odb::dbGroup_create $r ot_mrg_sel_$group];$g setType VOLTAGE_DOMAIN
 foreach i $members($group) {$g addInst $i}
 puts "OT_SEL_ROLE $group cells [llength $members($group)] fill $fill"
}
puts "OT_SEL_ROLE_TOTAL $count FFs [array size members] regions"
}
