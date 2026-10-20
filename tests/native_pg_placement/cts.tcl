# Native source-enabled ordering canary. Run only in a copied placement fixture.
# ENV: OT_PG_CANARY_ROOT, OT_PG_CANARY_SOURCE, OT_PG_CANARY_DB, OT_PG_STRICT.
set root $::env(OT_PG_CANARY_ROOT)
set source_root $::env(OT_PG_CANARY_SOURCE)
set libroot /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach pattern {*AO_RVT_TT* *INVBUF_RVT_TT* *OA_RVT_TT* *SEQ_RVT_TT* *SIMPLE_RVT_TT*} {
  foreach lib [glob $libroot/$pattern] {read_liberty $lib}
}
read_liberty $root/tap.lib
read_db $::env(OT_PG_CANARY_DB)
read_sdc [file rootname $::env(OT_PG_CANARY_DB)].sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
read_lef $root/tap.lef
set block [ord::get_db_block]
set clocknet [$block findNet clk]
set keep {}
foreach it [$clocknet getITerms] {
  set inst [$it getInst]
  if {[[$inst getMaster] isSequential] && [llength $keep] < 16} {lappend keep $inst}
}
if {[llength $keep] != 16} {error CANARY_REQUIRES_16_NATIVE_FF}
foreach inst [$block getInsts] {if {[lsearch -exact $keep $inst] < 0} {odb::dbInst_destroy $inst}}
set n 0
foreach inst $keep {
  $inst setLocation [expr {10000 + ($n % 4)*20000}] [expr {10000 + ($n / 4)*20000}]
  $inst setPlacementStatus PLACED
  incr n
}
set tap [odb::dbInst_create $block [[ord::get_db] findMaster TAP_CANARY] tap_canary]
$tap setLocation 80000 80000
$tap setPlacementStatus FIRM
foreach pin {RAW REF} {[$tap findITerm $pin] connect $clocknet}
# Persisted native rules cover the canary's actual VDD/VSS supply pins too.
global_connect
if {[info exists ::env(OT_PG_CANARY_PRE_SPEF)] && $::env(OT_PG_CANARY_PRE_SPEF) eq "1"} {
  # Successful SPEF load BEFORE installing observers exercises native-state admission.
  read_spef $root/partial.spef
}
# Record PG connectivity at every actual placement estimate, before STA sees it.
rename estimate_parasitics canary_native_estimate
set ::canary_estimates 0
set ::canary_bad 0
proc estimate_parasitics {args} {
  incr ::canary_estimates
  set checked 0; set missing 0
  foreach inst [[ord::get_db_block] getInsts] {
    if {![string match clkbuf_sp_* [$inst getName]] && ![string match ot_lrt_* [$inst getName]]} continue
    foreach mt [[$inst getMaster] getMTerms] {
      if {[$mt getSigType] ni {POWER GROUND}} continue
      incr checked
      set it [$inst findITerm [$mt getName]]
      if {$it eq "NULL" || [$it getNet] eq "NULL"} {incr missing}
    }
  }
  puts "CANARY_ESTIMATE index=$::canary_estimates checked=$checked missing=$missing"
  incr ::canary_bad $missing
  if {$missing && $::env(OT_PG_STRICT) eq "1"} {error CANARY_ESTIMATE_BEFORE_PG}
  return [canary_native_estimate {*}$args]
}
# Calibrated clock-wire model is restored before the final native estimate.
set ::canary_rc_apply 0; set ::canary_rc_restore 0
proc ot_rc_cal_apply {stage} {
  incr ::canary_rc_apply
  set_wire_rc -clock -resistance 2.14161E-02 -capacitance 1.0E-01
  return 1
}
proc ot_rc_cal_restore {} {
  incr ::canary_rc_restore
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
}
set ::env(OT_SPINE_PORT) clk
set ::env(OT_SPINE_ITERS) 2
set ::env(OT_SPINE_TOL_PS) 25
set ::env(OT_SPINE_LEAF_N) 4
set ::env(OT_SPINE_BIN) 20
if {[info exists ::env(OT_PG_CANARY_PAD)] && $::env(OT_PG_CANARY_PAD) eq "1"} {
  set ::env(OT_SPINE_TOL_PS) 1
  set ::env(OT_SPINE_STAGE_PS) 5
  set ::env(OT_SPINE_FINE_PS) 3
}
set ::env(OT_PG_HELPER) $source_root/native_pg_binding.tcl
if {$::env(OT_PG_CANARY_MODE) eq "spine"} {
  source $source_root/clock_spine.tcl
  # Native hook mechanism, not a complete canonical ORFS CTS pipeline.
  ot_clock_spines
} else {
set ::ot_lrt_targets [dict create TAP_CANARY/RAW [dict create ref REF tt 80 ff 80 ss 80]]
source $source_root/landed_raw_tap.tcl
ot_lrt_tap
}
if {$::env(OT_PG_CANARY_MODE) eq "spine" && ($::canary_rc_apply != 1 || $::canary_rc_restore != 1)} {error CANARY_RC_RESTORE}
set count 0; set missing 0
foreach inst [$block getInsts] {
  if {![string match clkbuf_sp_* [$inst getName]] && ![string match ot_lrt_* [$inst getName]]} continue
  incr count
  foreach mt [[$inst getMaster] getMTerms] {
    if {[$mt getSigType] ni {POWER GROUND}} continue
    if {[[$inst findITerm [$mt getName]] getNet] eq "NULL"} {incr missing}
  }
}
if {[info exists ::env(OT_PG_CANARY_DIRTY)] && $::env(OT_PG_CANARY_DIRTY) eq "1"} {
  if {$::env(OT_PG_CANARY_MODE) ne "spine" || $::env(OT_PG_STRICT) ne "1"} {error CANARY_DIRTY_PROFILE}
  set ordinary [odb::dbInst_create $block [[ord::get_db] findMaster BUFx4_ASAP7_75t_R] unrelated_data_buf]
  $ordinary setLocation 90000 90000
  $ordinary setPlacementStatus PLACED
  foreach pin {A Y} {
    set net [odb::dbNet_create $block unrelated_data_$pin]
    $net setSigType SIGNAL
    [$ordinary findITerm $pin] connect $net
  }
  # Actual rule APIs connect the two PG terminals before the explicit binder.
  foreach pin {VDD VSS} role {power ground} {
    set supply [[$tap findITerm $pin] getNet]
    add_global_connection -net [$supply getName] -inst_pattern {^unrelated_data_buf$} -pin_pattern "^${pin}$" -$role
  }
  set dirty_before $::ot_pg_bindings_dirty
  set raw_bound [ot_pg_bind_before_protect [ot_pg_prepare $block] $ordinary]
  if {$dirty_before != 2 || $raw_bound != 0} {error "CANARY_GLOBAL_DIRTY_CAUSE dirty=$dirty_before raw=$raw_bound"}
  set unprotected_clock 0
  foreach inst [$block getInsts] {
    if {[string match clkbuf_sp_* [$inst getName]] && ![$inst isDoNotTouch]} {incr unprotected_clock}
  }
  if {$unprotected_clock} {error CANARY_NEW_CLOCK_BUFFERS_NOT_ZERO}
  set estimate_before $::canary_estimates
  if {[info exists ::env(OT_PG_CANARY_CLK_SOURCE)]} {source $::env(OT_PG_CANARY_CLK_SOURCE)} else {source $source_root/clk_net_protect.tcl}
  ot_protect_clock_tree
  set estimate_delta [expr {$::canary_estimates - $estimate_before}]
  puts "CANARY_GLOBAL_DIRTY before=$dirty_before raw_binder=$raw_bound unprotected_clock=$unprotected_clock estimate_delta=$estimate_delta dirty=$::ot_pg_bindings_dirty"
  if {$estimate_delta != 1 || $::ot_pg_bindings_dirty != 0 || [$ordinary isDoNotTouch]} {error CANARY_GLOBAL_DIRTY_REFRESH}
}
if {$::env(OT_PG_STRICT) eq "1"} {
  set output $root/output_$::env(OT_PG_CANARY_MODE)
  file mkdir $output
  # The guarded native final write must neither repair PG nor leave RC dirty.
  write_db $output/6_final.odb
  puts "CANARY_FINAL_GUARD checked=[ot_pg_assert_all_native $block [ot_pg_prepare $block]] dirty=$::ot_pg_bindings_dirty"
}
puts "CANARY_DONE buffers=$count missing=$missing estimates=$::canary_estimates bad=$::canary_bad rc_apply=$::canary_rc_apply rc_restore=$::canary_rc_restore"
if {$::env(OT_PG_STRICT) eq "1" && $missing} {error CANARY_FINAL_PG}
exit
