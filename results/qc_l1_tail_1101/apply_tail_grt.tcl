set b [ord::get_db_block]
proc need {ok msg} {if {!$ok} {error $msg}}
proc clock_guides {b} {
 set rows {}
 foreach n [$b getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  foreach g [$n getGuides] {
   set r [$g getBox]
   lappend rows [list [$n getName] [[$g getLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  }
 }
 return [lsort $rows]
}
set frozen_clock_guides [clock_guides $b]
set original {}
foreach i [$b getInsts] {dict set original [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
set cn {};foreach n [$b getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend cn [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
set driver [$b findInst {_279616_}]
set sink [$b findInst {u_u_exp1.u_exp.nint\[6\]$_DFF_P_}]
need [expr {$driver ne "NULL" && $sink ne "NULL"}] {missing exact driver/sink}
need [expr {[[$driver getMaster] getName] eq "XNOR2x2_ASAP7_75t_R"}] {driver master mismatch}
set net [[$driver findITerm Y] getNet];set st [$sink findITerm D]
need [expr {[$st getNet] eq $net && [$net getSigType] eq "SIGNAL" && [llength [$net getITerms]]==2 && [llength [$net getBTerms]]==0}] {tail is not exact sole-sink DATA net}
need [expr {[$b findInst codex_l1_exp_tail_buf] eq "NULL" && [$b findNet codex_l1_exp_tail_net] eq "NULL"}] {names exist}
set master [[ord::get_db] findMaster BUFx6f_ASAP7_75t_R]
need [expr {$master ne "NULL"}] {BUF master missing}
# Every original cell remains fixed during legalisation, including CLOCK and all FFs.
foreach i [$b getInsts] {if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
global_route -start_incremental
set bi [odb::dbInst_create $b $master codex_l1_exp_tail_buf]
set nn [odb::dbNet_create $b codex_l1_exp_tail_net];$nn setSigType SIGNAL
[$bi findITerm A] connect $net
[$bi findITerm Y] connect $nn
$st disconnect;$st connect $nn
$bi setLocation 106704 190080;$bi setOrient R0;$bi setPlacementStatus PLACED
source /work/pg_connect.tcl
ot_pg_connect_all l1_tail
ot_pg_require_bound l1_tail
detailed_placement
check_placement -verbose
dict for {nm record} $original {
 set i [$b findInst $nm]
 need [expr {$i ne "NULL" && [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]] eq [lrange $record 0 2]}] "original master/location/orient changed: $nm"
 $i setPlacementStatus [lindex $record 3]
}
set ca {};foreach n [$b getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend ca [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
need [expr {[lsort $cn] eq [lsort $ca]}] {CLOCK connectivity changed}
set pf [open /work/tail_placement.tsv w];foreach i [$b getInsts] {puts $pf [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]]};close $pf
set actual_digest [lindex [exec sha256sum /work/tail_placement.tsv] 0]
set fh [open /work/reviewed_placement.sha256];set expected_digest [string trim [read $fh]];close $fh
need [expr {$actual_digest eq $expected_digest}] {placement differs from exact actual reviewed coupon}
global_route -end_incremental -congestion_iterations 50 -resistance_aware
need [expr {$frozen_clock_guides eq [clock_guides $b]}] {CLOCK pre-route guide geometry changed}
estimate_parasitics -global_routing
ot_mm_sync
set setup [ot_mm_ws max [ot_mm_sc]];set hold [ot_mm_ws min BC]
puts [format "L1_TAIL_GRT_FINAL TT %.6f FF %.6f" $setup $hold]
ot_mm_unsync
# ot_mm_unsync restores the native setup mode (called ss, using TT tc libraries).
write_sdc -no_timestamp /work/tail_grt.sdc
write_guides /work/tail.route.guide
write_db /work/tail_grt.odb
source /work/geom_dump.tcl
set fh [open /work/tail_grt_summary.txt w];puts $fh [format "TT %.6f FF %.6f" $setup $hold];close $fh
puts L1_TAIL_GRT_COMPLETE
