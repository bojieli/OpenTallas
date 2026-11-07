# GENERATED-COPY of tools/die_plan/pg_connect.tcl (FLOW 2026-10-26): supply binding after every cell-creating step.
# OpenROAD global_connect SKIPS dont_touch instances (ODB-0383). A custom CTS / spine / pad / hold step that creates
# cells after the floorplan PDN and protects them (s8b mscts_core.tcl: 108 ot_ms_* spine buffers, 216 VDD/VSS
# terminals) leaves them without supplies in every later checkpoint, including 6_final.odb. Two procs:
#   ot_pg_connect_all WHERE  - apply the design's own persisted global-connect rules to EVERY instance; protected
#                              instances with an unbound supply terminal are unprotected only around that one
#                              global_connect and re-protected at once (supply pins only: no signal net, cell,
#                              placement or size changes). OT_PG_STRICT=1 kits own binding themselves (no-op here).
#   ot_pg_require_bound WHERE - hard check: every POWER/GROUND MTerm of every instance master has an ITerm on a net
#                              of the same type; else error OT_PG_OPEN (the run fails at this step).
proc ot_pg_open_terms {inst} {
  set open 0
  foreach mt [[$inst getMaster] getMTerms] {
    set role [$mt getSigType]
    if {$role ni {POWER GROUND}} continue
    set term [$inst findITerm [$mt getName]]
    if {$term eq "NULL" || $term eq ""} { incr open; continue }
    set net [$term getNet]
    if {$net eq "NULL" || $net eq "" || [$net getSigType] ne $role} { incr open }
  }
  return $open
}
proc ot_pg_connect_all {where} {
  set block [ord::get_db_block]
  if {$block eq "NULL" || $block eq ""} { error "OT_PG_CONNECT $where: no block" }
  set rules [llength [$block getGlobalConnects]]
  if {!$rules} { error "OT_PG_CONNECT $where: design has no global-connect rules (PDN step missing)" }
  if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
    puts "OT_PG_CONNECT $where strict=1 skipped (native_pg_binding owns binding)"; return 0
  }
  set prot {}
  foreach inst [$block getInsts] {
    if {[$inst isDoNotTouch] && [ot_pg_open_terms $inst]} { lappend prot $inst }
  }
  foreach inst $prot { $inst setDoNotTouch 0 }
  set rc [catch {global_connect} err]
  foreach inst $prot { $inst setDoNotTouch 1 }
  if {$rc} { error "OT_PG_CONNECT $where: global_connect failed: $err" }
  puts "OT_PG_CONNECT $where rules=$rules protected_rebound=[llength $prot]"
  return [llength $prot]
}
proc ot_pg_require_bound {where} {
  set block [ord::get_db_block]
  set n 0; set terms 0; set first ""
  foreach inst [$block getInsts] {
    foreach mt [[$inst getMaster] getMTerms] { if {[$mt getSigType] in {POWER GROUND}} { incr terms } }
    set o [ot_pg_open_terms $inst]
    if {$o} {
      incr n $o
      if {$first eq ""} { set first "[$inst getName]([[$inst getMaster] getName] dont_touch=[$inst isDoNotTouch])" }
    }
  }
  if {$n} { error "OT_PG_OPEN $where open_pg_terms=$n of $terms first=$first" }
  puts "OT_PG_BOUND $where pg_terms=$terms open=0"
  return $terms
}
