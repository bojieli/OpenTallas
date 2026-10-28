# PG-ACTIVITY-3 complete stacked QC solve: actual coll_ftm M1-M7 (read-only final ODB) + exact canonical .672 die grid
# (M8 .48@8.64 off4.32, M9 .672@8.64 off4.32, VSS clock-cut stripes, 150-um checkerboard bumps, 70-um pads on M9),
# placed at canonical-window offset (X0,Y0) covering the upper-deck worst point (1098.278,2046.052). Load 0.5823 W/mm2 by cell area.
set NETS $::env(PGA3_NETS)
set DRY [expr {[info exists ::env(PGA3_DRY)] && $::env(PGA3_DRY)}]
set MODE $::env(PGA3_MODE)
set X0 691.2 ; set Y0 1296.0
set t0 [clock seconds]
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
read_db /old/run/results/asap7/dp_coll_ftm/base/6_final.odb
set b [ord::get_db_block]
set tech [ord::get_db_tech]
set dbu [$tech getDbUnitsPerMicron]
set ca [$b getCoreArea]
set cx0 [expr {[$ca xMin]/double($dbu)}]; set cy0 [expr {[$ca yMin]/double($dbu)}]
puts "PGA3_CORE $cx0 $cy0 [expr {[$ca xMax]/double($dbu)}] [expr {[$ca yMax]/double($dbu)}]"
proc lcount {} {
  global b
  set out {}
  foreach nn {VDD VSS} { array unset c; foreach sw [[$b findNet $nn] getSWires] { foreach w [$sw getWires] { if {[$w isVia]} {incr c(via)} else {incr c([[$w getTechLayer] getName])} } }
    lappend out "$nn:[lsort -stride 2 [array get c]]" }
  return $out
}
puts "PGA3_BEFORE [lcount]"
# die grid phase: window stripe centre lines at 4.32+8.64k (window coords) -> block coords
proc fmod {a m} { return [expr {$a - $m*floor($a/$m)}] }
proc shapes {} { global b dbu; set out {}
  foreach nn {VDD VSS} { foreach sw [[$b findNet $nn] getSWires] { foreach w [$sw getWires] { if {[$w isVia]} continue
    set l [[$w getTechLayer] getName]; if {$l in {M3 M4 M8 M9}} continue
    lappend out [list $nn $l [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } } }
  return [lsort $out] }
set S0 [shapes]
# regenerate the as-built tile recipe (gen_phys.PDN, exact) + die M8/M9 in one grid so pdngen builds every M7-M8-M9 via
set OX $::env(PGA3_OX); set OY $::env(PGA3_OY)
if {[catch {
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {4.32} -offset {2.064}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {1.968}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}
if {$MODE eq "stack"} {add_pdn_stripe -grid {top} -layer M8 -width 0.48 -pitch 8.64 -offset $OY -spacing 3.84 -starts_with POWER
add_pdn_stripe -grid {top} -layer M9 -width 0.672 -pitch 8.64 -offset $OX -spacing 3.648 -starts_with POWER}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
if {$MODE eq "stack"} {add_pdn_connect -grid {top} -layers {M7 M8}
add_pdn_connect -grid {top} -layers {M8 M9}}
pdngen -ripup
pdngen
} e]} { puts "PGA3_ERR pdn $e" }
set S1 [shapes]
array set DL {}; foreach x $S0 { if {[lsearch -exact -sorted $S1 $x] < 0} { incr DL([lindex $x 0]_[lindex $x 1]) } }
puts "PGA3_DIFF_BY_LAYER [array get DL]"
puts "PGA3_M1_M7_IDENTICAL [expr {$S0 eq $S1}] n0=[llength $S0] n1=[llength $S1]"
if {$S0 ne $S1} { set i 0; foreach x $S0 y $S1 { if {$x ne $y} { puts "PGA3_DIFF $x | $y"; if {[incr i] > 6} break } } }
puts "PGA3_AFTER_PDNGEN [lcount] t=[expr {[clock seconds]-$t0}]"
# phase report: first M8/M9 VDD stripe centre in window coords
foreach nn {VDD VSS} { foreach ly {M8 M9} { set v {}
  foreach sw [[$b findNet $nn] getSWires] { foreach w [$sw getWires] { if {[$w isVia] || [[$w getTechLayer] getName] ne $ly} continue
    if {$ly eq "M8"} {lappend v [expr {([$w yMin]+[$w yMax])/2.0/$dbu + $Y0}]} else {lappend v [expr {([$w xMin]+[$w xMax])/2.0/$dbu + $X0}]} } }
  set v [lsort -real -unique $v]; if {![llength $v]} continue; puts "PGA3_PHASE $nn $ly n=[llength $v] first=[lrange $v 0 2] mod8.64=[fmod [lindex $v 0] 8.64]" } }
# exact clock cuts (window coords -> block coords), VSS only, metal on the cut layer + vias touching that layer only
set cuts {}
foreach y {25.68 172.56 319.44 457.68 803.28 941.52 1088.4 1235.28 1408.08 1554.96 1701.84 1840.08 1986.96 2133.84 2272.08 2418.96 2565.84 2738.64 2885.52} {
  lappend cuts [list M8 -100000 [expr {$y-$Y0}] 100000 [expr {$y+0.48-$Y0}]] }
foreach x {535.344 1157.424 1770.864 2401.584} { lappend cuts [list M9 [expr {$x-$X0}] -100000 [expr {$x+0.672-$X0}] 100000] }
set del {}; set ncut 0; set nvia 0
foreach sw [[$b findNet VSS] getSWires] { foreach sb [$sw getWires] {
  foreach c $cuts { lassign $c ly x0 y0 x1 y1
    set hx0 [expr {round($x0*$dbu)}];set hy0 [expr {round($y0*$dbu)}];set hx1 [expr {round($x1*$dbu)}];set hy1 [expr {round($y1*$dbu)}]
    if {[$sb xMin] >= $hx1 || [$sb xMax] <= $hx0 || [$sb yMin] >= $hy1 || [$sb yMax] <= $hy0} continue
    if {[$sb isVia]} { set v [$sb getBlockVia]; if {$v eq "NULL"} {set v [$sb getTechVia]}
      set tl [[$v getTopLayer] getName]; set bl [[$v getBottomLayer] getName]
      if {$tl eq $ly || $bl eq $ly} { lappend del $sb; break } } elseif {[[$sb getTechLayer] getName] eq $ly} { lappend del $sb; break } } } }
foreach sb $del { if {[$sb isVia]} {incr nvia} else {incr ncut}; odb::dbSBox_destroy $sb }
puts "PGA3_CUT stripes=$ncut vias=$nvia"
if {$MODE eq "stack" && ($ncut < 11)} {error "PGA3 expected 10 M8 + 1 M9 VSS cut stripes, got $ncut"}
# bumps: checkerboard, window (131.16+150i, 4.8+150j), VDD when (i+j) odd; 70-um pads clipped to own-net M9 metal
foreach nn {VDD VSS} { set bt [$b findBTerm $nn]; if {$bt ne "NULL"} { odb::dbBTerm_destroy $bt } }
set BUMPS {}
set ba [$b getDieArea]
set nb 0; set npin 0; set nfb 0
if {$MODE eq "stack"} {
set m9 [$tech findLayer M9]
set ba [$b getDieArea]
set W [expr {[$ba xMax]/double($dbu)}]; set H [expr {[$ba yMax]/double($dbu)}]
set half [expr {round(35*$dbu)}]
set nb 0; set npin 0; set nfb 0
foreach nn {VDD VSS} { set s {}; foreach sw [[$b findNet $nn] getSWires] { foreach w [$sw getWires] { if {![$w isVia] && [$w getTechLayer] eq $m9} { lappend s [list [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } } }; set M9S($nn) $s }
for {set i 0} {$i < 40} {incr i} { for {set j 0} {$j < 40} {incr j} {
  set bx [expr {131.16+150*$i-$X0}]; set by [expr {4.8+150*$j-$Y0}]
  if {$bx < 0 || $by < 0 || $bx > $W || $by > $H} continue
  set nn [expr {(($i+$j)%2) ? "VDD" : "VSS"}]
  set px [expr {round($bx*$dbu)}]; set py [expr {round($by*$dbu)}]
  set hits {}
  foreach r $M9S($nn) { lassign $r x0 y0 x1 y1
    set ix0 [expr {max($x0,$px-$half)}]; set ix1 [expr {min($x1,$px+$half)}]; set iy0 [expr {max($y0,$py-$half)}]; set iy1 [expr {min($y1,$py+$half)}]
    if {$ix1 > $ix0 && $iy1 > $iy0} { lappend hits [list $ix0 $iy0 $ix1 $iy1] } }
  if {![llength $hits]} { incr nfb; continue }
  set bt [odb::dbBTerm_create [$b findNet $nn] ${nn}_b${i}_$j]; $bt setIoType INOUT; $bt setSigType [expr {$nn eq "VDD" ? "POWER" : "GROUND"}]
  foreach h $hits { set bp [odb::dbBPin_create $bt]; odb::dbBox_create $bp $m9 {*}$h; $bp setPlacementStatus FIRM; incr npin }
  incr nb; lappend BUMPS [list $nn $bx $by] } }
}
puts "PGA3_BUMPS n=$nb pins=$npin nohit=$nfb list=$BUMPS"
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set ar [expr {double([$ba xMax]-[$ba xMin])*([$ba yMax]-[$ba yMin])/$dbu/$dbu/1.e6}]
set target [expr {$ar*0.5823}]
set area 0.0; set cells {}
foreach i [$b getInsts] { set m [$i getMaster]; set ty [$m getType]
  if {![string match CORE* $ty]} continue
  set a [expr {double([$m getWidth])*[$m getHeight]}]; lappend cells [list [$i getName] $a]; set area [expr {$area+$a}] }
foreach z $cells { lassign $z n a; set_pdnsim_inst_power -inst $n -power [expr {$target*$a/$area}] }
puts "PGA3_LOAD area_mm2=$ar target_w=$target cells=[llength $cells] cellcover=[expr {$area/$dbu/$dbu/1e6/$ar}] uniform_all_core_cells_incl_fill"
if {$DRY} { write_def /p/stack_dry.def; puts "PGA3_DRY_DONE t=[expr {[clock seconds]-$t0}]"; exit }
foreach nn $NETS {
  if {[catch {check_power_grid -net $nn} e]} { puts "PGA3_PG_CHECK_FAIL $nn $e" } else { puts "PGA3_PG_CHECK_OK $nn" }
  if {[catch {analyze_power_grid -net $nn {*}[expr {$MODE eq "below" ? {-source_type FULL} : {}}] -error_file /p/err_${MODE}_$nn.rpt -voltage_file /p/ir_${MODE}_$nn.csv} e]} { puts "PGA3_PSM_FAIL $nn $e" } else { puts "PGA3_PSM_OK $nn t=[expr {[clock seconds]-$t0}]" }
}
puts PGA3_DONE
exit
