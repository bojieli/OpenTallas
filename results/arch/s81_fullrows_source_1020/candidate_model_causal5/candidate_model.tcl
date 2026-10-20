set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach lib [glob $P/lib/NLDM/*RVT*TT*.lib*] {read_liberty $lib}
read_db $::env(AUDIT_DB)
set b [ord::get_db_block]
set label $::env(AUDIT_LABEL)
set ::env(RESULTS_DIR) [file dirname $::env(AUDIT_DB)]
proc model_graph {tag} {
 set b [ord::get_db_block];set f [open /audit/$::env(AUDIT_LABEL)_signal_$tag.tsv w];set idnt 0;set ndnt 0
 foreach n [$b getNets] {if {[$n isDoNotTouch]} {incr ndnt}}
 foreach i [$b getInsts] {
  if {[$i isDoNotTouch]} {incr idnt}
  foreach p [$i getITerms] {
   if {[[$p getMTerm] getSigType] in {POWER GROUND}} continue
   set n [$p getNet];set nn [expr {$n eq "NULL"?"NULL":[$n getName]}]
   puts $f [join [list [$i getName] [[$i getMaster] getName] [[$p getMTerm] getName] $nn] "\t"]
  }
 }
 close $f
 set sha [lindex [exec sha256sum /audit/$::env(AUDIT_LABEL)_signal_$tag.tsv] 0]
 puts "MODEL_GRAPH tag=$tag signal_sha=$sha inst_dnt=$idnt net_dnt=$ndnt"
 return [list $sha $idnt $ndnt]
}
set before [model_graph before]
if {$label eq "hwin"} {
 set ::env(RESULTS_DIR) /case/routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base
 source /src/physical/ref_tile/dsdv_mu_hwin_c21n/hwin_native_fences.tcl
 ot_candidate_pg_ready MODEL
 ot_hj_fences_install
 ot_hj_assign_births 0
} else {
 set kit [expr {$label eq "lep"?"s81sl_lepwd_r3":"s81sl_lepnhwd_r3"}]
 source /src/physical/ref_tile/$kit/lep_band.tcl
 ot_lep_adopt_after_birth MODEL
}
set after [model_graph after]
if {$before ne $after} {error "MODEL functionalgraph/protection drift"}
set outside 0;set functional 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock] || [ot_candidate_physical_only $i]} continue
 incr functional
 if {[$i getGroup] eq "NULL"} {incr outside}
}
if {$outside} {error "MODEL unowned functional cells=$outside"}
ot_pg_audit_snapshot $b /audit/${label}_candidate_pg_causal5.json
puts "MODEL_BATCH_ADMISSION_PASS functional=$functional unowned=$outside NO_PLACEMENT_RUN"

# Isolated causal mutation of the in-memory diagnostic copy only.
proc model_find_master {name} {
 foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] getName] eq $name} {return [$i getMaster]}}
 error "MODEL missing existing actual master $name"
}
set master [model_find_master DFFHQNx1_ASAP7_75t_R]
set ff [odb::dbInst_create $b $master MODEL_UNDECLARED_FF]
if {$label eq "hwin"} {set rc [catch {ot_hj_assign_births 0} detail]} else {set rc [catch {ot_lep_adopt_after_birth MODEL_NEW_FF} detail]}
if {!$rc || ![string match {*unmodelled functional cell*} $detail]} {error "MODEL newFF negative not causal rc=$rc detail=$detail"}
puts "MODEL_NEW_FF_CAUSAL_REJECT $detail"
odb::dbInst_destroy $ff
set master [model_find_master BUFx2_ASAP7_75t_R]
set protected [odb::dbInst_create $b $master MODEL_PROTECTED_UNBOUND]
$protected setDoNotTouch true
set rc [catch {ot_pg_bind_batch_before_protect $b [list $protected]} detail]
if {!$rc || ![string match {*PROTECTED_UNBOUND*} $detail]} {error "MODEL protectedPG negative not causal rc=$rc detail=$detail"}
puts "MODEL_PROTECTED_UNBOUND_CAUSAL_REJECT $detail"
# No protection clearing: object dies only with this disposable process.

# Fresh bound BUF proves protection is checked independently of PG binding.
set test [odb::dbInst_create $b [model_find_master BUFx2_ASAP7_75t_R] MODEL_BOUND_PROTECTED]
ot_pg_bind_batch_before_protect $b [list $test]
if {$label eq "hwin"} {set gn ot_hj_CENTRE;set box [dict get $::ot_hj_boxes CENTRE]} else {set gn ot_lep_band;set box $::ot_lep_band}
ot_native_cell_fence_add $gn [list [$test getName]]
$test setPlacementStatus PLACED
$test setLocation 0 0
$test setDoNotTouch true
set old [list [$test getLocation] [$test getPlacementStatus]]
set rc [catch {ot_candidate_seed_new $gn $box [list [$test getName]]} detail]
if {!$rc || ![string match {*protected cell*} $detail] || $old ne [list [$test getLocation] [$test getPlacementStatus]]} {error "MODEL protected-move negative failed rc=$rc detail=$detail"}
puts "MODEL_PROTECTED_BOUND_MOVE_CAUSAL_REJECT unchanged=$old $detail"
# A different disposable fixed BUF never receives a protection-clear operation.
set fixed [odb::dbInst_create $b [model_find_master BUFx2_ASAP7_75t_R] MODEL_FIXED]
ot_pg_bind_batch_before_protect $b [list $fixed]
ot_native_cell_fence_add $gn [list [$fixed getName]]
$fixed setLocation 0 0
$fixed setPlacementStatus FIRM
set rc [catch {ot_candidate_seed_new $gn $box [list [$fixed getName]]} detail]
if {!$rc || ![string match {*nonmovable*} $detail] || [$fixed getLocation] ne {0 0}} {error "MODEL fixed-move negative failed rc=$rc detail=$detail"}
puts "MODEL_FIXED_MOVE_CAUSAL_REJECT $detail"
set movable [odb::dbInst_create $b [model_find_master BUFx2_ASAP7_75t_R] MODEL_MOVABLE]
ot_pg_bind_batch_before_protect $b [list $movable]
ot_native_cell_fence_add $gn [list [$movable getName]]
$movable setLocation 0 0
$movable setPlacementStatus PLACED
ot_candidate_seed_new $gn $box [list [$movable getName]]
if {[$movable getLocation] eq {0 0} || [$movable isDoNotTouch]} {error "MODEL movable positive failed"}
puts "MODEL_UNPROTECTED_MOVABLE_POSITIVE location=[$movable getLocation] role=[ot_candidate_birth_role $movable]"
rename get_libs model_real_get_libs
proc get_libs {args} {return {}}
set rc [catch {ot_candidate_birth_role $movable} detail]
rename get_libs {}
rename model_real_get_libs get_libs
if {!$rc || ![string match {*missing actual Liberty*} $detail]} {error "MODEL missing Liberty negative failed rc=$rc detail=$detail"}
puts "MODEL_MISSING_LIBERTY_CAUSAL_REJECT $detail"
