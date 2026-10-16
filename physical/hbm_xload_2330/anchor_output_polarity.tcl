# BD-ring cl2e: keep the actual output-polarity INV in the pin-launch stage.
# cl2d final ODB: flop420 (161.406,125.280), INV (8.262,279.990),
# E pin (172.8,125.532). Four long-wire BUFs create native launch489.6ps.
# This hook changes placement only, after detailed placement. It neither deletes
# hold buffers nor changes clock/data topology, timing constraints or RTL edges.
# Every target must be a single-fanout INV in an otherwise BUF/HB-only chain
# from a bq_d boundary pin to its DFF. Place on a genuinely free legal site
# within20um of that DFF; retain FIRM/dont_touch through CTS/route.
set ap_b [ord::get_db_block]
set ap_u [[ord::get_db_tech] getDbUnitsPerMicron]
set ap_core [$ap_b getCoreArea]
set ap_x0 [$ap_core xMin]; set ap_x1 [$ap_core xMax]
set ap_rows [dict create]; set ap_sw 0; set ap_sh 0
foreach r [$ap_b getRows] {
 set site [$r getSite];set w [$site getWidth];set h [$site getHeight]
 if {$ap_sw == 0} {set ap_sw $w;set ap_sh $h}
 if {$w != $ap_sw || $h != $ap_sh} {error "PIN_POLARITY mixed row sites"}
 lassign [$r getOrigin] x y
 if {$x != $ap_x0} {error "PIN_POLARITY staggered row origins unsupported"}
 dict set ap_rows $y [$r getOrient]
}
if {$ap_sw <= 0 || $ap_sh <= 0} {error "PIN_POLARITY no legal rows"}
proc ap_driver {net} {
 set found "NULL"
 foreach it [$net getITerms] {if {[$it isOutputSignal]} {
  if {$found ne "NULL"} {error "PIN_POLARITY multiple drivers"};set found $it
 }}
 return $found
}
set ap_targets {};set ap_seen [dict create];set ap_ports 0
foreach bt [$ap_b getBTerms] {
 if {[$bt getIoType] ne "OUTPUT" || ![regexp {^bq_d\[} [$bt getName]]} continue
 incr ap_ports;set net [$bt getNet];set inv "NULL";set ff "NULL"
 for {set hop 0} {$hop<20} {incr hop} {
  set it [ap_driver $net];if {$it eq "NULL"} {break}
  set i [$it getInst];set m [[$i getMaster] getName]
  if {[string match DFF* $m]} {set ff $i;break}
  if {![string match INV* $m] && ![string match BUF* $m] && ![string match HB* $m]} {break}
  set loads 0;foreach p [$net getITerms] {if {[$p isInputSignal]} {incr loads}}
  # The BTerm is also the final net's one load. Interior chain nets have one input ITerm.
  if {$loads>1} {error "PIN_POLARITY branching output chain [$bt getName]"}
  if {[string match INV* $m]} {
   if {$inv ne "NULL"} {error "PIN_POLARITY multiple inversions [$bt getName]"};set inv $i
  }
  set next "NULL";set ni 0
  foreach p [$i getITerms] {if {[$p isInputSignal]} {incr ni;set next [$p getNet]}}
  if {$ni!=1 || $next eq "NULL"} {break};set net $next
 }
 if {$ff eq "NULL" || $inv eq "NULL"} {error "PIN_POLARITY no single INV/DFF launch chain [$bt getName]"}
 if {[dict exists $ap_seen [$inv getName]]} {error "PIN_POLARITY shared inversion"}
 dict set ap_seen [$inv getName] 1
 lappend ap_targets [list $bt $inv $ff]
}
if {$ap_ports != 2048 || [llength $ap_targets]!=2048} {error "PIN_POLARITY expected2048 verified chains, got$ap_ports"}
# Occupy every site touched by a real placed cell. Targets release their old
# sites together, then receive new sites one at a time; no other cell moves.
set ap_occ [dict create]
foreach i [$ap_b getInsts] {
 if {[dict exists $ap_seen [$i getName]]} continue
 set bb [$i getBBox]
 set sx [expr {int(floor(double([$bb xMin]-$ap_x0)/$ap_sw))}]
 set ex [expr {int(ceil(double([$bb xMax]-$ap_x0)/$ap_sw))}]
 for {set y [expr {[$ap_core yMin]+int(floor(double([$bb yMin]-[$ap_core yMin])/$ap_sh))*$ap_sh}]} {$y<[$bb yMax]} {incr y $ap_sh} {
  if {![dict exists $ap_rows $y]} continue
  for {set x $sx} {$x<$ex} {incr x} {dict set ap_occ "$y,$x" 1}
 }
}
set ap_offsets {};set ap_ymax 32;set ap_xmax [expr {int(ceil(20.0*$ap_u/$ap_sw))}]
for {set dy [expr {-$ap_ymax}]} {$dy<=$ap_ymax} {incr dy} {
 for {set dx [expr {-$ap_xmax}]} {$dx<=$ap_xmax} {incr dx} {
  set cost [expr {abs($dx)*$ap_sw+abs($dy)*$ap_sh}]
  if {$cost<=20*$ap_u} {lappend ap_offsets [list $cost $dy $dx]}
 }
}
set ap_offsets [lsort -integer -index 0 $ap_offsets]
set ap_moved 0;set ap_max_before 0;set ap_max_after 0
foreach t $ap_targets {
 lassign $t bt inv ff
 lassign [$ff getLocation] fx fy;lassign [$inv getLocation] ix iy
 set before [expr {abs($ix-$fx)+abs($iy-$fy)}]
 set ap_max_before [expr {max($ap_max_before,$before)}]
 set nw [expr {int(ceil(double([[$inv getMaster] getWidth])/$ap_sw))}]
 if {[[$inv getMaster] getHeight]!=$ap_sh} {error "PIN_POLARITY nonstandard height"}
 set fxsite [expr {int(round(double($fx-$ap_x0)/$ap_sw))}]
 set found 0
 foreach off $ap_offsets {
  lassign $off cost dy dx;set y [expr {$fy+$dy*$ap_sh}];set x [expr {$fxsite+$dx}]
  if {![dict exists $ap_rows $y] || $x<0 || $ap_x0+($x+$nw)*$ap_sw>$ap_x1} continue
  set free 1
  for {set j $x} {$j<$x+$nw} {incr j} {if {[dict exists $ap_occ "$y,$j"]} {set free 0;break}}
  if {!$free} continue
  for {set j $x} {$j<$x+$nw} {incr j} {dict set ap_occ "$y,$j" 1}
  set nx [expr {$ap_x0+$x*$ap_sw}]
  $inv setOrient [dict get $ap_rows $y];$inv setLocation $nx $y;$inv setPlacementStatus FIRM
  set name [$inv getName]
  # Yosys-generated polarity names are plain _NNNN_; refuse an ambiguous STA lookup.
  set cells [get_cells -quiet $name]
  if {[llength $cells]!=1} {error "PIN_POLARITY ambiguous cell lookup$name"}
  set_dont_touch $cells
  set ap_max_after [expr {max($ap_max_after,abs($nx-$fx)+abs($y-$fy))}]
  if {$nx!=$ix || $y!=$iy} {incr ap_moved};set found 1;break
 }
 if {!$found} {error "PIN_POLARITY no legal free site within20um [$bt getName]"}
}
puts "PIN_POLARITY verified=$ap_ports moved=$ap_moved max_before_um=[expr {double($ap_max_before)/$ap_u}] max_after_um=[expr {double($ap_max_after)/$ap_u}]"
if {[check_placement -verbose]!=0} {error "PIN_POLARITY placement check failed"}
