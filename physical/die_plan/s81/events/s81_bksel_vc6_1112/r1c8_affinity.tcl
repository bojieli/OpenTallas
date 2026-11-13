uplevel #0 {
# Same-cycle control/source/capture affinity; executes after GPL, before DPL/CTS.
# Each 8-bit H2 subgroup is compact; its rpd/mbd reach is on the preceding full-cycle stage.
set rc_blk [ord::get_db_block]
set rc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rc_core [$rc_blk getCoreArea]
set rc_mac {}
foreach i [$rc_blk getInsts] {
 if {[[$i getMaster] isBlock]} {set b [$i getBBox]; lappend rc_mac [list [expr {[$b xMin]-6*$rc_dbu}] [expr {[$b yMin]-6*$rc_dbu}] [expr {[$b xMax]+6*$rc_dbu}] [expr {[$b yMax]+6*$rc_dbu}]]}
}
proc rc_out {x y} {
 global rc_mac rc_core rc_dbu
 for {set j 0} {$j<10} {incr j} {
  set changed 0
  foreach b $rc_mac {
   lassign $b x0 y0 x1 y1
   if {$x>$x0 && $x<$x1 && $y>$y0 && $y<$y1} {
    set choices [list [list [expr {$x-$x0}] $x0 $y] [list [expr {$x1-$x}] $x1 $y] [list [expr {$y-$y0}] $x $y0] [list [expr {$y1-$y}] $x $y1]]
    lassign [lindex [lsort -real -index 0 $choices] 0] unused x y
    set changed 1
   }
  }
  if {!$changed} break
 }
 return [list [expr {max([$rc_core xMin]+8*$rc_dbu,min([$rc_core xMax]-12*$rc_dbu,$x))}] [expr {max([$rc_core yMin]+8*$rc_dbu,min([$rc_core yMax]-12*$rc_dbu,$y))}]]
}
set rc_q {};set rc_c {}
foreach i [$rc_blk getInsts] {
 set n [string map [list "\\" ""] [$i getName]]
 if {[regexp {g_r1\[([0-9]+)\]\.q\[([0-9]+)\]} $n -> g bit]} {dict lappend rc_q "$g,[expr {$bit/8}]" $i}
 # Synthesis may name the exact same q flop by its g_c1 direct wire alias.
 # EW=37, IW=20: v[b]=r1_d[37*lane+20+b], lv=r1_d[37*lane+36].
 if {[regexp {g_c1\[([0-9]+)\]\.(v\[([0-9]+)\]|lv)\$_DFF} $n -> lane field vb]} {
  set absolute [expr {37*$lane + ($field eq "lv" ? 36 : 20+$vb)}]
  set g [expr {$absolute/27}];set bit [expr {$absolute%27}]
  dict lappend rc_q "$g,[expr {$bit/8}]" $i
 }
 if {[regexp {g_r1\[([0-9]+)\]\.g_cp8\[([0-9]+)\]\.(rp8|mb8|u_fl_r1s)} $n -> g rs]} {
  if {[[$i getMaster] isSequential]} {dict lappend rc_c "$g,$rs" $i}
 }
}
set rc_groups 0;set rc_qn 0;set rc_cn 0
set rc_f [open /work/r1c8_affinity.csv w];puts $rc_f {group,subgroup,q_count,control_count,x_um,y_um}
dict for {key qs} $rc_q {
 if {![dict exists $rc_c $key]} {error "R1C8 affinity: missing control group $key"}
 set cs [dict get $rc_c $key];set sx 0;set sy 0
 foreach q $qs {lassign [$q getLocation] x y;set sx [expr {$sx+$x}];set sy [expr {$sy+$y}]}
 lassign [rc_out [expr {round($sx/double([llength $qs]))}] [expr {round($sy/double([llength $qs]))}]] x y
 set idx 0
 foreach i [concat $qs $cs] {
  $i setLocation [expr {round($x+($idx%4)*1.62*$rc_dbu)}] [expr {round($y+($idx/4)*0.54*$rc_dbu)}]
  $i setPlacementStatus PLACED
  incr idx
 }
 puts $rc_f "$key,[llength $qs],[llength $cs],[expr {$x/double($rc_dbu)}],[expr {$y/double($rc_dbu)}]"
 incr rc_groups; incr rc_qn [llength $qs]; incr rc_cn [llength $cs]
}
close $rc_f
puts "OT_R1C8_AFFINITY groups=$rc_groups payload_flops=$rc_qn control_flops_latches=$rc_cn cycle_delta=0"
if {$rc_groups != 88 || $rc_qn != 592 || $rc_cn < 352} {error "R1C8 affinity: incomplete expected groups/payload/control"}

}
