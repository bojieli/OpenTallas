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

# The local group includes its mux and buffer topology, not just endpoints.
# Backward from each q D: include buffers and the first data mux, stop there.
proc rc_qcone {q} {
 set todo {};set seen {};set out {}
 foreach t [$q getITerms] {if {[[$t getMTerm] getName] eq "D" && [$t getNet] ne "NULL"} {lappend todo [$t getNet]}}
 while {[llength $todo]} {
  set n [lindex $todo 0];set todo [lrange $todo 1 end]
  if {[dict exists $seen $n]} continue
  dict set seen $n 1
  foreach t [$n getITerms] {
   if {[[$t getMTerm] getIoType] ne "OUTPUT"} continue
   set i [$t getInst];set m [$i getMaster]
   if {[$m isBlock] || [$m isSequential]} continue
   lappend out $i
   if {[regexp {^(BUF|INV|HB)} [$m getName]]} {
    foreach it [$i getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} {lappend todo [$it getNet]}}
   }
  }
  if {[dict size $seen]>256} {error "R1C8 q cone exceeded bounded depth"}
 }
 return [lsort -unique $out]
}
# Forward from each control flop/latch Q: include buffer tree and terminal muxes;
# sequential consumers stop traversal, so control launch timing remains unchanged.
proc rc_control_cone {i} {
 set todo {};set seen {};set out {}
 foreach t [$i getITerms] {if {[[$t getMTerm] getName] in {Q QN} && [$t getNet] ne "NULL"} {lappend todo [$t getNet]}}
 while {[llength $todo]} {
  set n [lindex $todo 0];set todo [lrange $todo 1 end]
  if {[dict exists $seen $n]} continue
  dict set seen $n 1
  foreach t [$n getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   set j [$t getInst];set m [$j getMaster]
   if {[$m isBlock] || [$m isSequential]} continue
   lappend out $j
   if {[regexp {^(BUF|INV|HB)} [$m getName]]} {
    foreach ot [$j getITerms] {if {[[$ot getMTerm] getIoType] eq "OUTPUT" && [$ot getNet] ne "NULL"} {lappend todo [$ot getNet]}}
   }
  }
  if {[dict size $seen]>256} {error "R1C8 control cone exceeded bounded depth"}
 }
 return [lsort -unique $out]
}
set rc_combs {};set rc_owners {};set rc_comb_n 0
# Check all ownership before moving any group: a shared cone must never drift
# to a different group's anchor silently.
dict for {key qs} $rc_q {
 set local {}
 foreach q $qs {lappend local {*}[rc_qcone $q]}
 foreach c [dict get $rc_c $key] {lappend local {*}[rc_control_cone $c]}
 set local [lsort -unique $local]
 foreach i $local {
  if {[dict exists $rc_owners $i] && [dict get $rc_owners $i] ne $key} {error "R1C8 shared local cone [$i getName] between $key and [dict get $rc_owners $i]"}
  dict set rc_owners $i $key
 }
 dict set rc_combs $key $local
 incr rc_comb_n [llength $local]
}

set rc_reserved {}
set rc_groups 0;set rc_qn 0;set rc_cn 0
set rc_f [open /work/r1c8_affinity.csv w];puts $rc_f {group,subgroup,q_count,control_count,x_um,y_um}
dict for {key qs} $rc_q {
 if {![dict exists $rc_c $key]} {error "R1C8 affinity: missing control group $key"}
 set cs [dict get $rc_c $key];set sx 0;set sy 0
 foreach q $qs {lassign [$q getLocation] x y;set sx [expr {$sx+$x}];set sy [expr {$sy+$y}]}
 lassign [rc_out [expr {round($sx/double([llength $qs]))}] [expr {round($sy/double([llength $qs]))}]] x y
 # Pack with actual master dimensions, then choose a whole-bundle location.
 # Fixed-pitch slots overlap wide mux/buffer cells and can trap DPL at a macro wall.
 set bundle [concat $qs $cs [dict get $rc_combs $key]]
 set pitch [expr {round(0.108*$rc_dbu)}];set width [expr {round(12.0*$rc_dbu)}]
 set rx 0;set ry 0;set rh 0;set offsets {}
 foreach i $bundle {
  set mw [[$i getMaster] getWidth];set mh [[$i getMaster] getHeight]
  if {$rx>0 && $rx+$mw>$width} {set rx 0;set ry [expr {$ry+$rh+$pitch}];set rh 0}
  dict set offsets $i [list $rx $ry]
  set rx [expr {$rx+$mw+$pitch}];set rh [expr {max($rh,$mh)}]
 }
 set height [expr {$ry+$rh}]
 set candidates {}
 for {set dx -100} {$dx<=100} {incr dx 4} {
  for {set dy -60} {$dy<=60} {incr dy 3} {lappend candidates [list [expr {$dx*$dx+$dy*$dy}] $dx $dy]}
 }
 set found 0
 foreach candidate [lsort -integer -index 0 $candidates] {
  lassign $candidate unused dx dy
  set bx [expr {round($x-$width/2.0+$dx*$rc_dbu)}];set by [expr {round($y-$height/2.0+$dy*$rc_dbu)}]
  set ex [expr {$bx+$width}];set ey [expr {$by+$height}]
  if {$bx<[$rc_core xMin]+$rc_dbu || $ex>[$rc_core xMax]-$rc_dbu || $by<[$rc_core yMin]+$rc_dbu || $ey>[$rc_core yMax]-$rc_dbu} continue
  set clear 1
  foreach bb [concat $rc_mac $rc_reserved] {
   lassign $bb mx0 my0 mx1 my1
   if {$bx<$mx1 && $ex>$mx0 && $by<$my1 && $ey>$my0} {set clear 0;break}
  }
  if {!$clear} continue
  set x $bx;set y $by;set found 1
  lappend rc_reserved [list [expr {$bx-$pitch}] [expr {$by-$pitch}] [expr {$ex+$pitch}] [expr {$ey+$pitch}]]
  break
 }
 if {!$found} {error "R1C8 no legal whole-bundle site for $key"}
 foreach i $bundle {
  lassign [dict get $offsets $i] ox oy
  $i setLocation [expr {$x+$ox}] [expr {$y+$oy}]
  $i setPlacementStatus PLACED
 }
 puts $rc_f "$key,[llength $qs],[llength $cs],[expr {$x/double($rc_dbu)}],[expr {$y/double($rc_dbu)}]"
 incr rc_groups; incr rc_qn [llength $qs]; incr rc_cn [llength $cs]
}
close $rc_f
puts "OT_R1C8_AFFINITY groups=$rc_groups payload_flops=$rc_qn control_flops_latches=$rc_cn local_mux_buffers=$rc_comb_n cycle_delta=0"
if {$rc_groups != 88 || $rc_qn != 592 || $rc_cn < 352} {error "R1C8 affinity: incomplete expected groups/payload/control"}

}
