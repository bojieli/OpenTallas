# COLLIO-F 10-23: one landing band per clock root (fx compact face, main).  Exact source-owned sequential members of
# every root (fixed pin flops counted, left in place); all counts reported at once on a mismatch.
set ot_cl_spec {
 rx {rx_wck rx_rck} {12.960000 10.800000 32.400000 118.800000} 2015
 cal {cal_ck} {12.960000 118.800000 32.400000 194.400000} 682
 lcal {cal_lck} {12.960000 194.400000 32.400000 237.600000} 144
 tx {tx_wck tx_rck} {2.160000 237.600000 32.400000 334.800000} 2015
 bank0 {codec1} {225.290000 129.600000 234.290000 207.380000} 596
 codec {codec0} {234.290000 16.200000 261.000000 340.200000} 3715
 bank1 {codec2} {261.000000 27.000000 270.000000 104.780000} 596
 bank2 {codec3} {261.000000 140.400000 270.000000 218.180000} 596
 bank3 {codec4} {261.000000 253.800000 270.000000 331.580000} 454
 phy {codec0p} {462.890000 10.800000 483.840000 345.600000} 3030
}
set ot_cl_sub {
 cal_io cal {^(cdc_fault\[|rst_n__ot_rl\d)} {2.160000 334.800000 40.000000 354.240000} 6
 lcal_e lcal {(g_safe_phy_slots\.|ot_prs_|phy_(tx|rx)_slot\$)} {462.890000 144.300000 483.840000 192.900000} 25
}
source /src/physical/common_flow/anchor_row_packing.tcl
namespace eval ot_coll_land {}
proc ot_coll_land::target {inst tx ty rows} {
 set m [$inst getMaster];set width [$m getWidth];set height [$m getHeight]
 set right [ot_anchor_pack::lower $rows $ty];set left [expr {$right-1}];set score Inf;set best {}
 while {$left>=0 || $right<[llength $rows]} {
  set lc Inf;set rc Inf
  if {$left>=0} {set lc [expr {abs([lindex $rows $left 0]-$ty)}]}
  if {$right<[llength $rows]} {set rc [expr {abs([lindex $rows $right 0]-$ty)}]}
  if {min($lc,$rc)>$score} break
  if {$lc<=$rc} {set ri $left;incr left -1} else {set ri $right;incr right}
  lassign [lindex $rows $ri] y x0 x1 ey pitch orient
  if {$ey-$y!=$height} continue
  set hi [expr {$x0+floor(double($x1-$width-$x0)/$pitch)*$pitch}]
  if {$hi<$x0} continue
  set x [expr {max($x0,min($hi,$x0+round(double($tx-$x0)/$pitch)*$pitch))}]
  set cost [expr {abs($x-$tx)+abs($y-$ty)}]
  if {$cost<$score} {set score $cost;set best [list $x $y $orient]}
 }
 if {$best eq ""} {error "OT_COLL_LAND no actual legal row for [$inst getName]"}
 lassign $best x y orient
 $inst setPlacementStatus PLACED;$inst setOrient $orient;$inst setLocation [expr {round($x)}] $y;$inst setPlacementStatus FIRM
}
set ot_cl_b [ord::get_db_block];set ot_cl_dbu [$ot_cl_b getDbUnitsPerMicron];set ot_cl_rows {}
foreach row [$ot_cl_b getRows] {set bb [$row getBBox];if {[$bb yMax]>[$bb yMin] && [$row getSpacing]>0} {lappend ot_cl_rows [list [$bb yMin] [$bb xMin] [$bb xMax] [$bb yMax] [$row getSpacing] [$row getOrient]]}}
set ot_cl_rows [lsort -integer -index 0 $ot_cl_rows]
if {![llength $ot_cl_rows]} {error {OT_COLL_LAND no legal rows}}
set ot_cl_owned {};set ot_cl_by {};set ot_cl_boxes {};set ot_cl_seen_cells {};set ot_cl_miss {};set ot_cl_fixed 0;set ot_cl_plan {}
foreach {name ports box expected} $ot_cl_spec {
 set queue {};set seen {};set members {}
 foreach port $ports {set bt [$ot_cl_b findBTerm $port];if {$bt eq "NULL" || [$bt getNet] eq "NULL"} {error "OT_COLL_LAND missing root $port"};lappend queue [$bt getNet]}
 for {set k 0} {$k<[llength $queue]} {incr k} {
  set net [lindex $queue $k];if {[dict exists $seen $net]} continue;dict set seen $net 1
  foreach it [$net getITerms] {
   if {![$it isInputSignal]} continue
   set inst [$it getInst];set m [$inst getMaster]
   if {[$m isBlock]} continue
   if {[$m isSequential]} {
    set n [$inst getName]
    if {[dict exists $ot_cl_seen_cells $n]} {error "OT_COLL_LAND duplicate sequential owner $n"}
    dict set ot_cl_seen_cells $n 1;lappend members $n
   } elseif {[regexp {^(BUF|INV|HB)} [$m getName]]} {foreach pin [$inst getITerms] {if {[$pin isOutputSignal] && [$pin getNet] ne "NULL"} {lappend queue [$pin getNet]}}}
  }
 }
 set groups [list $name [lsort -dictionary $members] $box $expected]
 foreach {sn sp sre sbox sexp} $ot_cl_sub {
  if {$sp ne $name} continue
  set sm {};set rest {}
  foreach n [lindex $groups 1] {if {[regexp $sre [string map {\\ {}} $n]]} {lappend sm $n} else {lappend rest $n}}
  lset groups 1 $rest;lappend groups $sn $sm $sbox $sexp
 }
 foreach {gname gm gbox gexp} $groups {
  if {[llength $gm]!=$gexp} {lappend ot_cl_miss "$gname actual [llength $gm] expected $gexp"}
  lappend ot_cl_plan $gname $gm $gbox
 }
}
if {[llength $ot_cl_miss]} {error "OT_COLL_LAND counts differ from the measured source counts: [join $ot_cl_miss {; }]"}
set pitch [lindex [lindex $ot_cl_rows 0] 4]
foreach {name all box} $ot_cl_plan {
 set members {}
 foreach n $all {set i [$ot_cl_b findInst $n];if {[$i isFixed]} {incr ot_cl_fixed} else {lappend members $n}}
 dict set ot_cl_by $name $members;dict set ot_cl_boxes $name $box
 if {![llength $members]} {puts "OT_COLL_LAND planned $name cells=0 (all [llength $all] fixed pin flops)";continue}
 set mw 0;set mh 0
 foreach n $members {set m [[$ot_cl_b findInst $n] getMaster];set mw [expr {max($mw,[$m getWidth])}];set mh [expr {max($mh,[$m getHeight])}]}
 lassign $box a b c d
 set x0 [expr {$a*$ot_cl_dbu}];set y0 [expr {$b*$ot_cl_dbu}];set width [expr {($c-$a)*$ot_cl_dbu}];set height [expr {($d-$b)*$ot_cl_dbu}]
 set cols [expr {max(1,int(floor($width/($mw+4*$pitch))))}];set nr [expr {int(ceil(double([llength $members])/$cols))}]
 if {$height/$nr<$mh+2*$pitch} {error "OT_COLL_LAND $name insufficient landing rows"}
 set k 0
 foreach n $members {
  set i [$ot_cl_b findInst $n]
  set tx [expr {$x0+$pitch+($k%$cols)*($width-$mw-2*$pitch)/max(1,$cols-1)}]
  set ty [expr {$y0+(int($k/$cols)+0.5)*$height/$nr-$mh/2.0}]
  ot_coll_land::target $i $tx $ty $ot_cl_rows
  lappend ot_cl_owned $n;incr k
 }
 puts "OT_COLL_LAND planned $name cells=[llength $members] fixed=[expr {[llength $all]-[llength $members]}] columns=$cols rows=$nr box=$box"
}
ot_anchor_pack::repair $ot_cl_b $ot_cl_owned
set fh [open $::env(RESULTS_DIR)/ot_coll_seq_landing.txt w]
dict for {name members} $ot_cl_by {
 lassign [dict get $ot_cl_boxes $name] x0 y0 x1 y1;set ax Inf;set ay Inf;set bx -Inf;set by -Inf
 foreach n $members {
  set i [$ot_cl_b findInst $n];set bb [$i getBBox]
  set a [expr {[$bb xMin]/double($ot_cl_dbu)}];set b [expr {[$bb yMin]/double($ot_cl_dbu)}];set c [expr {[$bb xMax]/double($ot_cl_dbu)}];set d [expr {[$bb yMax]/double($ot_cl_dbu)}]
  if {$a<$x0-2.16 || $b<$y0-2.16 || $c>$x1+2.16 || $d>$y1+2.16} {error "OT_COLL_LAND $name left its legal landing band: $n {$a $b $c $d}"}
  if {[$i getPlacementStatus] ne "FIRM"} {error "OT_COLL_LAND not FIRM: $n"}
  set ax [expr {min($ax,$a)}];set ay [expr {min($ay,$b)}];set bx [expr {max($bx,$c)}];set by [expr {max($by,$d)}]
  puts $fh $n
 }
 puts "OT_COLL_LAND actual $name cells=[llength $members] bbox={$ax $ay $bx $by}"
}
close $fh
puts "OT_COLL_LAND PASS [llength $ot_cl_owned] landed + $ot_cl_fixed fixed pin flops, exact source-owned sequential cells, one band per clock root (COLLIO-F main); zero exclusion regions"
