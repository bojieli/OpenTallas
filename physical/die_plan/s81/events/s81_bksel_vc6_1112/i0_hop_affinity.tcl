# BKSEL only: exact 593-bit u_fl_i0 hop affinity. No clock exception or new phase.
# OT_I0_HOP_MODE=probe|place|clock; OT_I0_HOP_OUT names an output directory.
uplevel #0 {
set ih_mode [expr {[info exists ::env(OT_I0_HOP_MODE)] ? $::env(OT_I0_HOP_MODE) : "probe"}]
if {$ih_mode ni {probe place clock}} {error "I0_HOP unknown mode $ih_mode"}
set ih_block [ord::get_db_block];set ih_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ih_out [expr {[info exists ::env(OT_I0_HOP_OUT)] ? $::env(OT_I0_HOP_OUT) : "/work/results/i0_hop_$ih_mode"}]
file mkdir $ih_out
proc ih_name {i} {string map [list "\\" ""] [$i getName]}
proc ih_clock {i} {
 set pins {};foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] eq "CLOCK" || [[$t getMTerm] getName] eq "CLK"} {lappend pins $t}}
 if {[llength $pins]!=1 || [[lindex $pins 0] getNet] eq "NULL"} {error "I0_HOP missing/ambiguous clock [ih_name $i]"}
 return [lindex $pins 0]
}
proc ih_signal_pin {i name} {
 set p {};foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq $name} {lappend p $t}}
 if {[llength $p]!=1 || [[lindex $p 0] getNet] eq "NULL"} {error "I0_HOP missing/ambiguous $name [ih_name $i]"}
 return [lindex $p 0]
}
proc ih_driver {n} {
 set ds {};foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds]!=1 || [llength [$n getBTerms]]} {error "I0_HOP missing/ambiguous/internal-port data driver [$n getName]"}
 return [lindex $ds 0]
}
proc ih_buffer {i} {regexp {^(BUF|INV|HB)} [[$i getMaster] getName]}
proc ih_inputs {i} {
 set ins {};foreach t [$i getITerms] {if {[[$t getMTerm] getIoType] eq "INPUT" && [[$t getMTerm] getSigType] ne "CLOCK"} {lappend ins $t}}
 if {[llength $ins]!=1 || [[lindex $ins 0] getNet] eq "NULL"} {error "I0_HOP non-unary buffer [ih_name $i]"}
 return [lindex $ins 0]
}
proc ih_positive_ff {i} {expr {[string match "DFF*" [[$i getMaster] getName]] && ![string match "DFFLQ*" [[$i getMaster] getName]] && ![string match {*$_DFF_N_*} [ih_name $i]]}}
proc ih_family {net} {
 set seen {};set parity 0
 while {1} {
  if {$net eq "NULL" || [dict exists $seen $net]} {error "I0_HOP missing/cyclic clock"}
  dict set seen $net 1
  set ports [$net getBTerms];set ds {}
  foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $t}}
  if {[llength $ports]} {
   if {[llength $ports]!=1 || [llength $ds] || [[lindex $ports 0] getName] ne "ck" || [[lindex $ports 0] getIoType] ne "INPUT"} {error "I0_HOP foreign clock root [$net getName]"}
   if {$parity!=0} {error "I0_HOP inverted fabric clock phase [$net getName]"}
   return [list ck $parity]
  }
  if {[llength $ds]!=1} {error "I0_HOP ambiguous clock driver [$net getName]"}
  set i [[lindex $ds 0] getInst]
  if {![ih_buffer $i] || [[$i getMaster] isSequential] || [[$i getMaster] isBlock]} {error "I0_HOP gated/foreign clock [ih_name $i]"}
  if {[string match "INV*" [[$i getMaster] getName]]} {set parity [expr {1-$parity}]}
  set net [[ih_inputs $i] getNet]
 }
}
# Read the explicit kit steering policy as well as the clock family. A common
# root alone does not authorize moving protected hard-child interface clocks.
if {![file isfile /work/config.mk]} {error "I0_HOP missing kit macro-group policy"}
set cf [open /work/config.mk];set config [read $cf];close $cf
set ih_keep_re {}
foreach line [split $config "\n"] {
 if {[regexp {^(override )?(export )?OT_RT_MGRP_KEEP_RE\s*[:?+]?=\s*(.*)$} $line -> ov ex value]} {set ih_keep_re [string trim [string map [list {$$} {$}] $value]]}
}
if {[info exists ::env(OT_RT_MGRP_KEEP_RE)] && [string trim $::env(OT_RT_MGRP_KEEP_RE)] ne $ih_keep_re} {error "I0_HOP environment/config macro-group policy mismatch"}
proc ih_protected {cap} {
 global ih_keep_re
 if {$ih_keep_re eq ""} {return {}}
 set hit {};set todo {}
 foreach t [$cap getITerms] {if {[[$t getMTerm] getName] in {Q QN} && [$t getNet] ne "NULL"} {lappend todo [list [$t getNet] 0]}}
 foreach item $todo {
  lassign $item n depth
  foreach t [$n getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   set i [$t getInst]
   if {[[$i getMaster] isBlock] && [regexp $ih_keep_re [$i getName]] && [[$t getMTerm] getSigType] ne "CLOCK"} {lappend hit [$i getName]}
   if {$depth==0 && [ih_buffer $i]} {
    foreach ot [$i getITerms] {if {[[$ot getMTerm] getIoType] ne "OUTPUT"} continue
     foreach u [[$ot getNet] getITerms] {if {[[$u getMTerm] getIoType] eq "INPUT" && [[[$u getInst] getMaster] isBlock] && [regexp $ih_keep_re [[$u getInst] getName]] && [[$u getMTerm] getSigType] ne "CLOCK"} {lappend hit [[$u getInst] getName]}}
    }
   }
  }
 }
 return [lsort -unique $hit]
}
set ih_protected_count 0
set ih_hops {};set ih_captures {};set ih_bits {};set ih_shared 0
foreach lat [$ih_block getInsts] {
 set ln [ih_name $lat]
 if {![regexp {^u_q\.u_s\.u_fl_i0\.g_lat\.l\[([0-9]+)\]} $ln -> bit]} continue
 if {![string match "DLL*" [[$lat getMaster] getName]] || $bit<0 || $bit>=593 || [dict exists $ih_bits $bit]} {error "I0_HOP invalid latch $ln"}
 dict set ih_bits $bit 1
 set net [[ih_signal_pin $lat D] getNet];set back {};set seen {}
 while {1} {
  if {[dict exists $seen $net]} {error "I0_HOP cyclic D chain $ln"};dict set seen $net 1
  set driver [ih_driver $net];set src [$driver getInst]
  if {[ih_positive_ff $src]} break
  if {![ih_buffer $src] || [[$src getMaster] isSequential] || [[$src getMaster] isBlock]} {error "I0_HOP foreign D logic [ih_name $src] -> $ln"}
  lappend back $src;set net [[ih_inputs $src] getNet]
 }
 set todo [list [[ih_signal_pin $lat Q] getNet]];set seen {};set forward {};set caps {}
 while {[llength $todo]} {
  set net [lindex $todo 0];set todo [lrange $todo 1 end]
  if {[dict exists $seen $net]} continue;dict set seen $net 1
  if {[llength [$net getBTerms]]} {error "I0_HOP Q reaches port $ln"}
  foreach t [$net getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   set j [$t getInst]
   if {[ih_positive_ff $j] && [[$t getMTerm] getName] eq "D"} {lappend caps $j;continue}
   if {![ih_buffer $j] || [[$j getMaster] isSequential] || [[$j getMaster] isBlock]} {error "I0_HOP foreign Q logic [ih_name $j] from $ln"}
   lappend forward $j
   foreach ot [$j getITerms] {if {[[$ot getMTerm] getIoType] eq "OUTPUT"} {lappend todo [$ot getNet]}}
  }
 }
 set caps [lsort -unique $caps]
 if {[llength $caps]!=1} {error "I0_HOP ambiguous captures $ln"}
 set cap [lindex $caps 0];set cn [ih_name $cap]
 if {![regexp {^u_q\.u_s\.i0_(last|lv\[[0-9]+\]|val\[[0-9]+\]|idx\[[0-9]+\])\$_DFF_P_} $cn] || [dict exists $ih_captures $cap]} {error "I0_HOP foreign/duplicate capture $cn"}
 dict set ih_captures $cap 1
 foreach i [list $src $lat $cap] {ih_family [[ih_clock $i] getNet]}
 if {$ih_mode eq "clock" && [[ih_clock $lat] getNet] ne [[ih_clock $src] getNet]} {error "I0_HOP latch is not launch-bound after follow-D: $ln"}
 # Move only D-chain buffers exclusive to this hop. Shared compare-branch
 # buffers remain untouched, as do the launch FF and every unrelated logic cell.
 set movable [lsort -unique $forward];set allowed [list $lat]
 foreach b $back {
  set exclusive 1
  foreach ot [$b getITerms] {
   if {[[$ot getMTerm] getIoType] ne "OUTPUT"} continue
   set on [$ot getNet]
   if {[llength [$on getBTerms]]} {set exclusive 0}
   foreach it [$on getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getInst] ni $allowed} {set exclusive 0}}
  }
  if {!$exclusive} {incr ih_shared;break}
  lappend allowed $b;lappend movable $b
 }
 set protected [ih_protected $cap]
 if {[llength $protected]} {incr ih_protected_count}
 lappend ih_hops [dict create bit $bit src $src lat $lat cap $cap buffers [lsort -unique $movable] protected $protected]
}
if {[llength $ih_hops]!=593 || [dict size $ih_captures]!=593 || [dict size $ih_bits]!=593} {error "I0_HOP incomplete mapping hops=[llength $ih_hops] captures=[dict size $ih_captures]"}
if {$ih_mode eq "clock" && $ih_protected_count>0} {error "I0_HOP refuses explicit macro keep-group override: $ih_protected_count captures protected by $ih_keep_re"}
set ih_macro {};foreach i [$ih_block getInsts] {if {[[$i getMaster] isBlock]} {set b [$i getBBox];lappend ih_macro [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}
set f [open $ih_out/macros.csv w];puts $f {x,y,w,h};foreach b $ih_macro {lassign $b x y ex ey;puts $f "[expr {$x/double($ih_dbu)}],[expr {$y/double($ih_dbu)}],[expr {($ex-$x)/double($ih_dbu)}],[expr {($ey-$y)/double($ih_dbu)}]"};close $f
set f [open $ih_out/hops.csv w];puts $f {bit,source,latch,capture,source_x,source_y,latch_x,latch_y,capture_x,capture_y,planned_x,planned_y,source_clock,capture_clock,buffers}
set ih_moves {};set core [$ih_block getCoreArea];set moved_clocks 0
foreach h $ih_hops {
 set src [dict get $h src];set lat [dict get $h lat];set cap [dict get $h cap]
 lassign [$src getLocation] sx sy;lassign [$lat getLocation] lx ly;lassign [$cap getLocation] cx cy
 set x [expr {$sx+[[$src getMaster] getWidth]+round(0.216*$ih_dbu)}];set y [expr {$sy+round(0.54*$ih_dbu)}]
 set members [concat [list $cap $lat] [dict get $h buffers]]
 set width 0;set height 0;foreach i $members {set width [expr {$width+[[$i getMaster] getWidth]+round(0.108*$ih_dbu)}];set height [expr {max($height,[[$i getMaster] getHeight])}]}
 # Whole bundle stays outside macro obstruction + 4.32um halo. Nearest safe
 # candidate is selected; no source FF, tap, macro or unrelated logic moves.
 set candidates {};for {set dx -40} {$dx<=40} {incr dx 2} {for {set dy -20} {$dy<=20} {incr dy 2} {lappend candidates [list [expr {$dx*$dx+$dy*$dy}] $dx $dy]}}
 set found 0
 foreach c [lsort -integer -index 0 $candidates] {
  lassign $c unused dx dy;set px [expr {$x+round($dx*$ih_dbu)}];set py [expr {$y+round($dy*$ih_dbu)}]
  if {$px<[$core xMin]+$ih_dbu || $px+$width>[$core xMax]-$ih_dbu || $py<[$core yMin]+$ih_dbu || $py+$height>[$core yMax]-$ih_dbu} continue
  set clear 1;set halo [expr {round(4.32*$ih_dbu)}]
  foreach b $ih_macro {lassign $b mx my ex ey;if {$px<$ex+$halo && $px+$width>$mx-$halo && $py<$ey+$halo && $py+$height>$my-$halo} {set clear 0;break}}
  if {$clear} {set found 1;break}
 }
 if {!$found} {error "I0_HOP no safe placement for [ih_name $cap]"}
 puts $f "[dict get $h bit],[ih_name $src],[ih_name $lat],[ih_name $cap],[expr {$sx/double($ih_dbu)}],[expr {$sy/double($ih_dbu)}],[expr {$lx/double($ih_dbu)}],[expr {$ly/double($ih_dbu)}],[expr {$cx/double($ih_dbu)}],[expr {$cy/double($ih_dbu)}],[expr {$px/double($ih_dbu)}],[expr {$py/double($ih_dbu)}],[[[ih_clock $src] getNet] getName],[[[ih_clock $cap] getNet] getName],[llength [dict get $h buffers]]"
 set offset 0
 foreach i $members {
  if {[dict exists $ih_moves $i]} {error "I0_HOP ambiguous moved buffer [ih_name $i]"}
  dict set ih_moves $i [list [expr {$px+$offset}] $py];set offset [expr {$offset+[[$i getMaster] getWidth]+round(0.108*$ih_dbu)}]
 }
}
close $f
# All maps, bounds and family checks finish before any mutation.
foreach h $ih_hops {if {[dict exists $ih_moves [dict get $h src]]} {error "I0_HOP would move a launch FF"}}
# Placement does not override OT_RT_MGRP_KEEP_RE: that policy controls clock
# landing only. Snapshot EVERY existing clock pin, including hard-child clocks.
set ih_clock_snapshot {}
if {$ih_mode eq "place"} {
 foreach i [$ih_block getInsts] {foreach t [$i getITerms] {
  if {[[$t getMTerm] getSigType] eq "CLOCK" || [[$t getMTerm] getName] eq "CLK"} {dict set ih_clock_snapshot $t [$t getNet]}
 }}
 dict for {i p} $ih_moves {lassign $p x y;$i setLocation $x $y;$i setPlacementStatus PLACED}
 dict for {t n} $ih_clock_snapshot {if {[$t getNet] ne $n} {error "I0_HOP PLACE changed an existing clock net"}}
 puts "I0_HOP_PLACE_CLOCKS_UNCHANGED pins=[dict size $ih_clock_snapshot] KEEP_RE_preserved=1"
}
if {$ih_mode eq "clock"} {
 foreach h $ih_hops {set target [[ih_clock [dict get $h src]] getNet];set pin [ih_clock [dict get $h cap]];if {[$pin getNet] ne $target} {$pin disconnect;$pin connect $target;incr moved_clocks}}
 foreach h $ih_hops {if {[[ih_clock [dict get $h cap]] getNet] ne [[ih_clock [dict get $h src]] getNet]} {error "I0_HOP failed clock binding"}}
}
puts "I0_HOP_VERIFIED mode=$ih_mode hops=593 captures=593 planned_cells=[dict size $ih_moves] shared_D_buffer_branches_untouched=$ih_shared clock_rebound=$moved_clocks root=ck phase=0 protected_captures=$ih_protected_count cycle_delta=0"
}
