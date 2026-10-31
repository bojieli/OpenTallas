# DIE-KV-47 2026-10-30: Q1 routed-DB hold ECO (no full re-route). Variant via env KV47_V (v1 = in-place master swaps,
# v2 = +10 ps margin: swap + one HB1xp67 inserted at rsd_o[180]/D). Starts from the routed 5_2_route.odb of p6b, keeps
# every existing wire, runs ONE detailed_route on the ECO DB (incremental), then compares per-net routing vs before.
set V $::env(KV47_V)
set_thread_count 16
set O $::env(KV47_OUT)
set R /work/run/results/asap7/hc_qkd_ectlk_q1__233_28x172_8/base
read_db $R/5_2_route.odb
set b [ord::get_db_block]
set tech [ord::get_db_tech]
proc mst {n} { set m [[ord::get_db] findMaster $n]; if {$m eq "NULL" || $m eq ""} { error "no master $n" }; return $m }
proc inst {n} { set i [$::b findInst $n]; if {$i eq "NULL" || $i eq ""} { error "no inst $n" }; return $i }
write_def $O/pre.def
set nins0 [llength [$b getInsts]]
set touched {}
proc swap {n m} {
  set i [inst $n]; set from [[$i getMaster] getName]
  lassign [$i getLocation] x y
  if {![$i swapMaster [mst $m]]} { error "swapMaster $n -> $m failed" }
  lassign [$i getLocation] x2 y2
  if {$x != $x2 || $y != $y2} { error "swap moved $n" }
  lappend ::touched $n
  puts "KV47_SWAP $n $from -> $m at $x $y orient [$i getOrient]"
}
if {$V eq "v1"} {
  swap hold8251 HB1xp67_ASAP7_75t_R
  swap _10624_ INVxp33_ASAP7_75t_R
} elseif {$V eq "v2"} {
  swap hold8251 HB2xp67_ASAP7_75t_R
  # one HB1xp67 between _10624_/Y and rsd_o[180]/D: old net keeps the driver + HB/A, new net HB/Y -> D
  # rsd_o[180] flop found through the 2-pin net of _10624_/Y (odb names are escaped)
  set on [[[inst _10624_] findITerm Y] getNet]
  set d ""; foreach it [$on getITerms] { if {[[$it getMTerm] getName] eq "D"} { set d $it } }
  if {$d eq ""} { error "no D load on _10624_/Y" }
  set ff [$d getInst]
  puts "KV47_FF [$ff getName] [[$ff getMaster] getName]"
  if {![string match {*rsd_o*180*DFF_P_} [$ff getName]]} { error "unexpected flop [$ff getName]" }
  puts "KV47_OLDNET [$on getName] iterms [llength [$on getITerms]] wire [expr {[$on getWire] ne "NULL" && [$on getWire] ne ""}]"
  if {[llength [$on getITerms]] != 2} { error "expected 2-pin net on rsd_o[180]/D" }
  # old net is a 2-pin net -> its wire is dropped (DRT re-routes the 2 short nets); every other wire stays
  set w [$on getWire]; if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w }
  set oldg {}; foreach g [$on getGuides] { lappend oldg [list [[$g getLayer] getName] [[$g getViaLayer] getName] [[$g getBox] xMin] [[$g getBox] yMin] [[$g getBox] xMax] [[$g getBox] yMax] [$g isConnectedToTerm]] }
  puts "KV47_OLDNET_GUIDES $oldg"
  set hb [odb::dbInst_create $b [mst HB1xp67_ASAP7_75t_R] kv47_hold180]
  set nn [odb::dbNet_create $b kv47_hold180_n]
  $d disconnect
  [$hb findITerm A] connect $on
  [$hb findITerm Y] connect $nn
  $d connect $nn
  foreach {t s} {VDD POWER VSS GROUND} { set pn [$b findNet $t]; [$hb findITerm $t] connect $pn }
  lassign [$ff getLocation] fx fy
  $hb setLocation $fx $fy; $hb setPlacementStatus PLACED
  lappend touched kv47_hold180
  # legalize only the new cell
  set locked {}
  foreach i [$b getInsts] { if {[$i getName] ne "kv47_hold180" && [$i getPlacementStatus] eq "PLACED"} { $i setPlacementStatus LOCKED; lappend locked $i } }
  detailed_placement
  foreach i $locked { $i setPlacementStatus PLACED }
  puts "KV47_INS kv47_hold180 HB1xp67 at [$hb getLocation] (FF at $fx $fy)"
  check_placement -verbose
} else { error "KV47_V $V" }
# routing guides for nets without wires (v2: the 2 split nets) via incremental GRT, special-net guides cleared first
source /work/kv47_eco/eco_drt_pre.tcl
set unrouted {}
foreach n [$b getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; if {($w eq "NULL" || $w eq "") && [llength [$n getITerms]] + [llength [$n getBTerms]] > 1} { lappend unrouted [$n getName] } }
puts "KV47_UNROUTED_NETS [llength $unrouted] [lrange $unrouted 0 9]"
foreach nn $unrouted { set n [$b findNet $nn]; puts "KV47_GUIDES $nn [llength [$n getGuides]]" }
if {[llength $unrouted]} {
  # ECO nets: the new net gets the old 2-pin net's GRT guides; both get an M1-M3 box over their pins (+4 gcells)
  foreach nn $unrouted {
    set n [$b findNet $nn]
    if {![info exists oldg]} { error "unrouted net $nn outside the v2 ECO" }
    if {$nn ne [$on getName]} { foreach g $oldg { lassign $g l vl x0 y0 x1 y1 ct; if {$l eq "M1"} continue; odb::dbGuide_create $n [$tech findLayer $l] [$tech findLayer $vl] [odb::new_Rect $x0 $y0 $x1 $y1] 0 } }
    set xs {}; set ys {}
    foreach it [$n getITerms] { set bb [[$it getInst] getBBox]; lappend xs [$bb xMin] [$bb xMax]; lappend ys [$bb yMin] [$bb yMax] }
    set x0 [expr {[tcl::mathfunc::min {*}$xs] - 2280}]; set x1 [expr {[tcl::mathfunc::max {*}$xs] + 2280}]
    set y0 [expr {[tcl::mathfunc::min {*}$ys] - 2280}]; set y1 [expr {[tcl::mathfunc::max {*}$ys] + 2280}]
    foreach {l vl} {M2 M2 M2 M3 M3 M3} { odb::dbGuide_create $n [$tech findLayer $l] [$tech findLayer $vl] [odb::new_Rect $x0 $y0 $x1 $y1] 0 }
    puts "KV47_GUIDE_CREATED $nn box $x0 $y0 $x1 $y1 now [llength [$n getGuides]]"
  }
}
# FREEZE: every signal net not on an ECO-touched instance has its dbWire re-encoded FIXED (clk_freeze.tcl
# ot_clk_fix_wire; DRT never rips up FIXED wires: clock nets and all other DATA wires stay token-identical, asserted
# after DRT). NOT setSpecial: the DRT writer drops special-net signal wires.
set eco_nets [dict create]
foreach t $touched { foreach it [[inst $t] getITerms] { set n [$it getNet]; if {$n ne "NULL" && $n ne "" && [$n getSigType] ni {POWER GROUND}} { dict set eco_nets [$n getName] 1 } } }
puts "KV47_ECO_NETS [dict size $eco_nets] [dict keys $eco_nets]"
# the ECO nets are re-routed whole (their old wires end at the old pin shapes): wires dropped, GRT guides kept
foreach nn [dict keys $eco_nets] { set n [$b findNet $nn]; set w [$n getWire]; if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w }; puts "KV47_ECO_NET $nn iterms [llength [$n getITerms]] guides [llength [$n getGuides]]"; if {![llength [$n getGuides]]} { error "ECO net $nn has no guide" } }
# every other routed signal net is locked with OpenROAD's supported FIXED wire type (clk_freeze.tcl ot_clk_fix_wire:
# byte-identical op stream, DRT never rips up / rewrites a FIXED net); asserted token-identical after DRT
source /work/clk_freeze.tcl
set frozen {}; set nfx 0
foreach n [$b getNets] { if {[$n getSigType] in {POWER GROUND} || [dict exists $eco_nets [$n getName]]} continue; set w [$n getWire]; if {$w eq "NULL" || $w eq ""} continue; incr nfx [ot_clk_fix_wire $n]; lappend frozen $n }
puts "KV47_FROZEN_NETS [llength $frozen] reencoded_FIXED $nfx"
detailed_route -output_drc $O/5_route_drc.rpt -output_maze $O/maze.log -droute_end_iter 64 -verbose 1
set bad 0
foreach n $frozen { if {[ot_clk_wire_tokens $n] ne $::ot_clk_tok([$n getName])} { incr bad; if {$bad < 10} { puts "KV47_FROZEN_CHANGED [$n getName]" } } }
puts "KV47_FROZEN_VERIFY nets [llength $frozen] changed $bad"
if {$bad} { error "KV47 frozen nets changed" }
check_antennas -report_file $O/drt_antennas.log
set unr {}
foreach n [$b getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; if {($w eq "NULL" || $w eq "") && [llength [$n getITerms]] + [llength [$n getBTerms]] > 1} { lappend unr [$n getName] } }
puts "KV47_POST_UNROUTED [llength $unr] [lrange $unr 0 19]"
if {[llength $unr]} { error "KV47 design has unrouted nets" }
write_def $O/post.def
write_db $O/5_2_route.odb
puts "KV47_ECO_DONE $V insts [llength [$b getInsts]] (was $nins0) touched $touched"
