# PREPARED, UNEXECUTED. Source only after exact retained5_1 and joint MM context load.
set b [ord::get_db_block]
proc require {ok msg} {if {!$ok} {error $msg}}
proc terms {n} {
 set rows {};foreach t [$n getITerms] {lappend rows [list [[$t getInst] getName] [[[$t getInst] getMaster] getName] [[$t getMTerm] getName] [[$t getMTerm] getIoType]]};return [lsort $rows]
}
proc bterm_ids {b} {
 set out {};foreach t [$b getBTerms] {set n [$t getNet];set nn {};if {$n ne "NULL"} {set nn [$n getName]};lappend out [list [$t getName] [$t getIoType] [$t getSigType] $nn]};return [lsort $out]
}
source /work/connectivity_guard.tcl
set original_bterms [bterm_ids $b]
set original_cells {};foreach i [$b getInsts] {dict set original_cells [$i getName] [[$i getMaster] getName]}
set locked {};set clock_before {}
foreach n [$b getNets] {
 if {[$n getSigType] ne "CLOCK"} continue
 foreach t [$n getITerms] {
  set i [$t getInst];set nm [$i getName]
  set storig [$i getPlacementStatus];if {[dict exists $locked $nm]} {set storig [dict get $locked $nm]}
  lappend clock_before [list [$n getName] [$n isSpecial] $nm [[$i getMaster] getName] [[$t getMTerm] getName] [$t isSpecial] [$i getLocation] [$i getOrient] $storig]
  if {![dict exists $locked $nm]} {dict set locked $nm [$i getPlacementStatus];if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
 }
}
set clock_before [lsort $clock_before]
set i [$b findInst {fanout24569}]
require [expr {$i ne "NULL" && [[$i getMaster] getName] eq {BUFx2_ASAP7_75t_R}}] {old DATA master mismatch}
require [expr {![dict exists $locked {fanout24569}]}] {candidate is clock-connected}
set n [[$i findITerm {A}] getNet]
require [expr {[$n getName] eq {net35111}}] {DATA net mismatch}
require [expr {[terms $n] eq [lsort [list [list {_227458_} {AND3x1_ASAP7_75t_R} {A} {INPUT}] [list {_227639_} {OA21x2_ASAP7_75t_R} {A1} {INPUT}] [list {_227644_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_227655_} {OA211x2_ASAP7_75t_R} {A1} {INPUT}] [list {_227659_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_227661_} {OA211x2_ASAP7_75t_R} {A1} {INPUT}] [list {_227666_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_227671_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_227681_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_276346_} {INVx1_ASAP7_75t_R} {A} {INPUT}] [list {_279439_} {OR3x1_ASAP7_75t_R} {A} {INPUT}] [list {_279473_} {NAND2x1_ASAP7_75t_R} {A} {INPUT}] [list {_279479_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279492_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279517_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279530_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279536_} {NOR2x1_ASAP7_75t_R} {A} {INPUT}] [list {_279537_} {AO22x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279557_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279563_} {AND2x2_ASAP7_75t_R} {A} {INPUT}] [list {_279568_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279581_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279583_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {fanout24569} {BUFx2_ASAP7_75t_R} {A} {INPUT}] [list {fanout35164} {BUFx3_ASAP7_75t_R} {Y} {OUTPUT}]]]}] {DATA fanout mismatch}
set n [[$i findITerm {Y}] getNet]
require [expr {[$n getName] eq {net24536}}] {DATA net mismatch}
require [expr {[terms $n] eq [lsort [list [list {_227699_} {NAND2x1_ASAP7_75t_R} {A} {INPUT}] [list {_279450_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279465_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279501_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279520_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279527_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279543_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279546_} {NAND2x1_ASAP7_75t_R} {A} {INPUT}] [list {_279547_} {OR2x2_ASAP7_75t_R} {A} {INPUT}] [list {_279552_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279569_} {AND2x2_ASAP7_75t_R} {A} {INPUT}] [list {_279574_} {NOR2x1_ASAP7_75t_R} {A} {INPUT}] [list {_279575_} {AO21x1_ASAP7_75t_R} {A1} {INPUT}] [list {_279576_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_279596_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_293205_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_323593_} {HAxp5_ASAP7_75t_R} {B} {INPUT}] [list {fanout24569} {BUFx2_ASAP7_75t_R} {Y} {OUTPUT}]]]}] {DATA fanout mismatch}
set i [$b findInst {fanout35140}]
require [expr {$i ne "NULL" && [[$i getMaster] getName] eq {BUFx4f_ASAP7_75t_R}}] {old DATA master mismatch}
require [expr {![dict exists $locked {fanout35140}]}] {candidate is clock-connected}
set n [[$i findITerm {A}] getNet]
require [expr {[$n getName] eq {net21386}}] {DATA net mismatch}
require [expr {[terms $n] eq [lsort [list [list {_198695_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_198700_} {AO21x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198760_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_198763_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_198778_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198780_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_198869_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_198870_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_199058_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_199125_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_199134_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {fanout35140} {BUFx4f_ASAP7_75t_R} {A} {INPUT}] [list {place21419} {BUFx6f_ASAP7_75t_R} {Y} {OUTPUT}]]]}] {DATA fanout mismatch}
set n [[$i findITerm {Y}] getNet]
require [expr {[$n getName] eq {net35087}}] {DATA net mismatch}
require [expr {[terms $n] eq [lsort [list [list {_198708_} {AND2x4_ASAP7_75t_R} {B} {INPUT}] [list {_198781_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_198785_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198786_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_198797_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198800_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_198846_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_198850_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198851_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_198852_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_198856_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_198858_} {AO21x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198868_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198874_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_198877_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_199039_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_199040_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_199041_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_199048_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_199051_} {OA211x2_ASAP7_75t_R} {C} {INPUT}] [list {_199055_} {AOI22x1_ASAP7_75t_R} {A2} {INPUT}] [list {_199066_} {AND3x1_ASAP7_75t_R} {C} {INPUT}] [list {_199126_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {_199127_} {AND4x1_ASAP7_75t_R} {D} {INPUT}] [list {fanout35140} {BUFx4f_ASAP7_75t_R} {Y} {OUTPUT}]]]}] {DATA fanout mismatch}
set sink [$b findInst {u_u_lrly1.c_va\[29\]$_DFF_P_}]
set sink_t [$sink findITerm D]
set old_net [$sink_t getNet]
require [expr {[$old_net getName] eq {u_u_lrly1.pa_q\[157\]}}] {hold net mismatch}
require [expr {[llength [$old_net getITerms]] == 2}] {hold branch no longer single sink}
require [expr {[$b findInst {codex_l1_hold_cva29_buf}] eq "NULL" && [$b findNet {codex_l1_hold_cva29}] eq "NULL"}] {candidate names already exist}

foreach master {BUFx2_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx6f_ASAP7_75t_R} {
 set found {};foreach lib [[ord::get_db] getLibs] {set mm [$lib findMaster $master];if {$mm ne "NULL"} {lappend found $mm}}
 require [expr {[llength $found]==1}] {target physical master does not uniquely resolve}
 set mm [lindex $found 0];set pins {}
 foreach p [$mm getMTerms] {lappend pins [list [$p getName] [$p getIoType] [$p getSigType]]}
 require [expr {[lsort $pins] eq [lsort {{A INPUT SIGNAL} {Y OUTPUT SIGNAL} {VDD INOUT POWER} {VSS INOUT GROUND}}]}] {target physical pin ABI mismatch}
 foreach lib {asap7sc7p5t_INVBUF_RVT_TT_nldm_211120 asap7sc7p5t_INVBUF_RVT_FF_nldm_211120} {
  require [expr {[llength [get_lib_cells $lib/$master]]==1}] {selected target Libmaster missing or ambiguous}
 }
}
global_route -start_incremental
replace_cell [get_cells {fanout24569}] [lindex [get_lib_cells */BUFx4_ASAP7_75t_R] 0]
replace_cell [get_cells {fanout35140}] [lindex [get_lib_cells */BUFx6f_ASAP7_75t_R] 0]
set bi [odb::dbInst_create $b [[ord::get_db] findMaster {BUFx2_ASAP7_75t_R}] {codex_l1_hold_cva29_buf}]
set nn [odb::dbNet_create $b {codex_l1_hold_cva29}]
$nn setSigType SIGNAL
[$bi findITerm A] connect $old_net
[$bi findITerm Y] connect $nn
$sink_t disconnect
$sink_t connect $nn
lassign [$sink getLocation] hx hy
$bi setLocation $hx $hy
$bi setOrient [$sink getOrient]
$bi setPlacementStatus PLACED
source /work/pg_connect.tcl
ot_pg_connect_all l1_three_data_edits
ot_pg_require_bound l1_three_data_edits
detailed_placement
check_placement -verbose
dict for {nm st} $locked {[$b findInst $nm] setPlacementStatus $st}
require [expr {$original_bterms eq [bterm_ids $b]}] {BTerm/source identity changed}
set clock_after {}
foreach n [$b getNets] {
 if {[$n getSigType] ne "CLOCK"} continue
 foreach t [$n getITerms] {set i [$t getInst];lappend clock_after [list [$n getName] [$n isSpecial] [$i getName] [[$i getMaster] getName] [[$t getMTerm] getName] [$t isSpecial] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
}
require [expr {$clock_before eq [lsort $clock_after]}] {CLOCK identity/geometry/flags changed}
dict for {nm st} $locked {[$b findInst $nm] setPlacementStatus $st}
set expected $original_cells
dict set expected {fanout24569} {BUFx4_ASAP7_75t_R}
dict set expected {fanout35140} {BUFx6f_ASAP7_75t_R}
dict set expected {codex_l1_hold_cva29_buf} {BUFx2_ASAP7_75t_R}
set actual {};foreach i [$b getInsts] {dict set actual [$i getName] [[$i getMaster] getName]}
require [expr {[lsort [dict keys $expected]] eq [lsort [dict keys $actual]]}] {extra/missing cell beyond three edits}
dict for {nm master} $expected {require [expr {[dict get $actual $nm] eq $master}] {extra master mutation}}

set incidence_after [incidence $b]
set incidence_expected $incidence_before
set sink_key [list IT {u_u_lrly1.c_va\[29\]$_DFF_P_} D]
dict set incidence_expected $sink_key [list {codex_l1_hold_cva29} SIGNAL 0 0]
dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} A] [list {u_u_lrly1.pa_q\[157\]} SIGNAL 0 0]
dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} Y] [list {codex_l1_hold_cva29} SIGNAL 0 0]
foreach p {VDD VSS} {
 set ref [dict get $incidence_before [list IT _145581_ $p]]
 set got [dict get $incidence_after [list IT {codex_l1_hold_cva29_buf} $p]]
 require [expr {[lrange $got 0 2] eq [lrange $ref 0 2]}] {new BUF PG net differs from existing native supply}
 dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} $p] $got
}
require_same_dict $incidence_expected $incidence_after {undeclared existing signal/PG connectivity mutation}
set nets_expected $nets_before
dict set nets_expected {codex_l1_hold_cva29} {SIGNAL 0}
require_same_dict $nets_expected [net_ids $b] {undeclared net creation/deletion/class mutation}
set pf [open /work/candidate_placement.tsv w]
set prows {};foreach pi [$b getInsts] {lappend prows [list [$pi getName] [[$pi getMaster] getName] [$pi getLocation] [$pi getOrient]]}
foreach row [lsort $prows] {puts $pf $row};close $pf
set pdigest [lindex [exec sha256sum /work/candidate_placement.tsv] 0]
if {$::env(CANDIDATE_PHASE) eq "place"} {
 write_db /work/candidate_place.odb
 source /work/geom_dump.tcl
 puts CANDIDATE_PLACE_COUPON_COMPLETE
 exit
}
require [expr {$::env(CANDIDATE_PHASE) eq "route" && $pdigest eq $::env(REVIEWED_PLACEMENT_SHA256)}] {unreviewed or nondeterministic actual placement; no route}
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
# Final joint policy consumer runs AFTER this last physical/RC change. No broad repair.
ot_mm_sync
puts [format "CANDIDATE_FINAL TT %.6f FF %.6f" [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
ot_mm_unsync
dict for {nm st} $locked {[$b findInst $nm] setPlacementStatus $st}
require [expr {$original_bterms eq [bterm_ids $b]}] {BTerm/source identity changed}
set clock_after {}
foreach n [$b getNets] {
 if {[$n getSigType] ne "CLOCK"} continue
 foreach t [$n getITerms] {set i [$t getInst];lappend clock_after [list [$n getName] [$n isSpecial] [$i getName] [[$i getMaster] getName] [[$t getMTerm] getName] [$t isSpecial] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
}
require [expr {$clock_before eq [lsort $clock_after]}] {CLOCK identity/geometry/flags changed}
dict for {nm st} $locked {[$b findInst $nm] setPlacementStatus $st}
set expected $original_cells
dict set expected {fanout24569} {BUFx4_ASAP7_75t_R}
dict set expected {fanout35140} {BUFx6f_ASAP7_75t_R}
dict set expected {codex_l1_hold_cva29_buf} {BUFx2_ASAP7_75t_R}
set actual {};foreach i [$b getInsts] {dict set actual [$i getName] [[$i getMaster] getName]}
require [expr {[lsort [dict keys $expected]] eq [lsort [dict keys $actual]]}] {extra/missing cell beyond three edits}
dict for {nm master} $expected {require [expr {[dict get $actual $nm] eq $master}] {extra master mutation}}

set incidence_after [incidence $b]
set incidence_expected $incidence_before
set sink_key [list IT {u_u_lrly1.c_va\[29\]$_DFF_P_} D]
dict set incidence_expected $sink_key [list {codex_l1_hold_cva29} SIGNAL 0 0]
dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} A] [list {u_u_lrly1.pa_q\[157\]} SIGNAL 0 0]
dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} Y] [list {codex_l1_hold_cva29} SIGNAL 0 0]
foreach p {VDD VSS} {
 set ref [dict get $incidence_before [list IT _145581_ $p]]
 set got [dict get $incidence_after [list IT {codex_l1_hold_cva29_buf} $p]]
 require [expr {[lrange $got 0 2] eq [lrange $ref 0 2]}] {new BUF PG net differs from existing native supply}
 dict set incidence_expected [list IT {codex_l1_hold_cva29_buf} $p] $got
}
require_same_dict $incidence_expected $incidence_after {undeclared existing signal/PG connectivity mutation}
set nets_expected $nets_before
dict set nets_expected {codex_l1_hold_cva29} {SIGNAL 0}
require_same_dict $nets_expected [net_ids $b] {undeclared net creation/deletion/class mutation}
write_guides $::env(RESULTS_DIR)/route.guide
write_db $::env(RESULTS_DIR)/5_1_grt.odb
set_mode ss
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
puts CANDIDATE_THREE_DATA_EDITS_COMPLETE
