# S81-SERDES-GEN 11-17: ported verbatim from the H17 hand kit (H_boot_transport_local.tcl); structural (exact BUF/INV trees, fail closed), no t13 coordinates.
# Run by serdes_corridor.tcl at PRE_DETAIL_PLACE after the boot-release sites are placed at post-GPL.
# PRIVATE H: exact exclusive reset BUF/INV trees, anchored to current strip3.
# Same ports/FFs/stages/nets/clocks. Never move shared logic or functional gates.
proc hboot_netname {p} {
 set n [$p getNet]
 if {$n eq "NULL" || $n eq {}} {return NULL}
 return [$n getName]
}
proc hboot_pinxy {p} {
 lassign [$p getAvgXY] ok x y
 if {!$ok} {error "H_BOOT_TRANSPORT missing pin geometry"}
 return [list $x $y]
}
proc hboot_out {i} {
 set out {}
 foreach p [$i getITerms] {if {[[$p getMTerm] getIoType] eq "OUTPUT"} {lappend out $p}}
 if {[llength $out]!=1} {error "H_BOOT_TRANSPORT expected one output [$i getName]"}
 return [lindex $out 0]
}
proc hboot_path {net wanted seen} {
 if {$net eq "NULL" || [dict exists $seen [$net getName]]} {return {}}
 dict set seen [$net getName] 1
 set source {}
 foreach p [$net getITerms] {if {[[$p getMTerm] getIoType] eq "OUTPUT"} {set source $p;break}}
 if {$source eq {}} {error "H_BOOT_TRANSPORT signal driver missing [$net getName]"}
 lassign [hboot_pinxy $source] sx sy;set paths {}
 foreach p [$net getITerms] {
  if {[[$p getMTerm] getIoType] ne "INPUT"} continue
  set i [$p getInst];lassign [hboot_pinxy $p] tx ty
  set hop [expr {abs($tx-$sx)+abs($ty-$sy)}]
  if {[dict exists $wanted [$i getName]]} {lappend paths $hop;continue}
  if {![ot_auth_input::wire $i]} {error "H_BOOT_TRANSPORT unexpected nonBUF/INV consumer [$i getName]"}
  foreach tail [hboot_path [[hboot_out $i] getNet] $wanted $seen] {lappend paths [expr {$hop+$tail}]}
 }
 return $paths
}
proc hboot_run {} {
 set b [ord::get_db_block];set d [expr {double([$b getDbUnitsPerMicron])}]
 set ff [ot_serdes_boot_release_registers $b];set anchors {}
 foreach i [$b getInsts] {
  if {![string match DFF* [[$i getMaster] getName]]} continue
  if {![regexp {g_locksafe[.]u_hold[.]lock_sync.*1.*DFF} [$i getName]]} continue
  if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} {error "H_BOOT_TRANSPORT original immutable anchor notfixed"}
  lappend anchors $i
 }
 if {[llength $anchors]!=1} {error "H_BOOT_TRANSPORT expected1 boundary authority anchor"}
 set anchor [lindex $anchors 0];lassign [$anchor getLocation] ax ay
 set first [dict get $ff 0];lassign [$first getLocation] ox oy
 if {[$first getPlacementStatus] in {FIRM LOCKED COVER}} {error "H_BOOT_TRANSPORT softBOOT0 unexpectedlyfixed"}
 $first setLocation $ax $oy
 set legs {};set allbuf {};set identity {}
 set authority {}
 foreach n [$b getNets] {
  if {[regexp {(g_locksafe[.]u_hold[.]core_rst_n|g_locksafe[.]u_boot_release[.]rst_n|u_core[.]rst_g_authority)$} [$n getName]]} {set authority $n;break}
 }
 if {$authority eq {}} {error "H_BOOT_TRANSPORT original authority signal missing"}
 set nets [list $authority]
 for {set stage 0} {$stage<3} {incr stage} {lappend nets [[hboot_out [dict get $ff $stage]] getNet]}
 for {set stage -1} {$stage<3} {incr stage} {
  set net [lindex $nets [expr {$stage+1}]]
  if {[$net getSigType] in {CLOCK POWER GROUND}} {error "H_BOOT_TRANSPORT excludes clock/PG network"}
  lassign [ot_auth_input::walk $net {}] buffers leaves other
  if {[dict size $other]} {error "H_BOOT_TRANSPORT stage$stage has nonBUF/INV/nonreset consumers [dict keys $other]"}
  set expected [expr {$stage==2 ? 4 : 1}]
  if {[dict size $leaves]!=$expected} {error "H_BOOT_TRANSPORT stage$stage expected$expected reset leaves, got[dict size $leaves]"}
  if {$stage<2} {
   set target [dict get $ff [expr {$stage+1}]]
   if {![dict exists $leaves [$target getName]]} {error "H_BOOT_TRANSPORT stage$stage wrong next FF"}
  } else {
   dict for {name p} $leaves {if {![regexp {u_core[.]rs_[rt]\\?\[} $name]} {error "H_BOOT_TRANSPORT native leaf outside4syncscope $name"}}
  }
  set before [hboot_path $net $leaves {}]
  set source {};foreach p [$net getITerms] {if {[[$p getMTerm] getIoType] eq "OUTPUT"} {set source $p;break}}
  lassign [hboot_pinxy $source] sx sy;set tx 0.;set ty 0.
  dict for {name p} $leaves {lassign [hboot_pinxy $p] x y;set tx [expr {$tx+$x}];set ty [expr {$ty+$y}]}
  set tx [expr {$tx/[dict size $leaves]}];set ty [expr {$ty/[dict size $leaves]}]
  set direct [expr {(abs($tx-$sx)+abs($ty-$sy))/$d}]
  if {$direct>405} {error "H_BOOT_TRANSPORT stage$stage directspan exceeds sized405um: $direct"}
  dict for {name i} $buffers {
   if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "H_BOOT_TRANSPORT immutable buffer $name"}
   if {![dict size [ot_auth_input::exclusive $i $leaves]]} {error "H_BOOT_TRANSPORT shared buffer $name"}
   if {[dict exists $allbuf $name]} {error "H_BOOT_TRANSPORT buffer belongs to multiple stage signals $name"}
   set sig [list [[$i getMaster] getName]]
   foreach p [$i getITerms] {lappend sig [list [[$p getMTerm] getName] [hboot_netname $p]]}
   dict set identity $name $sig;dict set allbuf $name $i
  }
  lappend legs [list $stage $net $buffers $leaves $sx $sy $tx $ty $before]
 }
 # Occupancy from current full shape, with all original FIRM/macro sites intact.
 set ::ot_auth_input::b $b;set ::ot_auth_input::d $d
 set c [$b getCoreArea];set ::ot_auth_input::core [list [$c xMin] [$c yMin] [$c xMax] [$c yMax]]
 set ::ot_auth_input::macros {};set ::ot_auth_input::occ {};set halo [expr {8.64*$d}]
 foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {
   lassign [ot_auth_input::rectangle $i] x0 y0 x1 y1
   lappend ::ot_auth_input::macros [list [expr {$x0-$halo}] [expr {$y0-$halo}] [expr {$x1+$halo}] [expr {$y1+$halo}]]
  } elseif {![dict exists $allbuf [$i getName]]} {ot_auth_input::occupy [ot_auth_input::rectangle $i]}
 }
 # Include actual voltage-region/placement blockages, not just macro halos.
 foreach blockage [$b getBlockages] {
  set z [$blockage getBBox]
  lappend ::ot_auth_input::macros [list [$z xMin] [$z yMin] [$z xMax] [$z yMax]]
 }
 foreach leg $legs {
  lassign $leg stage net buffers leaves sx sy tx ty before
  set lx [expr {abs($tx-$sx)}];set ly [expr {abs($ty-$sy)}];set length [expr {$lx+$ly}];set k 0
  dict for {name i} $buffers {
   incr k;set desired [expr {$k/double([dict size $buffers]+1)}]
   set m [$i getMaster];set w [$m getWidth];set h [$m getHeight];set best {};set score 1e30
   # Horizontal-then-vertical legal corridor; M6/M7 overflight across PHY is
   # allowed, but BUF cells may occupy only real sites outside8.64um halos.
   for {set sample 0} {$sample<=100} {incr sample} {
    set t [expr {$sample/100.0}];set along [expr {$length*$t}]
    if {$along<=$lx} {set x [expr {$sx+($tx>=$sx?1:-1)*$along}];set y $sy
    } else {set x $tx;set y [expr {$sy+($ty>=$sy?1:-1)*($along-$lx)}]}
    for {set jitter 0} {$jitter<=8} {incr jitter} {
     foreach delta [list [list 0 [expr {$jitter*.27*$d}]] [list 0 [expr {-$jitter*.27*$d}]] [list [expr {$jitter*.54*$d}] 0] [list [expr {-$jitter*.54*$d}] 0]] {
      lassign $delta dx dy
      set px [expr {round(($x+$dx)/(.054*$d))*.054*$d}];set py [expr {round(($y+$dy)/(.27*$d))*.27*$d}]
      set box [list $px $py [expr {$px+$w}] [expr {$py+$h}]]
      if {![ot_auth_input::free $box]} continue
      set cost [expr {abs($t-$desired)*$length+abs($dx)+abs($dy)}]
      if {$cost<$score} {set score $cost;set best [list $px $py $box]}
     }
    }
   }
   if {![llength $best]} {error "H_BOOT_TRANSPORT stage$stage no legal corridor site for$name"}
   lassign $best x y box;ot_auth_input::occupy $box
   $i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED
  }
  set after [hboot_path $net $leaves {}];set maxpath 0.
  foreach path $after {set path [expr {$path/$d}];if {$path>$maxpath} {set maxpath $path}}
  if {$maxpath>405} {error "H_BOOT_TRANSPORT stage$stage actual BUF/INV pathwire exceeds sized405um: $maxpath"}
  puts "H_BOOT_TRANSPORT stage=$stage buffers=[dict size $buffers] before_path_um=[lmap p $before {expr {$p/$d}}] after_path_um=[lmap p $after {expr {$p/$d}}] direct_um=[expr {$length/$d}]"
 }
 dict for {name i} $allbuf {
  set sig [list [[$i getMaster] getName]]
  foreach p [$i getITerms] {lappend sig [list [[$p getMTerm] getName] [hboot_netname $p]]}
  if {$sig ne [dict get $identity $name]} {error "H_BOOT_TRANSPORT cell/master/net identity changed $name"}
 }
 set ::hboot_preview_cells $allbuf;set ::hboot_anchor_name [$anchor getName]
 puts "H_BOOT_TRANSPORT PASS movedBUF_INV=[dict size $allbuf]; BOOT0aligned_to_original_FIRMx=[expr {$ax/$d}], softFFx_delta_um=[expr {($ax-$ox)/$d}]; exact4legs+3BOOT+4native; signal-only no clock/port/FF/net/stage changes"
}
if {[catch {hboot_run} err opts]} {puts stderr [dict get $opts -errorinfo];error $err}
