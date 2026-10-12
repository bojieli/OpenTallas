# Modeled placement refinement; CP netlist and all timing constraints unchanged.
source /src/physical/ha2_truecredit_20261007/rx_capture_pin_plan.tcl
set cb [ord::get_db_block]
set cd [[ord::get_db_tech] getDbUnitsPerMicron]
set cc [$cb getCoreArea]
# hbm-phys-1010 [link] (cplg 86dbb17ed: detailed route stuck at 1.5-2k violations, 1,460 of them in ONE 20 x 20 um window
# at lane0 ram0's pin face): the write collar and the transport midpoints were seated 1.08 um from the macro edge,
# i.e. INSIDE the macro halo (MACRO_PLACE_HALO), on top of the SRAM's M4 pin escape (every M4 track of the face is a
# pin).  Seats now start outside the halo + 1.08 um, and the collar uses CW columns (default 16, 0.70 um pitch) so a
# 0.27-um row holds the pins that land on it without stacking cells.
set ha2_halo 2.0
if {[info exists ::env(MACRO_PLACE_HALO)]} {set ha2_halo [lindex $::env(MACRO_PLACE_HALO) 0]}
set ha2_gap [expr {$ha2_halo + 1.08}]
set ha2_cw [expr {[info exists ::env(HA2_COLLAR_COLS)] ? $::env(HA2_COLLAR_COLS) : 16}]
array set wd_sinks {}
array set caps {}
set raws {}
set macro_rects {}
foreach inst [$cb getInsts] {
 set n [$inst getName];regsub -all {\\} $n {} plain
 if {[regexp {^(.*g_lane\[[0-9]+\])\.g_ram\[([0-9]+)\]\.cap_q\[([0-9]+)\]} $plain -> lane bank bit]} {
  set caps([format {%s:%d:%d} $lane $bank $bit]) $inst
 }
 if {[regexp {^(.*g_lane\[([0-9]+)\])\.raw_q\[([0-9]+)\]} $plain -> lane laneid bit]} {
  lappend raws [list $inst $lane $laneid $bit]
 }
 # Each actual SRAM input is inventoried, including its transformed face.
 if {![string match ot_sram_1r1w* [[$inst getMaster] getName]]} continue
 set mb [$inst getBBox]
 lappend macro_rects [list [expr {double([$mb xMin])/$cd}] [expr {double([$mb yMin])/$cd}] [expr {double([$mb xMax])/$cd}] [expr {double([$mb yMax])/$cd}]]
 if {[$inst getOrient] ni {R0 MY MX R180}} {error "Unsupported transport macro orientation [$inst getOrient]"}
 foreach it [$inst getITerms] {
  set pn [[$it getMTerm] getName]
  if {![regexp {^wd_in\[([0-9]+)\]$} $pn -> bit]} continue
  set net [$it getNet];set ff ""
  for {set depth 0} {$depth<8} {incr depth} {
   set driver ""
   foreach dt [$net getITerms] {if {[$dt isOutputSignal]} {set driver $dt;break}}
   if {$driver eq ""} {error "Undriven SRAM write pin $n/$pn"}
   set di [$driver getInst];set mn [[$di getMaster] getName]
   if {[string match DFF* $mn]} {set ff $di;break}
   if {[regexp {^TIE} $mn]} break
   if {![regexp {^(INV|BUF)} $mn]} {error "Unexpected write driver $mn for $n/$pn"}
   set input ""
   foreach q [$di getITerms] {if {[$q isInputSignal]} {set input $q;break}}
   if {$input eq ""} {error "Missing write buffer input $mn"}
   set net [$input getNet]
  }
  if {$ff eq ""} continue
  set fn [$ff getName];regsub -all {\\} $fn {} fp
  if {![regexp {\.wd_q\[([0-9]+)\]} $fp]} {error "SRAM write pin is not owned by wd_q: $fn"}
  set xy [$it getAvgXY]
  if {[llength $xy]!=3 || ![lindex $xy 0]} {error "No physical coordinate for $n/$pn"}
  lappend wd_sinks($fn) [list $inst $it [lindex $xy 1] [lindex $xy 2] $bit]
 }
}
set inventory [open $::env(RESULTS_DIR)/ha2_write_sink_inventory.tsv w]
puts $inventory "flop\tsink_count\tall_sram_pin_destinations"
set anchored {}
foreach fn [lsort [array names wd_sinks]] {
 set dests $wd_sinks($fn);set names {}
 foreach dst $dests {lappend names "[[lindex $dst 0] getName]/[ [[lindex $dst 1] getMTerm] getName]"}
 puts $inventory "$fn\t[llength $dests]\t[join $names {,}]"
 # The sized design has one destination per bit. Do not silently seat a shared
 # driver against its first bank: preserve its full inventory and refuse it.
 if {[llength $dests]!=1} {close $inventory;error "Unmodeled shared write destinations: $fn -> $names"}
 set dst [lindex $dests 0];set mi [lindex $dst 0];set bit [lindex $dst 4]
 set mx [[ $mi getBBox] xMin];set xx [[ $mi getBBox] xMax]
 set px [lindex $dst 2];set py [lindex $dst 3]
 set ff [$cb findInst $fn];set width [expr {double([[$ff getMaster] getWidth])/$cd}]
 set col [expr {$bit%$ha2_cw}]
 if {abs($px-$mx)<abs($px-$xx)} {
  set x [expr {double($mx)/$cd-$ha2_gap-($col+1)*.70}]
 } else {set x [expr {double($xx)/$cd+$ha2_gap+$col*.70}]}
 # a face whose halo abuts the core edge has no room outside the halo: the previous in-halo collar (8 columns)
 if {$x<double([$cc xMin])/$cd || $x+$width>double([$cc xMax])/$cd} {
  set col [expr {$bit%8}]
  if {abs($px-$mx)<abs($px-$xx)} {set x [expr {double($mx)/$cd-1.08-($col+1)*.70}]} else {set x [expr {double($xx)/$cd+1.08+$col*.70}]}
 }
 set y [expr {floor(double($py)/$cd/.27)*.27}]
 if {$x<double([$cc xMin])/$cd || $x+$width>double([$cc xMax])/$cd || $y<double([$cc yMin])/$cd || $y+.27>double([$cc yMax])/$cd} {error "Write collar outside core: $fn"}
 $ff setLocation [expr {round($x*$cd)}] [expr {round($y*$cd)}];$ff setPlacementStatus FIRM
 lappend anchored $fn
}
close $inventory
if {[llength $anchored]!=1120} {error "Expected1120 bank-owned writes; found[llength $anchored]"}
foreach rr $raws {
 lassign $rr ff lane laneid bit
 set bank [expr {$bit/512}];set localbit [expr {$bit%512}]
 set key [format {%s:%d:%d} $lane $bank $localbit]
 if {![info exists caps($key)]} {error "Missing bank capture for [$ff getName]"}
 set cf $caps($key);set cxy [$cf getLocation]
 if {$bit<544} {set port [format {send_data[%d]} [expr {$laneid*544+$bit}]]} else {set port [format {return_tag[%d]} [expr {$laneid*16+$bit-544}]]}
 set bt [$cb findBTerm $port];set bb [$bt getBBox]
 set x [expr {(.5*[lindex $cxy 0]+.25*([$bb xMin]+[$bb xMax]))/$cd}]
 set y [expr {floor((.5*[lindex $cxy 1]+.25*([$bb yMin]+[$bb yMax]))/$cd/.27)*.27}]
 set width [expr {double([[$ff getMaster] getWidth])/$cd}]
 set x [expr {max(double([$cc xMin])/$cd,min($x,double([$cc xMax])/$cd-$width))}]
 set y [expr {max(double([$cc yMin])/$cd,min($y,double([$cc yMax])/$cd-.27))}]
 # Project the desired midpoint to the nearest real free channel. A firm
 # seed inside a macro would only move the long transport to legalization.
 set candidates [list [list $x $y]]
 foreach rect $macro_rects {
  lassign $rect x0 y0 x1 y1
  lappend candidates [list [expr {$x0-$ha2_gap-$width}] $y] [list [expr {$x1+$ha2_gap}] $y] \
    [list $x [expr {$y0-$ha2_gap-.27}]] [list $x [expr {$y1+$ha2_gap}]]
 }
 set best "";set cost 1e99
 foreach pos $candidates {
  lassign $pos px py;set py [expr {floor($py/.27)*.27}]
  if {$px<double([$cc xMin])/$cd || $px+$width>double([$cc xMax])/$cd || $py<double([$cc yMin])/$cd || $py+.27>double([$cc yMax])/$cd} continue
  set blocked 0
  foreach rect $macro_rects {
   lassign $rect x0 y0 x1 y1
   if {$px+$width>$x0-$ha2_gap+0.08 && $px<$x1+$ha2_gap-0.08 && $py+.27>$y0-$ha2_gap+0.08 && $py<$y1+$ha2_gap-0.08} {set blocked 1;break}
  }
  if {$blocked} continue
  set d [expr {abs($px-$x)+abs($py-$y)}]
  if {$d<$cost} {set cost $d;set best [list $px $py]}
 }
 if {$best eq ""} {error "No legal transport channel for [$ff getName]"}
 lassign $best x y
 $ff setLocation [expr {round($x*$cd)}] [expr {round($y*$cd)}];$ff setPlacementStatus FIRM
 lappend anchored [$ff getName]
}
if {[llength $raws]!=1120} {error "Expected1120 transport flops; found[llength $raws]"}
set fh [open $::env(RESULTS_DIR)/ha2_local_transport_flops.txt w];puts $fh [join $anchored "\n"];close $fh
puts "HA2_LOCAL_TRANSPORT anchored1120 write flops with full sink inventory and1120 capture-to-output transport flops"
