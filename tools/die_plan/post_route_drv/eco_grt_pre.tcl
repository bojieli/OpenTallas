# PRD seeds may already carry detailed clock/signal wires. FlexPA rejects any
# attached dbWire (DRT-0415), even though the repair must preserve that wire.
# Detach the original objects only while pin_access runs; restore on success
# and error. The normal PRD clock lock and clock geometry check are unchanged.
if {[info exists ::env(OT_ECO_GRT_PRE_CHAIN)] && $::env(OT_ECO_GRT_PRE_CHAIN) ne ""} {
  if {$::env(OT_ECO_GRT_PRE_CHAIN) eq "/work/eco_grt_pre.tcl"} {
    error "OT_PRD_PIN_ACCESS recursive pre-global-route chain"
  }
  # WF-1 11-14 (COORD friction 6: every late ECO on a kit generated with OT_GRT_NONPORT_HOLD=1 died in ~140 s at global_route
  # 'OT_GRT_NONPORT native session must explicitly select FF'): the setup ECO session is TT / TC and the chained kit
  # PRE_GLOBAL_ROUTE_TCL ends with the nonport hold adapter, which needs an FF native session.  Outside an FF native session (and not
  # a two-mode session, which the adapter supports) the adapter is switched off for the chain; the ECO hold repair has its own scope
  # (OT_HOLD_REPAIR_SCOPE) and sign-off judges FF hold afterwards, as for a kit without the adapter.
  set _wf1_np ""
  if {[info exists ::env(OT_GRT_NONPORT_HOLD)] && ![expr {[info exists ::ot_mm_active] && $::ot_mm_active}] &&
      !([info exists ::env(OT_VCLK_CORNER)] && [string tolower $::env(OT_VCLK_CORNER)] eq "ff")} {
    set _wf1_np $::env(OT_GRT_NONPORT_HOLD)
    set ::env(OT_GRT_NONPORT_HOLD) 0
    puts "OT_ECO_GRT nonport hold adapter skipped in this non-FF ECO session (WF-1)"
  }
  source $::env(OT_ECO_GRT_PRE_CHAIN)
  if {$_wf1_np ne ""} { set ::env(OT_GRT_NONPORT_HOLD) $_wf1_np }
}
if {![llength [info commands ::ot_prd_pin_access_original]]} {
  rename ::pin_access ::ot_prd_pin_access_original
  proc ::pin_access {args} {
    set parked {}
    set block [::ord::get_db_block]
    try {
      foreach net [$block getNets] {
        if {[$net getSigType] in {POWER GROUND}} continue
        set wire [$net getWire]
        if {$wire eq "NULL" || $wire eq ""} continue
        lappend parked [list $net $wire]
        $wire detach
      }
      puts "OT_PRD_PIN_ACCESS parked [llength $parked] existing wires; pin checking unchanged"
      return [uplevel 1 [list ::ot_prd_pin_access_original {*}$args]]
    } finally {
      set bad {}
      set transient 0
      foreach pair $parked {
        lassign $pair net wire
        set current [$net getWire]
        if {$current eq $wire} { continue }
        if {$current ne "NULL" && $current ne ""} {
          # FlexPA may create temporary route objects while assigning access.
          # Restore the original route, not the temporary access geometry.
          incr transient
          ::odb::dbWire_destroy $current
        }
        $wire attach $net
        if {[$net getWire] ne $wire} { lappend bad [$net getName] }
      }
      puts "OT_PRD_PIN_ACCESS restored [llength $parked] original wire objects; removed $transient transient pin-access wires"
      if {[llength $bad]} {
        error "OT_PRD_PIN_ACCESS failed to restore wire objects: [lrange $bad 0 9]"
      }
    }
  }
}
